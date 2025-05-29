from PySide6.QtWidgets import (
    QSizePolicy,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtWebEngineWidgets import QWebEngineView
import html
from airunner.gui.widgets.llm.contentwidgets.base_content_widget import (
    BaseContentWidget,
)


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

        # Generate HTML with mixed content
        html_content = self._wrap_mixed_html(parts)
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
        <html style='height:auto;width:100%;background:transparent;'>
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
        html, body {{
            background: transparent !important;
            color: #fff !important;
            font-family: '{self.font_family}', 'Arial', 'Liberation Sans', sans-serif !important;
            font-size: {self.font_size}px;
            margin: 0;
            padding: 0;
            height: auto;
            width: 100%;
            box-sizing: border-box;
            overflow: visible !important;
        }}
        .text {{
            white-space: pre-wrap;
        }}
        </style>
        </head>
        <body style='background:transparent !important;height:auto;width:100%;margin:0;padding:0;overflow:visible !important;'>
          {html_body}
        </body>
        </html>
        """

    def sizeHint(self):
        return QSize(500, 150)

    def minimumSizeHint(self):
        return QSize(300, 50)
