"""Tests for the chat surface host's environment handling (#2230).

The offscreen test harness must never build a QtWebEngine view, so the
placeholder path is asserted directly — that is the path every GUI
functional test exercises when it constructs ``ChatPromptWidget``.
"""

from __future__ import annotations

from PySide6.QtWidgets import QLabel

from airunner.components.chat.gui.chat_surface_endpoint import (
    ChatSurfaceEndpoint,
)
from airunner.components.chat.gui.widgets.chat_surface_widget import (
    PLACEHOLDER_TEXT,
    ChatSurfaceWidget,
    uses_placeholder_view,
)

_ENDPOINT = ChatSurfaceEndpoint(
    base_url="http://127.0.0.1:8188", token="token"
)


def test_placeholder_mode_skips_the_web_view(qapp, monkeypatch) -> None:
    """The test harness gets a placeholder instead of a web view."""
    monkeypatch.setenv("AIRUNNER_TEST_NO_GUI_LAUNCH", "1")
    monkeypatch.delenv("QT_QPA_PLATFORM", raising=False)
    assert uses_placeholder_view() is True

    surface = ChatSurfaceWidget(endpoint=_ENDPOINT)
    assert surface.view is None
    labels = surface.findChildren(QLabel)
    assert [label.text() for label in labels] == [PLACEHOLDER_TEXT]


def test_offscreen_platform_skips_the_web_view(qapp, monkeypatch) -> None:
    """An offscreen Qt platform gets a placeholder instead of a web view."""
    monkeypatch.delenv("AIRUNNER_TEST_NO_GUI_LAUNCH", raising=False)
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    assert uses_placeholder_view() is True

    surface = ChatSurfaceWidget(endpoint=_ENDPOINT)
    assert surface.view is None


def test_placeholder_surface_accepts_lifecycle_calls(
    qapp, monkeypatch
) -> None:
    """Load, reload and close are safe with no web view present."""
    monkeypatch.setenv("AIRUNNER_TEST_NO_GUI_LAUNCH", "1")
    surface = ChatSurfaceWidget(endpoint=_ENDPOINT)
    surface.load()
    surface.reload()
    surface.handle_close()
    assert surface.endpoint is _ENDPOINT
