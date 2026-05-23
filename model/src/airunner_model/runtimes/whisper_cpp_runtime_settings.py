"""Resolve whisper.cpp sidecar settings from AIRunner configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from airunner_model.settings import AIRUNNER_BASE_PATH

from airunner_model.runtimes.bundled_runtime_paths import (
    resolve_runtime_executable,
)
from airunner_model.runtimes.runtime_bind_host import (
    resolve_runtime_bind_host,
)


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8012
DEFAULT_INFERENCE_PATH = "/inference"
DEFAULT_REQUEST_PATH = ""
DEFAULT_LANGUAGE = "auto"
DEFAULT_STARTUP_TIMEOUT_SECONDS = 60.0


def _env_int(name: str, default: int) -> int:
    """Return an integer environment override when one is set."""
    value = os.environ.get(name)
    if value is None or not str(value).strip():
        return default
    try:
        return int(str(value).strip())
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    """Return a float environment override when one is set."""
    value = os.environ.get(name)
    if value is None or not str(value).strip():
        return default
    try:
        return float(str(value).strip())
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    """Return a boolean environment override when one is set."""
    value = os.environ.get(name)
    if value is None or not str(value).strip():
        return default
    return str(value).strip().lower() not in {"0", "false", "no", "off"}


def _load_path_settings() -> Any:
    """Return model-side path settings when one backend is provided."""
    return None


def _stt_base_directory(base_path: str, path_settings: Any) -> str:
    """Return the resolved STT model directory used by AIRunner."""
    configured_path = getattr(path_settings, "stt_model_path", "")
    if not configured_path:
        return os.path.join(
            os.path.expanduser(base_path),
            "text/models/stt",
        )

    expanded = os.path.expanduser(str(configured_path))
    if os.path.isabs(expanded):
        return expanded
    return os.path.join(os.path.expanduser(base_path), expanded)


def _discover_model_path(model_directory: str) -> Optional[str]:
    """Find the first whisper.cpp ggml model file in the STT directory."""
    candidate = Path(os.path.expanduser(model_directory))
    if candidate.is_file():
        if candidate.name.startswith("ggml-") and candidate.suffix == ".bin":
            return str(candidate)
        return None
    if not candidate.is_dir():
        return None

    preferred = sorted(candidate.rglob("ggml-*.bin"))
    if preferred:
        return str(preferred[0])
    return None


def _candidate_model_path(base_path: str, path_settings: Any) -> Optional[str]:
    """Return the configured whisper.cpp model path when one exists."""
    env_override = os.environ.get("AIRUNNER_WHISPER_MODEL_PATH", "").strip()
    if env_override:
        return os.path.expanduser(env_override)
    return _discover_model_path(_stt_base_directory(base_path, path_settings))


@dataclass(frozen=True)
class WhisperCppRuntimeSettings:
    """Resolved settings for the supervised whisper.cpp sidecar."""

    executable: str
    host: str
    port: int
    model_path: Optional[str]
    model_id: Optional[str]
    n_threads: int
    n_processors: int
    language: str
    request_path: str
    inference_path: str
    convert_audio: bool
    use_gpu: bool
    startup_timeout_seconds: float

    @property
    def endpoint(self) -> str:
        """Return the base HTTP endpoint exposed by the sidecar."""
        return f"http://{self.host}:{self.port}"

    @property
    def request_prefix(self) -> str:
        """Return the normalized request prefix for sidecar endpoints."""
        prefix = self.request_path.strip()
        if not prefix:
            return ""
        if not prefix.startswith("/"):
            prefix = f"/{prefix}"
        return prefix.rstrip("/")

    @property
    def normalized_inference_path(self) -> str:
        """Return the normalized inference endpoint path."""
        path = self.inference_path.strip() or DEFAULT_INFERENCE_PATH
        if not path.startswith("/"):
            path = f"/{path}"
        return path


def resolve_whisper_cpp_runtime_settings(
    path_settings: Any = None,
) -> WhisperCppRuntimeSettings:
    """Resolve whisper.cpp settings from environment and optional state."""
    resolved_path_settings = (
        path_settings if path_settings is not None else _load_path_settings()
    )
    base_path = getattr(
        resolved_path_settings,
        "base_path",
        AIRUNNER_BASE_PATH,
    )
    model_path = _candidate_model_path(base_path, resolved_path_settings)
    model_id = Path(model_path).name if model_path else None
    cpu_count = os.cpu_count() or 4

    return WhisperCppRuntimeSettings(
        executable=resolve_runtime_executable(
            "AIRUNNER_WHISPER_SERVER_BIN",
            "whisper-server",
        ),
        host=resolve_runtime_bind_host(
            "AIRUNNER_WHISPER_HOST",
            "AIRUNNER_RUNTIME_BIND_HOST",
        ),
        port=_env_int("AIRUNNER_WHISPER_PORT", DEFAULT_PORT),
        model_path=model_path,
        model_id=model_id,
        n_threads=_env_int(
            "AIRUNNER_WHISPER_THREADS",
            max(1, min(cpu_count, 8)),
        ),
        n_processors=_env_int("AIRUNNER_WHISPER_PROCESSORS", 1),
        language=os.environ.get("AIRUNNER_WHISPER_LANGUAGE", DEFAULT_LANGUAGE),
        request_path=os.environ.get(
            "AIRUNNER_WHISPER_REQUEST_PATH",
            DEFAULT_REQUEST_PATH,
        ),
        inference_path=os.environ.get(
            "AIRUNNER_WHISPER_INFERENCE_PATH",
            DEFAULT_INFERENCE_PATH,
        ),
        convert_audio=_env_bool("AIRUNNER_WHISPER_CONVERT_AUDIO", False),
        use_gpu=_env_bool("AIRUNNER_WHISPER_USE_GPU", True),
        startup_timeout_seconds=_env_float(
            "AIRUNNER_WHISPER_STARTUP_TIMEOUT",
            DEFAULT_STARTUP_TIMEOUT_SECONDS,
        ),
    )


__all__ = [
    "WhisperCppRuntimeSettings",
    "resolve_whisper_cpp_runtime_settings",
]