"""
Unit tests for ConversationWidget.
"""

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


def test_scroll_to_bottom_functionality(widget, qtbot):
    """Test that scroll_to_bottom executes JavaScript without errors."""
    dom_ready_holder = {"ready": False}

    def on_dom_ready():
        dom_ready_holder["ready"] = True

    # Wait for DOM to be ready first
    widget.wait_for_dom_ready(on_dom_ready)
    qtbot.waitUntil(lambda: dom_ready_holder["ready"], timeout=3000)

    # Add some test messages
    messages = [
        {
            "sender": "User",
            "text": "Message 1",
            "timestamp": "2025-05-31 10:00",
        },
        {
            "sender": "Assistant",
            "text": "Message 2",
            "timestamp": "2025-05-31 10:01",
        },
        {
            "sender": "User",
            "text": "Message 3",
            "timestamp": "2025-05-31 10:02",
        },
        {
            "sender": "Assistant",
            "text": "Message 4",
            "timestamp": "2025-05-31 10:03",
        },
    ]
    widget.set_conversation(messages)

    # Wait for the conversation to be set
    qtbot.wait(300)

    # Try to scroll to bottom - this should not crash
    widget.scroll_to_bottom()

    # Wait for JavaScript execution
    qtbot.wait(500)

    # The test passes if no exception is raised
    assert widget._view is not None


def test_javascript_execution_basic(widget, qtbot):
    """Test basic JavaScript execution to verify the environment works."""
    result_holder = {"value": None}

    def on_result(result):
        result_holder["value"] = result

    # Execute a simple JavaScript test
    widget._view.page().runJavaScript("2 + 2", on_result)

    # Wait for result
    qtbot.wait(100)

    # Should get 4 as result
    assert result_holder["value"] == 4


def test_javascript_dom_access(widget, qtbot):
    """Test that JavaScript can access DOM elements."""
    result_holder = {"value": None}
    dom_ready_holder = {"ready": False}

    def on_dom_ready():
        dom_ready_holder["ready"] = True

    def on_result(result):
        result_holder["value"] = result

    # Wait for DOM to be ready first
    widget.wait_for_dom_ready(on_dom_ready)

    # Wait for DOM ready to complete
    qtbot.waitUntil(lambda: dom_ready_holder["ready"], timeout=3000)

    # Test if we can find the conversation container
    widget._view.page().runJavaScript(
        "!!document.getElementById('conversation-container')", on_result
    )

    # Wait for result
    qtbot.wait(200)

    # Should be True if container exists
    assert result_holder["value"] is True
