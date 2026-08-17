"""Restricted builtins helpers for runtime execution.

IMPORTANT: this module is NOT a security boundary on its own. Python's
``exec`` cannot be safely sandboxed by removing builtins alone; a crafted
tool can still reach ``object.__subclasses__`` or the import machinery.
AIRunner treats this restricted-builtins namespace strictly as
defense-in-depth. The actual gate that decides whether a custom tool may run
at all is the ``safety_validated`` flag on the tool record (see
``airunner_services.database.models.llm_tool.LLMTool`` and
``ToolManager._load_custom_tools``).
"""

import builtins
from typing import Any, Dict


# Builtins that are safe to expose in the restricted namespace
SAFE_BUILTINS = {
    # Core functions
    'abs', 'all', 'any', 'bin', 'bool', 'bytes', 'callable',
    'chr', 'complex', 'dict', 'divmod', 'enumerate',
    'filter', 'float', 'format', 'frozenset', 'hasattr',
    'hash', 'hex', 'id', 'int', 'isinstance', 'issubclass',
    'iter', 'len', 'list', 'map', 'max', 'min', 'next',
    'oct', 'ord', 'pow', 'print', 'range', 'repr', 'reversed',
    'round', 'set', 'slice', 'sorted', 'str', 'sum', 'tuple',
    'zip',
    # Exceptions (for error handling)
    'Exception', 'ValueError', 'TypeError', 'KeyError', 'IndexError',
    'RuntimeError', 'StopIteration', 'AttributeError',
}
def create_safe_builtins() -> Dict[str, Any]:
    """Return a dict of builtins allowed in restricted execution."""

    safe_builtins: Dict[str, Any] = {}
    for name in SAFE_BUILTINS:
        if hasattr(builtins, name):
            safe_builtins[name] = getattr(builtins, name)
    return safe_builtins
