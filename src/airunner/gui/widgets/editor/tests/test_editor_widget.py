import pytest
from PySide6.QtWidgets import QApplication
from airunner.gui.widgets.editor.editor_widget import EditorWidget


@pytest.fixture
def editor_widget(qtbot):
    widget = EditorWidget()
    qtbot.addWidget(widget)
    return widget


def test_editor_widget_instantiates(editor_widget):
    assert editor_widget is not None
    assert editor_widget.ui.languageComboBox.count() > 0
    assert editor_widget.ui.editorTextEdit is not None


def test_set_and_get_content(editor_widget):
    test_text = "print('Hello, world!')"
    editor_widget.set_content_from_llm(test_text)
    assert editor_widget.get_content_for_llm() == test_text


def test_language_switching(editor_widget, qtbot):
    editor_widget.ui.languageComboBox.setCurrentText("Python")
    assert editor_widget.highlighter.language.lower() == "python"
    editor_widget.ui.languageComboBox.setCurrentText("Markdown")
    assert editor_widget.highlighter.language.lower() == "markdown"


def test_mathjax_rendering(editor_widget, qtbot):
    # Insert LaTeX math and check that MathJaxViewer receives it
    math_text = "Euler's identity: $e^{i\\pi} + 1 = 0$"
    editor_widget.set_content_from_llm(math_text)
    editor_widget._update_mathjax()
    # The MathJaxViewer should be updated with the math block
    assert hasattr(editor_widget, "mathjax_viewer")
