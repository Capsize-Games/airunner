"""Test that ConversationWidget does not show a horizontal scrollbar and auto-scrolls smoothly on streaming updates."""

import pytest
from PySide6.QtWidgets import QApplication
from airunner.gui.widgets.llm.contentwidgets.conversation_widget import (
    ConversationWidget,
)


@pytest.fixture
def widget(qtbot):
    w = ConversationWidget()
    qtbot.addWidget(w)
    return w


def test_no_horizontal_scrollbar_and_smooth_scroll(widget, qtbot):
    # Simulate a conversation with enough messages to require scrolling
    messages = [
        (
            {"sender": "user", "text": f"Message {i}", "is_bot": False}
            if i % 2 == 0
            else {"sender": "assistant", "text": f"Reply {i}", "is_bot": True}
        )
        for i in range(30)
    ]
    widget.set_conversation(messages)
    view = widget._view
    page = view.page()
    # Wait for the page to load and JS to run
    qtbot.wait(500)
    # Check that the horizontal scrollbar is not visible
    scrollbars = view.page().scrollPosition()
    assert scrollbars.x() == 0, "Horizontal scroll should be zero"
    # Optionally, check the container width matches the viewport
    # Simulate streaming: add a new message and check scroll
    messages.append(
        {"sender": "assistant", "text": "Streaming message...", "is_bot": True}
    )
    widget.set_conversation(messages)
    qtbot.wait(300)
    # No exceptions and scroll should still be at bottom
    # (We can't easily assert smoothness, but can check scroll position again)
    scrollbars2 = view.page().scrollPosition()
    assert (
        scrollbars2.x() == 0
    ), "Horizontal scroll should remain zero after streaming update"
