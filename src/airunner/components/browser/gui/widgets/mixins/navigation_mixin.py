"""
NavigationMixin for BrowserWidget.
Handles URL loading, navigation, and security indicators.

Google Python Style Guide applies.
"""

import re
import os
import hashlib
from PySide6.QtCore import QUrl, Slot
from PySide6.QtWidgets import QMessageBox
from airunner.enums import SignalCode
from airunner.settings import STATIC_BASE_PATH


class NavigationMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._last_failed_https_url = None  # Track last failed HTTPS URL
        self._last_attempted_http_url = None
        if hasattr(self, "ui") and hasattr(self.ui, "stage"):
            self.ui.stage.loadFinished.connect(self._on_load_finished)

    def _on_load_finished(self, success: bool):
        # Only handle HTTPS failures for fallback
        current_url = self.ui.stage.url().toString()
        if not success and current_url.startswith("https://"):
            # Only prompt if not already tried HTTP fallback
            if self._last_failed_https_url == current_url:
                reply = QMessageBox.warning(
                    self,
                    "HTTPS Failed",
                    f"Failed to load {current_url}.\n\nThis site may not support HTTPS.\nDo you want to try loading it over HTTP instead?\n\nWarning: HTTP is not secure.",
                    QMessageBox.Yes | QMessageBox.No,
                )
                if reply == QMessageBox.Yes:
                    http_url = current_url.replace("https://", "http://", 1)
                    self._last_attempted_http_url = http_url
                    self.ui.url.setText(http_url)
                    self.ui.stage.setUrl(QUrl(http_url))
                else:
                    self._last_attempted_http_url = None
            self._last_failed_https_url = None
        elif success:
            self._last_failed_https_url = None
            self._last_attempted_http_url = None

    def _update_security_indicators(self):
        if not hasattr(self.ui, "url"):
            return
        current_url = self.ui.stage.url().toString()
        if not current_url or current_url == "about:blank":
            self.ui.url.setStyleSheet(
                "QLineEdit { background: #111; color: #eee; }"
            )
            return
        if current_url.startswith("https://"):
            self.ui.url.setStyleSheet(
                "QLineEdit { background: #112211; color: #eee; }"
            )
            self.logger.debug("Secure connection detected")
        elif current_url.startswith("http://"):
            self.ui.url.setStyleSheet(
                "QLineEdit { background: #221111; color: #eee; }"
            )
            self.logger.warning("Insecure connection detected")
        else:
            self.ui.url.setStyleSheet(
                "QLineEdit { background: #111; color: #eee; }"
            )
        if current_url != self.ui.url.text():
            self.ui.url.setText(current_url)

    def on_browser_navigate(self, data):
        url = data.get("url", None)
        if url is not None:
            self.ui.stage.load(url)
        else:
            self.logger.error("No URL provided for navigation.")
