from airunner.enums import SignalCode
from airunner.gui.widgets.base_widget import BaseWidget
from airunner.gui.windows.prompt_browser.templates.prompt_browser_prompt_widget_ui import (
    Ui_prompt_widget,
)
from airunner.data.models import SavedPrompt


class PromptWidget(BaseWidget):
    widget_class_ = Ui_prompt_widget

    def __init__(self, *args, **kwargs):
        self.saved_prompt = kwargs.pop("saved_prompt")
        super().__init__(*args, **kwargs)
        self.ui.prompt.blockSignals(True)
        self.ui.negative_prompt.blockSignals(True)
        self.ui.secondary_prompt.blockSignals(True)
        self.ui.secondary_negative_prompt.blockSignals(True)
        self.ui.prompt.setPlainText(self.saved_prompt.prompt)
        self.ui.negative_prompt.setPlainText(self.saved_prompt.negative_prompt)
        self.ui.secondary_prompt.setPlainText(
            self.saved_prompt.secondary_prompt
        )
        self.ui.secondary_negative_prompt.setPlainText(
            self.saved_prompt.secondary_negative_prompt
        )
        self.ui.prompt.blockSignals(False)
        self.ui.negative_prompt.blockSignals(False)
        self.ui.secondary_prompt.blockSignals(False)
        self.ui.secondary_negative_prompt.blockSignals(False)

    def action_text_changed(self):
        self.save_prompt()

    def action_clicked_button_load(self):
        self.api.art.load(saved_prompt=self.saved_prompt)

    def action_clicked_button_delete(self):
        SavedPrompt.objects.delete(self.saved_prompt.id)

        self.deleteLater()

    def save_prompt(self):
        self.saved_prompt.prompt = self.ui.prompt.toPlainText()
        self.saved_prompt.negative_prompt = (
            self.ui.negative_prompt.toPlainText()
        )
        self.saved_prompt.secondary_prompt = (
            self.ui.secondary_prompt.toPlainText()
        )
        self.saved_prompt.secondary_negative_prompt = (
            self.ui.secondary_negative_prompt.toPlainText()
        )
        self.save()

    def save(self):
        new_saved_prompt = SavedPrompt.objects.filter_by_first(
            id=self.saved_prompt.id
        )
        if new_saved_prompt:
            for key in self.saved_prompt.__dict__.keys():
                if key != "_sa_instance_state":
                    setattr(
                        new_saved_prompt, key, getattr(self.saved_prompt, key)
                    )
            new_saved_prompt.save()
        else:
            self.saved_prompt.save()
