"""Tests for the StableDiffusionGeneratorForm loading watchdog.

The watchdog is defense-in-depth for the pinned-at-startup bug where a stale
``ModelStatus.LOADING`` from the daemon keeps the progress bar running and
disables the generate button indefinitely.  The form's heavy ``__init__`` is
bypassed (``__new__``) and the module-level ``QTimer``/``QApplication`` are
faked so the test runs without a real Qt event loop or database.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from airunner.components.art.gui.widgets.stablediffusion import (
    stablediffusion_generator_form as form_module,
)
from airunner.enums import ModelStatus, ModelType

pytestmark = pytest.mark.gui


class _FakeTimer:
    """Single-shot timer double captured by the module-level patch."""

    def __init__(self, parent=None):
        del parent
        self.single_shot = False
        self.interval_ms = None
        self.started = False
        self.stopped = False
        self.deleted = False
        self._callback = None

    def setSingleShot(self, value: bool) -> None:
        self.single_shot = value

    def setInterval(self, ms: int) -> None:
        self.interval_ms = ms

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True

    def deleteLater(self) -> None:
        self.deleted = True

    @property
    def timeout(self) -> "_FakeTimeout":
        return _FakeTimeout(self)

    def fire(self) -> None:
        if self._callback is not None:
            self._callback()


class _FakeTimeout:
    """Allows ``timer.timeout.connect(callback)`` like a real Qt timer."""

    def __init__(self, timer: _FakeTimer):
        self._timer = timer

    def connect(self, callback) -> None:
        self._timer._callback = callback


class _FakeProgressBar:
    def __init__(self):
        self.format = ""
        self.range = (0, 100)
        self.value = 0
        self.shown = False

    def setFormat(self, value: str) -> None:
        self.format = value

    def setRange(self, low: int, high: int) -> None:
        self.range = (low, high)

    def setValue(self, value: int) -> None:
        self.value = value

    def show(self) -> None:
        self.shown = True

    def minimum(self) -> int:
        return self.range[0]

    def maximum(self) -> int:
        return self.range[1]


class _FakeButton:
    def __init__(self):
        self.enabled = True

    def setEnabled(self, value: bool) -> None:
        self.enabled = value


class _FakeUI:
    def __init__(self):
        self.progress_bar = _FakeProgressBar()
        self.generate_button = _FakeButton()
        self.interrupt_button = _FakeButton()


def _make_form(**overrides):
    """Build the form object without running its heavy __init__."""
    StableDiffusionGeneratorForm = form_module.StableDiffusionGeneratorForm

    form = StableDiffusionGeneratorForm.__new__(StableDiffusionGeneratorForm)
    form._busy_progress_models = set()
    form._loading_watchdog_timer = None
    form._generation_in_progress = False
    form._backend_progress_started = False
    form._waiting_for_backend_progress = False
    form.ui = _FakeUI()
    form.image_request = SimpleNamespace(model_path=None)
    for key, value in overrides.items():
        setattr(form, key, value)
    return form


@pytest.fixture(autouse=True)
def _fake_qt(monkeypatch):
    """Replace Qt timer/processEvents so no real Qt objects are created."""
    monkeypatch.setattr(form_module, "QTimer", _FakeTimer)
    monkeypatch.setattr(
        form_module.QApplication,
        "processEvents",
        staticmethod(lambda: None),
    )


def _enter_loading(form):
    """Drive the form into the LOADING state and return the armed timer."""
    form.on_model_status_changed_signal(
        {"model": ModelType.SD, "status": ModelStatus.LOADING}
    )
    timer = form._loading_watchdog_timer
    assert timer is not None
    assert timer.single_shot is True
    assert timer.interval_ms == form._LOADING_WATCHDOG_TIMEOUT_MS
    assert timer.started is True
    return timer


def test_watchdog_releases_pinned_ui_at_startup():
    """A stale LOADING with no activity releases the UI after the timeout."""
    form = _make_form()
    _enter_loading(form)

    # Loading state is active: progress running, buttons disabled.
    assert form.ui.progress_bar.range == (0, 0)
    assert not form.ui.generate_button.enabled
    assert not form.ui.interrupt_button.enabled

    # No progress ever arrives: the watchdog fires and releases the UI.
    form._loading_watchdog_timer.fire()
    assert form.ui.generate_button.enabled is True
    assert form.ui.interrupt_button.enabled is True
    assert form._loading_watchdog_timer is None
    assert form.ui.progress_bar.range == (0, 100)
    assert form.ui.progress_bar.value == 0
    assert ModelType.SD not in form._progress_models()


def test_real_backend_progress_clears_watchdog():
    """A real progress event disarms the watchdog before it can fire."""
    form = _make_form(_generation_in_progress=True)
    _enter_loading(form)
    form.handle_progress_bar({"step": 1, "total": 10})
    assert form._loading_watchdog_timer is None
    assert form._backend_progress_started is True


def test_state_change_to_loaded_clears_watchdog():
    """Reaching LOADED (or any non-loading state) disarms the watchdog."""
    form = _make_form()
    _enter_loading(form)
    form.on_model_status_changed_signal(
        {"model": ModelType.SD, "status": ModelStatus.LOADED}
    )
    assert form._loading_watchdog_timer is None
    assert form.ui.generate_button.enabled is True
    assert form.ui.interrupt_button.enabled is True


def test_watchdog_never_interrupts_active_generation():
    """A generation waiting for backend progress is left untouched."""
    form = _make_form(
        _generation_in_progress=True,
        _waiting_for_backend_progress=True,
    )
    _enter_loading(form)
    form._loading_watchdog_timer.fire()

    # Generation still in flight: model stays busy, buttons stay disabled,
    # and the indeterminate progress bar is not reset.
    assert ModelType.SD in form._progress_models()
    assert not form.ui.generate_button.enabled
    assert not form.ui.interrupt_button.enabled
    assert form.ui.progress_bar.range == (0, 0)
    assert form._loading_watchdog_timer is None
