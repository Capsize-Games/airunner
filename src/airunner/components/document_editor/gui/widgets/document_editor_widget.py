"""
document_editor_widget.py

A code editor widget with line numbers and syntax highlighting for the AI Runner project.

Implements a QPlainTextEdit-based code editor with a custom line number area and Python syntax highlighting.

Follows project conventions for widget structure and documentation.
"""

from typing import Optional
import logging
import os

try:
    import fcntl  # POSIX advisory locks

    _HAS_FCNTL = True
except Exception:
    fcntl = None
    _HAS_FCNTL = False
from PySide6.QtCore import (
    Qt,
    QRect,
    QSize,
    QRegularExpression,
    QFile,
    QTextStream,
    QFileInfo,
    QTimer,
    Slot,
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
        # Autosave timer (debounced)
        self._autosave_delay_ms = 1500
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setSingleShot(True)
        self._autosave_timer.timeout.connect(self._perform_autosave)
        self._logger = logging.getLogger(__name__)
        # Track modification state reliably via the document's signal
        self._modified = False
        try:
            self.editor.document().modificationChanged.connect(
                self._on_modification_changed
            )
        except Exception:
            # Older Qt bindings or unexpected state; fall back to querying document
            self._logger.exception(
                "Failed to connect modificationChanged signal"
            )
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
        # Start listening for content changes to trigger autosave
        # Use the document's contentsChanged signal so we debounce on typing
        self.editor.document().contentsChanged.connect(
            self._on_document_contents_changed
        )

    @Slot()
    def on_run_button_clicked(self):
        self.save_file()
        self.emit_signal(
            SignalCode.RUN_SCRIPT,
            {
                "document_path": self.current_file_path,
            },
        )

    def _on_document_contents_changed(self):
        """Debounce document changes and trigger autosave after idle period.

        Does nothing when there's no current file path (unsaved/new documents).
        """
        if not self.current_file_path:
            return
        try:
            # restart the single-shot timer
            self._autosave_timer.start(self._autosave_delay_ms)
        except Exception:
            self._logger.exception("Failed to start autosave timer")

    def _on_modification_changed(self, modified: bool):
        """Update internal flag when QTextDocument reports modification changes."""
        try:
            self._modified = bool(modified)
            self._logger.debug(
                "Document modificationChanged -> %s", self._modified
            )
        except Exception:
            self._logger.exception("Error in _on_modification_changed handler")

    def _clear_modified(self):
        """Clear both the QTextDocument's modified flag and the internal flag."""
        try:
            doc = self.editor.document()
            # Temporarily block signals to avoid re-entrant handlers
            try:
                prev_block = doc.blockSignals(True)
            except Exception:
                prev_block = False
            try:
                # Disable undo/redo while clearing the flag to avoid
                # side-effects from the undo stack that can re-mark the doc
                try:
                    prev_undo = doc.isUndoRedoEnabled()
                    doc.setUndoRedoEnabled(False)
                except Exception:
                    prev_undo = None
                try:
                    doc.setModified(False)
                finally:
                    try:
                        if prev_undo is not None:
                            doc.setUndoRedoEnabled(prev_undo)
                    except Exception:
                        pass
            finally:
                try:
                    doc.blockSignals(prev_block)
                except Exception:
                    pass
            self._modified = False
        except Exception:
            self._logger.exception("Failed to clear modified flag")

    def _perform_autosave(self):
        """Called when autosave timer fires; saves if the document is modified."""
        if not self.current_file_path:
            return
        try:
            if not self.is_modified():
                return
            ok = self.save_file()
            if ok:
                self._logger.debug("Autosaved %s", self.current_file_path)
            else:
                self._logger.warning(
                    "Autosave failed for %s", self.current_file_path
                )
        except Exception:
            self._logger.exception(
                "Unexpected error during autosave for %s",
                self.current_file_path,
            )

    def load_file(self, file_path: str) -> bool:
        self.current_file_path = file_path
        try:
            # Use python file operations with advisory locking when available
            data = None
            try:
                with open(file_path, "r", encoding="utf-8") as fh:
                    if _HAS_FCNTL:
                        try:
                            fcntl.flock(fh.fileno(), fcntl.LOCK_SH)
                        except Exception:
                            self._logger.exception(
                                "Failed to acquire shared lock for %s",
                                file_path,
                            )
                    data = fh.read()
                    if _HAS_FCNTL:
                        try:
                            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
                        except Exception:
                            self._logger.exception(
                                "Failed to release shared lock for %s",
                                file_path,
                            )
            except FileNotFoundError:
                QMessageBox.warning(
                    self, "Error", f"File not found: {file_path}"
                )
                return False
            except Exception as ex:
                QMessageBox.warning(self, "Error", f"Cannot open file: {ex}")
                return False

            self.editor.setPlainText(data or "")
            # Clear modification state after programmatic load
            self._clear_modified()
            # Stop any pending autosave when a file is explicitly loaded
            try:
                self._autosave_timer.stop()
            except Exception:
                pass
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
        # Prefer the QTextDocument's authoritative state; fall back to
        # internal flag if needed.
        try:
            return bool(self.editor.document().isModified()) or bool(
                self._modified
            )
        except Exception:
            return bool(self._modified)

    def save_file(self, save_as_path: str = None) -> bool:
        path = save_as_path or self.current_file_path
        if not path:
            return False
        try:
            # Perform an atomic write using a temp file in the same directory
            dirpath = os.path.dirname(path) or "."
            basename = os.path.basename(path)
            tmp_name = os.path.join(dirpath, f".{basename}.airunner_tmp")
            written = False
            try:
                with open(tmp_name, "w", encoding="utf-8") as fh:
                    if _HAS_FCNTL:
                        try:
                            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
                        except Exception:
                            self._logger.exception(
                                "Failed to acquire exclusive lock for temp file %s",
                                tmp_name,
                            )
                    fh.write(self.editor.toPlainText())
                    fh.flush()
                    try:
                        os.fsync(fh.fileno())
                    except Exception:
                        # fsync may fail on some filesystems; log and continue
                        self._logger.exception("fsync failed for %s", tmp_name)
                    if _HAS_FCNTL:
                        try:
                            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
                        except Exception:
                            self._logger.exception(
                                "Failed to release exclusive lock for temp file %s",
                                tmp_name,
                            )
                # Atomically replace target
                os.replace(tmp_name, path)
                written = True
            finally:
                # Cleanup temp file if not replaced
                if not written and os.path.exists(tmp_name):
                    try:
                        os.remove(tmp_name)
                    except Exception:
                        self._logger.exception(
                            "Failed to remove temp file %s", tmp_name
                        )

            # Defensively clear modification flags on the document and our
            # internal flag. Use a singleShot to handle any race from
            # background formatting/highlighting that may mark the doc.
            self._clear_modified()
            try:
                QTimer.singleShot(0, self._clear_modified)
            except Exception:
                pass
            try:
                self._autosave_timer.stop()
            except Exception:
                pass
            return True
        except Exception as e:
            QMessageBox.warning(
                self, "Error", f"Error saving file {path}: {e}"
            )
            return False
