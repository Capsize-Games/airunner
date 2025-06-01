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
        super().__init__(*args, **kwargs)
        self.registered: bool = False
        self.signal_handlers = {
            SignalCode.BROWSER_NAVIGATE_SIGNAL: self.on_browser_navigate,
        }

    def on_browser_navigate(self, data):
        url = data.get("url", None)
        if url is not None:
            self.ui.stage.load(url)
        else:
            self.logger.error("No URL provided for navigation.")
