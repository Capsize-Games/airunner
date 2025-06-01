from airunner.enums import SignalCode
from airunner.gui.widgets.browser.templates.browser_ui import Ui_browser
import logging

from airunner.gui.widgets.base_widget import BaseWidget

logger = logging.getLogger(__name__)


class BrowserWidget(BaseWidget):
    """Widget that displays a conversation using a single QWebEngineView and HTML template.

    Args:
        parent (QWidget, optional): Parent widget.
    """

    widget_class_ = Ui_browser

    def __init__(self, *args, **kwargs):
        self.signal_handlers = {
            SignalCode.BROWSER_NAVIGATE_SIGNAL: self.on_browser_navigate,
        }
        super().__init__(*args, **kwargs)
        self.registered: bool = False
        self.ui.stage.loadFinished.connect(self.on_load_finished)

    def on_browser_navigate(self, data):
        print("navigate", data)
        url = data.get("url", None)
        if url is not None:
            self.ui.stage.load(url)
        else:
            self.logger.error("No URL provided for navigation.")

    def on_load_finished(self, ok):
        if ok:
            # Get the HTML content from the QWebEngineView
            def handle_html(html):
                # Emit the signal with the HTML string as a document
                self.emit_signal(
                    SignalCode.RAG_LOAD_DOCUMENTS,
                    {"documents": [html], "type": "html_string"},
                )

            self.ui.stage.page().toHtml(handle_html)
