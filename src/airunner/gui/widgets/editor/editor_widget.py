"""
EditorWidget: Markdown/Code Editor for AIRunner

This widget provides a markdown/code editing environment with syntax highlighting, MathJax rendering, and LLM agent integration.
"""

from typing import Optional
from PySide6.QtWidgets import QWidget
from airunner.gui.widgets.base_widget import BaseWidget
from airunner.gui.widgets.editor.editor_widget_ui import Ui_EditorWidget
from airunner.gui.widgets.editor.syntax_highlighter import SyntaxHighlighter
from airunner.gui.widgets.editor.mathjax_viewer import MathJaxViewer


class EditorWidget(BaseWidget):
    widget_class_ = Ui_EditorWidget

    def __init__(self, parent: Optional[QWidget] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui.languageComboBox.addItems(
            ["Markdown", "Python", "JavaScript", "C++", "JSON", "HTML", "Bash"]
        )
        self.ui.languageComboBox.setCurrentText("Markdown")
        self.highlighter = SyntaxHighlighter(
            self.ui.editorTextEdit.document(), "Markdown"
        )
        self.ui.languageComboBox.currentTextChanged.connect(self._on_language_changed)
        # MathJax integration
        self.mathjax_viewer = MathJaxViewer(self)
        mathjax_layout = (
            self.ui.mathjaxWidget.layout() if self.ui.mathjaxWidget.layout() else None
        )
        if mathjax_layout:
            mathjax_layout.addWidget(self.mathjax_viewer)
        else:
            from PySide6.QtWidgets import QVBoxLayout

            layout = QVBoxLayout(self.ui.mathjaxWidget)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(self.mathjax_viewer)
        self.ui.editorTextEdit.textChanged.connect(self._update_mathjax)
        # TODO: Connect editorTextEdit to LLM agent signals
        # TODO: Implement code execution trigger

    def _on_language_changed(self, language: str):
        self.highlighter.set_language(language)

    def _update_mathjax(self):
        # Extract LaTeX/math blocks from the editor and render in MathJaxViewer
        text = self.ui.editorTextEdit.toPlainText()
        import re

        # Simple: render all $...$ and $$...$$ blocks concatenated (improve as needed)
        math_blocks = re.findall(r"(\$\$.*?\$\$|\$.*?\$)", text, re.DOTALL)
        latex = "<br>".join(math_blocks) if math_blocks else ""
        self.mathjax_viewer.set_latex(latex)

    # Placeholder for LLM agent integration
    def set_content_from_llm(self, content: str):
        self.ui.editorTextEdit.setPlainText(content)

    def get_content_for_llm(self) -> str:
        return self.ui.editorTextEdit.toPlainText()

    def execute_code(self):
        # TODO: Implement code execution logic
        pass
