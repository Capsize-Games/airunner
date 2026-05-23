"""Download job endpoints for service-owned model acquisition."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from airunner_services.downloads.service import (
    fetch_civitai_model_info as fetch_civitai_model_info_service,
)
from airunner_services.downloads.job_service import DownloadJobService

router = APIRouter()


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


class UrlDownloadRequest(BaseModel):
    """Parameters for one generic URL download job."""

    url: str
    output_dir: str
    filename: str | None = None
    extract_zip: bool = False


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


def get_download_job_service(request: Request) -> DownloadJobService:
    """Return the process-wide download job service for the API app."""
    service = getattr(request.app.state, "download_job_service", None)
    if service is None:
        service = DownloadJobService()
        request.app.state.download_job_service = service
    return service


@router.post(
    "/huggingface",
    response_model=DownloadJobAcceptedResponse,
)
async def start_huggingface_download(
    payload: HuggingFaceDownloadRequest,
    request: Request,
) -> DownloadJobAcceptedResponse:
    """Queue one HuggingFace download through the shared job service."""
    service = get_download_job_service(request)
    job_id = await service.start_huggingface_download(
        repo_id=payload.repo_id,
        model_type=payload.model_type,
        output_dir=payload.output_dir,
        missing_files=payload.missing_files,
        gguf_filename=payload.gguf_filename,
        prefer_pre_quantized=payload.prefer_pre_quantized,
    )
    return DownloadJobAcceptedResponse(job_id=job_id)


@router.post(
    "/huggingface/file",
    response_model=DownloadJobAcceptedResponse,
)
async def start_huggingface_file_download(
    payload: HuggingFaceFileDownloadRequest,
    request: Request,
) -> DownloadJobAcceptedResponse:
    """Queue one single-file HuggingFace download job."""
    service = get_download_job_service(request)
    job_id = await service.start_huggingface_file_download(
        payload.repo_id,
        payload.filename,
        output_dir=payload.output_dir,
    )
    return DownloadJobAcceptedResponse(job_id=job_id)


@router.post(
    "/url",
    response_model=DownloadJobAcceptedResponse,
)
async def start_url_download(
    payload: UrlDownloadRequest,
    request: Request,
) -> DownloadJobAcceptedResponse:
    """Queue one generic URL download through the shared job service."""
    service = get_download_job_service(request)
    job_id = await service.start_url_download(
        payload.url,
        output_dir=payload.output_dir,
        filename=payload.filename,
        extract_zip=payload.extract_zip,
    )
    return DownloadJobAcceptedResponse(job_id=job_id)


@router.post(
    "/civitai/file",
    response_model=DownloadJobAcceptedResponse,
)
async def start_civitai_file_download(
    payload: CivitaiFileDownloadRequest,
    request: Request,
) -> DownloadJobAcceptedResponse:
    """Queue one single-file CivitAI download job."""
    service = get_download_job_service(request)
    job_id = await service.start_civitai_file_download(
        payload.url,
        output_path=payload.output_path,
        file_size=payload.file_size,
        api_key=payload.api_key,
    )
    return DownloadJobAcceptedResponse(job_id=job_id)


@router.post("/civitai/info")
async def fetch_civitai_model_info_route(
    payload: CivitaiModelInfoRequest,
) -> dict[str, Any]:
    """Return one selected-version-aware CivitAI model payload."""
    return await asyncio.to_thread(
        fetch_civitai_model_info_service,
        payload.url,
        payload.api_key or "",
    )


@router.get(
    "/status/{job_id}",
    response_model=DownloadJobStatusResponse,
)
async def get_download_job_status(
    job_id: str,
    request: Request,
) -> DownloadJobStatusResponse:
    """Return the tracked state for one download job."""
    service = get_download_job_service(request)
    job = await service.get_status(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Download job not found")
    return DownloadJobStatusResponse(**job.to_dict())


@router.delete(
    "/cancel/{job_id}",
    response_model=DownloadJobAcceptedResponse,
)
async def cancel_download_job(
    job_id: str,
    request: Request,
) -> DownloadJobAcceptedResponse:
    """Cancel one running download job when possible."""
    service = get_download_job_service(request)
    job = await service.get_status(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Download job not found")
    await service.cancel(job_id)
    updated_job = await service.get_status(job_id)
    status = "cancelled"
    if updated_job is not None:
        status = updated_job.status.value
    return DownloadJobAcceptedResponse(job_id=job_id, status=status)


__all__ = [
    "CivitaiFileDownloadRequest",
    "CivitaiModelInfoRequest",
    "DownloadJobAcceptedResponse",
    "DownloadJobStatusResponse",
    "HuggingFaceDownloadRequest",
    "HuggingFaceFileDownloadRequest",
    "UrlDownloadRequest",
    "cancel_download_job",
    "fetch_civitai_model_info_route",
    "get_download_job_service",
    "get_download_job_status",
    "router",
    "start_civitai_file_download",
    "start_huggingface_download",
    "start_huggingface_file_download",
    "start_url_download",
]