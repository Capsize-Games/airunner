"""
Test suite for message_widget.py in LLM widgets.
"""

import pytest
from airunner.gui.widgets.llm import message_widget


@pytest.fixture
def dummy_message_widget(qtbot):
    widget = message_widget.MessageWidget(
        name="User",
        message="Hello",
        message_id=1,
        conversation_id=1,
        is_bot=False,
    )
    qtbot.addWidget(widget)
    widget.show()
    return widget


def test_message_widget_constructs(dummy_message_widget):
    assert dummy_message_widget is not None
    assert dummy_message_widget.ui.user_name.text() == "User"
    assert dummy_message_widget.message == "Hello"
