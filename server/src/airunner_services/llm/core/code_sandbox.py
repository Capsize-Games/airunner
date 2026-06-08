"""Restricted builtins helpers for runtime execution.

SECURITY NOTE: Restricting __builtins__ is not a complete sandbox. Python code
can still escape via attribute traversal (e.g. ().__class__.__mro__[-1].__subclasses__()).
This is a best-effort mitigation only. The long-term fix is subprocess isolation.
All custom tool execution must go through a safety_validated=True gate and a hard
timeout (see tool_manager._compile_custom_tool).
"""

import builtins
from typing import Any, Dict

# Builtins that are safe to expose in the sandbox
SAFE_BUILTINS = {
    # Core functions
    "abs",
    "all",
    "any",
    "bin",
    "bool",
    "bytes",
    "callable",
    "chr",
    "complex",
    "dict",
    "divmod",
    "enumerate",
    "filter",
    "float",
    "format",
    "frozenset",
    "hasattr",
    "hash",
    "hex",
    "id",
    "int",
    "isinstance",
    "issubclass",
    "iter",
    "len",
    "list",
    "map",
    "max",
    "min",
    "next",
    "oct",
    "ord",
    "pow",
    "print",
    "range",
    "repr",
    "reversed",
    "round",
    "set",
    "slice",
    "sorted",
    "str",
    "sum",
    "tuple",
    "zip",
    # Exceptions (for error handling)
    "Exception",
    "ValueError",
    "TypeError",
    "KeyError",
    "IndexError",
    "RuntimeError",
    "StopIteration",
    "AttributeError",
}


def create_safe_builtins() -> Dict[str, Any]:
    """Return a dict of builtins allowed in restricted execution."""

    safe_builtins: Dict[str, Any] = {}
    for name in SAFE_BUILTINS:
        if hasattr(builtins, name):
            safe_builtins[name] = getattr(builtins, name)
    return safe_builtins
