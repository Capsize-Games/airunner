"""Tests for Qt bootstrap ordering during launcher startup."""

from __future__ import annotations

import importlib
import os
from types import MethodType
from types import SimpleNamespace

from PySide6.QtCore import Qt

from airunner import launcher
from airunner.app_mixins import ui_runtime_mixin
from airunner import qt_runtime_env


def test_launcher_prepares_qt_before_creating_qapplication(monkeypatch):
    """Launcher must prepare Qt before creating the first app."""
    events: list[str] = []

    class FakeQApplication:
        @staticmethod
        def instance():
            events.append("instance")
            return None

        def __init__(self, _args):
            events.append("create")

    monkeypatch.setattr(
        "airunner.app_mixins.ui_runtime_mixin.prepare_qt_runtime",
        lambda: events.append("prepare"),
    )
    monkeypatch.setattr("PySide6.QtWidgets.QApplication", FakeQApplication)
    qsettings_module = importlib.import_module(
        "airunner.utils.settings.get_qsettings"
    )
    agreement_module = importlib.import_module(
        "airunner.components.application.gui.dialogs."
        "first_run_agreement_dialog"
    )
    monkeypatch.setattr(qsettings_module, "get_qsettings", lambda: object())
    monkeypatch.setattr(
        agreement_module,
        "check_all_agreements",
        lambda _qsettings: True,
    )

    launcher._check_first_run_agreement()

    assert events == ["prepare", "instance", "create"]


def test_ui_runtime_start_reuses_launcher_app_without_late_attributes(
    monkeypatch,
):
    """UI runtime should not set Qt attributes after launcher app exists."""
    runtime = SimpleNamespace(
        headless=False,
        _launcher_app=SimpleNamespace(),
        app=None,
        signal_handler=lambda *_args: None,
    )
    prepare_calls: list[str] = []

    monkeypatch.setattr(
        ui_runtime_mixin,
        "prepare_qt_runtime",
        lambda: prepare_calls.append("prepare"),
    )
    monkeypatch.setattr(
        ui_runtime_mixin,
        "set_global_tooltip_style",
        lambda: None,
    )
    monkeypatch.setattr(ui_runtime_mixin.signal, "signal", lambda *_args: None)
    monkeypatch.setattr(
        ui_runtime_mixin.QApplication,
        "setAttribute",
        lambda *_args: (_ for _ in ()).throw(AssertionError("late")),
    )

    ui_runtime_mixin.UIRuntimeMixin.start(runtime)

    assert prepare_calls == ["prepare"]
    assert runtime.app is runtime._launcher_app
    assert runtime.app.api is runtime


def test_prepare_qt_runtime_preserves_software_rendering(monkeypatch):
    """Qt bootstrap must not override the software rendering path."""
    attrs: list[object] = []
    events: list[str] = []

    monkeypatch.setattr(ui_runtime_mixin, "_QT_RUNTIME_PREPARED", False)
    monkeypatch.setenv("QT_QUICK_BACKEND", "software")
    monkeypatch.setenv("QT_XCB_GL_INTEGRATION", "none")
    monkeypatch.delenv("QT_OPENGL", raising=False)
    monkeypatch.setattr(
        ui_runtime_mixin.QCoreApplication,
        "instance",
        lambda: None,
    )
    monkeypatch.setattr(
        ui_runtime_mixin.QSurfaceFormat,
        "setDefaultFormat",
        lambda _fmt: events.append("format"),
    )
    monkeypatch.setattr(
        ui_runtime_mixin.QApplication,
        "setAttribute",
        lambda attr: attrs.append(attr),
    )

    ui_runtime_mixin.prepare_qt_runtime()

    assert os.environ["QT_XCB_GL_INTEGRATION"] == "none"
    assert "QT_OPENGL" not in os.environ
    assert events == []
    assert (
        Qt.ApplicationAttribute.AA_UseDesktopOpenGL not in attrs
    )
    assert Qt.ApplicationAttribute.AA_UseSoftwareOpenGL in attrs


def test_configure_early_qt_environment_sets_linux_safe_defaults(
    monkeypatch,
):
    """Launcher-safe Qt defaults should be present before Qt startup."""
    monkeypatch.delenv("QT_QUICK_BACKEND", raising=False)
    monkeypatch.delenv("QT_XCB_GL_INTEGRATION", raising=False)
    monkeypatch.delenv("TOKENIZERS_PARALLELISM", raising=False)
    monkeypatch.delenv("FONTCONFIG_PATH", raising=False)

    qt_runtime_env.configure_early_qt_environment()

    assert os.environ["QT_QUICK_BACKEND"] == "software"
    assert os.environ["TOKENIZERS_PARALLELISM"] == "true"
    assert os.environ["QT_XCB_GL_INTEGRATION"] == "none"
    assert os.environ["QT_WIDGETS_NO_CHILD_RHI"] == "1"
    assert os.environ["QT_WIDGETS_RHI_BACKEND"] == "software"
    assert os.environ["FONTCONFIG_PATH"]


def test_prefers_software_qt_rendering_detects_widget_rhi_fallback(
    monkeypatch,
):
    """Qt runtime helper should detect the software widget fallback path."""
    monkeypatch.delenv("QT_QUICK_BACKEND", raising=False)
    monkeypatch.delenv("QT_OPENGL", raising=False)
    monkeypatch.delenv("QT_XCB_GL_INTEGRATION", raising=False)
    monkeypatch.delenv("QT_WIDGETS_RHI_BACKEND", raising=False)
    monkeypatch.delenv("LIBGL_ALWAYS_SOFTWARE", raising=False)

    assert qt_runtime_env.prefers_software_qt_rendering() is False

    monkeypatch.setenv("QT_WIDGETS_RHI_BACKEND", "software")

    assert qt_runtime_env.prefers_software_qt_rendering() is True


def test_show_main_application_dismisses_splash_and_reactivates(monkeypatch):
    """Main window handoff should close the splash and re-raise the app."""
    events: list[str] = []

    class FakeWindow:
        def __init__(self, **kwargs):
            events.append(("window_init", kwargs["app"]))

        def show(self):
            events.append("show")

        def raise_(self):
            events.append("raise")

        def activateWindow(self):
            events.append("activate")

    class FakeSplash:
        def hide(self):
            events.append("splash_hide")

        def finish(self, _window):
            events.append("splash_finish")

        def close(self):
            events.append("splash_close")

        def deleteLater(self):
            events.append("splash_delete")

    class FakeApp:
        def processEvents(self):
            events.append("process")

    runtime = SimpleNamespace(
        headless=False,
        main_window_class_=FakeWindow,
        window_class_params={},
        splash=FakeSplash(),
        _launcher_splash=FakeSplash(),
        update_splash_message=lambda *_args: events.append("splash_message"),
    )
    runtime.splash = runtime._launcher_splash
    runtime._present_main_window = (
        ui_runtime_mixin.UIRuntimeMixin._present_main_window
    )
    runtime._dismiss_splash_screen = MethodType(
        ui_runtime_mixin.UIRuntimeMixin._dismiss_splash_screen,
        runtime,
    )
    app = FakeApp()

    monkeypatch.setattr(ui_runtime_mixin, "qVersion", lambda: "6.9.0")
    monkeypatch.setattr(
        ui_runtime_mixin.QTimer,
        "singleShot",
        lambda _delay, callback: callback(),
    )

    ui_runtime_mixin.UIRuntimeMixin.show_main_application(runtime, app)

    assert app.main_window is not None
    assert runtime.splash is None
    assert runtime._launcher_splash is None
    assert "splash_finish" in events
    assert "splash_close" in events
    assert "splash_delete" in events
    assert events.count("activate") >= 2