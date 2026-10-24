"""Tests for early Qt software-rendering fallback selection."""

from __future__ import annotations

import os

import pytest

from airunner import qt_runtime_env
from airunner.qt_runtime_env import (
    SOFTWARE_RENDERING_ENV,
    configure_early_qt_environment,
)

SOFTWARE_VARS = (
    "QT_OPENGL",
    "QT_XCB_GL_INTEGRATION",
    "QT_WIDGETS_NO_CHILD_RHI",
    "QT_WIDGETS_RHI_BACKEND",
    "QTWEBENGINE_DISABLE_GPU",
    "QTWEBENGINE_CHROMIUM_FLAGS",
    "LIBGL_ALWAYS_SOFTWARE",
)


@pytest.fixture()
def clean_qt_env(monkeypatch, tmp_path):
    """Clear Qt env and point DRI detection at a temp directory."""
    for var in SOFTWARE_VARS + (
        "QT_QUICK_BACKEND",
        SOFTWARE_RENDERING_ENV,
        "DISPLAY",
        "WAYLAND_DISPLAY",
        "QT_QPA_PLATFORM",
    ):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(qt_runtime_env, "_DRI_PATH", tmp_path)
    return tmp_path


def _software_forced() -> bool:
    """Return whether the software fallbacks were applied."""
    return all(os.environ.get(var) for var in SOFTWARE_VARS)


def test_hardware_desktop_skips_software_fallbacks(
    clean_qt_env, monkeypatch
) -> None:
    """A display with a DRI device keeps hardware rendering."""
    monkeypatch.setenv("DISPLAY", ":0")
    (clean_qt_env / "card0").touch()
    configure_early_qt_environment()
    assert not _software_forced()


def test_missing_dri_device_keeps_software_fallbacks(
    clean_qt_env, monkeypatch
) -> None:
    """A display without a DRI device stays on software rendering."""
    monkeypatch.setenv("DISPLAY", ":0")
    configure_early_qt_environment()
    assert _software_forced()


def test_headless_session_keeps_software_fallbacks(clean_qt_env) -> None:
    """No display means software rendering even with a DRI device."""
    (clean_qt_env / "renderD128").touch()
    configure_early_qt_environment()
    assert _software_forced()


def test_offscreen_platform_keeps_software_fallbacks(
    clean_qt_env, monkeypatch
) -> None:
    """The offscreen test harness never needs the GPU."""
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("DISPLAY", ":0")
    (clean_qt_env / "card0").touch()
    configure_early_qt_environment()
    assert _software_forced()


def test_explicit_override_forces_software(
    clean_qt_env, monkeypatch
) -> None:
    """An explicit opt-in keeps software rendering on capable hardware."""
    monkeypatch.setenv(SOFTWARE_RENDERING_ENV, "1")
    monkeypatch.setenv("DISPLAY", ":0")
    (clean_qt_env / "card0").touch()
    configure_early_qt_environment()
    assert _software_forced()


def test_explicit_override_forces_hardware_attempt(
    clean_qt_env, monkeypatch
) -> None:
    """An explicit opt-out skips the fallbacks even when headless."""
    monkeypatch.setenv(SOFTWARE_RENDERING_ENV, "0")
    configure_early_qt_environment()
    assert not _software_forced()
