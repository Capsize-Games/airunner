from PySide6.QtWidgets import (
    QSizePolicy,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtWebEngineWidgets import QWebEngineView

from airunner.gui.widgets.llm.contentwidgets.base_content_widget import (
    BaseContentWidget,
)


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

        # Set size policy
        self.webView.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )

        # Add to layout
        self.layout.addWidget(self.webView)

        # Store the font properties for later use
        self.font_family = "Arial"
        self.font_size = 14

    def setContent(self, content):
        super().setContent(content)

        # Generate HTML with LaTeX content and MathJax rendering
        html_content = self._wrap_latex_html(content)
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

    def _wrap_latex_html(self, latex_content):
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
        </style>
        </head>
        <body style='background:transparent !important;height:auto;width:100%;margin:0;padding:0;overflow:visible !important;'>
          {latex_content}
        </body>
        </html>
        """

    def sizeHint(self):
        # A reasonable default size for LaTeX content
        return QSize(500, 150)

    def minimumSizeHint(self):
        return QSize(300, 50)
