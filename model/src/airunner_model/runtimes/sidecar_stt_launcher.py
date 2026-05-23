"""Process supervision for the whisper.cpp sidecar runtime."""

from __future__ import annotations

import os
import subprocess
import time
from typing import Any, Callable, Optional
from urllib.error import URLError
from urllib.request import urlopen

from airunner_model.contracts import RuntimeHealthStatus
from airunner_model.runtimes.file_policy import PathPolicyError
from airunner_model.runtimes.file_policy import resolve_existing_file
from airunner_model.runtimes.runtime_layout import (
	build_runtime_directory_layout,
)
from airunner_model.runtimes.whisper_cpp_runtime_settings import (
	WhisperCppRuntimeSettings,
)


HealthOpener = Callable[..., Any]
ProcessFactory = Callable[..., subprocess.Popen]


class SidecarSTTLauncher:
	"""Own the lifecycle of a long-lived whisper.cpp server process."""

	def __init__(
		self,
		settings: WhisperCppRuntimeSettings,
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
		self._log_handle = None

	@property
	def endpoint(self) -> str:
		"""Return the base HTTP endpoint for the managed process."""
		return self.settings.endpoint

	@property
	def inference_url(self) -> str:
		"""Return the whisper.cpp inference endpoint URL."""
		return (
			f"{self.endpoint}{self.settings.request_prefix}"
			f"{self.settings.normalized_inference_path}"
		)

	@property
	def last_error(self) -> str:
		"""Return the last launcher error message when one exists."""
		return self._last_error

	def command(self) -> list[str]:
		"""Build the whisper-server command line for the current settings."""
		model_path = self._required_model_path()
		command = [
			self.settings.executable,
			"--host",
			self.settings.host,
			"--port",
			str(self.settings.port),
			"--model",
			model_path,
			"--threads",
			str(self.settings.n_threads),
			"--processors",
			str(self.settings.n_processors),
			"--language",
			self.settings.language,
			"--inference-path",
			self.settings.normalized_inference_path,
		]
		if self.settings.request_prefix:
			command.extend(["--request-path", self.settings.request_prefix])
		if self.settings.convert_audio:
			command.append("--convert")
		if not self.settings.use_gpu:
			command.append("--no-gpu")
		return command

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
			self._close_log_handle()

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

	def _required_model_path(self) -> str:
		"""Return the configured ggml model path or raise a helpful error."""
		model_path = self.settings.model_path
		if not model_path:
			raise RuntimeError("No whisper.cpp model is configured")
		try:
			return resolve_existing_file(
				model_path,
				label="Configured whisper.cpp model",
			)
		except PathPolicyError as error:
			raise RuntimeError(str(error)) from error

	def _spawn_if_needed(self) -> None:
		"""Spawn the subprocess when it is not already alive."""
		if self.is_running():
			return
		command = self.command()
		environment = self._environment()
		stdout_handle = self._stdout_target()
		try:
			self._process = self._process_factory(
				command,
				stdout=stdout_handle,
				stderr=subprocess.STDOUT,
				env=environment,
			)
		except OSError as exc:
			self._close_log_handle()
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
				self._last_error = f"whisper.cpp exited with code {code}"
				raise RuntimeError(self._last_error)
			self._sleep(0.1)

		self.stop()
		self._last_error = "Timed out waiting for whisper.cpp to become ready"
		raise RuntimeError(self._last_error)

	def _health_url(self) -> str:
		"""Return the sidecar health-check URL."""
		return f"{self.endpoint}{self.settings.request_prefix}/health"

	def _environment(self) -> dict[str, str]:
		"""Return the child-process environment for the STT sidecar."""
		layout = build_runtime_directory_layout()
		layout.ensure_exists()
		environment = os.environ.copy()
		environment.update(layout.as_environment())
		return environment

	def _open_log_handle(self):
		"""Open the standardized log file for the STT sidecar."""
		layout = build_runtime_directory_layout()
		layout.ensure_exists()
		self._close_log_handle()
		self._log_handle = open(layout.log_file("stt-sidecar"), "ab")
		return self._log_handle

	def _stdout_target(self):
		"""Return the stdout target based on explicit file-logging opt-in."""
		if os.environ.get("AIRUNNER_SAVE_LOG_TO_FILE", "0") == "1":
			return self._open_log_handle()
		return subprocess.DEVNULL

	def _close_log_handle(self) -> None:
		"""Close the launcher-owned log file handle when one exists."""
		log_handle = self._log_handle
		self._log_handle = None
		if log_handle is not None:
			log_handle.close()


__all__ = ["SidecarSTTLauncher"]