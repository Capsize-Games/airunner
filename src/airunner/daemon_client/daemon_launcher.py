"""Subprocess launcher for the local AI Runner daemon."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Callable, Optional

ProcessFactory = Callable[..., subprocess.Popen]


class DaemonLauncher:
    """Start and stop a local daemon subprocess for the GUI client."""

    def __init__(
        self,
        config_path: Optional[Path] = None,
        *,
        process_factory: ProcessFactory = subprocess.Popen,
    ) -> None:
        self.config_path = config_path
        self._process_factory = process_factory
        self._process: Optional[subprocess.Popen] = None

    def command(self) -> list[str]:
        """Return the daemon launch command."""
        command = [sys.executable, "-m", "airunner.services.daemon"]
        if self.config_path is not None:
            command.extend(["--config", str(self.config_path)])
        return command

    def start(self) -> None:
        """Start the daemon when it is not already running."""
        if self.is_running():
            return
        self._process = self._process_factory(
            self.command(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
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