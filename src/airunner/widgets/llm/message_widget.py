from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.llm.templates.message_ui import Ui_message

from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QTextEdit
from PySide6.QtGui import QFontMetrics
from PySide6.QtCore import Qt, QSize
from PySide6.QtCore import Signal


class AutoResizingTextEdit(QTextEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.document().contentsChanged.connect(self.sizeChange)


class MessageWidget(BaseWidget):
    widget_class_ = Ui_message
    textChanged = Signal()

    def __init__(self, *args, **kwargs):
        self.name = kwargs.pop("name")
        self.message = kwargs.pop("message")
        self.is_bot = kwargs.pop("is_bot")
        super().__init__(*args, **kwargs)
        self.ui.content.setReadOnly(True)
        self.ui.content.insertPlainText(self.message)
        self.ui.content.document().contentsChanged.connect(self.sizeChange)
        self.ui.content.sizeHint = self.sizeHint
        self.ui.content.minimumSizeHint = self.minimumSizeHint
        name = self.name
        if self.is_bot:
            self.ui.bot_name.show()
            self.ui.bot_name.setText(f"{name}")
            self.ui.bot_name.setStyleSheet("font-weight: normal;")
            self.ui.user_name.hide()
        else:
            self.ui.user_name.show()
            self.ui.user_name.setText(f"{name}")
            self.ui.user_name.setStyleSheet("font-weight: normal;")
            self.ui.bot_name.hide()

        self.ui.content.setStyleSheet("border-radius: 5px; border: 5px solid #1f1f1f; background-color: #1f1f1f; color: #ffffff;")

    def sizeChange(self):
        doc_height = self.ui.content.document().size().height()
        self.setMinimumHeight(int(doc_height) + 25)
        self.textChanged.emit()

    def sizeHint(self):
        fm = QFontMetrics(self.font())
        h = fm.height() * (self.ui.content.document().lineCount() + 1)
        return QSize(self.width(), h)

    def minimumSizeHint(self):
        return self.sizeHint()

    def update_message(self, text):
        self.message += text
        self.ui.content.moveCursor(QTextCursor.MoveOperation.End)
        self.ui.content.insertPlainText(text)

