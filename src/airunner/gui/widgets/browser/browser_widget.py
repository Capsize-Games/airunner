import re
import os
import hashlib
from airunner.enums import SignalCode
from airunner.gui.widgets.browser.templates.browser_ui import Ui_browser
import logging
from trafilatura import extract
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lex_rank import LexRankSummarizer

from PySide6.QtCore import Slot, QUrl
from airunner.gui.widgets.base_widget import BaseWidget

logger = logging.getLogger(__name__)


class BrowserWidget(BaseWidget):
    """Widget that displays a conversation using a single QWebEngineView and HTML template.

    Args:
        parent (QWidget, optional): Parent widget.
    """

    widget_class_ = Ui_browser

    def __init__(self, *args, **kwargs):
        self.signal_handlers = {
            SignalCode.BROWSER_NAVIGATE_SIGNAL: self.on_browser_navigate,
        }
        super().__init__(*args, **kwargs)
        self.registered: bool = False
        self.ui.stage.loadFinished.connect(self.on_load_finished)
        self.ui.url.returnPressed.connect(self.on_submit_button_clicked)
        self._page_cache = {
            "html": None,
            "plaintext": None,
            "summary": None,
            "url": None,
        }
        # Set QWebEngineView background to transparent/black
        self.ui.stage.setStyleSheet("background: #111;")
        self.ui.stage.page().setBackgroundColor("#111111")

    @Slot()
    def on_next_button_clicked(self) -> None:
        """Navigate forward in the browser history."""
        self.ui.stage.forward()

    @Slot()
    def on_back_button_clicked(self) -> None:
        """Navigate backward in the browser history."""
        self.ui.stage.back()

    @Slot()
    def on_refresh_button_clicked(self) -> None:
        """Reload the current page in the browser."""
        self.ui.stage.reload()

    @Slot(bool)
    def on_plaintext_button_toggled(self, checked: bool) -> None:
        """Switch to plain text mode."""
        if checked and self._page_cache["plaintext"]:
            html = self._format_plaintext_as_html(
                self._page_cache["plaintext"]
            )
            self.ui.stage.setHtml(html, QUrl(self._page_cache["url"]))
        elif not checked and self._page_cache["html"]:
            # Restore the original HTML using setUrl to reload the page
            if self._page_cache["url"]:
                self.ui.stage.setUrl(QUrl(self._page_cache["url"]))

    @Slot(bool)
    def on_summarize_button_toggled(self, checked: bool) -> None:
        """Summarize the current page."""
        if checked and self._page_cache["summary"]:
            html = self._format_plaintext_as_html(self._page_cache["summary"])
            self.ui.stage.setHtml(html, QUrl(self._page_cache["url"]))
        elif not checked and self._page_cache["html"]:
            # Restore the original HTML using setUrl to reload the page
            if self._page_cache["url"]:
                self.ui.stage.setUrl(QUrl(self._page_cache["url"]))

    @Slot()
    def on_submit_button_clicked(self) -> None:
        """Sanitize and load the URL in the QWebEngineView.

        1. Ensure https is used
        2. Add scheme if missing
        3. Check if the URL is valid
        4. Load the URL in the QWebEngineView, using cache if available
        5. Update the URL field if it was modified
        6. Deselect the URL field
        """
        url = self.ui.url.text().strip()
        if not url:
            return
        original_url = url
        # Add scheme if missing
        if not url.startswith("http://") and not url.startswith("https://"):
            url = f"https://{url}"
        # Always use https
        url = url.replace("http://", "https://", 1)
        # Update the URL field if it was modified
        if url != original_url:
            self.ui.url.setText(url)
        # Deselect the URL field
        self.ui.url.clearFocus()
        # Basic URL validation (allow domain or IP, with optional path/query)
        pattern = re.compile(
            r"^https://([\w.-]+|\d{1,3}(?:\.\d{1,3}){3})(?::\d+)?(?:[/?#][^\s]*)?$"
        )
        if pattern.match(url):
            # Check cache before loading
            cache_dir = os.path.join(
                os.path.expanduser(self.path_settings.base_path),
                "cache",
                "browser",
            )
            os.makedirs(cache_dir, exist_ok=True)
            url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()
            cache_path = os.path.join(cache_dir, f"{url_hash}.html")
            if os.path.exists(cache_path):
                with open(cache_path, "r", encoding="utf-8") as f:
                    html = f.read()
                # Emit the signal with the HTML string as a document
                self.emit_signal(
                    SignalCode.RAG_LOAD_DOCUMENTS,
                    {
                        "documents": [html],
                        "type": "html_string",
                        "clear_documents": True,
                    },
                )
                self.ui.stage.setHtml(html, QUrl(url))
            else:
                self.ui.stage.setUrl(QUrl(url))
        else:
            logger.warning(f"Invalid URL entered: {url}")

    def on_browser_navigate(self, data):
        print("navigate", data)
        url = data.get("url", None)
        if url is not None:
            self.ui.stage.load(url)
        else:
            self.logger.error("No URL provided for navigation.")

    def _format_plaintext_as_html(self, text: str) -> str:
        """Wrap plaintext or summary in simple HTML for display with dark background."""
        return (
            "<html><body style='background:#111;color:#eee;font-family:monospace;white-space:pre-wrap;padding:1em;'>"
            f"{text}"
            "</body></html>"
        )

    def on_load_finished(self, ok):
        if ok:
            # Get the HTML content from the QWebEngineView
            def handle_html(html):
                cache_dir = os.path.join(
                    os.path.expanduser(self.path_settings.base_path),
                    "cache",
                    "browser",
                )
                os.makedirs(cache_dir, exist_ok=True)
                url = self.ui.stage.url().toString()
                url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()
                cache_path = os.path.join(cache_dir, f"{url_hash}.html")
                with open(cache_path, "w", encoding="utf-8") as f:
                    f.write(html)
                # In-memory cache
                self._page_cache["html"] = html
                self._page_cache["url"] = url
                # Extract plaintext
                plaintext = extract(html) or ""
                self._page_cache["plaintext"] = plaintext
                # Summarize using sumy LexRank (as in conversation.py)
                summary = ""
                if plaintext:
                    try:
                        parser = PlaintextParser.from_string(
                            plaintext, Tokenizer("english")
                        )
                        summarizer = LexRankSummarizer()
                        sentence_count = 1
                        summary_sentences = summarizer(
                            parser.document, sentence_count
                        )
                        summary = "\n".join(
                            [str(sentence) for sentence in summary_sentences]
                        )
                    except Exception as e:
                        logger.warning(f"Summarization failed: {e}")
                self._page_cache["summary"] = summary
                # If plaintext or summary toggles are active, update the view
                if (
                    hasattr(self.ui, "plaintext_button")
                    and self.ui.plaintext_button.isChecked()
                    and plaintext
                ):
                    html_out = self._format_plaintext_as_html(plaintext)
                    self.ui.stage.setHtml(html_out, QUrl(url))
                elif (
                    hasattr(self.ui, "summarize_button")
                    and self.ui.summarize_button.isChecked()
                    and summary
                ):
                    html_out = self._format_plaintext_as_html(summary)
                    self.ui.stage.setHtml(html_out, QUrl(url))
                # Emit the signal with the HTML string as a document
                self.emit_signal(
                    SignalCode.RAG_LOAD_DOCUMENTS,
                    {
                        "documents": [html],
                        "type": "html_string",
                        "clear_documents": True,
                    },
                )

            self.ui.stage.page().toHtml(handle_html)
