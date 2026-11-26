"""get_application_state must return its JSON payload, not a NameError message.

autonomous_control_state_tools.py called ``json.dumps`` without importing
``json``; the tool wrapper swallowed the NameError and returned
"Error getting application state: name 'json' is not defined".
"""

import json
import logging
from types import SimpleNamespace

from airunner_services.llm.managers.tools.autonomous_control_state_tools import (
    _application_state_result,
    build_get_application_state_tool,
)


def _owner():
    return SimpleNamespace(
        logger=logging.getLogger("test"),
        rag_manager=object(),
        active_llm_model_name="test-model",
        current_conversation_id=7,
        get_all_tools=lambda: [1, 2, 3],
    )


def test_application_state_result_is_json():
    state = json.loads(_application_state_result(_owner()))

    assert state["llm"]["model"] == "test-model"
    assert state["llm"]["tools_count"] == 3
    assert state["conversation"]["current_id"] == 7
    assert state["capabilities"]["rag"] is True


def test_get_application_state_tool_returns_state_not_error():
    tool = build_get_application_state_tool(_owner())

    result = tool.invoke({})

    assert not result.startswith("Error")
    assert json.loads(result)["application"]["name"] == "AI Runner"
