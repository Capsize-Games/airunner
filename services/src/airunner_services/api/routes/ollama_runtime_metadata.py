"""Build schema-complete Ollama metadata from local runtime evidence.

This module keeps catalog capabilities separate from the active runtime
profile. It performs only local registry lookups and file metadata reads; it
never hashes model files or assumes that a model is loaded.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re
import stat
from typing import Any

from airunner_common.contract_enums import ModelStatus, ModelType
from airunner_services.llm.provider_config import LLMProviderConfig
from airunner_services.model_management.model_registry import ModelRegistry
from airunner_services.model_management.model_registry import (
    ModelType as RegistryModelType,
)

_UTC = timezone.utc
_ZERO_TIME = datetime.min.replace(tzinfo=_UTC)
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
_PARAMETER_SIZE_RE = re.compile(
    r"(?<![A-Za-z0-9.])(\d+(?:\.\d+)?B)(?![A-Za-z0-9])",
    re.IGNORECASE,
)
_QUANTIZATION_RE = re.compile(
    r"(?<![A-Za-z0-9])((?:IQ|Q)\d+_[A-Z0-9]+|BF16|F16)(?![A-Za-z0-9])",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class VerifiedFileDigest:
    """A previously verified file digest bound to one unchanged file."""

    canonical_path: str
    sha256: str
    size_bytes: int
    device: int
    inode: int
    mtime_ns: int


@dataclass(frozen=True)
class OllamaRuntimeMetadata:
    """Ollama list/process/show views for one local model artifact."""

    name: str
    model_id: str
    size_bytes: int
    digest: str
    modified_at: str
    family: str
    parameter_size: str
    quantization_level: str
    format: str
    runtime_context_length: int
    catalog_context_length: int | None
    size_vram_bytes: int
    expires_at: str
    capabilities: tuple[str, ...]

    @property
    def details(self) -> dict[str, Any]:
        """Return fields required by Ollama's list/process model schema."""
        return {
            "parent_model": "",
            "format": self.format,
            "family": self.family,
            "families": [self.family] if self.family else [],
            "parameter_size": self.parameter_size,
            "quantization_level": self.quantization_level,
        }

    def list_model(self) -> dict[str, Any]:
        """Return an Ollama ``/api/tags`` model object."""
        return {
            "name": self.name,
            "model": self.name,
            "modified_at": self.modified_at,
            "size": self.size_bytes,
            "digest": self.digest,
            "details": self.details,
        }

    def process_model(self) -> dict[str, Any]:
        """Return an Ollama ``/api/ps`` process object."""
        return {
            "name": self.name,
            "model": self.name,
            "size": self.size_bytes,
            "digest": self.digest,
            "details": self.details,
            "expires_at": self.expires_at,
            "size_vram": self.size_vram_bytes,
            "context_length": self.runtime_context_length,
        }

    def show_response(self) -> dict[str, Any]:
        """Return catalog capability metadata, never the active profile."""
        model_info: dict[str, int] = {}
        if self.catalog_context_length is not None:
            model_info["context_length"] = self.catalog_context_length
        return {
            "model_info": model_info,
            "capabilities": list(self.capabilities),
        }


def _timestamp(value: datetime | None) -> str:
    """Format a UTC timestamp; unknown Ollama time fields use Go's zero time."""
    if value is None:
        value = _ZERO_TIME
    elif value.tzinfo is None or value.utcoffset() is None:
        value = value.replace(tzinfo=_UTC)
    return value.astimezone(_UTC).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )


def _catalog_model(model_id: str, path: Path | None):
    registry = ModelRegistry()
    model = registry.get_model(model_id) if model_id else None
    if model is None and path is not None:
        model = registry.get_model(path.name)
    if model is None or model.model_type is not RegistryModelType.LLM:
        return None, {}
    info = LLMProviderConfig.get_model_info("local", model.model_id or "")
    return model, info


def _regular_file_identity(path: Path | None) -> tuple[Path | None, Any | None]:
    if path is None:
        return None, None
    try:
        resolved = path.expanduser().resolve(strict=True)
        info = resolved.stat()
    except (OSError, RuntimeError):
        return None, None
    if not stat.S_ISREG(info.st_mode):
        return None, None
    return resolved, info


def _cached_digest(
    path: Path | None,
    file_stat: Any | None,
    cached: VerifiedFileDigest | None,
) -> str:
    if path is None or file_stat is None or cached is None:
        return ""
    if not _SHA256_RE.fullmatch(cached.sha256):
        return ""
    try:
        canonical = str(path.resolve(strict=True))
    except (OSError, RuntimeError):
        return ""
    if (
        canonical != cached.canonical_path
        or file_stat.st_size != cached.size_bytes
        or file_stat.st_dev != cached.device
        or file_stat.st_ino != cached.inode
        or file_stat.st_mtime_ns != cached.mtime_ns
    ):
        return ""
    return cached.sha256


def _parameter_size(name: str) -> str:
    match = _PARAMETER_SIZE_RE.search(name)
    return match.group(1).upper() if match else ""


def _quantization(filename: str) -> str:
    match = _QUANTIZATION_RE.search(filename)
    return match.group(1).upper() if match else ""


def build_ollama_runtime_metadata(
    artifact_path: str | Path | None,
    *,
    model_id: str = "",
    runtime_context_length: int | None = None,
    measured_vram_bytes: int | None = None,
    expires_at: datetime | None = None,
    verified_digest: VerifiedFileDigest | None = None,
) -> OllamaRuntimeMetadata:
    """Create truthful local metadata without reading model contents.

    A caller may supply the active manager path and its known catalog id. A
    digest is emitted only when a verified digest receipt still matches the
    file's canonical path, device, inode, size, and modification time.
    """
    candidate = Path(artifact_path) if artifact_path else None
    path, file_stat = _regular_file_identity(candidate)
    model, info = _catalog_model(model_id.strip(), path)

    resolved_model_id = str(getattr(model, "model_id", "") or "")
    if resolved_model_id:
        name = f"{resolved_model_id}:latest"
    elif path is not None:
        name = f"{path.stem}:latest"
    else:
        name = ""

    identity_lower = resolved_model_id.lower()
    family = next(
        (
            candidate
            for marker, candidate in (
                ("qwen", "qwen"),
                ("mistral", "mistral"),
                ("phi", "phi"),
                ("llama", "llama"),
                ("gpt-oss", "gpt-oss"),
            )
            if marker in identity_lower
        ),
        "",
    )
    catalog_name = str(info.get("name", "") or "")
    parameter_size = _parameter_size(catalog_name) if model is not None else ""
    quantization_level = _quantization(path.name) if path is not None else ""
    runtime_format = ""
    if model is not None and model.preferred_runtime_format == "gguf":
        runtime_format = "gguf"
    elif path is not None and path.suffix.lower() == ".gguf":
        runtime_format = "gguf"

    modified_at = _timestamp(
        datetime.fromtimestamp(file_stat.st_mtime, tz=_UTC)
        if file_stat is not None
        else None
    )
    size_bytes = int(file_stat.st_size) if file_stat is not None else 0
    digest = _cached_digest(path, file_stat, verified_digest)

    context_value = info.get("context_length") if model is not None else None
    catalog_context_length = (
        int(context_value)
        if isinstance(context_value, (int, float)) and int(context_value) > 0
        else None
    )
    runtime_length = (
        int(runtime_context_length)
        if isinstance(runtime_context_length, int) and runtime_context_length > 0
        else 0
    )
    vram_bytes = (
        int(measured_vram_bytes)
        if isinstance(measured_vram_bytes, int) and measured_vram_bytes > 0
        else 0
    )

    capabilities: list[str] = []
    if model is not None:
        capabilities.append("completion")
        if bool(info.get("function_calling")):
            capabilities.append("tools")
        if bool(info.get("vision_capable")):
            capabilities.append("vision")

    return OllamaRuntimeMetadata(
        name=name,
        model_id=resolved_model_id,
        size_bytes=size_bytes,
        digest=digest,
        modified_at=modified_at,
        family=family,
        parameter_size=parameter_size,
        quantization_level=quantization_level,
        format=runtime_format,
        runtime_context_length=runtime_length,
        catalog_context_length=catalog_context_length,
        size_vram_bytes=vram_bytes,
        expires_at=_timestamp(expires_at),
        capabilities=tuple(capabilities),
    )


def metadata_from_loaded_manager(
    manager: Any,
    *,
    measured_vram_bytes: int | None = None,
    expires_at: datetime | None = None,
    verified_digest: VerifiedFileDigest | None = None,
) -> OllamaRuntimeMetadata | None:
    """Read one loaded manager's active artifact and actual GGUF profile."""
    statuses = getattr(manager, "model_status", None)
    status = statuses.get(ModelType.LLM) if isinstance(statuses, dict) else None
    if status not in (ModelStatus.LOADED, ModelStatus.READY):
        return None

    active_path = getattr(manager, "_current_model_path", None)
    if not isinstance(active_path, (str, Path)) or not str(active_path).strip():
        return None

    model_id = ""
    resolver = getattr(manager, "_resolve_model_id_from_path", None)
    if callable(resolver):
        try:
            model_id = str(resolver(str(active_path)) or "")
        except Exception:
            model_id = ""
    if not model_id:
        settings = getattr(manager, "llm_settings", None)
        model_id = str(getattr(settings, "model_id", "") or "")

    chat_model = getattr(manager, "_chat_model", None)
    runtime_context_length = getattr(chat_model, "n_ctx", None)
    return build_ollama_runtime_metadata(
        active_path,
        model_id=model_id,
        runtime_context_length=runtime_context_length,
        measured_vram_bytes=measured_vram_bytes,
        expires_at=expires_at,
        verified_digest=verified_digest,
    )


__all__ = [
    "OllamaRuntimeMetadata",
    "VerifiedFileDigest",
    "build_ollama_runtime_metadata",
    "metadata_from_loaded_manager",
]
