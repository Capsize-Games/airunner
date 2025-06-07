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
from airunner.utils.text.formatter_extended import FormatterExtended


class MarkdownWidget(BaseContentWidget):
    """Widget for displaying markdown content as rendered HTML with syntax highlighting.

    Args:
        parent (QWidget, optional): The parent widget.

    Public Methods:
        setContent(content: str): Set the markdown or HTML content to display. Accepts either raw markdown or HTML. If markdown is detected, it is converted to HTML with code block support.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        # Using QWebEngineView for better HTML/CSS rendering
        self.webView = QWebEngineView(self)

        # Configure the web view
        self.webView.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.webView.page().setBackgroundColor(Qt.GlobalColor.transparent)
        self.webView.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.webView.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.layout.addWidget(self.webView)

        # Store font properties
        self.font_family = "Arial"
        self.font_size = 9

        # Track content height
        self._content_height = 100
        self._allow_shrink = True  # Allow shrinking by default

        self.webView.loadFinished.connect(self._adjust_height)

        # Update: Load template from new static location using CONTENT_WIDGETS_BASE_PATH
        static_html_dir = os.path.join(CONTENT_WIDGETS_BASE_PATH, "html")
        self._jinja_env = Environment(
            loader=FileSystemLoader(static_html_dir),
            autoescape=select_autoescape(["html", "xml"]),
        )
        self._template = self._jinja_env.get_template(
            "content_widget.jinja2.html"
        )

    def setContent(self, content, streaming: bool = False):
        """Set the markdown or HTML content to display.

        Args:
            content (str): Markdown or HTML content. If markdown, it is converted to HTML with code block support.
            streaming (bool): If True, disables shrinking. If False, allows shrinking (default: False).
        """
        super().setContent(content)
        self._allow_shrink = not streaming
        # Detect if content is raw markdown (not HTML)
        if not content.strip().lower().startswith("<"):
            html_content = FormatterExtended._render_markdown_to_html(content)
        else:
            html_content = content
        self.webView.setHtml(
            self._template.render(
                content=html_content,
                mathjax_url=self.mathjax_url,
                font_family=self.font_family,
                font_size=self.font_size,
                static_base_path=f"{STATIC_BASE_PATH}/content_widgets",
                base_href=f"{STATIC_BASE_PATH}/content_widgets/",
            )
        )
        # self.sizeChanged.emit()  # Emit on content update

    def set_streaming_finished(self):
        """Call this when streaming is finished to allow shrinking and re-measure height."""
        self._allow_shrink = True
        # Re-measure height after streaming ends
        self.webView.page().runJavaScript(
            "typeof adjustContentHeight === 'function' ? adjustContentHeight() : (document.body ? document.body.scrollHeight : 100)",
            self._set_content_height,
        )

    def _adjust_height(self, success):
        if success:
            # Run JavaScript to measure content height, with fallback
            self.webView.page().runJavaScript(
                "typeof adjustContentHeight === 'function' ? adjustContentHeight() : (document.body ? document.body.scrollHeight : 100)",
                self._set_content_height,
            )

    def _set_content_height(self, height):
        if height and height > 0:
            if self._allow_shrink or height > self._content_height:
                self._content_height = height
                self.webView.setMinimumHeight(height)
                self.updateGeometry()
                self.sizeChanged.emit()

    def _wrap_html_content(self, content):
        return self._template.render(
            content=content,
            mathjax_url=self.mathjax_url,
            font_family=self.font_family,
            font_size=self.font_size,
            static_base_path=f"{STATIC_BASE_PATH}/content_widgets",
            base_href=f"{STATIC_BASE_PATH}/content_widgets/",
        )

    def setFont(self, font):
        self.font_family = font.family()
        self.font_size = font.pointSize()
        if self._content:
            # Re-render with new font settings
            self.setContent(self._content)

    def sizeHint(self):
        width = 9000
        height = max(100, self._content_height)
        return QSize(width, height)

    def minimumSizeHint(self):
        return QSize(9000, self._content_height)
