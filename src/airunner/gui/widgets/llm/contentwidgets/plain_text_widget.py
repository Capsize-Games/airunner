from PySide6.QtWidgets import (
    QSizePolicy,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import (
    QFontMetrics,
    QTextOption,
    QColor,
    QPalette,
    QTextCursor,
)
from PySide6.QtWidgets import QTextEdit, QFrame
from jinja2 import Environment, FileSystemLoader, select_autoescape
import os
from airunner.settings import CONTENT_WIDGETS_BASE_PATH, STATIC_BASE_PATH
from PySide6.QtWebEngineWidgets import QWebEngineView

from airunner.gui.widgets.llm.contentwidgets.base_content_widget import (
    BaseContentWidget,
)


class PlainTextWidget(BaseContentWidget):
    """Widget for displaying plain text content."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.webView = QWebEngineView(self)
        self.webView.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.webView.page().setBackgroundColor(Qt.GlobalColor.transparent)
        self.webView.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.webView.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.layout.addWidget(self.webView)
        self.font_family = "Arial"
        self.font_size = 12
        static_html_dir = os.path.join(CONTENT_WIDGETS_BASE_PATH, "html")
        self._jinja_env = Environment(
            loader=FileSystemLoader(static_html_dir),
            autoescape=select_autoescape(["html", "xml"]),
        )
        self._template = self._jinja_env.get_template("plain_text_widget.jinja2.html")

    def setContent(self, content):
        super().setContent(content)
        html_content = self._template.render(
            content=content,
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
            self.setContent(self._content)

    def updateSize(self):
        # No-op for QWebEngineView version
        pass

    def sizeHint(self):
        return QSize(600, 80)

    def minimumSizeHint(self):
        return QSize(200, 30)
