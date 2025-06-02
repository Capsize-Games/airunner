from PySide6.QtWidgets import (
    QSizePolicy,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtWebEngineWidgets import QWebEngineView

from airunner.gui.widgets.llm.contentwidgets.base_content_widget import (
    BaseContentWidget,
)
from jinja2 import Environment, FileSystemLoader, select_autoescape
import os
from airunner.settings import CONTENT_WIDGETS_BASE_PATH, STATIC_BASE_PATH


class LatexWidget(BaseContentWidget):
    """Widget for displaying LaTeX content using QWebEngineView."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.webView = QWebEngineView(self)

        # Configure the web view
        self.webView.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.webView.page().setBackgroundColor(Qt.GlobalColor.transparent)
        self.webView.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.webView.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        # Add to layout
        self.layout.addWidget(
            self.webView
        )  # Store the font properties for later use
        self.font_family = "Arial"
        self.font_size = 14

        # Jinja2 template setup
        static_html_dir = os.path.join(CONTENT_WIDGETS_BASE_PATH, "html")
        self._jinja_env = Environment(
            loader=FileSystemLoader(static_html_dir),
            autoescape=select_autoescape(["html", "xml"]),
        )
        self._template = self._jinja_env.get_template(
            "latex_widget.jinja2.html"
        )

    def setContent(self, content):
        super().setContent(content)
        html_content = self._template.render(
            content=content,
            mathjax_url=self.mathjax_url,
            font_family=self.font_family,
            font_size=self.font_size,
            static_base_path=f"{STATIC_BASE_PATH}/content_widgets",
            base_href=f"{STATIC_BASE_PATH}/content_widgets/",
        )
        self.webView.setHtml(html_content)
        self.sizeChanged.emit()

    def setFont(self, font):
        self.font_family = font.family()
        self.font_size = font.pointSize()
        if self._content:
            # Re-render with new font settings
            self.setContent(self._content)

    def sizeHint(self):
        # A reasonable default size for LaTeX content
        return QSize(9000, 150)

    def minimumSizeHint(self):
        return QSize(9000, 50)
