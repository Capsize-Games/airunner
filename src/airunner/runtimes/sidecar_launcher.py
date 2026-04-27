"""Process supervision for the llama.cpp sidecar runtime."""

from __future__ import annotations

import os
import subprocess
import time
from typing import Any, Callable, Optional
from urllib.error import URLError
from urllib.request import urlopen

from airunner.runtimes.contracts import RuntimeHealthStatus
from airunner.runtimes.llama_cpp_runtime_settings import (
    LlamaCppRuntimeSettings,
)

HealthOpener = Callable[..., Any]
ProcessFactory = Callable[..., subprocess.Popen]


class SidecarLauncher:
    """Own the lifecycle of a long-lived llama.cpp server process."""

    def __init__(
        self,
        settings: LlamaCppRuntimeSettings,
        *,
        process_factory: ProcessFactory = subprocess.Popen,
        health_opener: HealthOpener = urlopen,
        sleep: Callable[[float], None] = time.sleep,
        time_fn: Callable[[], float] = time.monotonic,
    ) -> None:
        self.settings = settings
        self._process_factory = process_factory
        self._health_opener = health_opener
        self._sleep = sleep
        self._time_fn = time_fn
        self._process: Optional[subprocess.Popen] = None
        self._last_error = ""

    @property
    def endpoint(self) -> str:
        """Return the local HTTP endpoint for the managed process."""
        return self.settings.endpoint

    @property
    def last_error(self) -> str:
        """Return the last launcher error message when one exists."""
        return self._last_error

    def command(self) -> list[str]:
        """Build the llama-server command line for the current settings."""
        model_path = self._required_model_path()
        return [
            self.settings.executable,
            "--host",
            self.settings.host,
            "--port",
            str(self.settings.port),
            "--model",
            model_path,
            "--ctx-size",
            str(self.settings.n_ctx),
            "--n-gpu-layers",
            str(self.settings.n_gpu_layers),
        ]

    def start(self) -> None:
        """Start the sidecar and wait until its health endpoint responds."""
        if self.is_ready():
            return
        self._last_error = ""
        self._spawn_if_needed()
        self._wait_until_ready()

    def stop(self) -> None:
        """Stop the managed process when one is running."""
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
        """Return True when the subprocess is still alive."""
        return self._process is not None and self._process.poll() is None

    def is_ready(self) -> bool:
        """Return True when the subprocess health endpoint is responding."""
        if not self.is_running():
            return False
        try:
            with self._health_opener(self._health_url(), timeout=1) as response:
                return 200 <= getattr(response, "status", 0) < 300
        except URLError:
            return False

    def health_status(self) -> tuple[RuntimeHealthStatus, str]:
        """Return the runtime health state exposed to AIRunner."""
        if self.is_ready():
            return RuntimeHealthStatus.READY, "ready"
        if self.is_running():
            return RuntimeHealthStatus.STARTING, "starting"
        if self._process is not None and self._process.poll() is not None:
            code = self._process.poll()
            return RuntimeHealthStatus.FAILED, f"exited with code {code}"
        if self._last_error:
            return RuntimeHealthStatus.FAILED, self._last_error
        return RuntimeHealthStatus.STOPPED, "not loaded"

    def _required_model_path(self) -> str:
        """Return the configured GGUF path or raise a helpful error."""
        model_path = self.settings.model_path
        if not model_path:
            raise RuntimeError("No GGUF model is configured for llama.cpp")
        expanded = os.path.expanduser(model_path)
        if not os.path.exists(expanded):
            raise RuntimeError(f"Configured GGUF model not found: {expanded}")
        return expanded

    def _spawn_if_needed(self) -> None:
        """Spawn the subprocess when it is not already alive."""
        if self.is_running():
            return
        command = self.command()
        try:
            self._process = self._process_factory(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError as exc:
            self._last_error = str(exc)
            raise RuntimeError(str(exc)) from exc

    def _wait_until_ready(self) -> None:
        """Poll the sidecar until it becomes healthy or times out."""
        deadline = self._time_fn() + self.settings.startup_timeout_seconds
        while self._time_fn() < deadline:
            if self.is_ready():
                return
            if self._process is not None and self._process.poll() is not None:
                code = self._process.poll()
                self._last_error = f"llama.cpp exited with code {code}"
                raise RuntimeError(self._last_error)
            self._sleep(0.1)

        self.stop()
        self._last_error = "Timed out waiting for llama.cpp to become ready"
        raise RuntimeError(self._last_error)

    def _health_url(self) -> str:
        """Return the sidecar health-check URL."""
        return f"{self.endpoint}/health"
