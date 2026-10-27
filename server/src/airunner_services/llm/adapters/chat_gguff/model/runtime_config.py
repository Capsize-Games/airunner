"""GGUF runtime-tuning and context-retry helpers."""

import os
from typing import Any, Optional


def _get_int_env(name: str) -> Optional[int]:
    """Parse an integer environment variable if present."""
    value = os.environ.get(name)
    if value is None or not str(value).strip():
        return None
    try:
        return int(str(value).strip())
    except ValueError:
        return None


def _get_bool_env(name: str) -> Optional[bool]:
    """Parse a boolean environment variable if present."""
    value = os.environ.get(name)
    if value is None or not str(value).strip():
        return None
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    return None


def resolve_llama_tuning(adapter: Any) -> dict[str, Any]:
    """Resolve optional llama.cpp tuning overrides from the environment."""
    tuning: dict[str, Any] = {
        "n_batch": adapter.n_batch,
        "offload_kqv": True,
    }
    _apply_optional_int_overrides(tuning)
    _apply_optional_bool_overrides(tuning)
    return tuning


def _apply_optional_int_overrides(tuning: dict[str, Any]) -> None:
    """Apply integer runtime overrides to llama.cpp tuning."""
    n_batch_override = _get_int_env("AIRUNNER_GGUF_N_BATCH")
    if n_batch_override is not None:
        tuning["n_batch"] = n_batch_override

    n_ubatch_override = _get_int_env("AIRUNNER_GGUF_N_UBATCH")
    if n_ubatch_override is not None:
        tuning["n_ubatch"] = n_ubatch_override

    n_threads_override = _get_int_env("AIRUNNER_GGUF_N_THREADS")
    if n_threads_override is not None:
        tuning["n_threads"] = n_threads_override

    n_threads_batch_override = _get_int_env("AIRUNNER_GGUF_N_THREADS_BATCH")
    if n_threads_batch_override is not None:
        tuning["n_threads_batch"] = n_threads_batch_override


def _apply_optional_bool_overrides(tuning: dict[str, Any]) -> None:
    """Apply boolean runtime overrides to llama.cpp tuning."""
    offload_kqv_override = _get_bool_env("AIRUNNER_GGUF_OFFLOAD_KQV")
    if offload_kqv_override is not None:
        tuning["offload_kqv"] = offload_kqv_override

    op_offload_override = _get_bool_env("AIRUNNER_GGUF_OP_OFFLOAD")
    if op_offload_override is not None:
        tuning["op_offload"] = op_offload_override


def format_llama_tuning(tuning: dict[str, Any]) -> str:
    """Format tuning fields for concise logging."""
    keys = [
        "n_batch",
        "n_ubatch",
        "n_threads",
        "n_threads_batch",
        "offload_kqv",
        "op_offload",
    ]
    return ", ".join(f"{key}={tuning[key]}" for key in keys if key in tuning)


def apply_runtime_env_overrides(adapter: Any) -> None:
    """Apply optional llama.cpp runtime overrides from the environment."""
    n_ctx_override = _get_int_env("AIRUNNER_GGUF_N_CTX")
    if n_ctx_override is not None and n_ctx_override > 0:
        adapter.n_ctx = n_ctx_override

    n_gpu_layers_override = _get_int_env("AIRUNNER_GGUF_N_GPU_LAYERS")
    if n_gpu_layers_override is not None:
        adapter.n_gpu_layers = n_gpu_layers_override
        return
    if _needs_safe_gpt_oss_cpu_default(adapter):
        adapter.n_gpu_layers = 0


def _needs_safe_gpt_oss_cpu_default(adapter: Any) -> bool:
    """Return True when GPT-OSS should avoid full offload by default."""
    model_path = str(getattr(adapter, "model_path", "")).lower()
    return "gpt-oss" in model_path and getattr(adapter, "n_gpu_layers", -1) < 0


def load_llama_with_context_fallback(
    adapter: Any,
    llama_cls: Any,
    base_kwargs: dict[str, Any],
) -> None:
    """Load llama.cpp and retry smaller contexts on allocation failure."""
    attempted_n_ctx = adapter.n_ctx
    for n_ctx in context_retry_sequence(adapter):
        try:
            _load_llama_for_context(adapter, llama_cls, base_kwargs, n_ctx)
            return
        except Exception as exc:
            attempted_n_ctx = _retry_n_ctx_or_raise(adapter, exc, n_ctx)

    adapter.n_ctx = attempted_n_ctx


def _load_llama_for_context(
    adapter: Any,
    llama_cls: Any,
    base_kwargs: dict[str, Any],
    n_ctx: int,
) -> None:
    """Load llama.cpp for one specific context size."""
    llama_kwargs = llama_kwargs_for_context(adapter, base_kwargs, n_ctx)
    adapter._llama = llama_cls(**llama_kwargs)
    adapter.n_ctx = n_ctx


def _retry_n_ctx_or_raise(
    adapter: Any,
    exc: Exception,
    n_ctx: int,
) -> int:
    """Return the next retry context or re-raise the current exception."""
    if not should_retry_context(exc, n_ctx):
        raise
    next_n_ctx = next_retry_context(n_ctx)
    if next_n_ctx is None:
        raise
    adapter.logger.warning(
        "Failed to create llama_context at n_ctx=%s; retrying with n_ctx=%s",
        n_ctx,
        next_n_ctx,
    )
    return next_n_ctx


def llama_kwargs_for_context(
    adapter: Any,
    base_kwargs: dict[str, Any],
    n_ctx: int,
) -> dict[str, Any]:
    """Return llama.cpp kwargs for one specific context size."""
    llama_kwargs = dict(base_kwargs)
    llama_kwargs["n_ctx"] = n_ctx
    if not adapter.use_yarn or n_ctx <= adapter.yarn_orig_ctx:
        return llama_kwargs
    _apply_yarn_context_scaling(adapter, llama_kwargs, n_ctx)
    return llama_kwargs


def _apply_yarn_context_scaling(
    adapter: Any,
    llama_kwargs: dict[str, Any],
    n_ctx: int,
) -> None:
    """Apply YaRN-specific context scaling parameters."""
    adapter.logger.info(
        "Enabling YaRN for extended context: %s -> %s",
        adapter.yarn_orig_ctx,
        n_ctx,
    )
    llama_kwargs["rope_scaling_type"] = 2
    llama_kwargs["yarn_orig_ctx"] = adapter.yarn_orig_ctx
    llama_kwargs["yarn_ext_factor"] = n_ctx / adapter.yarn_orig_ctx
    llama_kwargs["yarn_attn_factor"] = 1.0
    llama_kwargs["yarn_beta_fast"] = 32.0
    llama_kwargs["yarn_beta_slow"] = 1.0


def context_retry_sequence(adapter: Any) -> tuple[int, ...]:
    """Return candidate context sizes for llama.cpp retry attempts."""
    fallback_values = [adapter.n_ctx]
    for candidate in (16384, 8192, 4096):
        if candidate < adapter.n_ctx:
            fallback_values.append(candidate)
    return tuple(fallback_values)


def next_retry_context(current_n_ctx: int) -> Optional[int]:
    """Return the next smaller context retry target when one exists."""
    for candidate in (16384, 8192, 4096):
        if candidate < current_n_ctx:
            return candidate
    return None


def should_retry_context(exc: Exception, n_ctx: int) -> bool:
    """Return True when one smaller llama context should be attempted."""
    if n_ctx <= 4096:
        return False
    return "failed to create llama_context" in str(exc).lower()
