
from PySide6.QtCore import Slot

import trafilatura

from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.webbrowser.templates.web_browser_ui import Ui_web_browser_widget
from airunner.enums import SignalCode


class WebBrowserWidget(BaseWidget):
    widget_class_ = Ui_web_browser_widget

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.html = ""
        self.browser = self.ui.webEngineView
        self.browser.page().loadFinished.connect(self.on_load_finished)
    
    @Slot()
    def submit(self):
        url = self.ui.url.text()
        url = url.lower().strip().replace("http://", "").replace("https://", "")
        self.navigate(f"https://{url}")
    
    def navigate(self, url):
        self.browser.setUrl(url)
    
    def on_load_finished(self, success):
        if success:
            self.browser.page().toHtml(self.handle_html)
        else:
            print("Failed to load the page")
    
    def handle_html(self, html):
        self.html = html
        content = trafilatura.extract(
            self.html,
            output_format="txt",
            with_metadata=False,
            include_comments=False,
            include_formatting=False,
            include_links=False
        )
        self.emit_signal(SignalCode.WEB_BROWSER_PAGE_HTML, {"content": content})
