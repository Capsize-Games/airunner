"""Early Qt environment defaults shared by launcher and app entrypoints."""

from __future__ import annotations

import os
import sys


def configure_early_qt_environment() -> None:
    """Set safe Qt defaults before importing or creating Qt objects."""
    os.environ.setdefault("QT_QUICK_BACKEND", "software")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "true")
    if sys.platform.startswith("linux"):
        os.environ.setdefault("QT_OPENGL", "software")
        os.environ.setdefault("QT_XCB_GL_INTEGRATION", "none")
        os.environ.setdefault("QT_WIDGETS_NO_CHILD_RHI", "1")
        os.environ.setdefault("QT_WIDGETS_RHI_BACKEND", "software")
        os.environ.setdefault("QTWEBENGINE_DISABLE_GPU", "1")
        os.environ.setdefault(
            "QTWEBENGINE_CHROMIUM_FLAGS",
            "--disable-gpu --disable-gpu-compositing",
        )
        os.environ.setdefault("LIBGL_ALWAYS_SOFTWARE", "1")
    _configure_qt_logging_rules()
    _configure_fontconfig_path()


def _configure_qt_logging_rules() -> None:
    """Suppress verbose Qt warnings that do not affect app behavior."""
    qt_rules = [
        "qt.core.qmetaobject.connectslotsbyname.warning=false",
        "qt.qpa.*=false",
        "qt.qpa.gl=false",
        "qt.rhi.*=false",
        "qt.opengl.*=false",
    ]
    existing_rules = os.environ.get("QT_LOGGING_RULES", "")
    if not existing_rules:
        os.environ["QT_LOGGING_RULES"] = ";".join(qt_rules)
        return

    current_rules = [rule for rule in existing_rules.split(";") if rule]
    for rule in qt_rules:
        if rule not in current_rules:
            current_rules.append(rule)
    os.environ["QT_LOGGING_RULES"] = ";".join(current_rules)


def prefers_software_qt_rendering() -> bool:
    """Return whether the current process is configured for Qt software rendering."""
    return any(
        (
            os.environ.get("QT_QUICK_BACKEND") == "software",
            os.environ.get("QT_OPENGL") == "software",
            os.environ.get("QT_XCB_GL_INTEGRATION") == "none",
            os.environ.get("QT_WIDGETS_RHI_BACKEND") == "software",
            os.environ.get("LIBGL_ALWAYS_SOFTWARE") == "1",
        )
    )


def _configure_fontconfig_path() -> None:
    """Set a fallback fontconfig path when the environment lacks one."""
    if os.environ.get("FONTCONFIG_PATH"):
        return
    for path in _fontconfig_paths():
        if os.path.isdir(path):
            os.environ["FONTCONFIG_PATH"] = path
            return


def _fontconfig_paths() -> tuple[str, ...]:
    """Return common fontconfig directories for Linux desktops."""
    home_dir = os.path.expanduser("~")
    return (
        "/etc/fonts",
        "/usr/share/fontconfig",
        os.path.join(home_dir, ".config", "fontconfig"),
    )