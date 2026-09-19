"""First-class QtWebEngine host for the desktop chat surface (#2230).

Loads the built, cloud-excluded client bundle from the daemon's loopback
origin (``airunner_services.api.routes.client_bundle``), authenticates
every request with the loopback token, and refuses all non-loopback
egress.

The hosted surface is server-driven: it reads the roster, the conversation
list and the transcript from the daemon over ``/api/v1/events`` and
``/api/v1/llm/stream``. ``reload`` is therefore the whole control surface —
the page re-reads history after the Qt composer completes a turn.

Under the offscreen test harness (``AIRUNNER_TEST_NO_GUI_LAUNCH=1`` or
``QT_QPA_PLATFORM=offscreen``) no web view is created; a placeholder label
stands in, as the previous transcript widget did.
"""

from __future__ import annotations

import json
import os
from typing import Optional

from PySide6.QtCore import QUrl, Qt
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from airunner.components.chat.gui.chat_surface_endpoint import (
    ChatSurfaceEndpoint,
    resolve_chat_surface_endpoint,
)
from airunner.components.chat.gui.widgets.chat_surface_interceptor import (
    LoopbackTokenInterceptor,
)
from airunner.utils.application import get_logger
from airunner_common.settings import AIRUNNER_LOG_LEVEL

PLACEHOLDER_TEXT = "The chat surface is unavailable in this environment."


def uses_placeholder_view() -> bool:
    """Return whether this environment must skip the web view entirely."""
    if os.environ.get("AIRUNNER_TEST_NO_GUI_LAUNCH", "0") == "1":
        return True
    return os.environ.get("QT_QPA_PLATFORM", "").lower() == "offscreen"


class ChatSurfaceWidget(QWidget):
    """Host the built desktop chat client in a QtWebEngine view."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        endpoint: Optional[ChatSurfaceEndpoint] = None,
    ) -> None:
        super().__init__(parent)
        self.logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)
        self._endpoint = endpoint or resolve_chat_surface_endpoint()
        self._view: Optional[QWebEngineView] = (
            None if uses_placeholder_view() else self._build_view()
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._view or self._build_placeholder())

    def _build_view(self) -> QWebEngineView:
        """Return the configured web view, with the egress guard installed."""
        view = QWebEngineView(self)
        # The profile does not own the Python wrapper, so the reference is
        # kept: a temporary interceptor never fires at all.
        self._interceptor = LoopbackTokenInterceptor(
            self._endpoint.token, self
        )
        view.page().setUrlRequestInterceptor(self._interceptor)
        settings = view.settings()
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        settings.setAttribute(
            QWebEngineSettings.LocalContentCanAccessRemoteUrls, False
        )
        return view

    def _build_placeholder(self) -> QLabel:
        """Return the stand-in shown when no web view may be created."""
        label = QLabel(PLACEHOLDER_TEXT, self)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setObjectName("chat_surface_placeholder")
        return label

    @property
    def endpoint(self) -> ChatSurfaceEndpoint:
        """Return the loopback endpoint this surface is bound to."""
        return self._endpoint

    @property
    def view(self) -> Optional[QWebEngineView]:
        """Return the hosted web view, or None in a placeholder run."""
        return self._view

    def load(self) -> None:
        """Navigate to the hosted surface's entry document."""
        if self._view is None:
            self.logger.debug("Chat surface view skipped in this run")
            return
        self._view.setUrl(QUrl(self._endpoint.open_url()))

    def reload(self) -> None:
        """Re-read the surface from the daemon after a backend change."""
        if self._view is None:
            return
        if self._view.url().isEmpty():
            self.load()
            return
        self._view.reload()

    def stream_user_message(self, text: str) -> None:
        """Show the user's turn in the surface before it is persisted."""
        if text:
            self._call_bridge("user", text)

    def stream_token(self, text: str) -> None:
        """Append one streamed assistant token (a delta) to the surface."""
        if text:
            self._call_bridge("token", text)

    def finish_turn(self) -> None:
        """Drop the live buffer and let the surface re-read the thread.

        The Qt prompt owns sending, so the surface is told when a turn is
        over instead of being reloaded: a reload would reload the whole
        bundle and flash the window between messages.
        """
        self._run_script(
            "window.__airunnerChat && window.__airunnerChat.finish();"
        )

    def _call_bridge(self, method: str, text: str) -> None:
        """Evaluate one bridge call carrying a single string argument."""
        payload = json.dumps(text)
        self._run_script(
            f"window.__airunnerChat "
            f"&& window.__airunnerChat.{method}({payload});"
        )

    def _run_script(self, script: str) -> None:
        """Run a script in the hosted page, ignoring a placeholder run."""
        if self._view is None:
            return
        try:
            self._view.page().runJavaScript(script)
        except RuntimeError:
            self.logger.debug("Chat surface page already released")

    def handle_close(self) -> None:
        """Release the web view before the application exits."""
        if self._view is None:
            return
        try:
            self._view.stop()
            self._view.close()
        except RuntimeError:
            self.logger.debug("Chat surface view already released")


__all__ = ["PLACEHOLDER_TEXT", "ChatSurfaceWidget", "uses_placeholder_view"]
