"""
NavigationMixin for BrowserWidget.
Handles URL loading, navigation, and security indicators.

Google Python Style Guide applies.
"""

import re
import os
import hashlib
from PySide6.QtCore import QUrl, Slot
from airunner.enums import SignalCode
from airunner.components.browser.utils import normalize_url


class NavigationMixin:
    @Slot()
    def on_submit_button_clicked(self) -> None:
        url = self.ui.url.text().strip()
        if not url:
            return
        original_url = url
        if url.startswith("local:"):
            local_name = url[len("local:") :].strip()
            if not local_name:
                self.logger.warning(
                    "No local file specified after 'local:' scheme."
                )
                return
            user_web_dir = os.path.expanduser(
                os.path.join(self.path_settings.base_path, "web")
            )
            candidates = [
                os.path.join(user_web_dir, "html", f"{local_name}.html"),
                os.path.join(
                    user_web_dir, "html", f"{local_name}.jinja2.html"
                ),
            ]
            for file_path in candidates:
                if os.path.exists(file_path):
                    with open(file_path, "r", encoding="utf-8") as f:
                        html = f.read()
                    self.ui.stage.setHtml(html, QUrl.fromLocalFile(file_path))
                    self.ui.url.setText(f"local:{local_name}")
                    self._page_cache["html"] = html
                    self._page_cache["url"] = f"local:{local_name}"
                    self._page_cache["plaintext"] = None
                    self._page_cache["summary"] = None
                    return
            self.logger.warning("Local file not found")
            self.ui.url.setStyleSheet(
                "QLineEdit { background: #331111; color: #ff9999; }"
            )
            return
        if not url.startswith("http://") and not url.startswith("https://"):
            url = f"https://{url}"
        if url.startswith("http://"):
            url = url.replace("http://", "https://", 1)
            self.logger.info("Upgraded insecure URL to HTTPS")
        if url != original_url:
            self.ui.url.setText(url)
        self.ui.url.clearFocus()
        pattern = re.compile(
            r"^https://([\w.-]+|\d{1,3}(?:\.\d{1,3}){3})(?::\d+)?(?:[/?#][^\s]*)?$"
        )
        if pattern.match(url):
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
            self.logger.warning("Invalid or insecure URL rejected")
            self.ui.url.setStyleSheet(
                "QLineEdit { background: #331111; color: #ff9999; }"
            )

    @Slot()
    def on_next_button_clicked(self) -> None:
        self.ui.stage.forward()

    @Slot()
    def on_back_button_clicked(self) -> None:
        self.ui.stage.back()

    @Slot()
    def on_refresh_button_clicked(self) -> None:
        self.ui.stage.reload()

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
