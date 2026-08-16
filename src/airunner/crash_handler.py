"""Global crash capture for the AIRunner GUI launcher.

Installed before any Qt code runs so uncaught exceptions, native-level
faults, and background-thread failures reach an on-disk log instead of
silently terminating the process.
"""

from __future__ import annotations

import faulthandler
import os
import sys
import threading
import traceback
from typing import Optional, TextIO

from airunner.settings import AIRUNNER_BASE_PATH

_GUI_LOG_FILENAME = "gui.log"
_FAULT_LOG_FILENAME = "faulthandler.log"


def _default_log_dir() -> str:
    """Return the default crash-log directory."""
    return os.path.join(AIRUNNER_BASE_PATH, "logs")


_CONFIG = {
    "gui_log_path": os.path.join(_default_log_dir(), _GUI_LOG_FILENAME),
    "fault_log_path": os.path.join(_default_log_dir(), _FAULT_LOG_FILENAME),
}

_fault_log_handle: Optional[TextIO] = None
_error_dialog_shown = False
_error_dialog_lock = threading.Lock()


def _dialog_is_disabled() -> bool:
    """Return whether the one-time error dialog should be suppressed."""
    return any(
        (
            os.environ.get("QT_QPA_PLATFORM") == "offscreen",
            os.environ.get("AIRUNNER_TEST_NO_GUI_LAUNCH") == "1",
            os.environ.get("AIRUNNER_DISABLE_CRASH_DIALOG") == "1",
        )
    )


def _append_to_gui_log(message: str) -> None:
    """Append one message to the GUI crash log, ignoring I/O failures."""
    try:
        with open(_CONFIG["gui_log_path"], "a", encoding="utf-8") as handle:
            handle.write(message)
    except OSError:
        pass


def _show_one_time_error_dialog(summary: str) -> None:
    """Show a single error dialog for the first captured crash."""
    global _error_dialog_shown

    with _error_dialog_lock:
        if _error_dialog_shown or _dialog_is_disabled():
            return
        _error_dialog_shown = True

    try:
        from PySide6.QtWidgets import QApplication, QMessageBox
    except Exception:
        return

    try:
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        QMessageBox.critical(
            None,
            "AI Runner crashed",
            f"An unexpected error occurred:\n\n{summary}",
        )
        app.processEvents()
    except Exception:
        pass


def report_uncaught_exception(exc_type, exc_value, exc_tb) -> None:
    """Append an uncaught exception to the GUI log and show the dialog.

    Public so application startup code (``UIRuntimeMixin``) can preserve
    the crash capture when it installs its own ``sys.excepthook``.
    """
    formatted = "".join(
        traceback.format_exception(exc_type, exc_value, exc_tb)
    )
    _append_to_gui_log(formatted)
    summary = f"{getattr(exc_type, '__name__', exc_type)}: {exc_value}"
    _show_one_time_error_dialog(summary)


def _excepthook(exc_type, exc_value, exc_tb) -> None:
    if exc_type is not None and issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return

    report_uncaught_exception(exc_type, exc_value, exc_tb)
    sys.__excepthook__(exc_type, exc_value, exc_tb)


def _unraisablehook(unraisable) -> None:
    try:
        lines = [
            "Unraisable exception in background thread:\n",
            f"{getattr(unraisable.exc_type, '__name__', unraisable.exc_type)}: "
            f"{unraisable.exc_value}\n",
        ]
        if unraisable.exc_traceback is not None:
            lines.extend(traceback.format_tb(unraisable.exc_traceback))
        _append_to_gui_log("".join(lines))
    except Exception:
        pass
    finally:
        sys.__unraisablehook__(unraisable)


def install_faulthandler(log_dir: Optional[str] = None) -> str:
    """Enable faulthandler with the on-disk fault log.

    Re-enabling faulthandler later (for example the bare
    ``faulthandler.enable()`` in ``airunner.main``) resets the output
    stream, so this helper must be called again after any such reset to
    keep native-level faults landing in ``faulthandler.log``.

    Returns the fault-log path used.
    """
    global _fault_log_handle

    if log_dir is None:
        log_dir = _default_log_dir()
    else:
        log_dir = os.path.abspath(os.path.expanduser(log_dir))
    os.makedirs(log_dir, exist_ok=True)

    fault_log_path = os.path.join(log_dir, _FAULT_LOG_FILENAME)
    _CONFIG["fault_log_path"] = fault_log_path

    if _fault_log_handle is not None:
        try:
            _fault_log_handle.close()
        except Exception:
            pass
    _fault_log_handle = open(fault_log_path, "a", encoding="utf-8")
    faulthandler.enable(file=_fault_log_handle)
    return fault_log_path


def install_crash_handlers(log_dir: Optional[str] = None) -> None:
    """Install global crash capture before any Qt code runs.

    Safe to call more than once: later calls re-apply the exception and
    unraisable hooks and re-point faulthandler at the log file. This
    matters because the application startup path (``UIRuntimeMixin``)
    replaces ``sys.excepthook`` with its own handler after the launcher
    installs this one; a second call re-arms the on-disk capture.
    """
    if log_dir is None:
        log_dir = _default_log_dir()
    else:
        log_dir = os.path.abspath(os.path.expanduser(log_dir))
    os.makedirs(log_dir, exist_ok=True)

    _CONFIG["gui_log_path"] = os.path.join(log_dir, _GUI_LOG_FILENAME)

    install_faulthandler(log_dir=log_dir)

    sys.excepthook = _excepthook
    sys.unraisablehook = _unraisablehook
