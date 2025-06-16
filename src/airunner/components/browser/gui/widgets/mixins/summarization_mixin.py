"""
SummarizationMixin for BrowserWidget.
Handles plaintext and summary display logic.

Google Python Style Guide applies.
"""

from PySide6.QtCore import QUrl, Slot


class SummarizationMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui.summarize_button.blockSignals(True)
        self.ui.plaintext_button.blockSignals(True)
        self.ui.summarize_button.setChecked(
            self.browser_settings["private_browsing"]
        )
        self.ui.plaintext_button.setChecked(
            self.browser_settings["plaintext_display"]
        )
        self.ui.summarize_button.blockSignals(False)
        self.ui.plaintext_button.blockSignals(False)

    @Slot(bool)
    def on_plaintext_button_toggled(self, checked: bool) -> None:
        self.update_browser_settings(plaintext_display=checked)
        if checked and self._current_display_mode != "plaintext":
            self._extract_plaintext_if_needed()
            self._set_display_mode("plaintext")
        elif not checked:
            self._set_display_mode("html")

    @Slot(bool)
    def on_summarize_button_toggled(self, checked: bool) -> None:
        """Toggle summary view for the current page."""
        self.update_browser_settings(summary_display=checked)
        if checked and self._current_display_mode != "summary":
            self._extract_summary_if_needed()
            self._set_display_mode("summary")
        elif not checked:
            self._restore_display_mode(exclude="summary")

    def _set_display_mode(self, mode: str) -> None:
        """Set the display mode to 'html', 'plaintext', or 'summary'."""
        if mode == "html":
            url = self._page_cache.get("url", "")
            self.logger.info(f"Restoring HTML view with URL: {url}")
            if url:
                self.ui.stage.setUrl(QUrl("about:blank"))
                self.ui.stage.setUrl(QUrl(url))
                self._current_display_mode = "html"
            else:
                self.logger.warning(
                    "No URL found in _page_cache to restore HTML view."
                )
            return
        html = None
        if mode == "plaintext":
            text = self._page_cache.get("plaintext")
            if not text:
                self.logger.warning("Plaintext not available for display.")
                html = self._format_plaintext_as_html(
                    "<b>No plaintext available for this page.</b>"
                )
            else:
                html = self._format_plaintext_as_html(text)
        elif mode == "summary":
            text = self._page_cache.get("summary")
            if not text:
                self.logger.warning("Summary not available for display.")
                html = self._format_plaintext_as_html(
                    "<b>No summary available for this page.</b>"
                )
            else:
                html = self._format_plaintext_as_html(text)
        if html:
            self.ui.stage.setHtml(html, QUrl(self._page_cache.get("url", "")))
            self._current_display_mode = mode

    def _extract_plaintext_if_needed(self) -> None:
        """Extract and cache plaintext from the current page if not already cached, and update UI if needed."""
        if not self._page_cache.get("plaintext"):
            try:

                def _store_plaintext(text):
                    self._page_cache["plaintext"] = text or ""
                    # If user is still in plaintext mode, update the display
                    if (
                        hasattr(self.ui, "plaintext_button")
                        and self.ui.plaintext_button.isChecked()
                    ):
                        self._set_display_mode("plaintext")

                if hasattr(self.ui.stage, "page"):
                    self.ui.stage.page().runJavaScript(
                        "document.body.innerText", _store_plaintext
                    )
            except Exception as e:
                self.logger.warning(f"Failed to extract plaintext: {e}")

    def _extract_summary_if_needed(self) -> None:
        """Extract and cache a summary from the current page if not already cached, and update UI if needed."""
        if not self._page_cache.get("summary"):
            # Use plaintext as the source for summary
            plaintext = self._page_cache.get("plaintext")
            if not plaintext:
                # Extract plaintext first, then summarize in callback
                def _after_plaintext(text):
                    self._page_cache["plaintext"] = text or ""
                    self._page_cache["summary"] = self._summarize_text(
                        text or ""
                    )
                    if (
                        hasattr(self.ui, "summarize_button")
                        and self.ui.summarize_button.isChecked()
                    ):
                        self._set_display_mode("summary")

                if hasattr(self.ui.stage, "page"):
                    self.ui.stage.page().runJavaScript(
                        "document.body.innerText", _after_plaintext
                    )
            else:
                self._page_cache["summary"] = self._summarize_text(plaintext)

    def _summarize_text(self, text: str) -> str:
        """Return a simple summary of the text (placeholder: first 500 chars)."""
        if not text:
            return ""
        # TODO: Replace with real LLM or summarization logic
        return text[:500] + ("..." if len(text) > 500 else "")

    def _restore_display_mode(self, exclude: str = "") -> None:
        """Restore the display mode to the most appropriate available mode, excluding the given one."""
        # Priority: summary > plaintext > html
        if (
            exclude != "summary"
            and hasattr(self.ui, "summarize_button")
            and self.ui.summarize_button.isChecked()
            and self._page_cache["summary"]
        ):
            self._set_display_mode("summary")
        elif (
            exclude != "plaintext"
            and hasattr(self.ui, "plaintext_button")
            and self.ui.plaintext_button.isChecked()
            and self._page_cache["plaintext"]
        ):
            self._set_display_mode("plaintext")
        elif self._current_display_mode != "html":
            url = self._page_cache.get("url", "")
            if url:
                self.ui.stage.setUrl(QUrl("about:blank"))
                self.ui.stage.setUrl(QUrl(url))
                self._current_display_mode = "html"
        else:
            # Fallback: reload the current URL
            url = self._page_cache.get("url")
            if url:
                self.ui.stage.setUrl(QUrl("about:blank"))
                self.ui.stage.setUrl(QUrl(url))
                self._current_display_mode = "html"

    def _format_plaintext_as_html(self, text: str) -> str:
        """Format plaintext or summary as HTML for display."""
        return (
            "<html><body style='background:#111;color:#eee;font-family:monospace;white-space:pre-wrap;padding:1em;'>"
            f"{text}"
            "</body></html>"
        )
