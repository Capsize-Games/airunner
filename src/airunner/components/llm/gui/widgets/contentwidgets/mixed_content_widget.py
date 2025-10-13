import os
from PySide6.QtWidgets import (
    QSizePolicy,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtWebEngineWidgets import QWebEngineView
import html

from jinja2 import Environment, FileSystemLoader, select_autoescape
from airunner.components.llm.gui.widgets.contentwidgets.base_content_widget import (
    BaseContentWidget,
)
from airunner.settings import CONTENT_WIDGETS_BASE_PATH, STATIC_BASE_PATH


class MixedContentWidget(BaseContentWidget):
    """Widget for displaying mixed content (text with LaTeX formulas)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.webView = QWebEngineView(self)

        # Configure the web view
        self.webView.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.webView.page().setBackgroundColor(Qt.GlobalColor.transparent)
        self.webView.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.webView.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Set size policy
        self.webView.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )

        # Add to layout
        self.layout.addWidget(self.webView)

        # Store the font properties for later use
        self.font_family = "Arial"
        self.font_size = 14

    def setContent(self, parts):
        """
        Set the mixed content.

        Args:
            parts: A list of dictionaries, each with 'type' (text/latex) and 'content' keys
        """
        super().setContent(parts)

        static_html_dir = os.path.join(CONTENT_WIDGETS_BASE_PATH, "html")
        env = Environment(
            loader=FileSystemLoader(static_html_dir),
            autoescape=select_autoescape(["html", "xml"]),
        )
        template = env.get_template("mixed_content_widget.jinja2.html")
        html_content = template.render(
            content=self._wrap_mixed_html(parts),
            mathjax_url=self.mathjax_url,
            font_family=self.font_family,
            font_size=self.font_size,
            static_base_path=f"{STATIC_BASE_PATH}/content_widgets",
            base_href=f"{STATIC_BASE_PATH}/content_widgets/",
        )
        self.webView.setHtml(html_content)

        # Run JavaScript to adjust the size after rendering
        self.webView.page().runJavaScript(
            """
            document.body.style.overflow = 'hidden';
            document.documentElement.style.overflow = 'hidden';
            let height = document.body.scrollHeight;
            window.scrollTo(0,0);
            if (height > 0) {
                window.qtWidgetResize && window.qtWidgetResize(height);
            }
            """
        )
        self.sizeChanged.emit()

    def setFont(self, font):
        self.font_family = font.family()
        self.font_size = font.pointSize()
        if self._content:
            # Re-render with new font settings
            self.setContent(self._content)

    def _wrap_mixed_html(self, parts):
        html_parts = []
        for part in parts:
            if part["type"] == "latex":
                html_parts.append(part["content"])
            else:
                html_parts.append(
                    f"<span class='text-snippet'>{html.escape(part['content']).replace('\\n', '<br>')}</span>"
                )
        return "".join(html_parts)

    def sizeHint(self):
        return QSize(100, 150)

    def minimumSizeHint(self):
        return QSize(50, 50)
