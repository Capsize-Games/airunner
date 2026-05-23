"""Process supervision for the isolated TTS runtime."""

from __future__ import annotations

import copy
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Optional
from urllib.error import URLError
from urllib.request import urlopen

from airunner_services.runtimes.contracts import RuntimeHealthStatus
from airunner_services.runtimes.tts_daemon_runtime_settings import (
    TTSDaemonRuntimeSettings,
)
from airunner_services.config.runtime_layout import (
    build_runtime_directory_layout,
)
from airunner_services.daemon_config import DaemonConfig

HealthOpener = Callable[..., Any]
LaunchPreparer = Callable[[], None]
ProcessFactory = Callable[..., subprocess.Popen]
ConfigPathBuilder = Callable[[TTSDaemonRuntimeSettings], Path]


def _build_temp_daemon_config(
    settings: TTSDaemonRuntimeSettings,
) -> Path:
    """Clone one daemon config with a dedicated host and port."""
    layout = build_runtime_directory_layout()
    layout.ensure_exists()
    config_path = None
    if settings.base_daemon_config_path:
        config_path = Path(settings.base_daemon_config_path)
    base_config = DaemonConfig(config_path)
    config = copy.deepcopy(base_config.config)
    config.setdefault("server", {})["host"] = settings.host
    config.setdefault("server", {})["port"] = settings.port
    config.setdefault("models", {})["preload"] = []
    config.setdefault("health", {})["heartbeat_file"] = str(
        layout.heartbeat_file("tts-runtime")
    )
    config.setdefault("logging", {})["file"] = str(
        layout.log_file("tts-runtime")
    )
    config["runtime"] = layout.as_config()

    file_descriptor, temp_path = tempfile.mkstemp(
        prefix="airunner-tts-runtime-",
        suffix=".yaml",
        dir=str(layout.config_dir),
    )
    os.close(file_descriptor)
    temp_config = DaemonConfig(Path(temp_path))
    temp_config.config = config
    temp_config.save()
    return Path(temp_path)


def _prepare_managed_daemon_launch() -> None:
    """Perform the one-time setup required before launching a daemon."""
    from airunner_native.launcher import _configure_test_mode
    from airunner_services.database.setup import setup_database

    setup_database()
    if os.environ.get("AIRUNNER_ENVIRONMENT") == "test":
        _configure_test_mode()


class SidecarTTSLauncher:
    """Own the lifecycle of one dedicated TTS daemon process."""

    def __init__(
        self,
        settings: TTSDaemonRuntimeSettings,
        *,
        process_factory: ProcessFactory = subprocess.Popen,
        health_opener: HealthOpener = urlopen,
        config_path_builder: ConfigPathBuilder = _build_temp_daemon_config,
        launch_preparer: LaunchPreparer = _prepare_managed_daemon_launch,
        sleep: Callable[[float], None] = time.sleep,
        time_fn: Callable[[], float] = time.monotonic,
    ) -> None:
        self.settings = settings
        self._process_factory = process_factory
        self._health_opener = health_opener
        self._config_path_builder = config_path_builder
        self._launch_preparer = launch_preparer
        self._sleep = sleep
        self._time_fn = time_fn
        self._process: Optional[subprocess.Popen] = None
        self._config_path: Optional[Path] = None
        self._last_error = ""

    @property
    def endpoint(self) -> str:
        """Return the base HTTP endpoint for the managed process."""
        return self.settings.endpoint

    @property
    def api_base_url(self) -> str:
        """Return the TTS API base URL exposed by the sidecar daemon."""
        return f"{self.endpoint}/api/v1/tts"

    @property
    def last_error(self) -> str:
        """Return the last launcher error message when one exists."""
        return self._last_error

    def command(self) -> list[str]:
        """Build the daemon launch command for the TTS sidecar."""
        if self._config_path is None:
            self._config_path = self._config_path_builder(self.settings)
        return [
            sys.executable,
            "-m",
            "airunner_services.daemon",
            "--config",
            str(self._config_path),
        ]

    def start(self) -> None:
        """Start the TTS runtime and wait until health responds."""
        if self.is_ready():
            return
        self._last_error = ""
        self._spawn_if_needed()
        self._wait_until_ready()

    def stop(self) -> None:
        """Stop the managed process and clean up its temp config."""
        process = self._process
        self._process = None
        try:
            if process is None or process.poll() is not None:
                return
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        finally:
            self._cleanup_config()

    def is_running(self) -> bool:
        """Return True when the subprocess is still alive."""
        return self._process is not None and self._process.poll() is None

    def is_ready(self) -> bool:
        """Return True when the subprocess health endpoint responds."""
        if not self.is_running():
            return False
        try:
            with self._health_opener(self._health_url(), timeout=1) as response:
                return 200 <= getattr(response, "status", 0) < 300
        except (OSError, URLError):
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

    def _spawn_if_needed(self) -> None:
        """Spawn the subprocess when it is not already alive."""
        if self.is_running():
            return
        command = self.command()
        environment = self._environment()
        try:
            self._launch_preparer()
            self._process = self._process_factory(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=environment,
            )
        except Exception as exc:
            self._last_error = str(exc)
            self._cleanup_config()
            raise RuntimeError(str(exc)) from exc

    def _wait_until_ready(self) -> None:
        """Poll the sidecar until it becomes healthy or times out."""
        deadline = self._time_fn() + self.settings.startup_timeout_seconds
        while self._time_fn() < deadline:
            if self.is_ready():
                return
            if self._process is not None and self._process.poll() is not None:
                code = self._process.poll()
                self._last_error = f"tts runtime exited with code {code}"
                self._cleanup_config()
                raise RuntimeError(self._last_error)
            self._sleep(0.1)

        self.stop()
        self._last_error = "Timed out waiting for TTS runtime to become ready"
        raise RuntimeError(self._last_error)

    def _environment(self) -> dict[str, str]:
        """Return the child-process environment for the TTS daemon."""
        layout = build_runtime_directory_layout()
        layout.ensure_exists()
        environment = os.environ.copy()
        environment.update(layout.as_environment(self._config_path))
        environment.update(
            {
                "AIRUNNER_HEADLESS": "1",
                "AIRUNNER_HTTP_HOST": self.settings.host,
                "AIRUNNER_HTTP_PORT": str(self.settings.port),
                "AIRUNNER_LLM_ON": "0",
                "AIRUNNER_SD_ON": "0",
                "AIRUNNER_TTS_ON": "1",
                "AIRUNNER_STT_ON": "0",
                "AIRUNNER_CN_ON": "0",
                "AIRUNNER_KNOWLEDGE_ON": "0",
                "AIRUNNER_TTS_SIDECAR_PROCESS": "1",
            }
        )
        if self.settings.tts_model_path:
            environment["AIRUNNER_TTS_MODEL_PATH"] = (
                self.settings.tts_model_path
            )
        if self.settings.tts_model_type:
            environment["AIRUNNER_TTS_MODEL_TYPE"] = (
                self.settings.tts_model_type
            )
        return environment

    def _cleanup_config(self) -> None:
        """Delete the temporary config file used for this launcher."""
        config_path = self._config_path
        self._config_path = None
        if config_path is None:
            return
        config_path.unlink(missing_ok=True)

    def _health_url(self) -> str:
        """Return the sidecar health-check URL."""
        return f"{self.endpoint}/health"