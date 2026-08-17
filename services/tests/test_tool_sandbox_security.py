"""Unit tests for the fail-closed custom-tool sandbox (GitHub issue #2032).

Proves:
- A tool record without ``safety_validated=True`` is never compiled/executed.
- ``_compile_custom_tool`` refuses unvalidated records even when called
  directly.
- ``validate_code_safety`` now has real call sites (save path + shared
  helper), and only a passing validation yields ``safety_validated=True``.
"""

from __future__ import annotations

import os
from types import SimpleNamespace
from unittest import mock

import pytest

from airunner_services.api.routes.persistence_mutations import (
    _enforce_tool_code_values,
    _enforce_tool_safety,
)
from airunner_services.database.models.llm_tool import (
    LLMTool,
    validate_tool_code,
)
from airunner_services.llm.tool_manager import ToolManager


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


def test_compile_custom_tool_refuses_unvalidated_record() -> None:
    manager = ToolManager(rag_manager=None)
    with pytest.raises(PermissionError):
        manager._compile_custom_tool(_fake_record(safety_validated=False))


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


def test_enforce_tool_code_values_revalidates_bulk_updates() -> None:
    values = {
        "code": "@tool\ndef f():\n    import subprocess\n",
        "safety_validated": True,
    }
    _enforce_tool_code_values(LLMTool, values)
    assert values["safety_validated"] is False


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
