"""GGUF model discovery and runtime-loading helpers."""

import importlib.metadata as importlib_metadata
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

from packaging.version import InvalidVersion, Version

try:
    from gguf import GGUFReader
except ImportError:
    GGUFReader = None

try:
    import torch
except ImportError:
    torch = None


class UnsupportedGGUFArchitectureError(Exception):
    """Raised when llama-cpp-python cannot support a GGUF architecture."""

    def __init__(
        self,
        architecture: str,
        model_path: str,
        runtime_version: Optional[str] = None,
    ):
        self.architecture = architecture
        self.model_path = model_path
        self.runtime_version = runtime_version
        version_message = ""
        if runtime_version:
            version_message = (
                f" Installed llama-cpp-python version: {runtime_version}."
            )
        super().__init__(
            "GGUF model architecture "
            f"'{architecture}' is not supported by llama-cpp-python. "
            f"Model: {model_path}.{version_message} Use a GGUF model "
            "supported by the installed llama-cpp-python runtime."
        )


_KNOWN_UNSUPPORTED_ARCHITECTURES = {
    "mistral3": Version("0.3.16"),
    "qwen35": Version("0.3.16"),
}


def _current_llama_cpp_version() -> Optional[Version]:
    """Return the installed llama-cpp-python version when available."""
    try:
        return Version(importlib_metadata.version("llama-cpp-python"))
    except (importlib_metadata.PackageNotFoundError, InvalidVersion):
        return None


def _read_gguf_string_field(
    model_path: str,
    field_name: str,
) -> Optional[str]:
    """Return one GGUF metadata string field when it can be parsed."""
    if GGUFReader is None or not os.path.exists(model_path):
        return None

    try:
        reader = GGUFReader(model_path)
        field = reader.fields.get(field_name)
        if field is None or not getattr(field, "parts", None):
            return None
        value = bytes(field.parts[-1]).decode("utf-8", errors="ignore")
    except Exception:
        return None

    value = value.strip()
    return value or None


def _guess_architecture_from_path(model_path: str) -> Optional[str]:
    """Return a likely architecture from a known GGUF filename."""
    filename = os.path.basename(str(model_path)).lower()
    if "qwen3.5" in filename or "qwen35" in filename:
        return "qwen35"
    if "qwen3" in filename:
        return "qwen3"
    if "gpt-oss" in filename:
        return "gptoss"
    return None


def _metadata_int(metadata: Dict[str, Any], field_name: str) -> Optional[int]:
    """Return one llama.cpp metadata value parsed as an integer."""
    value = metadata.get(field_name)
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _estimate_known_kv_cache_gb(
    model_path: str,
    n_ctx: int,
    *,
    type_k_bytes: int = 1,
    type_v_bytes: int = 1,
) -> Optional[float]:
    """Estimate KV-cache size for known shipped GGUF models."""
    filename = os.path.basename(str(model_path)).lower()
    known_shapes = {}

    for marker, shape in known_shapes.items():
        if marker not in filename:
            continue
        block_count, head_count_kv, key_length, value_length = shape
        kv_bytes = (
            int(n_ctx)
            * block_count
            * head_count_kv
            * (
                key_length * int(type_k_bytes)
                + value_length * int(type_v_bytes)
            )
        )
        return kv_bytes / float(1024 ** 3)

    return None


def read_gguf_architecture(model_path: str) -> Optional[str]:
    """Return the GGUF general.architecture metadata value."""
    return _read_gguf_string_field(model_path, "general.architecture")


def estimate_gguf_kv_cache_gb(
    model_path: str,
    n_ctx: int,
    *,
    type_k_bytes: int = 1,
    type_v_bytes: int = 1,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[float]:
    """Estimate the GGUF KV-cache footprint for one configured context."""
    metadata_values = metadata or {}
    architecture = str(
        metadata_values.get("general.architecture", "")
    ).strip()
    if not architecture:
        return _estimate_known_or_missing_kv_cache(
            model_path,
            n_ctx,
            type_k_bytes=type_k_bytes,
            type_v_bytes=type_v_bytes,
        )

    prefix = f"{architecture}.attention"
    block_count = _metadata_int(metadata_values, f"{architecture}.block_count")
    head_count_kv = _metadata_int(
        metadata_values,
        f"{prefix}.head_count_kv",
    )
    key_length = _metadata_int(metadata_values, f"{prefix}.key_length")
    value_length = _metadata_int(metadata_values, f"{prefix}.value_length")
    if not all(
        value is not None
        for value in (block_count, head_count_kv, key_length, value_length)
    ):
        return None

    kv_bytes = (
        int(n_ctx)
        * int(block_count)
        * int(head_count_kv)
        * (
            int(key_length) * int(type_k_bytes)
            + int(value_length) * int(type_v_bytes)
        )
    )
    return kv_bytes / float(1024 ** 3)


def _estimate_known_or_missing_kv_cache(
    model_path: str,
    n_ctx: int,
    *,
    type_k_bytes: int,
    type_v_bytes: int,
) -> Optional[float]:
    """Return a known-shape estimate when metadata is missing."""
    estimated = _estimate_known_kv_cache_gb(
        model_path,
        n_ctx,
        type_k_bytes=type_k_bytes,
        type_v_bytes=type_v_bytes,
    )
    if estimated is not None:
        return estimated
    return None


def detect_known_unsupported_architecture(
    model_path: str,
) -> Optional[str]:
    """Return a known-unsupported GGUF architecture for this runtime."""
    architecture = _guess_architecture_from_path(model_path)
    if not architecture:
        architecture = read_gguf_architecture(model_path)
    if not architecture:
        return None

    max_supported_version = _KNOWN_UNSUPPORTED_ARCHITECTURES.get(architecture)
    runtime_version = _current_llama_cpp_version()
    if runtime_version is None or max_supported_version is None:
        return None
    if runtime_version <= max_supported_version:
        return architecture
    return None


@lru_cache(maxsize=16)
def _llama_chat_format_supported(name: str) -> bool:
    """Return True when the runtime supports a chat format."""
    if not name:
        return False
    try:
        from llama_cpp import llama_chat_format

        llama_chat_format.get_chat_completion_handler(name)
    except Exception:
        return False
    return True


def _detect_chat_format(model_path: str) -> Optional[str]:
    """Detect the appropriate chat format based on model filename."""
    path_lower = model_path.lower()
    if "gpt-oss" in path_lower:
        if _llama_chat_format_supported("gpt-oss"):
            return "gpt-oss"
        return None
    if "qwen" in path_lower:
        return "chatml"
    if any(name in path_lower for name in ["llama-3", "llama3", "meta-llama-3"]):
        return "llama-3"
    if any(name in path_lower for name in ["mistral", "magistral"]):
        return "mistral-instruct"
    return None


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


def resolve_llama_tuning(adapter: Any) -> Dict[str, Any]:
    """Resolve optional llama.cpp tuning overrides from the environment."""
    tuning: Dict[str, Any] = {
        "n_batch": adapter.n_batch,
        "offload_kqv": True,
    }
    _apply_optional_int_overrides(tuning)
    _apply_optional_bool_overrides(tuning)
    return tuning


def _apply_optional_int_overrides(tuning: Dict[str, Any]) -> None:
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

    n_threads_batch_override = _get_int_env(
        "AIRUNNER_GGUF_N_THREADS_BATCH"
    )
    if n_threads_batch_override is not None:
        tuning["n_threads_batch"] = n_threads_batch_override


def _apply_optional_bool_overrides(tuning: Dict[str, Any]) -> None:
    """Apply boolean runtime overrides to llama.cpp tuning."""
    offload_kqv_override = _get_bool_env("AIRUNNER_GGUF_OFFLOAD_KQV")
    if offload_kqv_override is not None:
        tuning["offload_kqv"] = offload_kqv_override

    op_offload_override = _get_bool_env("AIRUNNER_GGUF_OP_OFFLOAD")
    if op_offload_override is not None:
        tuning["op_offload"] = op_offload_override


def format_llama_tuning(tuning: Dict[str, Any]) -> str:
    """Format tuning fields for concise logging."""
    keys = [
        "n_batch",
        "n_ubatch",
        "n_threads",
        "n_threads_batch",
        "offload_kqv",
        "op_offload",
    ]
    return ", ".join(
        f"{key}={tuning[key]}" for key in keys if key in tuning
    )


def load_model(adapter: Any) -> None:
    """Load the GGUF model via llama-cpp-python."""
    if adapter._llama is not None:
        return

    _raise_for_unsupported_architecture(adapter)
    llama_cls, gpu_offload_supported = _load_llama_runtime()
    _warn_if_gpu_offload_is_missing(adapter, gpu_offload_supported)
    apply_runtime_env_overrides(adapter)
    _log_model_load_start(adapter, gpu_offload_supported)

    llama_tuning = resolve_llama_tuning(adapter)
    adapter.logger.info(
        "  runtime signature: %s",
        adapter._runtime_signature(llama_tuning),
    )

    llama_kwargs = _build_llama_kwargs(adapter, llama_tuning)
    adapter.logger.info(
        "  llama.cpp tuning: %s",
        format_llama_tuning(llama_tuning),
    )
    _load_llama_runtime_instance(adapter, llama_cls, llama_kwargs)
    _log_estimated_kv_cache(adapter)
    adapter.logger.info("✓ GGUF model loaded successfully")


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
    llama_tuning: Dict[str, Any],
) -> Dict[str, Any]:
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
    llama_kwargs: Dict[str, Any],
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


def apply_runtime_env_overrides(adapter: Any) -> None:
    """Apply optional llama.cpp runtime overrides from the environment."""
    n_ctx_override = _get_int_env("AIRUNNER_GGUF_N_CTX")
    if n_ctx_override is not None and n_ctx_override > 0:
        adapter.n_ctx = n_ctx_override

    n_gpu_layers_override = _get_int_env("AIRUNNER_GGUF_N_GPU_LAYERS")
    if n_gpu_layers_override is not None:
        adapter.n_gpu_layers = n_gpu_layers_override


def load_llama_with_context_fallback(
    adapter: Any,
    llama_cls: Any,
    base_kwargs: Dict[str, Any],
) -> None:
    """Load llama.cpp and retry smaller contexts on allocation failure."""
    attempted_n_ctx = adapter.n_ctx
    for n_ctx in context_retry_sequence(adapter):
        try:
            llama_kwargs = llama_kwargs_for_context(adapter, base_kwargs, n_ctx)
            adapter._llama = llama_cls(**llama_kwargs)
            adapter.n_ctx = n_ctx
            return
        except Exception as exc:
            if not should_retry_context(exc, n_ctx):
                raise
            next_n_ctx = next_retry_context(n_ctx)
            if next_n_ctx is None:
                raise
            adapter.logger.warning(
                "Failed to create llama_context at n_ctx=%s; retrying "
                "with n_ctx=%s",
                n_ctx,
                next_n_ctx,
            )
            attempted_n_ctx = next_n_ctx

    adapter.n_ctx = attempted_n_ctx


def llama_kwargs_for_context(
    adapter: Any,
    base_kwargs: Dict[str, Any],
    n_ctx: int,
) -> Dict[str, Any]:
    """Return llama.cpp kwargs for one specific context size."""
    llama_kwargs = dict(base_kwargs)
    llama_kwargs["n_ctx"] = n_ctx
    if not adapter.use_yarn or n_ctx <= adapter.yarn_orig_ctx:
        return llama_kwargs

    adapter.logger.info(
        "Enabling YaRN for extended context: %s -> %s",
        adapter.yarn_orig_ctx,
        n_ctx,
    )
    llama_kwargs["rope_scaling_type"] = 2
    llama_kwargs["yarn_orig_ctx"] = adapter.yarn_orig_ctx
    factor = n_ctx / adapter.yarn_orig_ctx
    llama_kwargs["yarn_ext_factor"] = factor
    llama_kwargs["yarn_attn_factor"] = 1.0
    llama_kwargs["yarn_beta_fast"] = 32.0
    llama_kwargs["yarn_beta_slow"] = 1.0
    return llama_kwargs


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


def find_gguf_file(
    model_dir: str,
    preferred_filename: Optional[str] = None,
) -> Optional[str]:
    """Find a GGUF file in a model directory."""
    model_path = Path(model_dir)
    if not model_path.exists():
        return None

    gguf_files = sorted(
        model_path.glob("*.gguf"),
        key=lambda path: path.name.lower(),
    )
    if not gguf_files:
        return None
    matched_preferred = _match_preferred_gguf(gguf_files, preferred_filename)
    if matched_preferred is not None:
        return matched_preferred
    for gguf_file in gguf_files:
        if "Q4_K_M" in gguf_file.name or "q4_k_m" in gguf_file.name:
            return str(gguf_file)
    return str(gguf_files[0])


def _match_preferred_gguf(
    gguf_files: list[Path],
    preferred_filename: Optional[str],
) -> Optional[str]:
    """Return the preferred GGUF file when the filename is known."""
    if not preferred_filename:
        return None
    preferred_name = str(preferred_filename).strip()
    for gguf_file in gguf_files:
        if gguf_file.name == preferred_name:
            return str(gguf_file)
    preferred_name = preferred_name.lower()
    for gguf_file in gguf_files:
        if gguf_file.name.lower() == preferred_name:
            return str(gguf_file)
    return None


def is_gguf_model(model_path: str) -> bool:
    """Check if a model path contains a GGUF model."""
    path = Path(model_path)
    if path.suffix == ".gguf":
        return path.exists()
    if path.is_dir():
        return find_gguf_file(str(path)) is not None
    return False