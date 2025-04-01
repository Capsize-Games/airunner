from airunner.gui.windows.prompt_browser.prompt_widget import PromptWidget
from airunner.gui.windows.prompt_browser.templates.prompt_browser_ui import Ui_prompt_browser
from airunner.gui.windows.base_window import BaseWindow


class PromptBrowser(BaseWindow):
    template_class_ = Ui_prompt_browser

    def initialize_window(self):
        self.setWindowTitle("Prompt Browser")

        for saved_prompt in self.saved_prompts:
            widget = PromptWidget(saved_prompt=saved_prompt)
            self.ui.scrollAreaWidgetContents.layout().addWidget(widget)
