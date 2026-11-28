"""The application-state tool must return JSON state, not an error string.

Regression coverage for the state payload builder and the built tool.
"""

from __future__ import annotations

import json
import logging
from unittest.mock import Mock

from airunner_services.llm.managers.tools.autonomous_control_state_tools import (
    _application_state_result,
    build_get_application_state_tool,
)


def _owner_mock() -> Mock:
    owner = Mock()
    owner.logger = logging.getLogger(__name__)
    owner.rag_manager = object()
    owner.active_llm_model_name = "unit-test-model"
    owner.current_conversation_id = 99
    owner.get_all_tools = lambda: ["alpha", "beta"]
    return owner


def test_state_payload_decodes_with_expected_sections() -> None:
    payload = json.loads(_application_state_result(_owner_mock()))

    assert payload["llm"]["model"] == "unit-test-model"
    assert payload["llm"]["tools_count"] == 2
    assert payload["conversation"]["current_id"] == 99
    assert payload["capabilities"]["rag"] is True


def test_tool_invocation_returns_state_document() -> None:
    rendered = build_get_application_state_tool(_owner_mock()).invoke({})

    assert not rendered.startswith("Error")
    assert json.loads(rendered)["application"]["name"] == "AI Runner"
