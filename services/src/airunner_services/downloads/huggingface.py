"""Service-owned helpers for HuggingFace download request planning."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Optional

from airunner_services.llm.provider_config import LLMProviderConfig
from airunner_services.runtimes.file_policy import PathPolicyError
from airunner_common.settings import AIRUNNER_BASE_PATH

_LLM_DOWNLOAD_TYPES = {"gguf", "llm"}


def safe_hf_filename(filename: str) -> str:
    """Return one normalized HF-relative path, rejecting escape attempts.

    HuggingFace file names legitimately contain ``/`` subdirectories
    (``tokenizer/merges.txt``), so unlike ``job_service._safe_filename``
    this keeps relative subpaths but still rejects NUL bytes, absolute
    paths, backslashes, and ``..`` components so a server-supplied name
    can never escape the model directory.
    """
    raw = str(filename or "").strip()
    if not raw or "\x00" in raw:
        raise PathPolicyError("HuggingFace filename is not allowed")
    if "\\" in raw:
        raise PathPolicyError("HuggingFace filename is not allowed")
    pure = PurePosixPath(raw)
    if pure.is_absolute() or ".." in pure.parts:
        raise PathPolicyError("HuggingFace filename is not allowed")
    normalized = str(pure)
    if not normalized or normalized in {".", ".."}:
        raise PathPolicyError("HuggingFace filename is not allowed")
    return normalized


@dataclass(frozen=True)
class HuggingFaceDownloadRequest:
    """Normalized payload for one HuggingFace download request."""

    repo_id: str
    model_type: str
    output_dir: Optional[str] = None
    version: Optional[str] = None
    pipeline_action: Optional[str] = None
    missing_files: Optional[list[str]] = None
    gguf_filename: Optional[str] = None

    def as_payload(self) -> dict[str, Any]:
        """Return one worker-ready payload dictionary."""
        return {
            "repo_id": self.repo_id,
            "model_type": self.model_type,
            "output_dir": self.output_dir,
            "version": self.version,
            "pipeline_action": self.pipeline_action,
            "missing_files": self.missing_files,
            "gguf_filename": self.gguf_filename,
        }


def prepare_huggingface_download_request(
    repo_id: str,
    model_type: str = "llm",
    output_dir: Optional[str] = None,
    version: Optional[str] = None,
    pipeline_action: Optional[str] = None,
    missing_files: Optional[list[str]] = None,
    gguf_filename: Optional[str] = None,
    prefer_pre_quantized: bool = True,
) -> HuggingFaceDownloadRequest:
    """Return one normalized request for the shared HF download worker."""
    resolved_download = _resolve_preferred_download(
        repo_id,
        model_type,
        prefer_pre_quantized,
    )
    repo_id, model_type, gguf_filename, missing_files = _apply_preferred_gguf(
        repo_id,
        model_type,
        gguf_filename,
        missing_files,
        resolved_download,
    )
    output_dir = _resolve_output_dir(
        output_dir,
        repo_id,
        model_type,
        resolved_download,
        prefer_pre_quantized,
    )
    if gguf_filename is not None:
        safe_hf_filename(gguf_filename)
    for missing_name in missing_files or []:
        safe_hf_filename(missing_name)
    repo_id = _resolved_repo_id(repo_id, resolved_download)
    return HuggingFaceDownloadRequest(
        repo_id=repo_id,
        model_type=model_type,
        output_dir=output_dir,
        version=version,
        pipeline_action=pipeline_action,
        missing_files=missing_files,
        gguf_filename=gguf_filename,
    )


def _resolve_preferred_download(
    repo_id: str,
    model_type: str,
    prefer_pre_quantized: bool,
) -> Optional[dict[str, Any]]:
    """Return one preferred local download target when HF lookup applies."""
    if model_type not in _LLM_DOWNLOAD_TYPES:
        return None
    return LLMProviderConfig.resolve_download_target(
        "local",
        repo_id=repo_id,
        prefer_pre_quantized=prefer_pre_quantized,
    )


def _apply_preferred_gguf(
    repo_id: str,
    model_type: str,
    gguf_filename: Optional[str],
    missing_files: Optional[list[str]],
    resolved_download: Optional[dict[str, Any]],
) -> tuple[str, str, Optional[str], Optional[list[str]]]:
    """Prefer a pre-quantized GGUF target when the provider config exposes one."""
    if not resolved_download or resolved_download.get("model_type") != "gguf":
        return repo_id, model_type, gguf_filename, missing_files
    return (
        resolved_download["repo_id"],
        "gguf",
        resolved_download["gguf_filename"],
        None,
    )


def _resolved_repo_id(
    repo_id: str,
    resolved_download: Optional[dict[str, Any]],
) -> str:
    """Return the normalized repository ID for one preferred download."""
    if not resolved_download:
        return repo_id
    return str(resolved_download.get("repo_id") or repo_id)


def _resolve_output_dir(
    output_dir: Optional[str],
    repo_id: str,
    model_type: str,
    resolved_download: Optional[dict[str, Any]],
    prefer_pre_quantized: bool,
) -> Optional[str]:
    """Return one default local output path for LLM-family downloads."""
    if output_dir is not None or model_type not in _LLM_DOWNLOAD_TYPES:
        return output_dir
    return LLMProviderConfig.get_local_storage_path(
        AIRUNNER_BASE_PATH,
        "local",
        model_id=(resolved_download or {}).get("model_id"),
        repo_id=repo_id,
        prefer_pre_quantized=prefer_pre_quantized and model_type == "gguf",
    )