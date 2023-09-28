from functools import partial

from PyQt6 import uic
from PyQt6.QtWidgets import QWidget, QVBoxLayout

from airunner.pyqt.windows.prompt_browser.prompt_browser_ui import Ui_prompt_browser
from airunner.windows.base_window import BaseWindow


class PromptBrowser(BaseWindow):
    template_class_ = Ui_prompt_browser

    def initialize_window(self):
        container = QWidget()
        container.setLayout(QVBoxLayout())
        for index, prompt in enumerate(self.settings_manager.prompts):
            widget = uic.loadUi('pyqt/prompt_browser_prompt_widget.ui')
            widget.prompt.setText(prompt.prompt)
            widget.negative_prompt.setText(prompt.negative_prompt)
            widget.load_button.clicked.connect(partial(self.load_prompt, prompt))
            widget.delete_button.clicked.connect(partial(self.delete_prompt, prompt, widget))
            widget.prompt.textChanged.connect(partial(self.save_prompt, widget, index))
            widget.negative_prompt.textChanged.connect(partial(self.save_prompt, widget, index))
            container.layout().addWidget(widget)
        self.ui.scrollArea.setWidget(container)

    def load_prompt(self, prompt):
        self.app.update_prompt(prompt.prompt)
        self.app.update_negative_prompt(prompt.negative_prompt)

    def delete_prompt(self, prompt, widget):
        self.settings_manager.delete_prompt(prompt)
        widget.deleteLater()

    def save_prompt(self, widget, index):
        prompts = self.settings_manager.prompts
        prompt = widget.prompt.toPlainText()
        negative_prompt = widget.negative_prompt.toPlainText()
        prompts[index].prompt = prompt
        prompts[index].negative_prompt = negative_prompt
        self.settings_manager.save_and_emit("prompts", prompts)

