import os
from airunner.gui.widgets.browser.templates.browser_ui import Ui_browser
import logging

from airunner.gui.widgets.base_widget import BaseWidget
from airunner.settings import CONTENT_WIDGETS_BASE_PATH

logger = logging.getLogger(__name__)


class GameWidget(BaseWidget):
    """Widget that displays a conversation using a single QWebEngineView and HTML template.

    Args:
        parent (QWidget, optional): Parent widget.
    """

    widget_class_ = Ui_browser

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def showEvent(self, event):
        super().showEvent(event)
        # Render the game template into the QWebEngineView (self.ui.stage)
        self.render_template(self.ui.stage, "game.jinja2.html")
