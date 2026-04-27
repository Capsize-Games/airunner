"""Resolve llama.cpp sidecar settings from AIRunner configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from airunner.components.llm.config.provider_config import LLMProviderConfig
from airunner.settings import AIRUNNER_BASE_PATH

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8011
DEFAULT_STARTUP_TIMEOUT_SECONDS = 60.0
DEFAULT_CONTEXT_LENGTH = 32768


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


def _load_llm_settings() -> Any:
    """Return persisted LLM settings when the database is available."""
    try:
        from airunner.components.llm.data.llm_generator_settings import (
            LLMGeneratorSettings,
        )

        return LLMGeneratorSettings.objects.first()
    except Exception:
        return None


def _load_path_settings() -> Any:
    """Return persisted path settings when the database is available."""
    try:
        from airunner.components.settings.data.path_settings import PathSettings

        return PathSettings.objects.first()
    except Exception:
        return None


def _candidate_model_id(llm_settings: Any) -> str:
    """Resolve the configured local model identifier when available."""
    if llm_settings is None:
        return ""

    for value in (
        getattr(llm_settings, "model_id", None),
        getattr(llm_settings, "model_version", None),
        getattr(llm_settings, "model_path", None),
    ):
        if not value:
            continue
        resolved = LLMProviderConfig.resolve_model_id("local", str(value))
        if resolved:
            return resolved
    return ""


def _gguf_in_directory(model_path: str) -> Optional[str]:
    """Return a GGUF file found inside a configured model directory."""
    candidate_path = Path(os.path.expanduser(model_path))
    if candidate_path.is_file() and candidate_path.suffix.lower() == ".gguf":
        return str(candidate_path)
    if not candidate_path.is_dir():
        return None

    gguf_files = sorted(candidate_path.glob("*.gguf"))
    if not gguf_files:
        return None
    return str(gguf_files[0])


def _candidate_model_path(llm_settings: Any) -> str:
    """Return the raw persisted model path when present."""
    if llm_settings is None:
        return ""

    for value in (
        getattr(llm_settings, "model_path", None),
        getattr(llm_settings, "model_version", None),
    ):
        if value and str(value).strip():
            return str(value).strip()
    return ""


def _resolve_model_path(
    llm_settings: Any,
    base_path: str,
    model_id: str,
) -> Optional[str]:
    """Resolve the GGUF model path that should be served by llama.cpp."""
    env_override = os.environ.get("AIRUNNER_LLAMA_MODEL_PATH", "").strip()
    if env_override:
        return os.path.expanduser(env_override)

    stored_path = _candidate_model_path(llm_settings)
    resolved_from_dir = _gguf_in_directory(stored_path)
    if resolved_from_dir is not None:
        return resolved_from_dir

    if model_id and model_id != "custom":
        expected = LLMProviderConfig.get_expected_local_artifact_path(
            base_path,
            "local",
            model_id=model_id,
        )
        if expected.lower().endswith(".gguf"):
            return expected

    if stored_path.endswith(".gguf"):
        return os.path.expanduser(stored_path)
    return None


def _context_length(model_id: str) -> int:
    """Return the preferred llama.cpp context length for a model."""
    if not model_id:
        return DEFAULT_CONTEXT_LENGTH

    model_info = LLMProviderConfig.get_model_info("local", model_id) or {}
    return int(
        model_info.get("native_context_length")
        or model_info.get("context_length")
        or DEFAULT_CONTEXT_LENGTH
    )


def _gpu_layers(llm_settings: Any) -> int:
    """Return the configured GPU offload policy for llama.cpp."""
    override = os.environ.get("AIRUNNER_LLAMA_N_GPU_LAYERS", "").strip()
    if override:
        try:
            return int(override)
        except ValueError:
            pass

    use_gpu = True
    if llm_settings is not None:
        use_gpu = bool(getattr(llm_settings, "use_gpu", True))
    return -1 if use_gpu else 0


@dataclass(frozen=True)
class LlamaCppRuntimeSettings:
    """Resolved settings for the supervised llama.cpp sidecar."""

    executable: str
    host: str
    port: int
    model_path: Optional[str]
    model_id: Optional[str]
    n_ctx: int
    n_gpu_layers: int
    startup_timeout_seconds: float

    @property
    def endpoint(self) -> str:
        """Return the HTTP endpoint exposed by the sidecar."""
        return f"http://{self.host}:{self.port}"


def resolve_llama_cpp_runtime_settings() -> LlamaCppRuntimeSettings:
    """Resolve sidecar settings from environment and persisted AIRunner state."""
    llm_settings = _load_llm_settings()
    path_settings = _load_path_settings()
    base_path = getattr(path_settings, "base_path", AIRUNNER_BASE_PATH)
    model_id = _candidate_model_id(llm_settings) or None
    default_ctx = _context_length(model_id or "")

    return LlamaCppRuntimeSettings(
        executable=os.environ.get(
            "AIRUNNER_LLAMA_SERVER_BIN",
            "llama-server",
        ),
        host=os.environ.get("AIRUNNER_LLAMA_HOST", DEFAULT_HOST),
        port=_env_int("AIRUNNER_LLAMA_PORT", DEFAULT_PORT),
        model_path=_resolve_model_path(
            llm_settings,
            os.path.expanduser(base_path),
            model_id or "",
        ),
        model_id=model_id,
        n_ctx=_env_int("AIRUNNER_LLAMA_N_CTX", default_ctx),
        n_gpu_layers=_gpu_layers(llm_settings),
        startup_timeout_seconds=_env_float(
            "AIRUNNER_LLAMA_STARTUP_TIMEOUT",
            DEFAULT_STARTUP_TIMEOUT_SECONDS,
        ),
    )
