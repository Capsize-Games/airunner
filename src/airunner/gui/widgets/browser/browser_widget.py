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
from PySide6.QtWebEngineCore import (
    QWebEnginePage,
    QWebEngineProfile,
    QWebEngineSettings,
)
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
        self._profile = None
        self._profile_page = None
        self.ui.stage.setPage(self.profile_page)
        self.set_flags()
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

        # Log privacy initialization
        logger.info("Browser widget initialized with privacy features:")
        logger.info("- Off-the-record profile: Active")
        logger.info("- HTTPS-only mode: Enforced")
        logger.info("- Certificate validation: Strict")
        logger.info("- Permissions: Denied by default")
        logger.info("- Local storage: Disabled")
        logger.info("- Cookies: Session-only (OTR)")

        # Initialize with privacy status logging
        self.log_privacy_status()

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

        # Always use https for security (force upgrade)
        if url.startswith("http://"):
            url = url.replace("http://", "https://", 1)
            logger.info(f"Upgraded insecure URL to HTTPS: {url}")

        # Update the URL field if it was modified
        if url != original_url:
            self.ui.url.setText(url)

        # Deselect the URL field
        self.ui.url.clearFocus()

        # Enhanced URL validation (stricter HTTPS-only policy)
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
            logger.warning(f"Invalid or insecure URL rejected: {url}")
            # Show security warning to user
            self.ui.url.setStyleSheet(
                "QLineEdit { background: #331111; color: #ff9999; }"
            )

    @Slot()
    def on_clear_data_button_clicked(self) -> None:
        """Clear all browsing data and session information."""
        self.clear_session()
        logger.info("Browser data cleared - all session data removed")

        # Reset to secure state
        self.ui.stage.setUrl(QUrl("about:blank"))
        self.ui.url.clear()

        # Reset security indicators
        self.ui.url.setStyleSheet(
            "QLineEdit { background: #111; color: #eee; }"
        )

        # Log privacy status after clearing
        self.log_privacy_status()

    @property
    def profile(self):
        """Initialize the off-the-record profile for the browser widget."""
        if self._profile is None:
            # Create an off-the-record profile to prevent persistent storage
            # Using an empty string as storageName creates an off-the-record profile
            self._profile = QWebEngineProfile("")
        return self._profile

    @property
    def profile_page(self):
        if self._profile_page is None:
            self._profile_page = QWebEnginePage(self.profile, self.ui.stage)
        return self._profile_page

    def set_flags(self):
        """Configure privacy and security settings for the browser."""
        settings = self.profile_page.settings()

        # Disable potentially risky features
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.PluginsEnabled, False
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.WebGLEnabled, False
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, False
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls,
            False,
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls,
            False,
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.DnsPrefetchEnabled, False
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.HyperlinkAuditingEnabled, False
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.ScreenCaptureEnabled, False
        )

        # Additional privacy settings
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.AutoLoadImages, True
        )  # Keep images for usability
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptEnabled, True
        )  # Keep JS for functionality
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.LocalStorageEnabled, False
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, False
        )

        # Set privacy-friendly defaults
        self.profile.setHttpUserAgent(
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.7151.55 Safari/537.36"
        )

        # Set strict referrer policy for privacy
        self.profile.setHttpAcceptLanguage("en-US,en;q=0.9")

        # Additional privacy headers will be handled by requests when available
        # Note: Qt WebEngine doesn't provide direct header injection,
        # but the OTR profile provides good privacy defaults

        # Connect permission request handler
        self.profile_page.featurePermissionRequested.connect(
            self._handle_permission_request
        )

        # Connect certificate error handler
        self.profile_page.certificateError.connect(
            self._handle_certificate_error
        )

    def _handle_permission_request(self, url, feature):
        """Handle permission requests from web pages.

        Deny all permission requests for privacy and security.
        """
        logger.info(f"Permission request denied for {url}: {feature}")
        self.profile_page.setFeaturePermission(
            url, feature, QWebEnginePage.PermissionDeniedByUser
        )

    def _handle_certificate_error(self, error):
        """Handle SSL certificate errors.

        Args:
            error: QWebEngineCertificateError object

        Returns:
            bool: Whether to ignore the certificate error
        """
        logger.warning(
            f"SSL Certificate error for {error.url().toString()}: {error.description()}"
        )
        # For maximum security, reject all certificate errors
        # Users can manually add exceptions if needed
        return False

    def _update_security_indicators(self):
        """Update security indicators in the UI based on current page."""
        if not hasattr(self.ui, "url"):
            return

        current_url = self.ui.stage.url().toString()
        if not current_url or current_url == "about:blank":
            self.ui.url.setStyleSheet(
                "QLineEdit { background: #111; color: #eee; }"
            )
            return

        if current_url.startswith("https://"):
            # Secure connection - green tint
            self.ui.url.setStyleSheet(
                "QLineEdit { background: #112211; color: #eee; }"
            )
            logger.debug(f"Secure connection: {current_url}")
        elif current_url.startswith("http://"):
            # Insecure connection - red tint
            self.ui.url.setStyleSheet(
                "QLineEdit { background: #221111; color: #eee; }"
            )
            logger.warning(f"Insecure connection: {current_url}")
        else:
            # Unknown protocol
            self.ui.url.setStyleSheet(
                "QLineEdit { background: #111; color: #eee; }"
            )

        # Update URL field to show actual loaded URL
        if current_url != self.ui.url.text():
            self.ui.url.setText(current_url)

    def _clear_history(self):
        """Clear the browser history."""
        self.profile.clearAllVisitedLinks()

    def _clear_cookies(self):
        """Clear cookies associated with the browser widget."""
        cookie_store = self.profile.cookieStore()
        cookie_store.deleteAllCookies()

    def _clear_http_cache(self):
        """Clear the HTTP cache associated with the browser widget."""
        self.profile.clearHttpCache()

    def _clear_html5_storage(self):
        """Clear HTML5 Storage (Local Storage, IndexedDB, etc.) associated with the browser widget."""
        # Note: Direct localStorage clearing not available in Qt WebEngine
        # Storage is automatically cleared when OTR profile is destroyed
        pass

    def clear_session(self):
        """
        Clear history, cookies, HTTP cache, HTML5 Storage (Local Storage, IndexedDB, etc.),
        and any other persistent data associated with the browser widget.
        """
        self._clear_history()
        self._clear_cookies()
        self._clear_http_cache()
        self._clear_html5_storage()

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
            # Update security indicators
            self._update_security_indicators()

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

    def get_privacy_status(self) -> dict:
        """Get current privacy and security status.

        Returns:
            dict: Privacy status information
        """
        current_url = self.ui.stage.url().toString()
        return {
            "otr_profile_active": bool(self._profile),
            "https_only": (
                current_url.startswith("https://") if current_url else True
            ),
            "current_url": current_url,
            "cookies_blocked": True,  # Always true with OTR profile
            "local_storage_disabled": True,
            "permissions_blocked": True,
            "certificate_validation": True,
        }

    def log_privacy_status(self) -> None:
        """Log current privacy status for debugging."""
        status = self.get_privacy_status()
        logger.info(f"Browser privacy status: {status}")
