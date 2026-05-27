"""Resolve llama.cpp sidecar settings from AIRunner configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from airunner_services.settings import AIRUNNER_BASE_PATH

from airunner_services.runtimes.bundled_runtime_paths import (
    resolve_runtime_executable,
)
from airunner_services.runtimes.runtime_bind_host import (
    resolve_runtime_bind_host,
)


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
    """Return persisted service-side LLM settings when available."""
    try:
        from airunner_services.database.models.llm_generator_settings import (
            LLMGeneratorSettings,
        )

        return LLMGeneratorSettings.objects.first()
    except Exception:
        return None


def _load_path_settings() -> Any:
    """Return persisted service-side path settings when available."""
    try:
        from airunner_services.database.models.path_settings import (
            PathSettings,
        )

        return PathSettings.objects.first()
    except Exception:
        return None


def _load_provider_config() -> Any:
    """Return the provider metadata helper when the service owns it."""
    try:
        from airunner_services.llm.provider_config import LLMProviderConfig

        return LLMProviderConfig
    except Exception:
        return None


def _candidate_model_id(llm_settings: Any) -> str:
    """Resolve the configured local model identifier when available."""
    if llm_settings is None:
        return ""

    provider_config = _load_provider_config()
    for value in (
        getattr(llm_settings, "model_id", None),
        getattr(llm_settings, "model_version", None),
        getattr(llm_settings, "model_path", None),
    ):
        if not value:
            continue
        if provider_config is None:
            continue
        resolved = provider_config.resolve_model_id("local", str(value))
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

    provider_config = _load_provider_config()
    if provider_config is not None and model_id and model_id != "custom":
        expected = provider_config.get_expected_local_artifact_path(
            base_path,
            "local",
            model_id=model_id,
        )
        if expected.lower().endswith(".gguf"):
            return expected

    stored_path = _candidate_model_path(llm_settings)
    if stored_path.endswith(".gguf"):
        return os.path.expanduser(stored_path)

    resolved_from_dir = _gguf_in_directory(stored_path)
    if resolved_from_dir is not None:
        return resolved_from_dir

    return None


def _context_length(model_id: str, profile_name: str = "default") -> int:
    """Return the preferred llama.cpp context length for a model."""
    if not model_id:
        return DEFAULT_CONTEXT_LENGTH

    provider_config = _load_provider_config()
    if provider_config is None:
        return DEFAULT_CONTEXT_LENGTH

    runtime_profile = provider_config.get_gguf_runtime_profile(
        "local",
        model_id,
        profile_name=profile_name,
    )
    default_n_ctx = runtime_profile.get("n_ctx")
    if default_n_ctx:
        return int(default_n_ctx)

    model_info = provider_config.get_model_info("local", model_id) or {}
    return int(
        model_info.get("native_context_length")
        or model_info.get("context_length")
        or DEFAULT_CONTEXT_LENGTH
    )


def _gpu_layers(
    llm_settings: Any,
    model_id: str,
    profile_name: str = "default",
) -> int:
    """Return the configured GPU offload policy for llama.cpp."""
    override = os.environ.get("AIRUNNER_LLAMA_N_GPU_LAYERS", "").strip()
    if override:
        try:
            return int(override)
        except ValueError:
            pass

    provider_config = _load_provider_config()
    if provider_config is not None and model_id:
        runtime_profile = provider_config.get_gguf_runtime_profile(
            "local",
            model_id,
            profile_name=profile_name,
        )
        default_n_gpu_layers = runtime_profile.get("n_gpu_layers")
        if default_n_gpu_layers is not None:
            return int(default_n_gpu_layers)

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
    runtime_profile: str
    n_ctx: int
    n_gpu_layers: int
    startup_timeout_seconds: float

    @property
    def endpoint(self) -> str:
        """Return the HTTP endpoint exposed by the sidecar."""
        return f"http://{self.host}:{self.port}"


def resolve_llama_cpp_runtime_settings(
    llm_settings: Any = None,
    path_settings: Any = None,
    runtime_profile: Optional[str] = None,
) -> LlamaCppRuntimeSettings:
    """Resolve sidecar settings from environment and optional persisted state."""
    resolved_llm_settings = (
        llm_settings if llm_settings is not None else _load_llm_settings()
    )
    resolved_path_settings = (
        path_settings if path_settings is not None else _load_path_settings()
    )
    base_path = getattr(
        resolved_path_settings,
        "base_path",
        AIRUNNER_BASE_PATH,
    )
    model_id = _candidate_model_id(resolved_llm_settings) or None
    selected_profile = str(runtime_profile or "default").strip() or "default"
    default_ctx = _context_length(model_id or "", selected_profile)

    return LlamaCppRuntimeSettings(
        executable=resolve_runtime_executable(
            "AIRUNNER_LLAMA_SERVER_BIN",
            "llama-server",
        ),
        host=resolve_runtime_bind_host(
            "AIRUNNER_LLAMA_HOST",
            "AIRUNNER_RUNTIME_BIND_HOST",
        ),
        port=_env_int("AIRUNNER_LLAMA_PORT", DEFAULT_PORT),
        model_path=_resolve_model_path(
            resolved_llm_settings,
            os.path.expanduser(base_path),
            model_id or "",
        ),
        model_id=model_id,
        runtime_profile=selected_profile,
        n_ctx=_env_int("AIRUNNER_LLAMA_N_CTX", default_ctx),
        n_gpu_layers=_gpu_layers(
            resolved_llm_settings,
            model_id or "",
            selected_profile,
        ),
        startup_timeout_seconds=_env_float(
            "AIRUNNER_LLAMA_STARTUP_TIMEOUT",
            DEFAULT_STARTUP_TIMEOUT_SECONDS,
        ),
    )


__all__ = [
    "LlamaCppRuntimeSettings",
    "resolve_llama_cpp_runtime_settings",
]