"""Request/response models for download job endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HuggingFaceDownloadRequest(BaseModel):
    """Parameters for one HuggingFace download job."""

    repo_id: str
    model_type: str = "llm"
    output_dir: str | None = None
    missing_files: list[str] | None = None
    gguf_filename: str | None = None
    prefer_pre_quantized: bool = True


class HuggingFaceFileDownloadRequest(BaseModel):
    """Parameters for one single-file HuggingFace download job."""

    repo_id: str
    filename: str
    output_dir: str


class CivitaiFileDownloadRequest(BaseModel):
    """Parameters for one single-file CivitAI download job."""

    url: str
    output_path: str
    file_size: int
    api_key: str | None = None


class CivitaiModelInfoRequest(BaseModel):
    """Parameters for one CivitAI metadata lookup."""

    url: str
    api_key: str | None = None


class CivitaiBrowserSearchRequest(BaseModel):
    """Parameters for one CivitAI model browser search."""

    query: str = ""
    base_models: list[str] | None = None
    model_types: list[str] | None = None
    limit: int = Field(default=20, ge=1, le=50)
    cursor: str | None = None
    api_key: str | None = None


class CivitaiBrowserModelRequest(BaseModel):
    """Parameters for one CivitAI browser detail fetch."""

    model_id: str
    base_models: list[str] | None = None
    model_types: list[str] | None = None
    api_key: str | None = None


class CivitaiImageRequest(BaseModel):
    """Parameters for one proxied CivitAI preview image fetch."""

    url: str
    max_bytes: int = Field(default=5_000_000, ge=1, le=25_000_000)
    width: int | None = Field(
        default=None,
        description="Desired thumbnail width (resized server-side)",
    )


class UrlDownloadRequest(BaseModel):
    """Parameters for one generic URL download job."""

    url: str
    output_dir: str
    filename: str | None = None
    extract_zip: bool = False


class NltkDownloadRequest(BaseModel):
    """Parameters for one NLTK data download job."""

    data_names: list[str]


class DownloadJobAcceptedResponse(BaseModel):
    """Response returned after queueing one download job."""

    job_id: str
    status: str = Field(default="running")


class DownloadJobStatusResponse(BaseModel):
    """Serialized state for one tracked download job."""

    job_id: str
    status: str
    progress: float
    result: Any | None = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
