"""Subprocess launcher for the local AI Runner daemon."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any, Callable, Optional

from airunner.linux_bundle_layout import build_linux_bundle_layout
from airunner.runtime_layout import build_runtime_directory_layout

ProcessFactory = Callable[..., subprocess.Popen]


class DaemonLauncher:
    """Start and stop a local daemon subprocess for the GUI client."""

    def __init__(
        self,
        config_path: Optional[Path] = None,
        *,
        process_factory: ProcessFactory = subprocess.Popen,
        stdout: Any = subprocess.DEVNULL,
        stderr: Any = subprocess.DEVNULL,
        working_directory: Optional[Path] = None,
        environment: Optional[dict[str, str]] = None,
    ) -> None:
        self.config_path = config_path
        self._process_factory = process_factory
        self._stdout = self._resolved_stdio(stdout)
        self._stderr = self._resolved_stdio(stderr)
        self._working_directory = working_directory
        self._environment = environment
        self._process: Optional[subprocess.Popen] = None

    def _resolved_stdio(self, stream: Any) -> Any:
        """Use inherited stdio in dev mode so daemon startup errors are visible."""
        if stream is not subprocess.DEVNULL:
            return stream
        if os.environ.get("DEV_ENV", "1") != "1":
            return stream
        return None

    def command(self) -> list[str]:
        """Return the daemon launch command."""
        bundle_layout = build_linux_bundle_layout()
        daemon_executable = bundle_layout.daemon_executable()
        if daemon_executable is not None:
            command = [str(daemon_executable)]
        else:
            command = [
                str(bundle_layout.python_executable),
                "-m",
                "airunner.services.daemon",
            ]
        if self.config_path is not None:
            command.extend(["--config", str(self.config_path)])
        return command

    def _process_working_directory(self) -> Optional[str]:
        """Return the daemon working directory for one launch."""
        if self._working_directory is not None:
            return str(self._working_directory)
        return str(build_linux_bundle_layout().bundle_root)

    def _process_environment(self) -> Optional[dict[str, str]]:
        """Return the environment for one daemon launch."""
        if self._environment is not None:
            return self._environment

        bundle_layout = build_linux_bundle_layout()
        runtime_layout = build_runtime_directory_layout()
        environment = dict(os.environ)
        environment.update(runtime_layout.as_environment(self.config_path))
        environment.pop("AIRUNNER_ART_SIDECAR_PROCESS", None)
        environment.pop("AIRUNNER_TTS_SIDECAR_PROCESS", None)
        environment.setdefault("AIRUNNER_HEADLESS", "1")
        environment.setdefault(
            "AIRUNNER_BUNDLE_ROOT",
            str(bundle_layout.bundle_root),
        )
        environment.setdefault(
            "AIRUNNER_PYTHON",
            str(bundle_layout.python_executable),
        )
        environment["PATH"] = bundle_layout.path_environment(
            environment.get("PATH")
        )
        environment.setdefault("QT_QPA_PLATFORM", "offscreen")
        environment.setdefault(
            "QT_LOGGING_RULES",
            "*.debug=false;qt.qpa.*=false",
        )
        environment.setdefault("AIRUNNER_NO_PRELOAD", "1")
        return environment

    def start(self) -> None:
        """Start the daemon when it is not already running."""
        if self.is_running():
            return
        self._process = self._process_factory(
            self.command(),
            stdout=self._stdout,
            stderr=self._stderr,
            cwd=self._process_working_directory(),
            env=self._process_environment(),
        )

    def stop(self) -> None:
        """Stop the launched daemon subprocess."""
        process = self._process
        self._process = None
        if process is None or process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)

    def is_running(self) -> bool:
        """Return True when the managed subprocess is alive."""
        return self._process is not None and self._process.poll() is None

    def last_exit_code(self) -> Optional[int]:
        """Return the child exit code when the daemon process has exited."""
        if self._process is None:
            return None
        return self._process.poll()