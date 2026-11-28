"""Unit tests for ToolManager.get_tools_for_action helpers.

_collect_named_tools and _collect_registry_search_tools were extracted
to keep get_tools_for_action within the long-function threshold.
These tests pin the name-resolution order, the search-keyword
filtering, and the registry-unavailable fallback.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

from airunner_common.contract_enums import LLMActionType

from airunner_services.llm.tool_manager import ToolManager


def _make_manager(tools=None):
    manager = ToolManager.__new__(ToolManager)
    manager.logger = MagicMock()
    registry = tools or {}
    manager._get_tool_by_name = lambda name: registry.get(name)
    manager._wrap_tool_with_dependencies = lambda info: MagicMock(
        name=info.name, description=info.description
    )
    manager.get_all_tools = MagicMock(return_value=["all"])
    return manager


def test_collect_named_tools_skips_missing():
    manager = _make_manager({"a": "tool-a", "b": "tool-b"})
    assert manager._collect_named_tools(["a", "missing", "b"]) == ["tool-a", "tool-b"]


def test_collect_named_tools_preserves_order():
    manager = _make_manager({"a": "tool-a", "b": "tool-b"})
    assert manager._collect_named_tools(["b", "a"]) == ["tool-b", "tool-a"]


def test_common_tools_included_for_unknown_action():
    manager = _make_manager(
        {
            "store_user_data": "s",
            "get_user_data": "g",
            "update_mood": "m",
        }
    )
    assert manager.get_tools_for_action("whatever") == ["s", "g", "m"]


def test_chat_action_adds_chat_tools():
    manager = _make_manager(
        {
            "store_user_data": "s",
            "clear_conversation": "c",
            "toggle_tts": "t",
        }
    )
    assert manager.get_tools_for_action(LLMActionType.CHAT) == ["s", "c", "t"]


def test_generate_image_action_adds_image_tools():
    manager = _make_manager(
        {
            "store_user_data": "s",
            "generate_image": "g",
            "open_image": "o",
        }
    )
    assert manager.get_tools_for_action(LLMActionType.GENERATE_IMAGE) == [
        "s",
        "g",
        "o",
    ]


def test_application_command_returns_all_tools():
    manager = _make_manager({"store_user_data": "s"})
    assert manager.get_tools_for_action(LLMActionType.APPLICATION_COMMAND) == ["all"]
    manager.get_all_tools.assert_called_once()


def test_rag_action_combines_registry_and_named(monkeypatch):
    from airunner_services.llm.core import tool_registry as registry_module

    info = SimpleNamespace(
        name="web_search", description="d", return_direct=False, category="search"
    )
    monkeypatch.setattr(registry_module, "ToolRegistry", MagicMock())
    registry_module.ToolRegistry.all.return_value = {"web_search": info}
    manager = _make_manager({"store_user_data": "s", "rag_search": "r"})
    tools = manager.get_tools_for_action(LLMActionType.PERFORM_RAG_SEARCH)
    assert tools[0] == "s"
    assert tools[-1] == "r"
    assert len(tools) == 3


def test_registry_unavailable_falls_back_to_named(monkeypatch):
    import airunner_services.llm.core.tool_registry as registry_module

    monkeypatch.setattr(
        registry_module, "ToolRegistry", MagicMock(side_effect=RuntimeError("x"))
    )
    manager = _make_manager({"store_user_data": "s", "rag_search": "r"})
    tools = manager.get_tools_for_action(LLMActionType.PERFORM_RAG_SEARCH)
    assert tools == ["s", "r"]
