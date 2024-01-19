from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.llm.templates.message_ui import Ui_message

from PyQt6.QtGui import QTextCursor


class MessageWidget(BaseWidget):
    widget_class_ = Ui_message

    def __init__(self, *args, **kwargs):
        self.name = kwargs.pop("name")
        self.message = kwargs.pop("message")
        self.is_bot = kwargs.pop("is_bot")
        super().__init__(*args, **kwargs)
        self.ui.content.setReadOnly(True)
        self.ui.content.setText(self.message)
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

        self.ui.content.setStyleSheet("color: #f2f2f2;")

    def update_message(self, text):
        self.message += text
        self.ui.content.moveCursor(QTextCursor.MoveOperation.End)
        self.ui.content.insertPlainText(text)
