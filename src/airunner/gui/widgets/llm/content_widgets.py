from PySide6.QtWidgets import (
    QTextEdit,
    QWidget,
    QVBoxLayout,
    QSizePolicy,
    QFrame,
)
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import (
    QFontMetrics,
    QTextOption,
    QColor,
    QPalette,
    QTextCursor,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
import html
import os


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

    @property
    def mathjax_url(self) -> str:
        use_cdn = os.environ.get("AIRUNNER_MATHJAX_CDN", "0") == "1"
        return (
            ("https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js")
            if use_cdn
            else "http://127.0.0.1:8765/tex-mml-chtml.js"
        )

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
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.textEdit.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.textEdit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

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
        self.sizeChanged.emit()  # Ensure sizeChanged is always emitted on content update

    def appendText(self, text):
        # Append text as it is streamed in
        cursor = self.textEdit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.textEdit.setTextCursor(cursor)
        self.textEdit.insertPlainText(text)
        self._content += text
        self.updateSize()
        self.sizeChanged.emit()

    def setFont(self, font):
        self.textEdit.setFont(font)
        self.updateSize()

    def updateSize(self):
        """
        Update the size of the widget based on the content height.
        """
        doc = self.textEdit.document()
        doc_height = doc.documentLayout().documentSize().height()
        height = doc_height + 10  # Add a little padding
        self.textEdit.setMinimumHeight(int(height))
        self.sizeChanged.emit()

    def sizeHint(self):
        """
        Provide a size hint based on the content size and the parent widget's width.
        """
        doc_layout = self.textEdit.document().documentLayout()
        width = min(
            max(300, int(self.textEdit.document().idealWidth()) + 20),
            self.parentWidget().width() if self.parentWidget() else 800,
        )
        height = max(50, int(doc_layout.documentSize().height()) + 10)
        return QSize(width, height)

    def minimumSizeHint(self):
        """
        Provide a minimum size hint based on the font metrics.
        """
        font_metrics = QFontMetrics(self.textEdit.font())
        min_height = font_metrics.lineSpacing() * 2 + 10
        return QSize(200, int(min_height))


class MarkdownWidget(BaseContentWidget):
    """Widget for displaying markdown content as rendered HTML with syntax highlighting."""

    def __init__(self, parent=None):
        super().__init__(parent)
        # Using QWebEngineView for better HTML/CSS rendering
        self.webView = QWebEngineView(self)

        # Configure the web view
        self.webView.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.webView.page().setBackgroundColor(Qt.GlobalColor.transparent)
        self.webView.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.webView.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Set up scrollbar policies - don't use WebEngine settings for this
        # as it may vary across Qt versions

        # Set size policy
        self.webView.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )

        # Add to layout
        self.layout.addWidget(self.webView)

        # Store font properties
        self.font_family = "Arial"
        self.font_size = 14

        # Track content height
        self._content_height = 100

    def setContent(self, content):
        super().setContent(content)
        # Add wrapping HTML with CSS for better appearance and dark theme support
        self.webView.setHtml(self._wrap_html_content(content))

        # Adjust height after content is loaded
        self.webView.loadFinished.connect(self._adjust_height)
        self.sizeChanged.emit()  # Emit on content update

    def _adjust_height(self, success):
        if success:
            # Run JavaScript to measure content height, but check for nulls
            self.webView.page().runJavaScript(
                """
                (function() {
                    if (document.body && document.body.style) {
                        document.body.style.overflow = 'hidden';
                    }
                    if (document.documentElement && document.documentElement.style) {
                        document.documentElement.style.overflow = 'hidden';
                    }
                    var height = (document.body && document.body.scrollHeight) ? document.body.scrollHeight : 100;
                    window.scrollTo(0,0);
                    return height;
                })()
                """,
                self._set_content_height,
            )

    def _set_content_height(self, height):
        if height and height > 0:
            self._content_height = height
            self.webView.setMinimumHeight(height)
            self.updateGeometry()
            self.sizeChanged.emit()

    def _wrap_html_content(self, content):
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
        /* Regular pre/code styles */
        pre {{
            white-space: pre-wrap;
            background-color: #2d2d2d;
            border-radius: 5px;
            padding: 10px;
            margin: 10px 0;
            border: 1px solid #444;
            overflow-x: auto;
        }}
        code {{
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            background-color: #2d2d2d;
            padding: 2px 4px;
            border-radius: 3px;
        }}
        /* Pygments code highlighting classes */
        .codehilite {{
            background-color: #2d2d2d !important;
            border-radius: 6px;
            margin: 10px 0;
            padding: 0;
            border: 1px solid #444;
            overflow-x: auto;
        }}
        .codehilite pre {{
            margin: 0;
            padding: 10px 5px 10px 5px; /* Reduced left and right padding */
            background-color: transparent;
            border: none;
        }}
        /* Line numbers */
        .linenodiv {{
            background-color: #262626;
            border-right: 1px solid #444;
            padding: 3px 5px 3px 3px; /* Reduced left and top/bottom padding */
            color: #777;
            text-align: right;
            user-select: none;
            margin-right: 5px; /* Reduced margin */
        }}
        /* Syntax colors - based on the monokai theme */
        .codehilite .hll {{ background-color: #49483e }}
        .codehilite .c {{ color: #75715e }} /* Comment */
        .codehilite .err {{ color: #960050; background-color: #1e0010 }} /* Error */
        .codehilite .k {{ color: #66d9ef }} /* Keyword */
        .codehilite .l {{ color: #ae81ff }} /* Literal */
        .codehilite .n {{ color: #f8f8f2 }} /* Name */
        .codehilite .o {{ color: #f92672 }} /* Operator */
        .codehilite .p {{ color: #f8f8f2 }} /* Punctuation */
        .codehilite .ch {{ color: #75715e }} /* Comment.Hashbang */
        .codehilite .cm {{ color: #75715e }} /* Comment.Multiline */
        .codehilite .cp {{ color: #75715e }} /* Comment.Preproc */
        .codehilite .cpf {{ color: #75715e }} /* Comment.PreprocFile */
        .codehilite .c1 {{ color: #75715e }} /* Comment.Single */
        .codehilite .cs {{ color: #75715e }} /* Comment.Special */
        .codehilite .kc {{ color: #66d9ef }} /* Keyword.Constant */
        .codehilite .kd {{ color: #66d9ef }} /* Keyword.Declaration */
        .codehilite .kn {{ color: #f92672 }} /* Keyword.Namespace */
        .codehilite .kp {{ color: #66d9ef }} /* Keyword.Pseudo */
        .codehilite .kr {{ color: #66d9ef }} /* Keyword.Reserved */
        .codehilite .kt {{ color: #66d9ef }} /* Keyword.Type */
        .codehilite .ld {{ color: #e6db74 }} /* Literal.Date */
        .codehilite .m {{ color: #ae81ff }} /* Literal.Number */
        .codehilite .s {{ color: #e6db74 }} /* Literal.String */
        .codehilite .na {{ color: #a6e22e }} /* Name.Attribute */
        .codehilite .nb {{ color: #f8f8f2 }} /* Name.Builtin */
        .codehilite .nc {{ color: #a6e22e }} /* Name.Class */
        .codehilite .no {{ color: #66d9ef }} /* Name.Constant */
        .codehilite .nd {{ color: #a6e22e }} /* Name.Decorator */
        .codehilite .ni {{ color: #f8f8f2 }} /* Name.Entity */
        .codehilite .ne {{ color: #a6e22e }} /* Name.Exception */
        .codehilite .nf {{ color: #a6e22e }} /* Name.Function */
        .codehilite .nl {{ color: #f8f8f2 }} /* Name.Label */
        .codehilite .nn {{ color: #f8f8f2 }} /* Name.Namespace */
        /* Table styles */
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 10px 0;
        }}
        th, td {{
            border: 1px solid #666;
            padding: 8px;
            text-align: left;
        }}
        th {{
            background-color: #444;
        }}
        </style>
        </head>
        <body style='background:transparent !important;height:auto;width:100%;margin:0;padding:0;overflow:visible !important;'>
        {content}
        </body>
        </html>
        """

    def setFont(self, font):
        self.font_family = font.family()
        self.font_size = font.pointSize()
        if self._content:
            # Re-render with new font settings
            self.setContent(self._content)

    def sizeHint(self):
        width = 500
        height = max(100, self._content_height)
        return QSize(width, height)

    def minimumSizeHint(self):
        return QSize(300, 100)


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
