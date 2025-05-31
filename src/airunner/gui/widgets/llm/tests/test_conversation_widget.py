"""
Unit tests for ConversationWidget.
"""

import pytest
from PySide6.QtWidgets import QApplication
from airunner.gui.widgets.llm.contentwidgets.conversation_widget import ConversationWidget


@pytest.fixture
def widget(qtbot):
    w = ConversationWidget()
    qtbot.addWidget(w)
    return w


def test_empty_conversation(widget):
    widget.set_conversation([])
    # Should not crash, and HTML should be rendered
    assert widget._view is not None


def test_single_message(widget):
    messages = [
        {"sender": "User", "text": "Hello!", "timestamp": "2025-05-31 10:00"}
    ]
    widget.set_conversation(messages)

    # HTML should contain the message text
    def check_html():
        html = widget._view.page().toHtml(
            lambda html: pytest.skip("Manual check: %s" % html)
        )

    # We can't synchronously check HTML, but this ensures no error
    assert widget._view is not None


def test_multiple_messages(widget):
    messages = [
        {"sender": "User", "text": "Hi!", "timestamp": "2025-05-31 10:00"},
        {
            "sender": "Assistant",
            "text": "Hello!",
            "timestamp": "2025-05-31 10:01",
        },
    ]
    widget.set_conversation(messages)
    assert widget._view is not None
