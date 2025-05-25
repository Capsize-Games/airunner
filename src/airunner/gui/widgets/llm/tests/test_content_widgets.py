"""
Test suite for content_widgets.py in LLM widgets.
"""

import pytest
from airunner.gui.widgets.llm import content_widgets
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from unittest.mock import MagicMock


@pytest.fixture
def base_content_widget(qtbot):
    widget = content_widgets.BaseContentWidget()
    qtbot.addWidget(widget)
    widget.show()
    return widget


@pytest.fixture
def plain_text_widget(qtbot):
    widget = content_widgets.PlainTextWidget()
    qtbot.addWidget(widget)
    widget.show()
    return widget


@pytest.fixture
def markdown_widget(qtbot):
    widget = content_widgets.MarkdownWidget()
    qtbot.addWidget(widget)
    widget.show()
    return widget


def test_set_and_get_content(base_content_widget):
    base_content_widget.setContent("test content")
    assert base_content_widget.content() == "test content"


def test_set_font_does_not_crash(base_content_widget):
    # setFont is a no-op in base, but should not crash
    base_content_widget.setFont(None)


def test_size_hints_are_qsize(base_content_widget):
    from PySide6.QtCore import QSize

    assert isinstance(base_content_widget.sizeHint(), QSize)
    assert isinstance(base_content_widget.minimumSizeHint(), QSize)


def test_plaintextwidget_set_content_emits_signal(plain_text_widget, qtbot):
    signal_triggered = []
    plain_text_widget.sizeChanged.connect(
        lambda: signal_triggered.append(True)
    )
    plain_text_widget.setContent("Hello world")
    assert plain_text_widget.textEdit.toPlainText() == "Hello world"
    assert signal_triggered


def test_plaintextwidget_append_text_appends_and_emits(
    plain_text_widget, qtbot
):
    plain_text_widget.setContent("Hello")
    signal_triggered = []
    plain_text_widget.sizeChanged.connect(
        lambda: signal_triggered.append(True)
    )
    plain_text_widget.appendText(", world!")
    assert plain_text_widget.textEdit.toPlainText() == "Hello, world!"
    assert plain_text_widget.content() == "Hello, world!"
    assert signal_triggered


def test_plaintextwidget_set_font_updates(plain_text_widget):
    from PySide6.QtGui import QFont

    font = QFont("Arial", 18)
    plain_text_widget.setFont(font)
    assert plain_text_widget.textEdit.font().family() == "Arial"
    assert plain_text_widget.textEdit.font().pointSize() == 18


def test_markdownwidget_set_content_emits_signal(markdown_widget, qtbot):
    signal_triggered = []
    markdown_widget.sizeChanged.connect(lambda: signal_triggered.append(True))
    markdown_widget.setContent("# Title\nSome **markdown** text.")
    assert markdown_widget._content == "# Title\nSome **markdown** text."
    assert signal_triggered


def test_markdownwidget_set_font_updates(markdown_widget):
    from PySide6.QtGui import QFont

    font = QFont("Times New Roman", 16)
    markdown_widget.setFont(font)
    assert markdown_widget.font_family == "Times New Roman"
    assert markdown_widget.font_size == 16


def test_markdownwidget_size_hints(markdown_widget):
    from PySide6.QtCore import QSize

    assert isinstance(markdown_widget.sizeHint(), QSize)
    assert isinstance(markdown_widget.minimumSizeHint(), QSize)
