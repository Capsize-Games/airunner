"""
PrivacyMixin for BrowserWidget.
Handles private browsing mode, privacy UI, and browser profile logic.

Google Python Style Guide applies.
"""

from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEngineSettings
from PySide6.QtWebEngineCore import QWebEnginePage


class PrivacyMixin:
    def _set_private_browsing(self, enabled: bool):
        self._private_browsing_enabled = enabled
        self._update_private_browsing_icon(enabled)
        self._update_private_browsing_styling(enabled)
        if enabled:
            self.clear_session()
            self.logger.info("Private browsing enabled - session data cleared")
        else:
            self.logger.info(
                "Private browsing disabled - normal browsing mode"
            )
        self._profile = None
        self._profile_page = None
        self.ui.stage.setPage(self.profile_page)
        self.log_privacy_status()

    def _update_private_browsing_icon(self, enabled: bool):
        from PySide6.QtGui import QIcon

        if enabled:
            icon_path = ":/dark/icons/feather/dark/eye-off.svg"
            self.ui.private_browse_button.setToolTip(
                "Private browsing enabled - Click to disable"
            )
        else:
            icon_path = ":/dark/icons/feather/dark/eye.svg"
            self.ui.private_browse_button.setToolTip(
                "Private browsing disabled - Click to enable"
            )
        icon = QIcon()
        icon.addFile(icon_path)
        self.ui.private_browse_button.setIcon(icon)

    def _update_private_browsing_styling(self, enabled: bool):
        if enabled:
            purple_style = """
                QPushButton#private_browse_button {
                    background-color: #4a1a4a;
                    border: 2px solid #8b4a8b;
                    border-radius: 4px;
                    color: #e6b3e6;
                }
                QPushButton#private_browse_button:checked {
                    background-color: #6b2a6b;
                    border-color: #aa5aaa;
                }
                QPushButton#private_browse_button:hover {
                    background-color: #5a2a5a;
                    border-color: #9a5a9a;
                }
            """
            self.ui.private_browse_button.setStyleSheet(purple_style)
            url_style = """
                QLineEdit#url {
                    border-left: 3px solid #8b4a8b;
                }
            """
            self.ui.url.setStyleSheet(url_style)
        else:
            self.ui.private_browse_button.setStyleSheet("")
            self.ui.url.setStyleSheet("")

    @property
    def profile(self):
        if self._profile is None:
            private_mode = getattr(
                self,
                "_private_browsing_enabled",
                (
                    self.ui.private_browse_button.isChecked()
                    if hasattr(self, "ui")
                    else False
                ),
            )
            if private_mode:
                self._profile = QWebEngineProfile(parent=self)
                self.logger.info(f"Private browsing: Enabled")
                self.logger.info(f"Persistent storage: Disabled")
                self.logger.info(f"Cookies: Session-only")
            else:
                self._profile = QWebEngineProfile(
                    "airunner_persistent", parent=self
                )
                self.logger.info(f"Private browsing: Disabled")
                self.logger.info(f"Persistent storage: Enabled")
                self.logger.info(f"Cookies: Persistent allowed")
        return self._profile

    @property
    def profile_page(self):
        if self._profile_page is None:
            self._profile_page = QWebEnginePage(self.profile, self.ui.stage)
        return self._profile_page

    def set_flags(self):
        settings = self.profile_page.settings()
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
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.AutoLoadImages, True
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptEnabled, True
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.LocalStorageEnabled, False
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, False
        )
        self.profile.setHttpUserAgent(
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.7151.55 Safari/537.36"
        )
        self.profile.setHttpAcceptLanguage("en-US,en;q=0.9")
        self.profile_page.featurePermissionRequested.connect(
            self._handle_permission_request
        )
        self.profile_page.certificateError.connect(
            self._handle_certificate_error
        )

    def _handle_permission_request(self, url, feature):
        from PySide6.QtWebEngineWidgets import QWebEnginePage

        self.logger.info(f"Permission request denied for feature: {feature}")
        self.profile_page.setFeaturePermission(
            url, feature, QWebEnginePage.PermissionDeniedByUser
        )

    def _handle_certificate_error(self, error):
        self.logger.warning(
            f"SSL Certificate error for {error.url().toString()}: {error.description()}"
        )
        return False

    def log_privacy_status(self):
        self.logger.info(
            f"Private browsing: {'ENABLED' if self._private_browsing_enabled else 'DISABLED'}"
        )

    def get_privacy_status(self) -> dict:
        return {
            "private_browsing": self._private_browsing_enabled,
            "profile": str(self.profile),
        }
