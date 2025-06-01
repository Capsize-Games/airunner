"""
Custom QWebEnginePage for ConversationWidget to intercept link clicks and emit navigation signals.

This module provides ConversationWebEnginePage, a QWebEnginePage subclass that prevents navigation on link clicks and emits a signal for external browser navigation.
"""

from PySide6.QtCore import QUrl
from PySide6.QtWebEngineCore import QWebEnginePage
from airunner.enums import SignalCode


class ConversationWebEnginePage(QWebEnginePage):
    def __init__(self, qt_parent, widget_for_signal):
        super().__init__(qt_parent)
        self._parent_widget = widget_for_signal

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
            self._parent_widget.emit(
                SignalCode.BROWSER_NAVIGATE_SIGNAL, {"url": url.toString()}
            )
            return False
        return super().acceptNavigationRequest(url, nav_type, is_main_frame)
