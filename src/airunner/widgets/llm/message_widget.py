from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.llm.templates.message_ui import Ui_message_widget


class MessageWidget(BaseWidget):
    widget_class_ = Ui_message_widget

    def __init__(self, *args, **kwargs):
        self.is_bot = kwargs.pop("is_bot")
        self.message = kwargs.pop("message")
        super().__init__(*args, **kwargs)
        self.ui.name.setText(f"{self.message.name}:")
        self.ui.message.setPlainText(self.message.message)
        if self.is_bot:
            self.ui.name.setStyleSheet("font-weight: normal;")
        else:
            self.ui.name.setStyleSheet("font-weight: bold;")

        self.ui.message.setStyleSheet("color: #f2f2f2;")
