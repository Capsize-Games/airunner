from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.llm.templates.message_ui import Ui_message_widget


class MessageWidget(BaseWidget):
    widget_class_ = Ui_message_widget

    def __init__(self, *args, **kwargs):
        self.is_bot = kwargs.pop("is_bot")
        self.message = kwargs.pop("message")
        super().__init__(*args, **kwargs)
        self.ui.name.setText(f"{self.message.name}:")
        self.ui.message.setText(self.message.message)
        if self.is_bot:
            self.ui.name.setStyleSheet("color: #0000ff;")
        else:
            self.ui.name.setStyleSheet("color: #ff0000;")
