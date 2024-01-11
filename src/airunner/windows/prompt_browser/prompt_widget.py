from airunner.widgets.base_widget import BaseWidget
from airunner.windows.prompt_browser.templates.prompt_browser_prompt_widget_ui import Ui_prompt_widget
from airunner.data.session_scope import session_scope


class PromptWidget(BaseWidget):
    widget_class_ = Ui_prompt_widget

    def __init__(self, *args, **kwargs):
        self.prompt_data = kwargs.pop("prompt_data")
        super().__init__(*args, **kwargs)
        self.ui.prompt.setPlainText(self.prompt_data.prompt)
        self.ui.negative_prompt.setPlainText(self.prompt_data.negative_prompt)

    def action_text_changed_prompt(self):
        self.save_prompt()

    def action_text_changed_negative_prompt(self):
        self.save_prompt()

    def action_clicked_button_load(self):
        self.app.load_prompt(self.prompt_data)

    def action_clicked_button_delete(self):
        with session_scope() as session:
            session.delete(self.prompt_data)
        self.deleteLater()

    def save_prompt(self):
        with session_scope() as session:
            session.add(self.prompt_data)
            self.prompt_data.prompt = self.ui.prompt.toPlainText()
            self.prompt_data.negative_prompt = self.ui.negative_prompt.toPlainText()
