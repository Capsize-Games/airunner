"""
Test suite for content_widgets.py in LLM widgets.
"""

import pytest
from airunner.gui.widgets.llm import content_widgets
from PySide6.QtWidgets import QApplication


@pytest.fixture
def base_content_widget(qtbot):
    widget = content_widgets.BaseContentWidget()
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
