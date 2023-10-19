from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.llm.templates.message_ui import Ui_message_widget


class MessageWidget(BaseWidget):
    widget_class_ = Ui_message_widget

    def __init__(self, *args, **kwargs):
        self.message = kwargs.pop("message")
        super().__init__(*args, **kwargs)
        self.ui.name.setText(self.message.name)
        self.ui.message.setPlainText(self.message.message)
