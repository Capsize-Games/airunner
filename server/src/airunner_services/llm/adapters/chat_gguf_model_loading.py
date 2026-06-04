"""GGUF runtime-loading helpers."""

import os
import re
from typing import Any

from airunner_services.llm.adapters.chat_gguf_hf_chat_handler import (
    configure_chat_handler,
)
from airunner_services.llm.adapters.chat_gguf_model_metadata import (
    _current_llama_cpp_version,
    detect_known_unsupported_architecture,
    estimate_gguf_kv_cache_gb,
    UnsupportedGGUFArchitectureError,
)
from airunner_services.llm.adapters.chat_gguf_model_runtime_config import (
    apply_runtime_env_overrides,
    format_llama_tuning,
    load_llama_with_context_fallback,
    resolve_llama_tuning,
)

try:
    import torch
except ImportError:
    torch = None


def load_model(adapter: Any) -> None:
    """Load the GGUF model via llama-cpp-python."""
    if adapter._llama is not None:
        return
    _raise_for_unsupported_architecture(adapter)
    llama_cls, gpu_offload_supported = _prepare_runtime_load(adapter)
    llama_tuning = _resolve_and_log_runtime_signature(adapter)
    llama_kwargs = _build_llama_kwargs(adapter, llama_tuning)
    _log_llama_tuning(adapter, llama_tuning)
    _load_llama_runtime_instance(adapter, llama_cls, llama_kwargs)
    configure_chat_handler(adapter)
    _log_estimated_kv_cache(adapter)
    adapter.logger.info("✓ GGUF model loaded successfully")


def _prepare_runtime_load(adapter: Any) -> tuple[Any, bool]:
    """Load runtime hooks, apply env overrides, and log load startup."""
    llama_cls, gpu_offload_supported = _load_llama_runtime()
    _warn_if_gpu_offload_is_missing(adapter, gpu_offload_supported)
    apply_runtime_env_overrides(adapter)
    _log_model_load_start(adapter, gpu_offload_supported)
    return llama_cls, gpu_offload_supported


def _resolve_and_log_runtime_signature(adapter: Any) -> dict[str, Any]:
    """Resolve llama tuning and log the resulting runtime signature."""
    llama_tuning = resolve_llama_tuning(adapter)
    adapter.logger.info(
        "  runtime signature: %s",
        adapter._runtime_signature(llama_tuning),
    )
    return llama_tuning


def _log_llama_tuning(adapter: Any, llama_tuning: dict[str, Any]) -> None:
    """Log the selected llama.cpp tuning parameters."""
    adapter.logger.info(
        "  llama.cpp tuning: %s",
        format_llama_tuning(llama_tuning),
    )


def _raise_for_unsupported_architecture(adapter: Any) -> None:
    """Raise when the current runtime cannot load the model architecture."""
    unsupported_architecture = detect_known_unsupported_architecture(
        adapter.model_path
    )
    if unsupported_architecture is None:
        return
    runtime_version = _current_llama_cpp_version()
    raise UnsupportedGGUFArchitectureError(
        unsupported_architecture,
        adapter.model_path,
        runtime_version=str(runtime_version)
        if runtime_version is not None
        else None,
    )


def _load_llama_runtime() -> tuple[Any, bool]:
    """Import llama.cpp runtime hooks and detect GPU offload support."""
    try:
        from llama_cpp import Llama, llama_supports_gpu_offload
    except ImportError as exc:
        raise ImportError(
            "llama-cpp-python is required for GGUF support. "
            "Install with: pip install llama-cpp-python"
        ) from exc

    gpu_offload_supported = False
    try:
        gpu_offload_supported = bool(llama_supports_gpu_offload())
    except Exception:
        gpu_offload_supported = False
    return Llama, gpu_offload_supported


def _warn_if_gpu_offload_is_missing(
    adapter: Any,
    gpu_offload_supported: bool,
) -> None:
    """Warn when CUDA is present but llama.cpp GPU offload is unavailable."""
    cuda_available = bool(
        torch is not None
        and hasattr(torch, "cuda")
        and torch.cuda.is_available()
    )
    if adapter.n_gpu_layers == 0 or not cuda_available:
        return
    if gpu_offload_supported:
        return
    adapter.logger.warning(
        "CUDA is available, but this llama-cpp-python build does not "
        "support GPU offload. GGUF inference will run on CPU until "
        "llama-cpp-python is rebuilt with GGML_CUDA=on."
    )


def _log_model_load_start(
    adapter: Any,
    gpu_offload_supported: bool,
) -> None:
    """Log the starting GGUF runtime load information."""
    adapter.logger.info(
        "Loading GGUF model file=%s from %s",
        os.path.basename(adapter.model_path),
        adapter.model_path,
    )
    adapter.logger.info(
        f"  chat_format={adapter._detected_format or 'auto'}, "
        f"n_ctx={adapter.n_ctx}, "
        f"n_gpu_layers={adapter.n_gpu_layers}"
    )
    _log_model_file_size(adapter)
    if adapter.n_gpu_layers != 0:
        adapter.logger.info(
            "  llama.cpp GPU offload support=%s",
            gpu_offload_supported,
        )


def _log_model_file_size(adapter: Any) -> None:
    """Log GGUF file size when the model file is readable."""
    try:
        model_size_gb = os.path.getsize(adapter.model_path) / float(1024 ** 3)
    except OSError:
        return
    adapter.logger.info("  GGUF file size=%.2f GiB", model_size_gb)


def _build_llama_kwargs(
    adapter: Any,
    llama_tuning: dict[str, Any],
) -> dict[str, Any]:
    """Build llama.cpp constructor kwargs for one adapter."""
    llama_kwargs = {
        "model_path": adapter.model_path,
        "n_ctx": adapter.n_ctx,
        "n_gpu_layers": adapter.n_gpu_layers,
        "flash_attn": adapter.flash_attn,
        "type_k": 8,
        "type_v": 8,
        "verbose": False,
        **llama_tuning,
    }
    if adapter._detected_format is not None:
        llama_kwargs["chat_format"] = adapter._detected_format
    return llama_kwargs


def _load_llama_runtime_instance(
    adapter: Any,
    llama_cls: Any,
    llama_kwargs: dict[str, Any],
) -> None:
    """Load llama.cpp and normalize common GGUF runtime failures."""
    try:
        load_llama_with_context_fallback(adapter, llama_cls, llama_kwargs)
    except Exception as exc:
        _raise_normalized_runtime_error(adapter, exc)


def _raise_normalized_runtime_error(adapter: Any, exc: Exception) -> None:
    """Raise a normalized GGUF load error from one llama.cpp exception."""
    error_msg = str(exc).lower()
    if "unknown model architecture" in error_msg:
        architecture = _extract_runtime_architecture(error_msg)
        raise UnsupportedGGUFArchitectureError(
            architecture,
            adapter.model_path,
        ) from exc
    if "failed to load model" in error_msg:
        raise RuntimeError(
            f"Failed to load GGUF model from {adapter.model_path}: {exc}. "
            "This may be due to an unsupported model architecture or "
            "corrupted file."
        ) from exc
    raise exc


def _extract_runtime_architecture(error_msg: str) -> str:
    """Extract one architecture name from a llama.cpp error string."""
    arch_match = re.search(
        r"unknown model architecture[:\s]*['\"]?(\w+)['\"]?",
        error_msg,
    )
    if arch_match:
        return arch_match.group(1)
    return "unknown"


def _log_estimated_kv_cache(adapter: Any) -> None:
    """Log the estimated q8 KV-cache size when metadata is available."""
    estimated_kv_cache_gb = estimate_gguf_kv_cache_gb(
        adapter.model_path,
        adapter.n_ctx,
        type_k_bytes=1,
        type_v_bytes=1,
        metadata=getattr(adapter._llama, "metadata", None),
    )
    if estimated_kv_cache_gb is None:
        return
    adapter.logger.info(
        "  estimated q8 KV cache at n_ctx=%s: %.2f GiB",
        adapter.n_ctx,
        estimated_kv_cache_gb,
    )