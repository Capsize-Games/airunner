"""GGUF metadata and architecture helpers."""

import importlib.metadata as importlib_metadata
import os
from typing import Any, Optional

from packaging.version import InvalidVersion, Version

try:
    from gguf import GGUFReader
except ImportError:
    GGUFReader = None


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

_KNOWN_KV_CACHE_SHAPES: dict[str, tuple[int, int, int, int]] = {}


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


def _metadata_int(
    metadata: dict[str, Any],
    field_name: str,
) -> Optional[int]:
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
    shape = _known_kv_cache_shape(filename)
    if shape is None:
        return None
    return _kv_cache_gb_from_shape(
        n_ctx,
        shape,
        type_k_bytes=type_k_bytes,
        type_v_bytes=type_v_bytes,
    )


def _known_kv_cache_shape(
    filename: str,
) -> Optional[tuple[int, int, int, int]]:
    """Return one known KV-cache shape for a shipped GGUF filename."""
    for marker, shape in _KNOWN_KV_CACHE_SHAPES.items():
        if marker in filename:
            return shape
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
    metadata: Optional[dict[str, Any]] = None,
) -> Optional[float]:
    """Estimate the GGUF KV-cache footprint for one configured context."""
    metadata_values = metadata or {}
    architecture = str(metadata_values.get("general.architecture", "")).strip()
    if not architecture:
        return _estimate_known_kv_cache_gb(
            model_path,
            n_ctx,
            type_k_bytes=type_k_bytes,
            type_v_bytes=type_v_bytes,
        )

    return _metadata_kv_cache_estimate(
        metadata_values,
        architecture,
        n_ctx,
        type_k_bytes=type_k_bytes,
        type_v_bytes=type_v_bytes,
    )


def _metadata_kv_cache_estimate(
    metadata: dict[str, Any],
    architecture: str,
    n_ctx: int,
    *,
    type_k_bytes: int,
    type_v_bytes: int,
) -> Optional[float]:
    """Estimate KV-cache size directly from parsed GGUF metadata."""
    shape = _metadata_kv_cache_shape(metadata, architecture)
    if shape is None:
        return None
    return _kv_cache_gb_from_shape(
        n_ctx,
        shape,
        type_k_bytes=type_k_bytes,
        type_v_bytes=type_v_bytes,
    )


def _metadata_kv_cache_shape(
    metadata: dict[str, Any],
    architecture: str,
) -> Optional[tuple[int, int, int, int]]:
    """Return KV-cache shape fields parsed from GGUF metadata."""
    prefix = f"{architecture}.attention"
    shape = (
        _metadata_int(metadata, f"{architecture}.block_count"),
        _metadata_int(metadata, f"{prefix}.head_count_kv"),
        _metadata_int(metadata, f"{prefix}.key_length"),
        _metadata_int(metadata, f"{prefix}.value_length"),
    )
    if any(value is None for value in shape):
        return None
    return shape


def _kv_cache_gb_from_shape(
    n_ctx: int,
    shape: tuple[int, int, int, int],
    *,
    type_k_bytes: int,
    type_v_bytes: int,
) -> float:
    """Return one KV-cache size estimate in gigabytes for a model shape."""
    block_count, head_count_kv, key_length, value_length = shape
    kv_bytes = (
        int(n_ctx)
        * int(block_count)
        * int(head_count_kv)
        * (
            int(key_length) * int(type_k_bytes)
            + int(value_length) * int(type_v_bytes)
        )
    )
    return kv_bytes / float(1024**3)


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
