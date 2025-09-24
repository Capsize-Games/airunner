"""
document_editor_widget.py

A code editor widget with line numbers and syntax highlighting for the AI Runner project.

Implements a QPlainTextEdit-based code editor with a custom line number area and Python syntax highlighting.

Follows project conventions for widget structure and documentation.
"""

from typing import Optional
from PySide6.QtCore import (
    Qt,
    QRect,
    QSize,
    QRegularExpression,
    QFile,
    QTextStream,
    QFileInfo, Slot,
)
from PySide6.QtGui import (
    QColor,
    QPainter,
    QFont,
    QFontMetrics,
    QSyntaxHighlighter,
    QTextCharFormat,
)
from PySide6.QtWidgets import QWidget, QPlainTextEdit, QMessageBox
from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.document_editor.gui.templates.document_editor_ui import (
    Ui_Form,
)
from airunner.enums import SignalCode


class LineNumberArea(QWidget):
    """Widget for displaying line numbers next to a QPlainTextEdit."""

    def __init__(self, editor: "CodeEditor"):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)


class CodeEditor(QPlainTextEdit):
    """QPlainTextEdit subclass with line number area and syntax highlighting support."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._line_number_area = LineNumberArea(self)
        self.setFont(QFont("Consolas", 11))
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.line_number_area_update)
        self.update_line_number_area_width(0)

    def line_number_area_width(self) -> int:
        digits = max(2, len(str(self.blockCount())))
        font_metrics = QFontMetrics(self.font())
        space = 8 + font_metrics.horizontalAdvance("9") * digits
        return space

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self._line_number_area.scroll(0, dy)
        else:
            self._line_number_area.update(
                0, rect.y(), self._line_number_area.width(), rect.height()
            )
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._line_number_area.setGeometry(
            QRect(
                cr.left(), cr.top(), self.line_number_area_width(), cr.height()
            )
        )

    def line_number_area_paint_event(self, event):
        painter = QPainter(self._line_number_area)
        painter.fillRect(event.rect(), QColor(245, 245, 245))
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(
            self.blockBoundingGeometry(block)
            .translated(self.contentOffset())
            .top()
        )
        bottom = top + int(self.blockBoundingRect(block).height())
        height = self.fontMetrics().height()
        current_line = self.textCursor().blockNumber()
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                if block_number == current_line:
                    painter.setPen(QColor(30, 144, 255))
                    font = painter.font()
                    font.setBold(True)
                    painter.setFont(font)
                else:
                    painter.setPen(Qt.gray)
                    font = painter.font()
                    font.setBold(False)
                    painter.setFont(font)
                painter.drawText(
                    0,
                    top,
                    self._line_number_area.width() - 4,
                    height,
                    Qt.AlignRight,
                    number,
                )
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1

    def line_number_area_update(self):
        self._line_number_area.update()

    def line_number_area(self) -> QWidget:
        return self._line_number_area


class PythonSyntaxHighlighter(QSyntaxHighlighter):
    """Basic syntax highlighter for Python and other common languages."""

    def __init__(self, document, language: str = "python"):
        super().__init__(document)
        self.highlighting_rules = None
        self.language = language
        self.set_language_rules(language)

    def set_language_rules(self, language: str):
        self.language = language
        self.highlighting_rules = []
        if language == "python":
            keyword_format = QTextCharFormat()
            keyword_format.setForeground(QColor(0, 0, 200))
            keyword_format.setFontWeight(QFont.Weight.Bold)
            keywords = [
                "and",
                "as",
                "assert",
                "break",
                "class",
                "continue",
                "def",
                "del",
                "elif",
                "else",
                "except",
                "False",
                "finally",
                "for",
                "from",
                "global",
                "if",
                "import",
                "in",
                "is",
                "lambda",
                "None",
                "nonlocal",
                "not",
                "or",
                "pass",
                "raise",
                "return",
                "True",
                "try",
                "while",
                "with",
                "yield",
            ]
            for word in keywords:
                pattern = QRegularExpression(rf"\\b{word}\\b")
                self.highlighting_rules.append((pattern, keyword_format))
            string_format = QTextCharFormat()
            string_format.setForeground(QColor(163, 21, 21))
            # Correct regex for single and double quoted strings
            self.highlighting_rules.append(
                (QRegularExpression(r'"([^"\\]|\\.)*"'), string_format)
            )
            self.highlighting_rules.append(
                (QRegularExpression(r"'([^'\\]|\\.)*'"), string_format)
            )
            comment_format = QTextCharFormat()
            comment_format.setForeground(QColor(0, 128, 0))
            self.highlighting_rules.append(
                (QRegularExpression(r"#.*"), comment_format)
            )
            number_format = QTextCharFormat()
            number_format.setForeground(QColor(43, 145, 175))
            self.highlighting_rules.append(
                (QRegularExpression(r"\\b[0-9]+\\b"), number_format)
            )
        elif language == "json":
            key_format = QTextCharFormat()
            key_format.setForeground(QColor(0, 0, 200))
            self.highlighting_rules.append(
                (QRegularExpression(r'"(\\w+)":'), key_format)
            )
            string_format = QTextCharFormat()
            string_format.setForeground(QColor(163, 21, 21))
            self.highlighting_rules.append(
                (QRegularExpression(r'"([^"\\]|\\.)*"'), string_format)
            )
            number_format = QTextCharFormat()
            number_format.setForeground(QColor(43, 145, 175))
            self.highlighting_rules.append(
                (QRegularExpression(r"\\b[0-9]+\\b"), number_format)
            )
        elif language == "javascript":
            keyword_format = QTextCharFormat()
            keyword_format.setForeground(QColor(0, 0, 200))
            keyword_format.setFontWeight(QFont.Weight.Bold)
            keywords = [
                "function",
                "var",
                "let",
                "const",
                "if",
                "else",
                "for",
                "while",
                "return",
                "true",
                "false",
                "null",
            ]
            for word in keywords:
                pattern = QRegularExpression(rf"\\b{word}\\b")
                self.highlighting_rules.append((pattern, keyword_format))
            string_format = QTextCharFormat()
            string_format.setForeground(QColor(163, 21, 21))
            self.highlighting_rules.append(
                (QRegularExpression(r'"([^"\\]|\\.)*"'), string_format)
            )
            self.highlighting_rules.append(
                (QRegularExpression(r"'([^'\\]|\\.)*'"), string_format)
            )
            comment_format = QTextCharFormat()
            comment_format.setForeground(QColor(0, 128, 0))
            self.highlighting_rules.append(
                (QRegularExpression(r"//.*"), comment_format)
            )
        elif language == "html":
            tag_format = QTextCharFormat()
            tag_format.setForeground(QColor(0, 0, 200))
            self.highlighting_rules.append(
                (QRegularExpression(r"<[^>]+>"), tag_format)
            )
        elif language == "css":
            selector_format = QTextCharFormat()
            selector_format.setForeground(QColor(0, 0, 200))
            self.highlighting_rules.append(
                (
                    QRegularExpression(r"[.#]?[a-zA-Z0-9_-]+(?=\\s*\\{)"),
                    selector_format,
                )
            )
            property_format = QTextCharFormat()
            property_format.setForeground(QColor(163, 21, 21))
            self.highlighting_rules.append(
                (QRegularExpression(r"[a-zA-Z-]+(?=:)"), property_format)
            )
        elif language == "markdown":
            header_format = QTextCharFormat()
            header_format.setForeground(QColor(0, 0, 200))
            header_format.setFontWeight(QFont.Weight.Bold)
            self.highlighting_rules.append(
                (QRegularExpression(r"^#+.*"), header_format)
            )
        else:
            self.highlighting_rules = []
        self.rehighlight()

    def highlightBlock(self, text: str):
        for pattern, fmt in self.highlighting_rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                match = it.next()
                self.setFormat(
                    match.capturedStart(), match.capturedLength(), fmt
                )


class DocumentEditorWidget(BaseWidget):
    """Code editor widget with line numbers and syntax highlighting."""

    widget_class_ = Ui_Form

    icons = [
        ("play", "run_button"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.editor = CodeEditor(self)
        self.highlighter = PythonSyntaxHighlighter(self.editor.document())
        self.current_file_path = None
        # Replace the auto-generated editor with our custom one
        self.ui.gridLayout.replaceWidget(self.ui.editor, self.editor)
        self.ui.editor.deleteLater()
        self.ui.editor = self.editor
        # Add the line number area to the left
        self.ui.gridLayout.addWidget(
            self.editor.line_number_area(), 0, 0, 1, 1
        )
        self.ui.gridLayout.setColumnStretch(1, 1)
        self.ui.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.ui.gridLayout.setSpacing(0)

    @Slot()
    def on_run_button_clicked(self):
        self.emit_signal(SignalCode.RUN_SCRIPT, {
            "document_path": self.current_file_path,
        })

    def load_file(self, file_path: str) -> bool:
        self.current_file_path = file_path
        try:
            q_file = QFile(file_path)
            if not q_file.open(
                QFile.OpenModeFlag.ReadOnly | QFile.OpenModeFlag.Text
            ):
                QMessageBox.warning(
                    self, "Error", f"Cannot open file: {q_file.errorString()}"
                )
                return False
            stream = QTextStream(q_file)
            self.editor.setPlainText(stream.readAll())
            q_file.close()
            self.editor.document().setModified(False)
            self.update_syntax_highlighter(file_path)
            return True
        except Exception as e:
            QMessageBox.warning(
                self, "Error", f"Error loading file {file_path}: {e}"
            )
            return False

    def update_syntax_highlighter(self, file_path: str):
        suffix = QFileInfo(file_path).suffix().lower()
        language = "plaintext"
        if suffix == "py":
            language = "python"
        elif suffix == "json":
            language = "json"
        elif suffix == "js":
            language = "javascript"
        elif suffix == "html":
            language = "html"
        elif suffix == "css":
            language = "css"
        elif suffix == "md":
            language = "markdown"
        if hasattr(self, "highlighter") and self.highlighter:
            self.highlighter.set_language_rules(language)
        else:
            self.highlighter = PythonSyntaxHighlighter(
                self.editor.document(), language=language
            )

    def file_path(self) -> str | None:
        return self.current_file_path

    def is_modified(self) -> bool:
        return self.editor.document().isModified()

    def save_file(self, save_as_path: str = None) -> bool:
        path = save_as_path or self.current_file_path
        if not path:
            return False
        try:
            q_file = QFile(path)
            if not q_file.open(
                QFile.OpenModeFlag.WriteOnly | QFile.OpenModeFlag.Text
            ):
                QMessageBox.warning(
                    self, "Error", f"Cannot save file: {q_file.errorString()}"
                )
                return False
            stream = QTextStream(q_file)
            stream << self.editor.toPlainText()
            q_file.close()
            self.editor.document().setModified(False)
            return True
        except Exception as e:
            QMessageBox.warning(
                self, "Error", f"Error saving file {path}: {e}"
            )
            return False
