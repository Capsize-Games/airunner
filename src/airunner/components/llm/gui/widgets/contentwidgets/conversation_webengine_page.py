"""
Custom QWebEnginePage for ConversationWidget to intercept link clicks and emit navigation signals.

This module provides ConversationWebEnginePage, a QWebEnginePage subclass that prevents navigation on link clicks and emits a signal for external browser navigation.
"""

from PySide6.QtCore import QUrl
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings


class ConversationWebEnginePage(QWebEnginePage):
    def __init__(self, qt_parent, widget_for_signal):
        super().__init__(qt_parent)
        self._parent_widget = widget_for_signal
        # Enable local content access for file:// URLs
        view = getattr(widget_for_signal, "ui", None)
        if view and hasattr(view, "stage"):
            settings = view.stage.settings()
            settings.setAttribute(
                QWebEngineSettings.LocalContentCanAccessRemoteUrls, True
            )
            settings.setAttribute(
                QWebEngineSettings.LocalContentCanAccessFileUrls, True
            )
            settings.setAttribute(
                QWebEngineSettings.AllowRunningInsecureContent, True
            )
            settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
            settings.setAttribute(
                QWebEngineSettings.JavascriptCanAccessClipboard, True
            )
            settings.setAttribute(QWebEngineSettings.ErrorPageEnabled, True)

    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        """Capture JavaScript console messages for debugging"""
        super().javaScriptConsoleMessage(level, message, lineNumber, sourceID)

    def acceptNavigationRequest(
        self,
        url: QUrl,
        nav_type: QWebEnginePage.NavigationType,
        is_main_frame: bool,
    ) -> bool:
        if (
            nav_type == QWebEnginePage.NavigationType.NavigationTypeLinkClicked
            and is_main_frame
        ):
            self._parent_widget.navigate(url.toString())
            return False
        return super().acceptNavigationRequest(url, nav_type, is_main_frame)
