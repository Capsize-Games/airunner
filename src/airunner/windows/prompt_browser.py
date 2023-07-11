from PyQt6 import uic
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from airunner.windows.base_window import BaseWindow


class PromptBrowser(BaseWindow):
    template_name = "prompt_browser"
    window_title = "Prompt Browser"

    @property
    def prompts_manager(self):
        return self.settings_manager

    def initialize_window(self):
        container = QWidget()
        container.setLayout(QVBoxLayout())
        for prompt in self.prompts_manager.settings.prompts.get():
            widget = uic.loadUi('pyqt/prompt_browser_prompt_widget.ui')
            widget.prompt.setText(prompt['prompt'])
            widget.negative_prompt.setText(prompt['negative_prompt'])
            widget.load_button.clicked.connect(lambda val, _prompt=prompt: self.load_prompt(_prompt))
            widget.delete_button.clicked.connect(lambda val, _prompt=prompt, _widget=widget: self.delete_prompt(_prompt, widget))
            container.layout().addWidget(widget)

            # self.template.scrollArea is a QScrollArea object
            # we need to get the widget inside it to add our widget to it
        self.template.scrollArea.setWidget(container)

    def load_prompt(self, prompt):
        self.app.update_prompt(prompt['prompt'])
        self.app.update_negative_prompt(prompt['negative_prompt'])

    def delete_prompt(self, prompt, widget):
        prompts = self.prompts_manager.settings.prompts.get()
        prompts.remove(prompt)
        self.prompts_manager.settings.prompts.set(prompts)
        self.prompts_manager.save_settings()
        widget.deleteLater()
