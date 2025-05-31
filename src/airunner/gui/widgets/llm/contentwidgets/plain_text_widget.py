from PySide6.QtWidgets import (
    QSizePolicy,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import (
    QFontMetrics,
    QTextOption,
    QColor,
    QPalette,
    QTextCursor,
)
from PySide6.QtWidgets import QTextEdit, QFrame

from airunner.gui.widgets.llm.contentwidgets.base_content_widget import (
    BaseContentWidget,
)


class PlainTextWidget(BaseContentWidget):
    """Widget for displaying plain text content."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.textEdit = QTextEdit(self)
        self.textEdit.setReadOnly(True)
        self.textEdit.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.textEdit.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.textEdit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        # Make the background transparent
        palette = self.textEdit.palette()
        palette.setColor(QPalette.ColorRole.Base, QColor(0, 0, 0, 0))
        self.textEdit.setPalette(palette)

        # Set word wrap mode to make text fit within the widget
        self.textEdit.setWordWrapMode(
            QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere
        )
        self.textEdit.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)

        # Set frame style
        self.textEdit.setFrameStyle(QFrame.Shape.NoFrame)

        # Add to layout
        self.layout.addWidget(self.textEdit)

        # Connect to document size changes
        self.textEdit.document().contentsChanged.connect(self.updateSize)

    def setContent(self, content):
        super().setContent(content)
        self.textEdit.setPlainText(content)
        self.updateSize()
        self.sizeChanged.emit()  # Ensure sizeChanged is always emitted on content update

    def appendText(self, text):
        # Append text as it is streamed in
        cursor = self.textEdit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.textEdit.setTextCursor(cursor)
        self.textEdit.insertPlainText(text)
        self._content += text
        self.updateSize()
        self.sizeChanged.emit()

    def setFont(self, font):
        self.textEdit.setFont(font)
        self.updateSize()

    def updateSize(self):
        """
        Update the size of the widget based on the content height.
        """
        doc = self.textEdit.document()
        doc_height = doc.documentLayout().documentSize().height()
        height = doc_height + 10  # Add a little padding
        self.textEdit.setMinimumHeight(int(height))
        self.sizeChanged.emit()

    def sizeHint(self):
        """
        Provide a size hint based on the content size and the parent widget's width.
        """
        doc_layout = self.textEdit.document().documentLayout()
        width = min(
            max(300, int(self.textEdit.document().idealWidth()) + 20),
            self.parentWidget().width() if self.parentWidget() else 800,
        )
        height = max(50, int(doc_layout.documentSize().height()) + 10)
        return QSize(width, height)

    def minimumSizeHint(self):
        """
        Provide a minimum size hint based on the font metrics.
        """
        font_metrics = QFontMetrics(self.textEdit.font())
        min_height = font_metrics.lineSpacing() * 2 + 10
        return QSize(200, int(min_height))
