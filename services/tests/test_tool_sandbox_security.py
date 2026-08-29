"""Unit tests for the fail-closed custom-tool sandbox (GitHub issue #2032).

Proves:
- A tool record without ``safety_validated=True`` is never compiled/executed.
- ``_compile_custom_tool`` refuses unvalidated records even when called
  directly.
- ``validate_code_safety`` is an AST analyzer: imports, dunder attribute
  chains, denylisted builtins and module-root chains are rejected with
  specific messages; benign tools and literal strings pass.
- ``validate_code_safety`` now has real call sites (save path + shared
  helper), and only a passing validation yields ``safety_validated=True``.

CI note (issue #2054 / security-coverage): the validator assertions run in
the lean ``[development]`` install used by ``Hybrid Runtime CI``. Only the
``ToolManager`` assertions, which need the langchain agent stack, are guarded
by a scoped ``importorskip`` below.
"""

from __future__ import annotations

import os
from types import SimpleNamespace
from unittest import mock

import pytest

from airunner_services.database.models.llm_tool import (
    LLMTool,
    validate_tool_code,
)


# ---------------------------------------------------------------------------
# AST validator (pure stdlib — runs in the lean CI install)
# ---------------------------------------------------------------------------


def test_validate_ast_rejects_dunder_mro_chain() -> None:
    code = (
        "@tool\n"
        "def f():\n"
        "    return ().__class__.__mro__[1].__subclasses__()\n"
    )
    is_safe, message = validate_tool_code(code)
    assert is_safe is False
    assert "__class__" in message or "__subclasses__" in message


def test_validate_ast_rejects_getattr_globals() -> None:
    code = '@tool\ndef f():\n    return getattr(x, "__globals__")\n'
    is_safe, message = validate_tool_code(code)
    assert is_safe is False
    assert "getattr" in message


def test_validate_ast_rejects_import_statement() -> None:
    code = "@tool\ndef f():\n    import os\n    return 1\n"
    is_safe, message = validate_tool_code(code)
    assert is_safe is False
    assert "import" in message


def test_validate_ast_rejects_from_import() -> None:
    code = "@tool\ndef f():\n    from sys import modules\n    return 1\n"
    is_safe, message = validate_tool_code(code)
    assert is_safe is False
    assert "import" in message


def test_validate_ast_rejects_builtins_concat_eval() -> None:
    code = '@tool\ndef f():\n    return __builtins__["ev"+"al"]("1")\n'
    is_safe, message = validate_tool_code(code)
    assert is_safe is False
    assert "__builtins__" in message


def test_validate_ast_rejects_breakpoint() -> None:
    code = "@tool\ndef f():\n    breakpoint()\n"
    is_safe, message = validate_tool_code(code)
    assert is_safe is False
    assert "breakpoint" in message


def test_validate_ast_rejects_subprocess_module_root() -> None:
    code = "@tool\ndef f():\n    import subprocess\n    return 1\n"
    is_safe, message = validate_tool_code(code)
    assert is_safe is False
    assert "import" in message


def test_validate_ast_accepts_benign_tool() -> None:
    """A benign tool passes (the ``@tool`` decorator is injected into the
    exec namespace by ToolManager, so no import is required — matching the
    codebase's example tool fixtures)."""
    code = (
        "@tool\n"
        "def add(a: int, b: int) -> int:\n"
        '    """Add two numbers."""\n'
        "    return a + b\n"
    )
    is_safe, message = validate_tool_code(code)
    assert is_safe is True, message


def test_validate_ast_accepts_literal_open_string() -> None:
    """A literal string containing ``open(`` must not be rejected."""
    code = (
        "@tool\n"
        "def f():\n"
        '    """Opens the file (open(the file)) — not a call."""\n'
        '    return "open(the file)"\n'
    )
    is_safe, message = validate_tool_code(code)
    assert is_safe is True, message


def test_validate_ast_requires_tool_decorator() -> None:
    code = "def f():\n    return 1\n"
    is_safe, message = validate_tool_code(code)
    assert is_safe is False
    assert "@tool" in message


def test_validate_ast_rejects_syntax_error() -> None:
    code = "@tool\ndef f(:\n"
    is_safe, message = validate_tool_code(code)
    assert is_safe is False
    assert "syntax" in message.lower()


def test_validate_ast_accepts_plain_math_tool() -> None:
    """A benign tool that does arithmetic still passes."""
    code = "@tool\ndef add(a: int, b: int) -> int:\n    return a + b\n"
    is_safe, message = validate_tool_code(code)
    assert is_safe is True, message


# ---------------------------------------------------------------------------
# ToolManager-level assertions (need the langchain agent stack)
# ---------------------------------------------------------------------------

# The tool manager pulls in the long-running agent stack, which imports
# langgraph/langchain_core at module import time. Only the tests below need
# it; everything above is lean-env runnable (issue #2054 / security coverage).
# The imports are guarded so a lean install skips just these tests, not the
# AST-validator assertions above.
try:
    from airunner_services.api.routes.persistence_mutations import (  # noqa: E402
        _enforce_tool_code_values,
        _enforce_tool_safety,
    )
    from airunner_services.llm.tool_manager import ToolManager  # noqa: E402

    _TOOL_MANAGER_IMPORTS_OK = True
except ImportError:  # pragma: no cover - lean install path
    _TOOL_MANAGER_IMPORTS_OK = False

_NEEDS_TOOL_MANAGER = pytest.mark.skipif(
    not _TOOL_MANAGER_IMPORTS_OK,
    reason="ToolManager tests need the llm-native agent stack",
)


def _fake_record(**overrides) -> SimpleNamespace:
    values = {
        "name": "evil_tool",
        "display_name": "Evil Tool",
        "description": "test",
        "code": "@tool\ndef evil():\n    import subprocess\n",
        "enabled": True,
        "safety_validated": False,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


@_NEEDS_TOOL_MANAGER
def test_unvalidated_tool_is_never_compiled() -> None:
    manager = ToolManager(rag_manager=None)
    fake = _fake_record(safety_validated=False)
    with mock.patch(
        "airunner_services.database.models.llm_tool.LLMTool"
    ) as mock_model:
        mock_model.objects.filter_by.return_value = [fake]
        with mock.patch.object(
            manager, "_compile_custom_tool"
        ) as compile_spy:
            tools = manager._load_custom_tools()

    assert tools == []
    compile_spy.assert_not_called()


@_NEEDS_TOOL_MANAGER
def test_validated_tool_is_compiled() -> None:
    manager = ToolManager(rag_manager=None)
    fake = _fake_record(safety_validated=True)
    sentinel = object()
    with mock.patch(
        "airunner_services.database.models.llm_tool.LLMTool"
    ) as mock_model:
        mock_model.objects.filter_by.return_value = [fake]
        with mock.patch.object(
            manager, "_compile_custom_tool", return_value=sentinel
        ) as compile_spy:
            tools = manager._load_custom_tools()

    assert tools == [sentinel]
    compile_spy.assert_called_once_with(fake)


@_NEEDS_TOOL_MANAGER
def test_compile_custom_tool_refuses_unvalidated_record() -> None:
    manager = ToolManager(rag_manager=None)
    with pytest.raises(PermissionError):
        manager._compile_custom_tool(_fake_record(safety_validated=False))


@_NEEDS_TOOL_MANAGER
def test_enforce_tool_safety_sets_flag_only_after_real_pass() -> None:
    unsafe = LLMTool(
        name="unsafe",
        code="@tool\ndef f():\n    import subprocess\n    return 'x'\n",
    )
    _enforce_tool_safety(unsafe)
    assert unsafe.safety_validated is False

    safe = LLMTool(
        name="safe",
        code="@tool\ndef g():\n    return 'hello'\n",
    )
    _enforce_tool_safety(safe)
    assert safe.safety_validated is True

    # A caller-supplied True must never survive an actual validation pass
    # when the code is unsafe.
    spoofed = LLMTool(
        name="spoofed",
        code="@tool\ndef h():\n    __import__('os')\n",
        safety_validated=True,
    )
    _enforce_tool_safety(spoofed)
    assert spoofed.safety_validated is False


@_NEEDS_TOOL_MANAGER
def test_enforce_tool_code_values_revalidates_bulk_updates() -> None:
    values = {
        "code": "@tool\ndef f():\n    import subprocess\n",
        "safety_validated": True,
    }
    _enforce_tool_code_values(LLMTool, values)
    assert values["safety_validated"] is False


@_NEEDS_TOOL_MANAGER
def test_validate_tool_code_shared_helper() -> None:
    is_safe, _message = validate_tool_code(
        "@tool\ndef f():\n    return 'ok'\n"
    )
    assert is_safe is True

    is_safe, message = validate_tool_code(
        "@tool\ndef f():\n    os.system('rm -rf /')\n"
    )
    assert is_safe is False
    assert "os.system" in message or "rm" in message


@_NEEDS_TOOL_MANAGER
def test_persistence_mutations_have_real_validation_call_sites() -> None:
    """The daemon save path must invoke the safety enforcement helpers."""
    module_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "services",
        "src",
        "airunner_services",
        "api",
        "routes",
        "persistence_mutations.py",
    )
    with open(module_path, encoding="utf-8") as handle:
        source = handle.read()

    # Enforcement helper must be defined and actually called from the
    # record-creation and record-update paths.
    assert "_enforce_tool_safety" in source
    assert "def _enforce_tool_safety" in source
    assert source.count("_enforce_tool_safety(") >= 3
    assert "def _enforce_tool_code_values" in source
    assert "_enforce_tool_code_values(model_cls, values)" in source
