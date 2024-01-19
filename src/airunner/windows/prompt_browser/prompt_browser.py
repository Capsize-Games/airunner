from airunner.windows.prompt_browser.prompt_widget import PromptWidget
from airunner.windows.prompt_browser.templates.prompt_browser_ui import Ui_prompt_browser
from airunner.windows.base_window import BaseWindow


class PromptBrowser(BaseWindow):
    template_class_ = Ui_prompt_browser

    def initialize_window(self):
        for index, prompt_data in enumerate(self.settings["saved_prompts"]):
            widget = PromptWidget(prompt_data=prompt_data, index=index)
            self.ui.scrollAreaWidgetContents.layout().addWidget(widget)