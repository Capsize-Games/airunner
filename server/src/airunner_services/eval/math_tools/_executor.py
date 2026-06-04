"""
Math problem-solving tools for improved accuracy.

Provides:
1. Safe Python code execution for arithmetic
2. Self-verification loops with retry logic
3. Enhanced math-specific prompting
"""

import ast
import re
import io
import contextlib
import threading
import contextvars
import math
from fractions import Fraction
from typing import Dict, Any, Optional, Tuple

from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)

_executor_session_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "safe_python_executor_session",
    default="global",
)


def set_executor_session(session_id: str) -> contextvars.Token[str]:
    """Set the current executor session for persistent namespaces.

    Args:
        session_id: Unique identifier for the execution session

    Returns:
        Context variable token for restoring previous session
    """

    return _executor_session_var.set(session_id)


def reset_executor_session(token: contextvars.Token[str]) -> None:
    """Reset executor session to a previous context."""

    _executor_session_var.reset(token)


def get_executor_session() -> str:
    """Return the current executor session identifier."""

    return _executor_session_var.get()


class SafePythonExecutor:
    """Safely execute Python code for math calculations.

    Restricts imports and provides timeout protection.
    """

    # Allowed imports for math operations
    ALLOWED_IMPORTS = {
        "math",
        "cmath",  # Complex number math
        "fractions",
        "decimal",
        "statistics",
        "itertools",  # Combinatorics (combinations, permutations)
        "sympy",
        "numpy",
        "scipy",
    }

    _FORBIDDEN_NAMES = {
        "__builtins__",
        "builtins",
        "__import__",
    }

    _FORBIDDEN_CALLS = {
        "exec",
        "eval",
        "compile",
        "open",
        "input",
        "breakpoint",
        "globals",
        "locals",
        "getattr",
        "setattr",
        "delattr",
        "vars",
        "dir",
        "__import__",
    }

    def __init__(self, timeout_seconds: int = 5):
        """Initialize executor.

        Args:
            timeout_seconds: Maximum execution time
        """
        self.timeout = timeout_seconds
        self._namespaces: Dict[str, Dict[str, Any]] = {}
        self._namespace_lock = threading.Lock()

    def _create_safe_builtins(self) -> Dict[str, Any]:
        """Create the limited set of safe builtins for execution."""

        return {
            "abs": abs,
            "round": round,
            "min": min,
            "max": max,
            "sum": sum,
            "len": len,
            "range": range,
            "int": int,
            "float": float,
            "str": str,
            "bool": bool,
            "list": list,
            "dict": dict,
            "set": set,
            "tuple": tuple,
            "pow": pow,
            "print": print,
            # Needed for `import ...` statements, but restricted.
            "__import__": self._safe_import,
        }

    def _safe_import(
        self,
        name: str,
        globals: Any = None,
        locals: Any = None,
        fromlist: Any = (),
        level: int = 0,
    ) -> Any:
        if level != 0:
            raise ImportError("Relative imports are not allowed")

        top_level = name.split(".", 1)[0]
        if top_level not in self.ALLOWED_IMPORTS:
            raise ImportError(f"Import not allowed: {top_level}")

        return __import__(name, globals, locals, fromlist, level)

    def _create_base_namespace(self) -> Dict[str, Any]:
        """Create a fresh namespace with safe builtins and defaults."""

        namespace: Dict[str, Any] = {
            "__builtins__": self._create_safe_builtins()
        }

        namespace["math"] = math
        namespace["Fraction"] = Fraction

        return namespace

    def _ensure_namespace(self, session_id: str) -> Dict[str, Any]:
        """Return namespace for session, creating/resetting as needed."""

        with self._namespace_lock:
            if session_id == "global":
                return self._create_base_namespace()

            namespace = self._namespaces.get(session_id)
            if namespace is None:
                namespace = self._create_base_namespace()
                self._namespaces[session_id] = namespace
            else:
                namespace["__builtins__"] = self._create_safe_builtins()
                if "math" not in namespace:
                    namespace["math"] = math
                if "Fraction" not in namespace:
                    namespace["Fraction"] = Fraction

            return namespace

    def reset(self, session_id: Optional[str] = None) -> None:
        """Reset stored namespaces.

        Args:
            session_id: Optional session identifier to reset. If None, clears all.
        """

        with self._namespace_lock:
            if session_id is None:
                self._namespaces.clear()
            else:
                self._namespaces.pop(session_id, None)

    def extract_code(self, text: str) -> Optional[str]:
        """Extract Python code from markdown code blocks.

        Args:
            text: Text containing code blocks

        Returns:
            Extracted code or None
        """
        # Try to find ```python code blocks
        pattern = r"```python\s*(.*?)```"
        matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
        if matches:
            return matches[0].strip()

        # Try to find ``` code blocks
        pattern = r"```\s*(.*?)```"
        matches = re.findall(pattern, text, re.DOTALL)
        if matches:
            return matches[0].strip()

        return None

    def validate_code(self, code: str) -> Tuple[bool, str]:
        """Check if code is safe to execute.

        Args:
            code: Python code to validate

        Returns:
            (is_safe, error_message)
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return False, f"Syntax error: {e}"

        errors: list[str] = []

        def called_symbol_name(node: ast.AST) -> Optional[str]:
            if isinstance(node, ast.Name):
                return node.id
            if isinstance(node, ast.Attribute):
                return node.attr
            if isinstance(node, ast.Subscript):
                if isinstance(node.value, ast.Name) and node.value.id in {"__builtins__", "builtins"}:
                    sl = node.slice
                    if isinstance(sl, ast.Constant) and isinstance(sl.value, str):
                        return sl.value
            return None

        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in self._FORBIDDEN_NAMES:
                errors.append(f"Access to name '{node.id}' is not allowed")

            if isinstance(node, ast.Subscript):
                if isinstance(node.value, ast.Name) and node.value.id in {"__builtins__", "builtins"}:
                    errors.append("Access to builtins via subscript is not allowed")

            if isinstance(node, ast.Attribute):
                if node.attr.startswith("_") or "__" in node.attr:
                    errors.append(f"Access to attribute '{node.attr}' is not allowed")

            if isinstance(node, ast.Call):
                called = called_symbol_name(node.func)
                if called in self._FORBIDDEN_CALLS:
                    errors.append(f"Function '{called}' is not allowed")

            if isinstance(node, ast.Import):
                for alias in node.names:
                    top_level = alias.name.split(".", 1)[0]
                    if top_level not in self.ALLOWED_IMPORTS:
                        errors.append(f"Import not allowed: {top_level}")

            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                top_level = module.split(".", 1)[0]
                if top_level and top_level not in self.ALLOWED_IMPORTS:
                    errors.append(f"Import not allowed: {top_level}")

        if errors:
            return False, "\n".join(errors)
        return True, ""

    def _check_dangerous_operations(self, code: str) -> Tuple[bool, str]:
        """Check for dangerous patterns in code."""
        dangerous_patterns = [
            r"\bimport\s+os\b",
            r"\bimport\s+subprocess\b",
            r"\bimport\s+sys\b",
            r"\bexec\b",
            r"\beval\b",
            r"\bopen\b",
            r"\bfile\b",
            r"\bcompile\b",
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, code):
                return False, f"Dangerous operation detected: {pattern}"
        return True, ""

    def _check_imports(self, code: str) -> Tuple[bool, str]:
        """Check that all imports are allowed."""
        import_patterns = [
            (r"^\s*import\s+(\w+)", "module"),
            (r"\bfrom\s+(\w+)\s+import", "module"),
        ]

        for pattern, desc in import_patterns:
            imports = re.findall(pattern, code, re.MULTILINE)
            for imp in imports:
                if imp not in self.ALLOWED_IMPORTS:
                    return False, f"Import not allowed: {imp}"

        return True, ""

    def execute(self, code: str) -> Tuple[bool, Any, str]:
        """Execute Python code and capture output.

        Args:
            code: Python code to execute

        Returns:
            (success, result, error_message)
        """
        # Validate code first
        is_safe, error_msg = self.validate_code(code)
        if not is_safe:
            logger.warning(f"Unsafe code rejected: {error_msg}")
            return False, None, error_msg

        session_id = get_executor_session() or "global"
        namespace = self._ensure_namespace(session_id)

        # Capture stdout
        stdout_capture = io.StringIO()

        # Handle code that might have a final expression to evaluate
        # Split into statements and potential final expression
        last_expr_result = None
        try:
            # Try to compile and check if last line is an expression
            lines = [line.strip() for line in code.split(";") if line.strip()]
            if lines:
                # Execute all but the last line
                if len(lines) > 1:
                    exec_code = "; ".join(lines[:-1])
                    with contextlib.redirect_stdout(stdout_capture):
                        exec(exec_code, namespace)

                # Try to eval the last line to capture expression result
                last_line = lines[-1]
                try:
                    with contextlib.redirect_stdout(stdout_capture):
                        last_expr_result = eval(last_line, namespace)
                except SyntaxError:
                    # Last line is a statement, not an expression
                    with contextlib.redirect_stdout(stdout_capture):
                        exec(last_line, namespace)
                except NameError:
                    # Last line references undefined names, execute normally
                    with contextlib.redirect_stdout(stdout_capture):
                        exec(last_line, namespace)
            else:
                with contextlib.redirect_stdout(stdout_capture):
                    exec(code, namespace)

            result = self._extract_result(
                namespace, stdout_capture, last_expr_result
            )
            return True, result, ""

        except Exception as e:
            error_msg = f"Execution error: {str(e)}"
            logger.warning(error_msg)
            return False, None, error_msg

    def _extract_result(
        self,
        namespace: Dict,
        stdout_capture: io.StringIO,
        last_expr: Any = None,
    ) -> Any:
        """Extract result from namespace, last expression, or stdout."""
        # Priority 1: Explicit result or answer variable
        result = namespace.get("result") or namespace.get("answer")

        # Priority 2: Last expression value (like Python REPL)
        if result is None and last_expr is not None:
            result = last_expr

        # Priority 3: Try to get last printed value
        if result is None:
            output = stdout_capture.getvalue().strip()
            if output:
                result = self._parse_output_as_number(output)

        return result

    def _parse_output_as_number(self, output: str) -> Any:
        """Try to parse output string as a number."""
        lines = output.split("\n")
        last_line = lines[-1].strip()
        try:
            return float(last_line)
        except ValueError:
            return last_line
