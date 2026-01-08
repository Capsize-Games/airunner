"""Runtime compilation and execution of generated LangGraph code.

This module provides functionality to compile and execute LangGraph workflows
at runtime, enabling dynamic agent creation from visual graphs.
"""

from __future__ import annotations

import ast
import builtins
from types import ModuleType
from typing import Any, Dict, Optional
from pathlib import Path

from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger
from airunner.components.llm.core.code_sandbox import create_safe_builtins


logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


class LangGraphRuntime:
    """Compile and execute generated LangGraph code at runtime.

    This class allows dynamically generated Python code to be compiled
    and executed in an isolated namespace, with proper error handling
    and logging.
    """

    def __init__(self):
        """Initialize the runtime."""
        self.compiled_modules: Dict[str, ModuleType] = {}

    _ALLOWED_IMPORT_PREFIXES: tuple[str, ...] = (
        "typing",
        "langgraph",
        "logging",
    )

    _FORBIDDEN_CALLS: set[str] = {
        "exec",
        "eval",
        "compile",
        "open",
        "__import__",
        "input",
        "breakpoint",
        "globals",
        "locals",
        "vars",
        "dir",
        "getattr",
        "setattr",
        "delattr",
    }

    _FORBIDDEN_NAMES: set[str] = {
        "__builtins__",
        "builtins",
    }

    def _safe_import(self, name: str, globals=None, locals=None, fromlist=(), level: int = 0):
        # Disallow relative imports.
        if level and level != 0:
            raise ImportError("Relative imports are not allowed")

        normalized = (name or "").strip()
        if not normalized:
            raise ImportError("Empty import is not allowed")

        allowed = any(
            normalized == p or normalized.startswith(p + ".")
            for p in self._ALLOWED_IMPORT_PREFIXES
        )
        if not allowed:
            raise ImportError(f"Import not allowed: {normalized}")

        return builtins.__import__(name, globals, locals, fromlist, level)

    def _validate_security(self, code: str, module_name: str) -> None:
        """Validate code for dangerous constructs.

        Note: LangGraph generated code needs imports; we allow only a small
        allowlist of import prefixes and block common RCE primitives.
        """
        try:
            tree = ast.parse(code)
        except SyntaxError:
            # Let the normal compile path raise a friendlier error.
            return

        errors: list[str] = []

        def called_symbol_name(node: ast.AST) -> Optional[str]:
            # Only treat direct builtin-style calls as dangerous. Attribute calls
            # like workflow.compile() are common and should not be flagged.
            if isinstance(node, ast.Name):
                return node.id
            if isinstance(node, ast.Subscript):
                if (
                    isinstance(node.value, ast.Name)
                    and node.value.id in {"__builtins__", "builtins"}
                ):
                    sl = node.slice
                    if isinstance(sl, ast.Constant) and isinstance(sl.value, str):
                        return sl.value
            return None

        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in self._FORBIDDEN_NAMES:
                errors.append(f"Access to name '{node.id}' is not allowed")

            if isinstance(node, (ast.Import, ast.ImportFrom)):
                modules: list[str] = []
                if isinstance(node, ast.Import):
                    modules = [a.name for a in node.names]
                else:
                    modules = [node.module] if node.module else []

                for mod in modules:
                    if not mod:
                        errors.append("Empty import is not allowed")
                        continue
                    allowed = any(
                        mod == p or mod.startswith(p + ".")
                        for p in self._ALLOWED_IMPORT_PREFIXES
                    )
                    if not allowed:
                        errors.append(f"Import not allowed: {mod}")

            if isinstance(node, ast.Call):
                called = called_symbol_name(node.func)
                if called in self._FORBIDDEN_CALLS:
                    errors.append(f"Function '{called}' is not allowed")

                # Block string-based dunder access attempts.
                if called in {"getattr", "setattr", "delattr"} and len(node.args) >= 2:
                    arg = node.args[1]
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        v = arg.value
                        if v.startswith("_") or "__" in v:
                            errors.append(
                                f"String-based private/dunder attribute access is not allowed: {v!r}"
                            )

            if isinstance(node, ast.Attribute):
                # Disallow private/dunder attribute access.
                if node.attr.startswith("_") or "__" in node.attr:
                    errors.append(f"Access to attribute '{node.attr}' is not allowed")

        if errors:
            msg = "; ".join(sorted(set(errors)))
            raise RuntimeError(
                f"Rejected generated module '{module_name}' for unsafe code: {msg}"
            )

    def compile_and_load(
        self,
        code: str,
        module_name: str = "agent_workflow",
        validate: bool = True,
    ) -> ModuleType:
        """Compile Python code and load as module.

        Args:
            code: Python code string
            module_name: Name for the module
            validate: Whether to validate syntax before execution

        Returns:
            Compiled module

        Raises:
            SyntaxError: If code has syntax errors
            RuntimeError: If compilation fails
        """
        logger.info(f"Compiling module: {module_name}")

        # Always perform a lightweight security validation pass.
        self._validate_security(code, module_name)

        # Validate syntax first if requested
        if validate:
            try:
                compile(code, f"<{module_name}>", "exec")
            except SyntaxError as e:
                logger.error(f"Syntax error in generated code: {e}")
                raise

        # Create module
        module = ModuleType(module_name)
        module.__file__ = f"<generated:{module_name}>"
        safe_builtins = create_safe_builtins()
        # Required for defining classes (e.g., TypedDict state classes).
        safe_builtins["__build_class__"] = builtins.__build_class__
        safe_builtins["object"] = builtins.object
        safe_builtins["type"] = builtins.type
        safe_builtins["super"] = builtins.super
        safe_builtins["__import__"] = self._safe_import
        module.__dict__["__builtins__"] = safe_builtins

        # Compile and exec
        try:
            compiled = compile(code, module.__file__, "exec")
            exec(compiled, module.__dict__)
        except Exception as e:
            logger.error(
                f"Failed to compile module '{module_name}': {e}",
                exc_info=True,
            )
            raise RuntimeError(f"Module compilation failed: {str(e)}") from e

        # Cache
        self.compiled_modules[module_name] = module

        logger.info(f"Module '{module_name}' compiled successfully")
        return module

    def load_from_file(self, file_path: Path) -> ModuleType:
        """Load and compile code from a file.

        Args:
            file_path: Path to Python file

        Returns:
            Compiled module

        Raises:
            FileNotFoundError: If file doesn't exist
            RuntimeError: If compilation fails
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        logger.info(f"Loading code from: {file_path}")
        code = file_path.read_text()

        module_name = file_path.stem
        return self.compile_and_load(code, module_name)

    def execute_workflow(
        self,
        module: ModuleType,
        initial_state: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Execute the compiled workflow.

        Args:
            module: Compiled module
            initial_state: Initial state dict
            config: Optional LangGraph config (for checkpointing, etc.)

        Returns:
            Final state

        Raises:
            RuntimeError: If module doesn't have required attributes
            Exception: If workflow execution fails
        """
        if not hasattr(module, "app"):
            raise RuntimeError(
                "Module must have 'app' attribute (compiled workflow)"
            )

        logger.info("Executing workflow")

        try:
            if config:
                result = module.app.invoke(initial_state, config)
            else:
                result = module.app.invoke(initial_state)

            logger.info("Workflow execution completed")
            return result

        except Exception as e:
            logger.error(f"Workflow execution error: {e}", exc_info=True)
            raise

    def execute_from_code(
        self,
        code: str,
        initial_state: Dict[str, Any],
        module_name: str = "temp_workflow",
        config: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Compile and execute code in one step.

        Args:
            code: Python code string
            initial_state: Initial state dict
            module_name: Name for the module
            config: Optional LangGraph config

        Returns:
            Final state
        """
        module = self.compile_and_load(code, module_name)
        return self.execute_workflow(module, initial_state, config)

    def get_module(self, module_name: str) -> Optional[ModuleType]:
        """Get a cached compiled module.

        Args:
            module_name: Name of the module

        Returns:
            Module if found, None otherwise
        """
        return self.compiled_modules.get(module_name)

    def clear_cache(self) -> None:
        """Clear all cached compiled modules."""
        self.compiled_modules.clear()
        logger.info("Cleared module cache")

    def validate_code(self, code: str) -> tuple[bool, Optional[str]]:
        """Validate Python code without executing it.

        Args:
            code: Python code to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            compile(code, "<validation>", "exec")
            return True, None
        except SyntaxError as e:
            error_msg = f"Line {e.lineno}: {e.msg}"
            return False, error_msg
        except Exception as e:
            return False, str(e)

    def inspect_module(self, module: ModuleType) -> Dict[str, Any]:
        """Inspect a compiled module.

        Args:
            module: Compiled module

        Returns:
            Dict with module information
        """
        info = {
            "name": module.__name__,
            "file": getattr(module, "__file__", None),
            "has_app": hasattr(module, "app"),
            "functions": [],
            "classes": [],
        }

        for name, obj in module.__dict__.items():
            if name.startswith("_"):
                continue

            if callable(obj):
                info["functions"].append(name)
            elif isinstance(obj, type):
                info["classes"].append(name)

        return info


class StreamingExecutor:
    """Execute workflows with streaming support.

    This class allows workflows to be executed with step-by-step
    visibility, useful for debugging and monitoring.
    """

    def __init__(self, runtime: LangGraphRuntime):
        """Initialize streaming executor.

        Args:
            runtime: LangGraphRuntime instance
        """
        self.runtime = runtime

    def execute_with_streaming(
        self,
        module: ModuleType,
        initial_state: Dict[str, Any],
        callback: Optional[callable] = None,
    ) -> Any:
        """Execute workflow with step-by-step callbacks.

        Args:
            module: Compiled module
            initial_state: Initial state
            callback: Optional callback function called after each step
                     Signature: callback(node_name: str, state: Dict)

        Returns:
            Final state
        """
        if not hasattr(module, "app"):
            raise RuntimeError("Module must have 'app' attribute")

        logger.info("Executing workflow with streaming")

        try:
            # Use LangGraph's stream method if available
            if hasattr(module.app, "stream"):
                for chunk in module.app.stream(initial_state):
                    if callback:
                        callback(chunk)
                return chunk
            else:
                # Fallback to regular execution
                result = module.app.invoke(initial_state)
                if callback:
                    callback(result)
                return result

        except Exception as e:
            logger.error(f"Streaming execution error: {e}", exc_info=True)
            raise
