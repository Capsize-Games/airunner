"""
Test suite for document_widget.py in LLM widgets.
"""

import pytest
from unittest.mock import MagicMock
from airunner.gui.widgets.llm import document_widget


@pytest.fixture
def doc_widget(qtbot):
    dummy_file = MagicMock()
    dummy_file.file_path = "dummy.txt"
    dummy_delete = MagicMock()
    widget = document_widget.DocumentWidget(
        target_file=dummy_file, delete_function=dummy_delete
    )
    qtbot.addWidget(widget)
    widget.show()
    return widget


def test_document_widget_constructs(doc_widget):
    assert doc_widget is not None
    # Check that the label text is set correctly
    assert doc_widget.ui.label.text() == "dummy.txt"


def test_document_widget_on_delete_calls_delete_function(doc_widget):
    doc_widget.on_delete()
    doc_widget.delete_function.assert_called()
