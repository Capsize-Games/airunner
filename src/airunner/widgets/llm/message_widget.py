from airunner.enums import SignalCode
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.llm.templates.message_ui import Ui_message

from PySide6.QtGui import QTextCursor, QFontDatabase, QFont
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

        self.register(SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL, self.on_application_settings_changed_signal)
        self.font_family = None
        self.font_size = None
        self.set_chat_font()

    def on_application_settings_changed_signal(self):
        self.set_chat_font()

    def set_chat_font(self):
        font_setting = self.get_font_setting_by_name("chat")
        font_family = font_setting.font_family
        font_size = font_setting.font_size
        if self.font_family != font_family or self.font_size != font_size:
            self.font_family = font_family
            self.font_size = font_size
            # Check if the font family is available
            if self.font_family in QFontDatabase().families():
                font = QFont(self.font_family, self.font_size)
                font.setFamilies([
                    self.font_family,
                    "Noto Color Emoji",
                ])
                self.ui.content.setFont(font)

    def set_content_size(self):
        doc_height = self.ui.content.document().size().height()
        doc_width = self.ui.content.document().size().width()
        self.setMinimumHeight(int(doc_height) + 25)
        self.setMinimumWidth(int(doc_width))

    def sizeChange(self):
        self.set_content_size()
        self.textChanged.emit()

    def resizeEvent(self, event):
        self.set_content_size()
        super().resizeEvent(event)

    def sizeHint(self):
        fm = QFontMetrics(self.font())
        h = fm.height() * (self.ui.content.document().lineCount() + 1)
        return QSize(self.width(), h)

    def minimumSizeHint(self):
        return self.sizeHint()

    def update_message(self, text):
        self.message += text

        # strip double spaces from self.message
        self.message = self.message.replace("  ", " ")

        self.ui.content.setPlainText(self.message)

