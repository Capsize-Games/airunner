"""PTY-backed terminal session manager for the coding workspace."""

from dataclasses import dataclass, field
import os
import pty
import select
import subprocess
from threading import RLock, Thread
from uuid import uuid4

from PySide6.QtCore import QObject, Signal


@dataclass
class TerminalSessionInfo:
    """State for one terminal session."""

    session_id: str
    argv: list[str]
    working_directory: str
    process: subprocess.Popen
    master_fd: int
    output_chunks: list[str] = field(default_factory=list)
    exit_code: int | None = None
    reader_thread: Thread | None = None

    @property
    def is_running(self) -> bool:
        """Return whether the session process is still active."""
        return self.process.poll() is None

    def output_text(self) -> str:
        """Return the accumulated terminal output."""
        return "".join(self.output_chunks)


class TerminalSessionManager(QObject):
    """Manage PTY-backed terminal sessions and live output."""

    outputReceived = Signal(str, str)
    sessionFinished = Signal(str, int)
    sessionError = Signal(str, str)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._lock = RLock()
        self._sessions: dict[str, TerminalSessionInfo] = {}

    def start_session(
        self,
        argv: list[str],
        working_directory: str | None = None,
        environment: dict[str, str] | None = None,
    ) -> str:
        """Start a PTY-backed terminal session and return its ID."""
        cwd = os.path.abspath(working_directory or os.getcwd())
        session_id = str(uuid4())
        master_fd, slave_fd = pty.openpty()
        process = subprocess.Popen(
            argv,
            cwd=cwd,
            env=environment,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            start_new_session=True,
            close_fds=True,
        )
        os.close(slave_fd)
        session = TerminalSessionInfo(
            session_id=session_id,
            argv=list(argv),
            working_directory=cwd,
            process=process,
            master_fd=master_fd,
        )
        reader = Thread(
            target=self._pump_output,
            args=(session_id,),
            daemon=True,
        )
        session.reader_thread = reader
        with self._lock:
            self._sessions[session_id] = session
        reader.start()
        return session_id

    def start_shell_session(
        self,
        command: str,
        working_directory: str | None = None,
        environment: dict[str, str] | None = None,
    ) -> str:
        """Start a shell command inside a PTY-backed session."""
        return self.start_session(
            ["/bin/bash", "-lc", command],
            working_directory=working_directory,
            environment=environment,
        )

    def send_input(
        self,
        session_id: str,
        text: str,
        append_newline: bool = True,
    ) -> bool:
        """Send input to an active terminal session."""
        session = self.get_session(session_id)
        if session is None or not session.is_running:
            return False
        payload = text + ("\n" if append_newline else "")
        os.write(session.master_fd, payload.encode("utf-8"))
        return True

    def stop_session(self, session_id: str, timeout: float = 1.0) -> bool:
        """Stop a running terminal session."""
        session = self.get_session(session_id)
        if session is None:
            return False
        if session.is_running:
            session.process.terminate()
            try:
                session.process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                session.process.kill()
                session.process.wait(timeout=timeout)
        return True

    def get_session(self, session_id: str) -> TerminalSessionInfo | None:
        """Return session info for a known terminal session."""
        with self._lock:
            return self._sessions.get(session_id)

    def session_output(self, session_id: str) -> str:
        """Return the captured output for a terminal session."""
        session = self.get_session(session_id)
        if session is None:
            return ""
        return session.output_text()

    def _pump_output(self, session_id: str) -> None:
        """Read PTY output until the process exits."""
        session = self.get_session(session_id)
        if session is None:
            return
        while True:
            ready, _, _ = select.select([session.master_fd], [], [], 0.1)
            if ready:
                try:
                    chunk = os.read(session.master_fd, 4096)
                except OSError as exc:
                    self.sessionError.emit(session_id, str(exc))
                    break
                if chunk:
                    text = chunk.decode("utf-8", errors="replace")
                    with self._lock:
                        session.output_chunks.append(text)
                    self.outputReceived.emit(session_id, text)
            if session.process.poll() is not None and not ready:
                break
        exit_code = session.process.wait()
        with self._lock:
            session.exit_code = exit_code
        self._close_master_fd(session)
        self.sessionFinished.emit(session_id, exit_code)

    def _close_master_fd(self, session: TerminalSessionInfo) -> None:
        """Close the PTY master file descriptor for a session."""
        try:
            os.close(session.master_fd)
        except OSError:
            pass