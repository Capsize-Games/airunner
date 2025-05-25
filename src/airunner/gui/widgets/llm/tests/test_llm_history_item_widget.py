"""
Test suite for llm_history_item_widget.py in LLM widgets.
"""

import pytest
from unittest.mock import MagicMock
from airunner.gui.widgets.llm import llm_history_item_widget


@pytest.fixture
def history_item_widget(qtbot):
    mock_conversation = MagicMock()
    mock_conversation.summarize.return_value = "summary"
    mock_conversation.chatbot_id = 1
    mock_conversation.timestamp = "now"
    widget = llm_history_item_widget.LLMHistoryItemWidget(
        conversation=mock_conversation
    )
    qtbot.addWidget(widget)
    widget.show()
    return widget


def test_history_item_widget_constructs(history_item_widget):
    assert history_item_widget is not None
    assert (
        history_item_widget.ui.conversation_description.toPlainText()
        == "summary"
    )
