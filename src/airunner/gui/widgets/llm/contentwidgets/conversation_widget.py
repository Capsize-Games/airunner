"""
ConversationWidget: Single QWebEngineView-based chat display widget.

Renders the entire conversation as HTML using Jinja2, replacing per-message widgets.

See REFACTOR.md for design rationale.
"""

from typing import List, Dict, Any
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtWebEngineWidgets import QWebEngineView
from jinja2 import (
    Environment,
    FileSystemLoader,
    select_autoescape,
)
import os
import logging
from airunner.utils.text.formatter_extended import FormatterExtended
from airunner.settings import CONTENT_WIDGETS_BASE_PATH

logger = logging.getLogger(__name__)


class ConversationWidget(QWidget):
    """Widget that displays a conversation using a single QWebEngineView and HTML template.

    Args:
        parent (QWidget, optional): Parent widget.
    """

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)
        self._view = QWebEngineView(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._view)
        self.setLayout(layout)

        # Set up Jinja2 environment with correct static content widgets path
        static_html_dir = os.path.join(CONTENT_WIDGETS_BASE_PATH, "html")
        self._env = Environment(
            loader=FileSystemLoader(static_html_dir),
            autoescape=select_autoescape(["html", "xml"]),
        )
        self._template = self._env.get_template("conversation.html")

    def _get_widget_template_for_type(self, content_type: str) -> str:
        """Return the relative path to the widget template for a given content type."""
        mapping = {
            FormatterExtended.FORMAT_PLAINTEXT: "plain_text_widget.jinja2.html",
            FormatterExtended.FORMAT_LATEX: "latex_widget.jinja2.html",
            FormatterExtended.FORMAT_MIXED: "mixed_content_widget.jinja2.html",
            FormatterExtended.FORMAT_MARKDOWN: "content_widget.jinja2.html",
        }
        return mapping.get(
            content_type,
            "plain_text_widget.jinja2.html",
        )

    def set_conversation(self, messages: List[Dict[str, Any]]) -> None:
        """Update the conversation display.

        Args:
            messages (List[Dict[str, Any]]): List of message dicts (sender, text, timestamp, etc).
        """
        # Enrich each message with widget_template and content fields
        enriched_messages = []
        for msg in messages:
            content = msg.get("text") or msg.get("content") or ""
            fmt = FormatterExtended.format_content(content)
            widget_template = self._get_widget_template_for_type(fmt["type"])
            enriched_messages.append(
                {
                    **msg,
                    "widget_template": widget_template,
                    "content": fmt["content"],
                    "content_type": fmt["type"],
                    "parts": fmt.get("parts"),
                    # Provide defaults for widget templates
                    "font_size": 16,
                    "static_base_path": "/static/content_widgets",
                    "base_href": None,
                }
            )
        html = self._template.render(messages=enriched_messages)
        self._view.setHtml(html)
        self._view.page().runJavaScript(
            """
            var container = document.getElementById('conversation-container');
            if (container) { container.scrollTop = container.scrollHeight; }
            """
        )
