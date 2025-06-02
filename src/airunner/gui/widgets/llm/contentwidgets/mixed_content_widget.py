import os
from PySide6.QtWidgets import (
    QSizePolicy,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtWebEngineWidgets import QWebEngineView
import html

from jinja2 import Environment, FileSystemLoader, select_autoescape
from airunner.gui.widgets.llm.contentwidgets.base_content_widget import (
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
        html_body = ""
        for part in parts:
            if part["type"] == "latex":
                html_body += part["content"]
            else:
                html_body += f"<span class='text'>{html.escape(part['content']).replace('\\n', '<br>')}</span>"
        return f"""
        <html>
        <head>
        <script type='text/javascript'>
          window.MathJax = {{
            tex: {{inlineMath: [['$','$'], ['\\(','\\)']], displayMath: [['$$','$$'], ['\\[','\\]']]}},
            options: {{ skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code'] }},
            svg: {{ fontCache: 'global' }}
          }};
        </script>
        <script type='text/javascript' src='{self.mathjax_url}'></script>
        <style>
        html {{
            width: 100%;
            height: auto;
            box-sizing: border-box;
        }}
        body {{
            color: #fff !important;
            font-family: '{self.font_family}', 'Arial', 'Liberation Sans', sans-serif !important;
            font-size: {self.font_size}px;
            margin: 0;
            padding: 0;
            height: auto;
            width: 100%;
            box-sizing: border-box;
            overflow: visible !important;
            border: 4px solid blue !important;
        }}
        .text {{
            white-space: pre-wrap;
            border: 4px solid green !important;
            display: inline-block;
            background: rgba(0,255,0,0.08) !important;
        }}
        .latex-debug {{
            border: 4px dashed orange !important;
            background: rgba(255,165,0,0.08) !important;
            display: inline-block;
        }}
        </style>
        </head>
        <body>
          {self._wrap_latex_debug(html_body)}
        </body>
        </html>
        """

    def _wrap_latex_debug(self, html_body: str) -> str:
        """Wrap LaTeX content in a debug span for border visibility."""
        import re

        # This is a simple regex to wrap LaTeX blocks (very basic, for debug only)
        # It will wrap $$...$$ and $...$ blocks
        html_body = re.sub(
            r"(\$\$.*?\$\$)",
            r'<span class="latex-debug">\\1</span>',
            html_body,
            flags=re.DOTALL,
        )
        html_body = re.sub(
            r"(\$[^$]+\$)", r'<span class="latex-debug">\\1</span>', html_body
        )
        return html_body

    def sizeHint(self):
        return QSize(9000, 150)

    def minimumSizeHint(self):
        return QSize(9000, 50)
