"""
SummarizationMixin for BrowserWidget.
Handles plaintext and summary display logic.

Google Python Style Guide applies.
"""

from PySide6.QtCore import QUrl, Slot


class SummarizationMixin:
    @Slot(bool)
    def on_plaintext_button_toggled(self, checked: bool) -> None:
        """Toggle plaintext view for the current page."""
        if (
            checked
            and self._page_cache["plaintext"]
            and self._current_display_mode != "plaintext"
        ):
            self._set_display_mode("plaintext")
        elif not checked:
            self._restore_display_mode(exclude="plaintext")

    @Slot(bool)
    def on_summarize_button_toggled(self, checked: bool) -> None:
        """Toggle summary view for the current page."""
        if (
            checked
            and self._page_cache["summary"]
            and self._current_display_mode != "summary"
        ):
            self._set_display_mode("summary")
        elif not checked:
            self._restore_display_mode(exclude="summary")

    def _set_display_mode(self, mode: str) -> None:
        """Set the display mode to 'html', 'plaintext', or 'summary'."""
        html = None
        if mode == "plaintext":
            html = self._format_plaintext_as_html(
                self._page_cache["plaintext"]
            )
        elif mode == "summary":
            html = self._format_plaintext_as_html(self._page_cache["summary"])
        if html:
            self.ui.stage.setHtml(html, QUrl(self._page_cache["url"]))
            self._current_display_mode = mode

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
        elif self._current_display_mode != "html" and self._page_cache["url"]:
            self.ui.stage.setUrl(QUrl(self._page_cache["url"]))
            self._current_display_mode = "html"

    def _format_plaintext_as_html(self, text: str) -> str:
        """Format plaintext or summary as HTML for display."""
        return (
            "<html><body style='background:#111;color:#eee;font-family:monospace;white-space:pre-wrap;padding:1em;'>"
            f"{text}"
            "</body></html>"
        )
