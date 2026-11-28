"""Restricted Python execution for the built-in math LLM tools.

This is production code, not benchmark tooling: it is imported by
services/src/airunner_services/llm/tools/math_tools.py to back the
sympy_compute/numpy_compute/python_compute tools an LLM agent can
call. It previously lived under airunner_services.eval (issue #2189),
which made a production code-execution sandbox look like test-support
code and blocked eval/ from ever being extracted into its own
repository, since production code cannot depend on a benchmark
harness.

This module is a peer of code_sandbox.py in this same package: that
one backs arbitrary custom tools with a much smaller restricted-
builtins set and states plainly that restricted builtins alone are
not a security boundary. The same caveat applies here. See #2142
(T01) and #2145 (T02) for the actual isolation-boundary design; this
module is deliberately not changed by that move beyond its location.

Confinement (issue #2491): executing here never means ``exec`` in
this process. After the parent-side AST validation below passes, the
code runs in ``math_worker.py``, a fresh interpreter that applies
resource limits (address space, CPU) and is killed on
the wall-clock timeout, so even a tight C-level loop cannot hang or
exhaust the service. No process-count limit is set: validated math
code has no spawn primitive, while BLAS thread pools need room.
Session namespaces are rebuilt in the child by
replaying previously accepted snippets; only JSON-safe values cross
back, never pickles.
"""

import ast
import json
import os
import re
import subprocess
import sys
import threading
import contextvars
import math
from fractions import Fraction
from typing import Dict, Any, List, Optional, Tuple

from airunner_common.settings import AIRUNNER_LOG_LEVEL
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
        "hasattr",
        # ``str.format``/``format_map`` can walk an object graph from a
        # format string (``"{0.__class__}".format(obj)``), so both the
        # builtin and the method forms are forbidden. The ``Call``
        # check in ``validate_code`` matches method calls by attribute
        # name, so these entries cover ``x.format(...)`` too.
        "format",
        "format_map",
        "__import__",
    }

    #: Dotted imports are rejected: only exact top-level module names
    #: may be imported, so ``import numpy.linalg`` cannot smuggle a
    #: submodule with a wider surface than the allow-listed top level.
    _ALLOWED_DOTTED_IMPORTS = frozenset()

    #: Namespace keys user code may never overwrite or inject. They are
    #: snapshotted before each run and restored afterwards.
    _PROTECTED_KEYS = ("__builtins__", "math", "Fraction")

    #: Cap on replayed session history per named session.
    _MAX_HISTORY_ENTRIES = 50
    _MAX_HISTORY_CHARS = 200000

    def __init__(self, timeout_seconds: int = 5):
        """Initialize executor.

        Args:
            timeout_seconds: Maximum execution time
        """
        try:
            timeout = int(timeout_seconds)
        except (TypeError, ValueError):
            timeout = 5
        self.timeout = timeout if timeout > 0 else 5
        self._namespaces: Dict[str, Dict[str, Any]] = {}
        self._history: Dict[str, List[str]] = {}
        self._namespace_lock = threading.Lock()
        #: PID of the worker spawned by the most recent execute() that
        #: reached spawn (None when validation rejected the code or
        #: the spawn itself failed). Introspection aid proving the
        #: code ran off-process.
        self.last_worker_pid: Optional[int] = None

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

    @classmethod
    def _dotted_import_allowed(cls, dotted: str) -> bool:
        """Return whether one dotted module path may be imported."""
        if "." not in dotted:
            return dotted in cls.ALLOWED_IMPORTS
        return dotted in cls._ALLOWED_DOTTED_IMPORTS

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

        if not self._dotted_import_allowed(name):
            top_level = name.split(".", 1)[0]
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
        """Reset stored namespaces and replay histories.

        Args:
            session_id: Optional session identifier to reset. If None, clears all.
        """

        with self._namespace_lock:
            if session_id is None:
                self._namespaces.clear()
                self._history.clear()
            else:
                self._namespaces.pop(session_id, None)
                self._history.pop(session_id, None)

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
                    if not self._dotted_import_allowed(alias.name):
                        top_level = alias.name.split(".", 1)[0]
                        errors.append(f"Import not allowed: {top_level}")

            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module and not self._dotted_import_allowed(module):
                    top_level = module.split(".", 1)[0]
                    errors.append(f"Import not allowed: {top_level}")

        if errors:
            return False, "\n".join(errors)
        return True, ""

    @staticmethod
    def _worker_path() -> str:
        """Return the path of the confined worker script."""
        here = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(here, "math_worker.py")

    def _replay_history(self, session_id: str) -> List[str]:
        """Return the accepted snippets to replay for one session."""
        if session_id == "global":
            return []
        with self._namespace_lock:
            return list(self._history.get(session_id, []))

    def _record_success(
        self, session_id: str, code: str, bindings: Any
    ) -> None:
        """Append one accepted snippet and merge its safe bindings.

        ``bindings`` crosses the worker boundary, so it is untrusted:
        protected keys and dunder names are dropped even though the
        worker already filters them.
        """
        if session_id == "global":
            return
        if not isinstance(bindings, dict):
            bindings = {}
        with self._namespace_lock:
            stored = self._namespaces.get(session_id)
            if stored is None:
                stored = self._create_base_namespace()
                self._namespaces[session_id] = stored
            for key, value in bindings.items():
                if not isinstance(key, str):
                    continue
                if key in self._PROTECTED_KEYS:
                    continue
                if key.startswith("__") and key.endswith("__"):
                    continue
                stored[key] = value
            history = self._history.setdefault(session_id, [])
            history.append(code)
            overflow = len(history) - self._MAX_HISTORY_ENTRIES
            if overflow > 0:
                del history[:overflow]
            while (
                sum(len(item) for item in history)
                > self._MAX_HISTORY_CHARS
            ):
                history.pop(0)

    def _run_in_worker(
        self, history: List[str], code: str
    ) -> Tuple[bool, Any, Any]:
        """Spawn the confined worker and collect its single reply."""
        request = {
            "history": history,
            "code": code,
            "timeout_ms": self.timeout * 1000,
        }
        try:
            payload = json.dumps(request).encode("utf-8")
        except (TypeError, ValueError) as exc:
            error_msg = f"Execution error: cannot encode request: {exc}"
            logger.warning(error_msg)
            return False, error_msg, None
        try:
            proc = subprocess.Popen(
                [sys.executable, self._worker_path()],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                close_fds=True,
            )
        except OSError as exc:
            error_msg = f"Execution error: math worker spawn failed: {exc}"
            logger.warning(error_msg)
            return False, error_msg, None
        self.last_worker_pid = proc.pid
        try:
            stdout, stderr = proc.communicate(
                payload, timeout=self.timeout
            )
        except subprocess.TimeoutExpired:
            proc.kill()
            try:
                proc.wait(timeout=5)
            except (OSError, subprocess.TimeoutExpired):
                pass
            error_msg = (
                f"Execution timed out after {self.timeout} seconds"
            )
            logger.warning(error_msg)
            return False, error_msg, None
        if proc.returncode != 0:
            tail = stderr.decode("utf-8", "replace")[-500:]
            error_msg = (
                "Execution error: math worker exited with status "
                f"{proc.returncode}: {tail}"
            )
            logger.warning(error_msg)
            return False, error_msg, None
        if stderr:
            logger.debug(
                "math worker stderr: %s",
                stderr.decode("utf-8", "replace")[:2000],
            )
        try:
            response = json.loads(stdout.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            error_msg = (
                f"Execution error: math worker returned an "
                f"invalid response: {exc}"
            )
            logger.warning(error_msg)
            return False, error_msg, None
        if not isinstance(response, dict) or not response.get("ok"):
            detail = (
                response.get("error")
                if isinstance(response, dict)
                else None
            )
            error_msg = (
                str(detail)
                if detail
                else "Execution error: unknown worker failure"
            )
            logger.warning(error_msg)
            return False, error_msg, None
        if response.get("pid") != self.last_worker_pid:
            logger.debug(
                "math worker pid mismatch (expected %s, reported %s)",
                self.last_worker_pid,
                response.get("pid"),
            )
        return True, response.get("result"), response

    def execute(self, code: str) -> Tuple[bool, Any, str]:
        """Execute Python code in a confined worker and capture output.

        The code is compiled once and executed with ``exec`` only, in
        the worker process: there is no ``eval`` sink for a trailing
        expression and this process never execs the code. Callers
        (``sympy_compute``/``numpy_compute``/``python_compute``) must
        store the final value in a ``result`` (or ``answer``) variable
        or print it. The worker applies resource limits and the parent
        kills it on ``self.timeout`` seconds, so an expired run
        reports a timeout instead of hanging the caller.

        Args:
            code: Python code to execute

        Returns:
            (success, result, error_message)
        """
        # Validate code first (no worker is spawned for unsafe code).
        is_safe, error_msg = self.validate_code(code)
        if not is_safe:
            logger.warning("Unsafe code rejected: %s", error_msg)
            return False, None, error_msg

        try:
            compile(code, "<math_executor>", "exec")
        except (SyntaxError, ValueError) as exc:
            error_msg = f"Syntax error: {exc}"
            logger.warning("Code rejected: %s", error_msg)
            return False, None, error_msg

        session_id = get_executor_session() or "global"
        history = self._replay_history(session_id)
        if (
            len(history) >= self._MAX_HISTORY_ENTRIES
            or sum(len(item) for item in history)
            > self._MAX_HISTORY_CHARS
        ):
            error_msg = (
                "Execution error: session history limit exceeded; "
                "reset the session to continue"
            )
            logger.warning(error_msg)
            return False, None, error_msg

        ok, result, response = self._run_in_worker(history, code)
        if not ok:
            assert isinstance(result, str) or result is None
            return False, None, result  # type: ignore[return-value]
        assert isinstance(response, dict)
        self._record_success(session_id, code, response.get("bindings"))
        return True, result, ""

    def _parse_output_as_number(self, output: str) -> Any:
        """Try to parse output string as a number.

        Kept for backward compatibility; the confined worker performs
        result extraction and carries its own copy.
        """
        lines = output.split("\n")
        last_line = lines[-1].strip()
        try:
            return float(last_line)
        except ValueError:
            return last_line

