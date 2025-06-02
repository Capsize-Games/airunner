from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
)
from PySide6.QtCore import Qt, QSize, Signal
import os
from airunner.settings import MATHJAX_VERSION, STATIC_BASE_PATH


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
            else f"{STATIC_BASE_PATH}/mathjax/MathJax-{MATHJAX_VERSION}/es5/tex-mml-chtml.js"
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
