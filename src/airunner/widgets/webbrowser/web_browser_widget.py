from abc import ABC

from PySide6.QtCore import Slot

import trafilatura

from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.webbrowser.templates.web_browser_ui import Ui_web_browser_widget


class WebBrowserWidget(BaseWidget, ABC):
    widget_class_ = Ui_web_browser_widget

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.browser = self.ui.webEngineView
        self.navigate("https://duckduckgo.com", search_query="ducks")
        self.get_page_html()

    def navigate(self, url, search_query=None):
        if search_query:
            search_url = f"https://duckduckgo.com/?q={search_query.replace(' ', '+')}"
            self.browser.setUrl(search_url)
        else:
            self.browser.setUrl(url)
    
    def get_page_html(self):
        self.browser.page().toHtml(lambda html: print(html))