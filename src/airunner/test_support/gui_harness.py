"""Support helpers for headless GUI functional tests."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable

from PySide6.QtCore import Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton


Predicate = Callable[[], bool]


@dataclass
class FakeAPI:
    """Minimal backend object injected into QApplication for GUI tests."""

    headless: bool = False
    daemon_client: Any = None
    api_adapter: Any = None
    sounddevice_manager: Any = None
    llm: Any = None
    art: Any = None
    tts: Any = None
    stt: Any = None
    emitted_signals: list[tuple[Any, dict[str, Any]]] = field(
        default_factory=list
    )


@dataclass
class FakePathSettings:
    """Small path-settings object for path widget functional tests."""

    base_path: str
    model_base_path: str
    models_path: str = ""
    hf_cache_path: str = ""
    documents_path: str = ""


def install_fake_api(
    qapp: QApplication,
    api: FakeAPI | None = None,
) -> FakeAPI:
    """Attach one fake API object to the QApplication."""
    bound_api = api or FakeAPI()
    qapp.api = bound_api
    return bound_api


def clear_fake_api(qapp: QApplication) -> None:
    """Remove one fake API object from the QApplication."""
    if hasattr(qapp, "api"):
        delattr(qapp, "api")


def pump_events(wait_ms: int = 0) -> None:
    """Process pending Qt events for one short interval."""
    app = QApplication.instance()
    if app is None:
        return
    app.processEvents()
    if wait_ms > 0:
        QTest.qWait(wait_ms)
        app.processEvents()


def wait_until(
    predicate: Predicate,
    timeout_ms: int = 1000,
    message: str = "Timed out waiting for GUI state",
) -> None:
    """Pump the event loop until one predicate becomes true."""
    deadline = time.monotonic() + (timeout_ms / 1000)
    while time.monotonic() < deadline:
        if predicate():
            return
        pump_events(10)
    raise AssertionError(message)


def assert_event_loop_responsive(
    action: Callable[[], Any],
    timeout_ms: int = 500,
) -> Any:
    """Run one action and confirm queued GUI work still executes."""
    fired = [False]
    QTimer.singleShot(0, lambda: fired.__setitem__(0, True))
    result = action()
    wait_until(
        lambda: fired[0],
        timeout_ms=timeout_ms,
        message="Qt event loop stopped responding after one action",
    )
    return result


def click_button(button: QPushButton, timeout_ms: int = 500) -> None:
    """Click one button and assert the GUI stays responsive."""

    def _click() -> None:
        QTest.mouseClick(button, Qt.MouseButton.LeftButton)

    assert_event_loop_responsive(_click, timeout_ms=timeout_ms)