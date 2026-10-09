"""Worker-side confinement primitives (issue #2145, T01 section 3).

Structural pre-exec guard, capability-scoped file helpers, resource
limits and capped stdout capture for the spawned custom-tool worker.
Stdlib-only: the child loads this file by path so it never imports the
service package (whose ``__init__`` chains pull the agent stack).
"""

from __future__ import annotations

import ast
import io
import os
from typing import Any, Callable

#: Last-mile mirror of the admission validator's denylists in
#: ``database/models/llm_tool.py``. The worker is stdlib-only so it
#: cannot import that module; the parity test in ``test_release_t02``
#: pins the shared bypass classes against drift.
_GUARD_DENIED_CALLS = frozenset(
    {
        "exec",
        "eval",
        "compile",
        "__import__",
        "getattr",
        "setattr",
        "delattr",
        "globals",
        "locals",
        "vars",
        "open",
        "input",
        "breakpoint",
        "help",
        "memoryview",
    }
)
_GUARD_DENIED_ROOTS = frozenset(
    {
        "os",
        "sys",
        "subprocess",
        "shutil",
        "socket",
        "ctypes",
        "pathlib",
        "importlib",
    }
)


class CapabilityDenied(Exception):
    """Raised when tool code reaches past its granted boundary."""


def _attribute_root(node: ast.Attribute) -> str | None:
    """Return the base name of one attribute chain, if any."""
    current: ast.AST = node
    while isinstance(current, ast.Attribute):
        current = current.value
    if isinstance(current, ast.Name):
        return current.id
    return None


def _guard_node(node: ast.AST) -> str | None:
    """Reject one hostile AST node, or return None when clear."""
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        return "import statements are not allowed"
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        if node.func.id in _GUARD_DENIED_CALLS:
            return f"call to '{node.func.id}' is not allowed"
    if isinstance(node, ast.Attribute):
        if node.attr.startswith("__") and node.attr.endswith("__"):
            return f"attribute access to '{node.attr}' is not allowed"
        root = _attribute_root(node)
        if root in _GUARD_DENIED_ROOTS:
            return f"access through '{root}' is not allowed"
    if isinstance(node, ast.Name):
        if node.id in {"__builtins__", "__loader__"}:
            return f"use of '{node.id}' is not allowed"
    return None


def guard_tool_code(code: str) -> str | None:
    """Reject hostile constructs; None means structurally clear."""
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError) as exc:
        return f"syntax error: {exc}"
    for node in ast.walk(tree):
        reason = _guard_node(node)
        if reason is not None:
            return reason
    return None


def resolve_grant_path(path: str, roots: tuple[str, ...]) -> str:
    """Canonicalize one path and require it under a granted root."""
    if not isinstance(path, str) or not path:
        raise CapabilityDenied("file path must be a nonempty string")
    resolved = os.path.realpath(path)
    for root in roots:
        if resolved == root or resolved.startswith(root + os.sep):
            return resolved
    raise CapabilityDenied("path is outside the granted roots")


def make_granted_read(roots: tuple[str, ...]) -> Callable[[str], bytes]:
    """Build the ``granted_read`` helper scoped to ``roots``."""

    def granted_read(path: str) -> bytes:
        """Read bytes from one path inside the granted roots."""
        resolved = resolve_grant_path(path, roots)
        with open(resolved, "rb") as handle:
            return handle.read()

    return granted_read


def make_granted_write(roots: tuple[str, ...]) -> Callable[[str, Any], int]:
    """Build the ``granted_write`` helper scoped to ``roots``."""

    def granted_write(path: str, data: Any) -> int:
        """Write bytes (or str) to one path inside the grants."""
        resolved = resolve_grant_path(path, roots)
        if isinstance(data, str):
            data = data.encode("utf-8")
        if not isinstance(data, bytes):
            raise CapabilityDenied("granted_write needs bytes or str")
        with open(resolved, "wb") as handle:
            return handle.write(data)

    return granted_write


class _WorkerTool:
    """Minimal ``@tool`` marker so the worker finds the entry point."""

    def __init__(self, func: Callable[..., Any]) -> None:
        self.func = func
        self.name = getattr(func, "__name__", "custom_tool")
        self.description = (getattr(func, "__doc__", "") or "").strip()
        self.__name__ = self.name

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self.func(*args, **kwargs)


def _decorate_tool(kwargs: dict[str, Any]) -> Callable[[Any], Any]:
    """Build the decorator applying name/description overrides."""

    def wrap(func: Any) -> _WorkerTool:
        wrapped = _WorkerTool(func)
        if kwargs.get("name"):
            wrapped.name = str(kwargs["name"])
            wrapped.__name__ = wrapped.name
        if kwargs.get("description"):
            wrapped.description = str(kwargs["description"])
        return wrapped

    return wrap


def tool(first: Any = None, **kwargs: Any) -> Any:
    """Accept ``@tool`` bare or ``@tool(...)`` like langchain."""
    if isinstance(first, str):
        kwargs.setdefault("name", first)
        return _decorate_tool(kwargs)
    if callable(first):
        return _decorate_tool(kwargs)(first)
    return _decorate_tool(kwargs)


def find_tool(namespace: dict[str, Any], want_name: str) -> Any:
    """Return the ``@tool`` entry point, preferring ``want_name``."""
    found = [v for v in namespace.values() if isinstance(v, _WorkerTool)]
    if not found:
        raise LookupError("no @tool function found")
    for candidate in found:
        if candidate.name == want_name:
            return candidate
    return found[0]


def build_namespace(
    create_safe_builtins: Callable[[], dict[str, Any]],
    roots: tuple[str, ...],
) -> dict[str, Any]:
    """Build the restricted exec namespace with granted helpers."""
    return {
        "tool": tool,
        "__name__": "__custom_tool__",
        "__builtins__": create_safe_builtins(),
        "granted_read": make_granted_read(roots),
        "granted_write": make_granted_write(roots),
    }


class CappedWriter(io.StringIO):
    """Collect stdout up to a byte cap, then count the overflow."""

    def __init__(self, cap_bytes: int) -> None:
        super().__init__()
        self._cap = cap_bytes
        self._used = 0
        self.overflow = 0

    def write(self, text: str) -> int:
        """Append one write while under the cap; count the rest."""
        size = len(text.encode("utf-8"))
        if self._used + size <= self._cap:
            self._used += size
            return super().write(text)
        self.overflow += size
        return len(text)

    def text(self) -> str:
        """Return the captured output within the cap."""
        return self.getvalue()


def _apply_one_limit(
    resource_mod: Any, name: str, pair: tuple[int, int], applied: dict
) -> None:
    """Set one rlimit best-effort, recording what stuck."""
    number = getattr(resource_mod, name, None)
    if number is None:
        return
    try:
        resource_mod.setrlimit(number, pair)
    except (OSError, ValueError):
        return
    applied[name] = f"{pair[0]}/{pair[1]}"


def apply_resource_limits(timeout_ms: int) -> dict[str, str]:
    """Apply Linux rlimits best-effort; return what stuck."""
    applied: dict[str, str] = {}
    try:
        import resource as resource_mod
    except ImportError:
        return applied
    cpu = max(1, int(timeout_ms // 1000) + 5)
    cap = 512 * 1024 * 1024
    limits = {
        "RLIMIT_AS": (cap, cap),
        "RLIMIT_CPU": (cpu, cpu),
        "RLIMIT_NPROC": (0, 0),
    }
    for name, pair in limits.items():
        _apply_one_limit(resource_mod, name, pair, applied)
    return applied


__all__ = [
    "CappedWriter",
    "CapabilityDenied",
    "apply_resource_limits",
    "build_namespace",
    "find_tool",
    "guard_tool_code",
    "make_granted_read",
    "make_granted_write",
    "resolve_grant_path",
    "tool",
]
