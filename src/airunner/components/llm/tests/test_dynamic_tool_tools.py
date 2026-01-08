"""Unit tests for dynamic tool creation tooling."""

import pytest

from airunner.components.llm.tools.dynamic_tool_tools import (
    clear_dynamic_tools,
    create_dynamic_tool,
)


def test_create_dynamic_tool_disabled_by_default(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("AIRUNNER_ENABLE_DYNAMIC_TOOLS", raising=False)
    clear_dynamic_tools()

    out = create_dynamic_tool(
        name="hello_tool",
        description="Say hello",
        parameters_json='{"name": {"type": "str", "description": "Name"}}',
        code='result = f"Hello, {name}!"',
        category="system",
    )

    assert isinstance(out, str)
    assert "disabled" in out.lower()
