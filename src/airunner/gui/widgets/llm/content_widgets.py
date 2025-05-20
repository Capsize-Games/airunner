from PySide6.QtWidgets import (
    QTextEdit,
    QWidget,
    QVBoxLayout,
    QTextBrowser,
    QLabel,
    QSizePolicy,
    QFrame,
)
from PySide6.QtCore import Qt, QSize, Signal, QEvent, QRectF, QObject
from PySide6.QtGui import (
    QFont,
    QFontMetrics,
    QPainter,
    QTextOption,
    QColor,
    QPalette,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
import html


class BaseContentWidget(QWidget):
    """Base class for all content widgets with common functionality."""

    sizeChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._content = ""
        # Set up a vertical layout to hold the content
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # Configure the widget for transparent background
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAutoFillBackground(False)

    def setContent(self, content):
        """Set the content for this widget - to be implemented by subclasses."""
        self._content = content

    def content(self):
        """Return the raw content."""
        return self._content

    def setFont(self, font):
        """Set the font for the content - to be implemented by subclasses."""
        pass

    def sizeHint(self):
        """Default size hint - should be overridden by subclasses."""
        return QSize(500, 100)

    def minimumSizeHint(self):
        """Default minimum size hint - should be overridden by subclasses."""
        return QSize(300, 50)


class PlainTextWidget(BaseContentWidget):
    """Widget for displaying plain text content."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.textEdit = QTextEdit(self)
        self.textEdit.setReadOnly(True)
        self.textEdit.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.textEdit.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        # Make the background transparent
        palette = self.textEdit.palette()
        palette.setColor(QPalette.ColorRole.Base, QColor(0, 0, 0, 0))
        self.textEdit.setPalette(palette)

        # Set word wrap mode to make text fit within the widget
        self.textEdit.setWordWrapMode(
            QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere
        )
        self.textEdit.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)

        # Set frame style
        self.textEdit.setFrameStyle(QFrame.Shape.NoFrame)

        # Add to layout
        self.layout.addWidget(self.textEdit)

        # Connect to document size changes
        self.textEdit.document().contentsChanged.connect(self.updateSize)

    def setContent(self, content):
        super().setContent(content)
        self.textEdit.setPlainText(content)
        self.updateSize()

    def setFont(self, font):
        self.textEdit.setFont(font)
        self.updateSize()

    def updateSize(self):
        # Calculate the size based on the document
        doc = self.textEdit.document()
        docHeight = doc.size().height()

        # Add a small padding
        height = docHeight + 10
        self.textEdit.setMinimumHeight(height)
        self.sizeChanged.emit()

    def sizeHint(self):
        doc = self.textEdit.document()
        width = min(max(500, doc.idealWidth() + 20), 1000)
        height = max(50, doc.size().height() + 10)
        return QSize(width, height)

    def minimumSizeHint(self):
        return QSize(300, 50)


class MarkdownWidget(BaseContentWidget):
    """Widget for displaying markdown content as rendered HTML."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.textBrowser = QTextBrowser(self)
        self.textBrowser.setReadOnly(True)
        self.textBrowser.setOpenExternalLinks(True)
        self.textBrowser.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.textBrowser.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        # Make background transparent
        palette = self.textBrowser.palette()
        palette.setColor(QPalette.ColorRole.Base, QColor(0, 0, 0, 0))
        self.textBrowser.setPalette(palette)

        # Set word wrap mode
        self.textBrowser.setWordWrapMode(
            QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere
        )
        self.textBrowser.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)

        # Set frame style
        self.textBrowser.setFrameStyle(QFrame.Shape.NoFrame)

        # Add to layout
        self.layout.addWidget(self.textBrowser)

        # Connect to document size changes
        self.textBrowser.document().contentsChanged.connect(self.updateSize)

    def setContent(self, content):
        super().setContent(content)
        # The content should already be HTML rendered from markdown
        self.textBrowser.setHtml(content)
        self.updateSize()

    def setFont(self, font):
        self.textBrowser.setFont(font)
        self.updateSize()

    def updateSize(self):
        # Calculate the size based on the document
        doc = self.textBrowser.document()
        docHeight = doc.size().height()

        # Set the height with a small margin
        height = docHeight + 10
        self.textBrowser.setMinimumHeight(height)
        self.sizeChanged.emit()

    def sizeHint(self):
        doc = self.textBrowser.document()
        width = min(max(500, doc.idealWidth() + 20), 1000)
        height = max(50, doc.size().height() + 10)
        return QSize(width, height)

    def minimumSizeHint(self):
        return QSize(300, 50)


class LatexWidget(BaseContentWidget):
    """Widget for displaying LaTeX content using QWebEngineView."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.webView = QWebEngineView(self)

        # Configure the web view
        self.webView.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.webView.page().setBackgroundColor(Qt.GlobalColor.transparent)

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

    def setFont(self, font):
        self.font_family = font.family()
        self.font_size = font.pointSize()
        if self._content:
            # Re-render with new font settings
            self.setContent(self._content)

    def _wrap_latex_html(self, latex_content):
        """Wrap LaTeX content in HTML with MathJax for rendering."""
        escaped_content = html.escape(latex_content)

        return f"""
        <html style='height:auto;width:100%;background:transparent;'>
        <head>
        <script type="text/javascript" async
          src="https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.7/MathJax.js?config=TeX-MML-AM_CHTML">
        </script>
        <script type="text/x-mathjax-config">
          MathJax.Hub.Config({{
            tex2jax: {{inlineMath: [['$','$'], ['\\\\(','\\\\)']],
                       displayMath: [['$$','$$'], ['\\\\[','\\\\]']]}},
            "HTML-CSS": {{
              scale: 100,
              availableFonts: ["TeX"],
              preferredFont: "TeX",
              webFont: "TeX",
              imageFont: "TeX",
              linebreaks: {{ automatic: true }}
            }},
            CommonHTML: {{
              linebreaks: {{ automatic: true }}
            }}
          }});
          
          MathJax.Hub.Queue(function() {{
            var height = document.body.scrollHeight;
            window.qtWidgetResize && window.qtWidgetResize(height);
          }});
        </script>
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
          {escaped_content}
        </body>
        </html>
        """

    def sizeHint(self):
        # A reasonable default size for LaTeX content
        return QSize(500, 150)

    def minimumSizeHint(self):
        return QSize(300, 50)


class MixedContentWidget(BaseContentWidget):
    """Widget for displaying mixed content (text with LaTeX formulas)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.webView = QWebEngineView(self)

        # Configure the web view
        self.webView.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.webView.page().setBackgroundColor(Qt.GlobalColor.transparent)

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

    def setFont(self, font):
        self.font_family = font.family()
        self.font_size = font.pointSize()
        if self._content:
            # Re-render with new font settings
            self.setContent(self._content)

    def _wrap_mixed_html(self, parts):
        """Wrap mixed content in HTML with MathJax for rendering LaTeX parts."""
        html_body = ""

        for part in parts:
            if part["type"] == "latex":
                html_body += f"<span class='latex-formula'>{html.escape(part['content'])}</span>"
            else:  # text
                html_body += f"<span class='text'>{html.escape(part['content']).replace('\n', '<br>')}</span>"

        return f"""
        <html style='height:auto;width:100%;background:transparent;'>
        <head>
        <script type="text/javascript" async
          src="https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.7/MathJax.js?config=TeX-MML-AM_CHTML">
        </script>
        <script type="text/x-mathjax-config">
          MathJax.Hub.Config({{
            tex2jax: {{inlineMath: [['$','$'], ['\\\\(','\\\\)']],
                       displayMath: [['$$','$$'], ['\\\\[','\\\\]']]}},
            "HTML-CSS": {{
              scale: 100,
              availableFonts: ["TeX"],
              preferredFont: "TeX",
              webFont: "TeX",
              imageFont: "TeX",
              linebreaks: {{ automatic: true }}
            }},
            CommonHTML: {{
              linebreaks: {{ automatic: true }}
            }}
          }});
          
          MathJax.Hub.Queue(function() {{
            var height = document.body.scrollHeight;
            window.qtWidgetResize && window.qtWidgetResize(height);
          }});
        </script>
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
