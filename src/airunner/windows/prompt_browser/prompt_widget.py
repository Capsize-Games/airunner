from airunner.aihandler.enums import SignalCode
from airunner.widgets.base_widget import BaseWidget
from airunner.windows.prompt_browser.templates.prompt_browser_prompt_widget_ui import Ui_prompt_widget


class PromptWidget(BaseWidget):
    widget_class_ = Ui_prompt_widget

    def __init__(self, *args, **kwargs):
        self.index = kwargs.pop("index")
        self.prompt_data = kwargs.pop("prompt_data")
        super().__init__(*args, **kwargs)
        self.ui.prompt.setPlainText(self.prompt_data["prompt"])
        self.ui.negative_prompt.setPlainText(self.prompt_data["negative_prompt"])

    def action_text_changed_prompt(self):
        self.save_prompt()

    def action_text_changed_negative_prompt(self):
        self.save_prompt()

    def action_clicked_button_load(self):
        self.emit(SignalCode.LOAD_SD_PROMPT_SIGNAL, self.index)

    def action_clicked_button_delete(self):
        self.deleteLater()

    def save_prompt(self):
        self.emit(SignalCode.UPDATE_SAVED_SD_PROMPT_SIGNAL, (
            self.index,
            self.ui.prompt.toPlainText(), 
            self.ui.negative_prompt.toPlainText()
        ))
