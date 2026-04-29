"""Early Qt environment defaults shared by launcher and app entrypoints."""

from __future__ import annotations

import os
import sys


def configure_early_qt_environment() -> None:
    """Set safe Qt defaults before importing or creating Qt objects."""
    os.environ.setdefault("QT_QUICK_BACKEND", "software")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "true")
    if sys.platform.startswith("linux"):
        os.environ.setdefault("QT_XCB_GL_INTEGRATION", "none")
        os.environ.setdefault("QT_WIDGETS_NO_CHILD_RHI", "1")
        os.environ.setdefault("QT_WIDGETS_RHI_BACKEND", "software")
    _configure_fontconfig_path()


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