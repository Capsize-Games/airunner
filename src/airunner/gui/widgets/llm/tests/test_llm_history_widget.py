"""
Test suite for llm_history_widget.py in LLM widgets.
"""

import pytest
from unittest.mock import patch, MagicMock
from airunner.gui.widgets.llm import llm_history_widget


@pytest.fixture
def history_widget(qtbot):
    mock_convo = MagicMock()
    mock_convo.summarize.return_value = "summary"
    mock_convo.chatbot_id = 1
    mock_convo.timestamp = "now"
    with patch(
        "airunner.data.models.Conversation.objects.order_by"
    ) as mock_order_by:
        mock_order_by.return_value.all.return_value = [mock_convo]
        widget = llm_history_widget.LLMHistoryWidget()
        qtbot.addWidget(widget)
        widget.show()
        return widget


def test_history_widget_constructs_and_loads(history_widget):
    # Should add at least one child LLMHistoryItemWidget
    layout = history_widget.ui.gridLayout_2
    found = False
    for i in range(layout.count()):
        item = layout.itemAt(i)
        if hasattr(item, "widget") and item.widget() is not None:
            found = True
    assert found
