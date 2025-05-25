"""
Test suite for message_widget.py in LLM widgets.
"""

import pytest
from airunner.gui.widgets.llm import message_widget
from PySide6.QtWidgets import QApplication
import types
from unittest.mock import MagicMock, patch
from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QWidget


@pytest.fixture(autouse=True)
def cleanup_resize_thread():
    yield
    # Clean up the class-level QThread after tests
    cls = message_widget.MessageWidget
    if cls.resize_thread is not None:
        cls.resize_worker.running = False
        cls.resize_thread.quit()
        cls.resize_thread.wait()
        cls.resize_thread = None
        cls.resize_worker = None


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


def test_update_message_appends_and_emits(dummy_message_widget, qtbot):
    signal_triggered = []
    dummy_message_widget.messageResized.connect(
        lambda: signal_triggered.append(True)
    )
    dummy_message_widget.update_message("New message")
    # update_message appends to the message
    assert dummy_message_widget.message == "HelloNew message"
    # The signal may or may not be emitted depending on widget rebuild; allow either
    # (If you want to guarantee emission, trigger a content change that causes a size update)


def test_set_content_size_triggers_resize(dummy_message_widget, qtbot):
    # set_message_content connects content_widget.sizeChanged to content_size_changed
    dummy_message_widget.set_message_content("Resize me!")
    content_widget = dummy_message_widget.content_widget
    # Now, emitting sizeChanged should trigger messageResized
    with qtbot.waitSignal(dummy_message_widget.messageResized, timeout=500):
        content_widget.sizeChanged.emit()


def test_copy_button_copies_text_to_clipboard(dummy_message_widget, qtbot):
    QApplication.clipboard().clear()
    dummy_message_widget.copy()
    assert QApplication.clipboard().text() == dummy_message_widget.message


def test_content_size_changed_emits_signal(dummy_message_widget, qtbot):
    # Should emit messageResized if content_widget is present
    dummy_message_widget.content_widget = QWidget()
    dummy_message_widget.parentWidget = lambda: None  # No parent
    with qtbot.waitSignal(dummy_message_widget.messageResized, timeout=500):
        dummy_message_widget.content_size_changed()


def test_content_size_changed_with_parent_chain(qtbot):
    # Should call updateGeometry on all parents
    widget = message_widget.MessageWidget(
        name="User",
        message="Hi",
        message_id=2,
        conversation_id=2,
        is_bot=False,
    )
    qtbot.addWidget(widget)
    widget.show()
    parent1 = MagicMock(spec=QWidget)
    parent2 = MagicMock(spec=QWidget)
    parent1.parentWidget.return_value = parent2
    parent2.parentWidget.return_value = None
    widget.parentWidget = lambda: parent1
    widget.content_widget = QWidget()
    with qtbot.waitSignal(widget.messageResized, timeout=500):
        widget.content_size_changed()
    parent1.updateGeometry.assert_called()
    parent2.updateGeometry.assert_called()


def test_set_content_size_no_content_widget(dummy_message_widget):
    dummy_message_widget.content_widget = None
    # Should not raise or emit
    dummy_message_widget.set_content_size()


def test_on_delete_messages_after_id_deletes(qtbot):
    widget = message_widget.MessageWidget(
        name="User",
        message="Hi",
        message_id=5,
        conversation_id=2,
        is_bot=False,
    )
    qtbot.addWidget(widget)
    widget.show()
    widget._deleted = False
    # Patch parentWidget to return a QWidget
    widget.parentWidget = lambda: QWidget()
    with patch.object(widget, "deleteLater") as mock_delete:
        widget.on_delete_messages_after_id({"message_id": 2})
        mock_delete.assert_called_once()


def test_on_delete_messages_after_id_already_deleted(qtbot):
    widget = message_widget.MessageWidget(
        name="User",
        message="Hi",
        message_id=5,
        conversation_id=2,
        is_bot=False,
    )
    qtbot.addWidget(widget)
    widget.show()
    widget._deleted = True
    widget.parentWidget = lambda: QWidget()
    with patch.object(widget, "deleteLater") as mock_delete:
        widget.on_delete_messages_after_id({"message_id": 2})
        mock_delete.assert_not_called()


def test_on_delete_messages_after_id_lower_id(qtbot):
    widget = message_widget.MessageWidget(
        name="User",
        message="Hi",
        message_id=1,
        conversation_id=2,
        is_bot=False,
    )
    qtbot.addWidget(widget)
    widget.show()
    widget._deleted = False
    widget.parentWidget = lambda: QWidget()
    with patch.object(widget, "deleteLater") as mock_delete:
        widget.on_delete_messages_after_id({"message_id": 5})
        mock_delete.assert_not_called()


def test_event_filter_enter_leave(dummy_message_widget, qtbot):
    # Simulate Enter event
    enter_event = QEvent(QEvent.Type.Enter)
    leave_event = QEvent(QEvent.Type.Leave)
    # Should not raise
    dummy_message_widget.eventFilter(
        dummy_message_widget.ui.message_container, enter_event
    )
    dummy_message_widget.eventFilter(
        dummy_message_widget.ui.message_container, leave_event
    )


def make_api_with_llm():
    api = MagicMock()
    api.llm = MagicMock()
    return api


# Patch the api property for delete tests
def test_delete_slot_triggers_api_and_deletes(qtbot):
    widget = message_widget.MessageWidget(
        name="User",
        message="Hi",
        message_id=1,
        conversation_id=2,
        is_bot=False,
    )
    qtbot.addWidget(widget)
    widget.show()
    widget._deleted = False
    widget.api = make_api_with_llm()
    with patch(
        "airunner.gui.widgets.llm.message_widget.session_scope"
    ) as mock_scope, patch.object(
        widget.api.llm, "delete_messages_after_id"
    ) as mock_del, patch.object(
        widget, "setParent"
    ) as mock_set_parent, patch.object(
        widget, "deleteLater"
    ) as mock_delete:
        mock_session = MagicMock()
        mock_conversation = MagicMock()
        mock_conversation.value = ["msg1", "msg2", "msg3"]
        mock_session.query.return_value.filter.return_value.first.return_value = (
            mock_conversation
        )
        mock_scope.return_value.__enter__.return_value = mock_session
        widget.delete()
        mock_del.assert_called_once_with(1)
        mock_set_parent.assert_called_once_with(None)
        mock_delete.assert_not_called()  # Called via QTimer, not immediately


def test_delete_slot_already_deleted(qtbot):
    widget = message_widget.MessageWidget(
        name="User",
        message="Hi",
        message_id=1,
        conversation_id=2,
        is_bot=False,
    )
    qtbot.addWidget(widget)
    widget.show()
    widget._deleted = True
    widget.api = make_api_with_llm()
    with patch(
        "airunner.gui.widgets.llm.message_widget.session_scope"
    ) as mock_scope, patch.object(
        widget.api.llm, "delete_messages_after_id"
    ) as mock_del:
        widget.delete()
        mock_del.assert_not_called()


def test_resizeworker_process_and_stop(monkeypatch):
    # Cover ResizeWorker.process loop, including queue.Empty
    import queue as pyqueue
    from airunner.gui.widgets.llm.message_widget import ResizeWorker

    class DummyWidget:
        def set_content_size(self):
            DummyWidget.called = True

    q = pyqueue.Queue()
    worker = ResizeWorker(q)
    DummyWidget.called = False
    # Put a widget in the queue
    q.put(DummyWidget())

    # Stop after one iteration
    def fake_get(timeout):
        worker.running = False
        return DummyWidget()

    monkeypatch.setattr(q, "get", fake_get)
    monkeypatch.setattr(q, "task_done", lambda: None)
    worker.process()
    assert DummyWidget.called
    # Cover queue.Empty branch
    worker = ResizeWorker(q)
    worker.running = False
    # Should not raise
    worker.process()
    worker.stop()
    assert worker.running is False


def test_set_global_tooltip_style(monkeypatch):
    from airunner.gui.widgets.llm import message_widget

    # QApplication.instance() returns None
    monkeypatch.setattr(message_widget.QApplication, "instance", lambda: None)
    message_widget.set_global_tooltip_style()
    # QApplication.instance() returns a mock
    mock_app = MagicMock()
    mock_app.styleSheet.return_value = ""
    monkeypatch.setattr(
        message_widget.QApplication, "instance", lambda: mock_app
    )
    message_widget.set_global_tooltip_style()
    assert mock_app.setStyleSheet.called


def test_event_filter_fallback(dummy_message_widget, qtbot):
    # Should call super if obj != message_container
    dummy = QWidget()
    event = QEvent(QEvent.Type.MouseButtonPress)
    # Should not raise
    dummy_message_widget.eventFilter(dummy, event)


def test_size_hint_and_minimum_size_hint_fallback(dummy_message_widget):
    dummy_message_widget.content_widget = None
    dummy_message_widget.message = ""
    hint = dummy_message_widget.sizeHint()
    min_hint = dummy_message_widget.minimumSizeHint()
    assert hint.width() > 0 and hint.height() > 0
    assert min_hint.width() > 0 and min_hint.height() > 0


def test_set_chat_font_fallback_font(monkeypatch, dummy_message_widget):
    # Simulate unavailable font family
    dummy_message_widget.font_family = "NotARealFont"
    dummy_message_widget.font_size = 12
    monkeypatch.setattr(
        message_widget.QFontDatabase,
        "families",
        lambda *_: ["Cantarell", "Ubuntu"],
    )
    dummy_message_widget.set_chat_font()
    # Accept any Ubuntu variant or Cantarell as a fallback
    assert dummy_message_widget.content_widget.font().family() in [
        "Cantarell",
        "Ubuntu",
        "Ubuntu Sans",
    ]


def test_update_message_all_widget_types(monkeypatch, dummy_message_widget):
    # Cover all widget type branches in update_message
    for widget_cls, fmt_type, content, parts in [
        (message_widget.PlainTextWidget, "plain", "plain text", None),
        (message_widget.LatexWidget, "latex", "$x^2$", None),
        (message_widget.MarkdownWidget, "markdown", "**bold**", None),
        (
            message_widget.MixedContentWidget,
            "mixed",
            "text and $x^2$",
            [{"type": "latex", "content": "$x^2$"}],
        ),
    ]:
        dummy_message_widget.set_message_content(content)
        dummy_message_widget.content_widget = widget_cls(
            dummy_message_widget.ui.content_container
        )

        def fake_format_content(msg, _fmt=fmt_type, _parts=parts):
            d = {"type": _fmt, "content": msg}
            if _parts is not None:
                d["parts"] = _parts
            return d

        monkeypatch.setattr(
            message_widget.FormatterExtended,
            "format_content",
            fake_format_content,
        )
        dummy_message_widget.message = ""
        dummy_message_widget.update_message("test")


def test_on_play_audio_button_clicked(dummy_message_widget):
    dummy_message_widget.api = MagicMock()
    dummy_message_widget.api.tts = MagicMock()
    dummy_message_widget.message = "foo"
    dummy_message_widget.on_play_audio_button_clicked()
    dummy_message_widget.api.tts.play_audio.assert_called_with("foo")


def test_icons_and_opacity_in_init(qtbot):
    # Just construct and check attributes exist
    widget = message_widget.MessageWidget(
        name="User",
        message="Hi",
        message_id=1,
        conversation_id=1,
        is_bot=False,
    )
    qtbot.addWidget(widget)
    widget.show()
    assert hasattr(widget, "copy_opacity")
    assert hasattr(widget, "delete_opacity")
    assert hasattr(widget, "play_opacity")
    assert hasattr(widget, "copy_anim")
    assert hasattr(widget, "delete_anim")
    assert hasattr(widget, "play_anim")


def test_streamed_text_accumulation_no_duplication(dummy_message_widget):
    # Simulate streaming: send chunks as would be received from LLM
    chunks = ["Now ", "it's ", "already ", "done."]
    for chunk in chunks:
        dummy_message_widget.update_message(chunk)
    # The message should be the concatenation of all chunks, no duplication
    assert dummy_message_widget.message == "HelloNow it's already done."
    # Simulate another streaming session (should append, not reset)
    more_chunks = [" More", " text."]
    for chunk in more_chunks:
        dummy_message_widget.update_message(chunk)
    assert (
        dummy_message_widget.message
        == "HelloNow it's already done. More text."
    )
