"""
Watchdog-based auto-reload for development.

Wraps a server command as a subprocess and restarts it whenever Python
source files change in watched directories.  Toggle with environment
variable ``AIRUNNER_DEV_RELOAD=1``.

Usage (standalone)::

    python -m airunner_services.dev_reload airunner-server --host 0.0.0.0

Usage (Docker entrypoint)::

    AIRUNNER_DEV_RELOAD=1 docker compose up

The reloader watches ``/app/server/src`` by default (the bind-mounted
source directory inside the dev container).  Additional watch paths can
be supplied via ``AIRUNNER_DEV_RELOAD_PATHS`` (colon-separated).
"""

from __future__ import annotations

import logging
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional, Sequence

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────

_WATCH_EXTENSIONS = frozenset({".py"})
_IGNORE_PATTERNS = frozenset({
    "__pycache__", ".mypy_cache", ".pytest_cache",
    ".ruff_cache", ".git", "node_modules",
    ".tox", "venv", ".venv", "build", "dist",
})
# File-name suffixes that are always ignored (editor temp files, etc.).
_IGNORE_SUFFIXES = frozenset({
    ".swp", ".swx", ".swo",  # vim
    ".pyc", ".pyo",           # compiled Python
    "~",                       # emacs / gedit backup
})

# Debounce interval: wait this many seconds after the *last* file change
# event before triggering a restart so rapid multi-file saves (e.g. IDE
# "save all") only cause a single reload.
_DEBOUNCE_INTERVAL = float(
    os.environ.get("AIRUNNER_DEV_RELOAD_DEBOUNCE", "1.0")
)


def _env_flag(name: str, default: bool = False) -> bool:
    """Return True when env var *name* is set to a truthy value."""
    val = os.environ.get(name, "").strip().lower()
    if not val:
        return default
    return val in {"1", "true", "yes", "on"}


def _default_watch_paths() -> list[Path]:
    """Return the list of directories to watch for changes.

    Respects ``AIRUNNER_DEV_RELOAD_PATHS`` (colon-separated) when set;
    otherwise defaults to ``/app/server/src`` (Docker dev container)
    falling back to the ``server/src`` relative to the repo root.
    """
    env_paths = os.environ.get("AIRUNNER_DEV_RELOAD_PATHS", "").strip()
    if env_paths:
        return [Path(p) for p in env_paths.split(":") if p]

    # Default: the bind-mounted source inside the Docker dev container.
    docker_src = Path("/app/server/src")
    if docker_src.is_dir():
        return [docker_src]

    # Bare-metal fallback: resolve relative to this file's location.
    this_file = Path(__file__).resolve()
    # dev_reload.py → airunner_services → src → server
    repo_root = this_file.parents[2]
    server_src = repo_root / "server" / "src"
    if server_src.is_dir():
        return [server_src]

    return []


# ── Event handler ────────────────────────────────────────────────────────

class _ChangeHandler(FileSystemEventHandler):
    """Flag that a restart is needed when a ``.py`` file genuinely changes.

    Docker bind mounts and filesystem implementations can emit spurious
    ``IN_MODIFY`` events on ``.py`` source files when Python imports
    them (e.g. atime updates triggering inotify).  To avoid false
    restarts this handler tracks per-file ``st_mtime`` and only signals
    a change when the modification time has actually moved forward.
    """

    def __init__(self):
        super().__init__()
        self.changed = False
        self._last_path: str = ""
        # Map: resolved path → last-known st_mtime.
        self._mtimes: dict[str, float] = {}

    def on_any_event(self, event):
        del event  # unused
        self.changed = True

    def dispatch(self, event):
        """Ignore non-.py, excluded dirs, temp files, and false positives."""
        src_path = getattr(event, "src_path", "")
        if not src_path:
            return
        path = Path(src_path)

        # Skip directories and non-regular-file events.
        if path.is_dir() or not path.suffix:
            return

        # Skip ignored directories.
        if set(path.parts) & _IGNORE_PATTERNS:
            return

        # Skip files with ignored suffixes (editor temp, .pyc, etc.).
        if path.suffix in _IGNORE_SUFFIXES:
            return
        if src_path.endswith("~"):
            return

        # Only care about Python source files.
        if path.suffix not in _WATCH_EXTENSIONS:
            return

        # Verify the file's mtime actually changed.  Resolve symlinks
        # so Docker bind-mount path aliasing doesn't defeat the cache.
        try:
            resolved = str(path.resolve(strict=False))
        except (OSError, RuntimeError):
            return
        try:
            current_mtime = path.stat().st_mtime
        except OSError:
            return
        last_mtime = self._mtimes.get(resolved)
        if last_mtime is None:
            # First time seeing this file — record baseline, ignore.
            self._mtimes[resolved] = current_mtime
            return
        if current_mtime == last_mtime:
            return  # false positive — mtime unchanged
        self._mtimes[resolved] = current_mtime

        self._last_path = src_path
        super().dispatch(event)


# ── Reloader ─────────────────────────────────────────────────────────────

class DevReloader:
    """Run *command* as a managed subprocess; restart on file changes."""

    def __init__(
        self,
        command: Sequence[str],
        watch_paths: Optional[list[Path]] = None,
    ):
        self._command = list(command)
        self._watch_paths = watch_paths or _default_watch_paths()
        self._process: Optional[subprocess.Popen] = None
        self._observer: Optional[Observer] = None
        self._handler = _ChangeHandler()
        self._shutdown_requested = False

    # -- Public API --------------------------------------------------------

    def run(self) -> int:
        """Block until shutdown; return the last process exit code."""
        self._setup_signal_handlers()
        self._start_observer()
        try:
            return self._run_loop()
        finally:
            self._cleanup()

    # -- Internals ---------------------------------------------------------

    def _setup_signal_handlers(self) -> None:
        """Forward SIGTERM/SIGINT to the child and set the shutdown flag."""
        signal.signal(signal.SIGTERM, self._on_shutdown_signal)
        signal.signal(signal.SIGINT, self._on_shutdown_signal)

    def _on_shutdown_signal(self, signum: int, _frame) -> None:
        logger.info("Received signal %s; shutting down reloader.", signum)
        self._shutdown_requested = True
        self._terminate_child()

    def _start_observer(self) -> None:
        """Schedule the watchdog observer on all configured watch paths."""
        paths = [p for p in self._watch_paths if p.is_dir()]
        if not paths:
            logger.warning(
                "No watchable directories found. "
                "Set AIRUNNER_DEV_RELOAD_PATHS to a colon-separated "
                "list of directories to watch."
            )
            return
        observer = Observer()
        for watch_path in paths:
            observer.schedule(
                self._handler, str(watch_path), recursive=True
            )
            logger.info("Watching: %s", watch_path)
        observer.start()
        self._observer = observer

    def _terminate_child(self) -> None:
        """Stop the managed subprocess and every descendant.

        Because ``_start_child`` creates a new session
        (``start_new_session=True``), the child's PID is also its
        process-group ID.  Sending ``SIGTERM`` to the process group
        ensures the daemon grandchild — which otherwise outlives the
        intermediate ``airunner-server`` process — is also stopped.
        """
        if self._process is None:
            return
        pid = self._process.pid
        if self._process.poll() is None:
            logger.info(
                "Stopping server process group (PGID %s)...", pid
            )
            try:
                os.killpg(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                self._process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                logger.warning(
                    "Server did not stop; sending SIGKILL to group."
                )
                try:
                    os.killpg(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                self._process.wait()

    def _start_child(self) -> subprocess.Popen:
        """Launch the server command."""
        logger.info("Starting: %s", " ".join(self._command))
        return subprocess.Popen(
            self._command,
            # Place the child in its own process group so signals sent
            # to the reloader don't also hit the child prematurely.
            start_new_session=True,
        )

    def _run_loop(self) -> int:
        """Main loop: start server, watch for changes, restart on change.

        A startup grace period (``_MIN_UPTIME``) is enforced after every
        child launch so that import-time ``.pyc`` generation and other
        one-shot startup writes do not trigger an immediate restart.
        After the grace window expires, any file change triggers a restart
        after a ``_DEBOUNCE_INTERVAL`` quiet period to batch rapid saves.

        If the child exits before ``_MIN_UPTIME`` elapses (e.g. connect-only
        to a stale daemon, or an immediate crash), a ``_COOLDOWN`` period
        is applied before any file-change restart is allowed.
        """
        _MIN_UPTIME = 3.0   # seconds before file-change restarts are allowed
        _COOLDOWN = 10.0     # seconds to wait after a rapid child exit

        self._handler.changed = False
        self._process = self._start_child()
        started_at = time.monotonic()
        exit_code: int = 0

        while not self._shutdown_requested:
            # Check if the child exited on its own.
            if self._process.poll() is not None:
                exit_code = self._process.returncode
                uptime = time.monotonic() - started_at
                if uptime < _MIN_UPTIME:
                    # Rapid exit — something is wrong.  Cooldown before
                    # allowing a file-change restart.
                    logger.warning(
                        "Server exited with code %s after %.1fs "
                        "(rapid exit). Cooling down for %.0fs...",
                        exit_code, uptime, _COOLDOWN,
                    )
                    self._handler.changed = False
                    time.sleep(_COOLDOWN)
                    if self._shutdown_requested:
                        break
                else:
                    logger.info(
                        "Server process exited with code %s. "
                        "Restarting on next file change...",
                        exit_code,
                    )
                    while (
                        not self._shutdown_requested
                        and not self._handler.changed
                    ):
                        time.sleep(0.5)
                if self._shutdown_requested:
                    break
                self._handler.changed = False
                self._process = self._start_child()
                started_at = time.monotonic()
                continue

            # File change detected.
            if self._handler.changed:
                now = time.monotonic()
                uptime = now - started_at
                if uptime < _MIN_UPTIME:
                    # Startup grace window — suppress noise.
                    self._handler.changed = False
                else:
                    # Past grace window — debounce, then restart.
                    self._handler.changed = False
                    time.sleep(_DEBOUNCE_INTERVAL)
                    if self._handler.changed:
                        self._handler.changed = False
                        continue
                    logger.info(
                        "Source files changed (%s);"
                        " restarting server...",
                        self._handler._last_path,
                    )
                    self._terminate_child()
                    self._process = self._start_child()
                    started_at = time.monotonic()

            time.sleep(0.5)

        self._terminate_child()
        return exit_code

    def _cleanup(self) -> None:
        """Stop the observer and ensure the child is terminated."""
        if self._observer is not None and self._observer.is_alive():
            self._observer.stop()
            self._observer.join(timeout=5)
        self._terminate_child()


# ── CLI entry point ──────────────────────────────────────────────────────

def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the reloader with the given command line.

    Usage::

        python -m airunner_services.dev_reload airunner-server --host 0.0.0.0
    """
    if argv is None:
        argv = sys.argv[1:]

    if not argv:
        print(
            "Usage: python -m airunner_services.dev_reload "
            "<command> [args...]",
            file=sys.stderr,
        )
        return 2

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [dev-reload] %(message)s",
        datefmt="%H:%M:%S",
    )

    reloader = DevReloader(command=argv)
    return reloader.run()


if __name__ == "__main__":
    raise SystemExit(main())
