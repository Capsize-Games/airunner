from PySide6.QtWidgets import (
    QSizePolicy,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtWebEngineWidgets import QWebEngineView

from airunner.gui.widgets.llm.contentwidgets.base_content_widget import (
    BaseContentWidget,
)


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
        """Set the markdown or HTML content to display.

        Args:
            content (str): Markdown or HTML content. If markdown, it is converted to HTML with code block support.
        """
        super().setContent(content)
        # Detect if content is raw markdown (not HTML)
        if not content.strip().lower().startswith("<"):
            from airunner.utils.text.formatter_extended import (
                FormatterExtended,
            )

            html_content = FormatterExtended._render_markdown_to_html(content)
        else:
            html_content = content
        self.webView.setHtml(self._wrap_html_content(html_content))
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
