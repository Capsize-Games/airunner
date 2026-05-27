from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.art.gui.windows.prompt_browser.templates.prompt_browser_prompt_widget_ui import (
    Ui_prompt_widget,
)


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
        self.resource_store.delete("SavedPrompt", self.saved_prompt.id)

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
        new_saved_prompt = self.resource_store.get(
            "SavedPrompt",
            self.saved_prompt.id,
        )
        if new_saved_prompt:
            values = {
                "prompt": self.saved_prompt.prompt,
                "negative_prompt": self.saved_prompt.negative_prompt,
                "secondary_prompt": self.saved_prompt.secondary_prompt,
                "secondary_negative_prompt": (
                    self.saved_prompt.secondary_negative_prompt
                ),
            }
            self.resource_store.update(
                "SavedPrompt",
                self.saved_prompt.id,
                values,
            )
