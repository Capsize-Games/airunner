"""Unit tests for the PTY-backed terminal session manager."""

import sys
import time

from PySide6.QtCore import QCoreApplication

from airunner.components.document_editor.terminal import (
    TerminalSessionManager,
)


def _wait_for(predicate, timeout: float = 5.0) -> None:
    """Wait for a condition or raise an assertion error."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.05)
    raise AssertionError("Timed out waiting for condition")


def test_terminal_session_manager_captures_output():
    """Terminal sessions should stream and retain command output."""
    manager = TerminalSessionManager()
    session_id = manager.start_session(
        [sys.executable, "-c", "print('hello from terminal')"]
    )

    _wait_for(
        lambda: manager.get_session(session_id) is not None
        and not manager.get_session(session_id).is_running,
    )

    output = manager.session_output(session_id)
    assert "hello from terminal" in output


def test_terminal_session_manager_supports_interactive_input():
    """Terminal sessions should accept interactive input."""
    manager = TerminalSessionManager()
    session_id = manager.start_session(
        [
            sys.executable,
            "-c",
            "import sys; print(sys.stdin.readline().strip())",
        ]
    )

    _wait_for(lambda: manager.get_session(session_id) is not None)
    assert manager.send_input(session_id, "typed through pty")
    _wait_for(lambda: not manager.get_session(session_id).is_running)

    output = manager.session_output(session_id)
    assert "typed through pty" in output


def test_terminal_session_manager_stops_long_running_process():
    """Terminal sessions should support explicit stop requests."""
    manager = TerminalSessionManager()
    session_id = manager.start_session(
        [sys.executable, "-c", "import time; time.sleep(30)"]
    )

    _wait_for(
        lambda: manager.get_session(session_id) is not None
        and manager.get_session(session_id).is_running,
    )
    assert manager.stop_session(session_id, timeout=0.2)
    _wait_for(lambda: not manager.get_session(session_id).is_running)
    assert manager.get_session(session_id).exit_code is not None


def test_terminal_session_manager_ignores_clean_pty_eof():
    """Clean process exit should not emit a PTY error signal."""
    app = QCoreApplication.instance() or QCoreApplication([])
    manager = TerminalSessionManager()
    errors = []
    manager.sessionError.connect(lambda _sid, error: errors.append(error))
    session_id = manager.start_session(
        [sys.executable, "-c", "print('done')"]
    )

    _wait_for(
        lambda: manager.get_session(session_id) is not None
        and not manager.get_session(session_id).is_running,
    )
    for _ in range(20):
        app.processEvents()
        time.sleep(0.01)

    assert errors == []