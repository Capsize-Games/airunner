"""Download job endpoints for service-owned model acquisition."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field
from airunner_model.url_safety import safe_fetch_bytes

from airunner_services.downloads.service import (
    fetch_civitai_browser_model_info,
    fetch_civitai_model_info as fetch_civitai_model_info_service,
    search_civitai_models,
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
    "/nltk",
    response_model=DownloadJobAcceptedResponse,
)
async def start_nltk_download(
    payload: NltkDownloadRequest,
    request: Request,
) -> DownloadJobAcceptedResponse:
    """Queue one NLTK data download through the shared job service."""
    service = get_download_job_service(request)
    job_id = await service.start_nltk_download(payload.data_names)
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


@router.post("/civitai/models")
async def search_civitai_models_route(
    payload: CivitaiBrowserSearchRequest,
) -> dict[str, Any]:
    """Return one filtered CivitAI browser search payload."""
    return await asyncio.to_thread(
        search_civitai_models,
        payload.query,
        base_models=payload.base_models,
        model_types=payload.model_types,
        limit=payload.limit,
        cursor=payload.cursor,
        api_key=payload.api_key or "",
    )


@router.post("/civitai/model")
async def fetch_civitai_browser_model_route(
    payload: CivitaiBrowserModelRequest,
) -> dict[str, Any]:
    """Return one filtered CivitAI browser detail payload."""
    try:
        return await asyncio.to_thread(
            fetch_civitai_browser_model_info,
            payload.model_id,
            base_models=payload.base_models,
            model_types=payload.model_types,
            api_key=payload.api_key or "",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/civitai/image")
async def fetch_civitai_image_route(
    payload: CivitaiImageRequest,
) -> Response:
    """Return one CivitAI preview image through the daemon process."""
    try:
        image_bytes = await asyncio.to_thread(
            safe_fetch_bytes,
            payload.url,
            max_bytes=payload.max_bytes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return Response(
        content=image_bytes,
        media_type="application/octet-stream",
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
    "CivitaiImageRequest",
    "CivitaiBrowserModelRequest",
    "CivitaiBrowserSearchRequest",
    "CivitaiFileDownloadRequest",
    "CivitaiModelInfoRequest",
    "DownloadJobAcceptedResponse",
    "DownloadJobStatusResponse",
    "HuggingFaceDownloadRequest",
    "HuggingFaceFileDownloadRequest",
    "NltkDownloadRequest",
    "UrlDownloadRequest",
    "cancel_download_job",
    "fetch_civitai_image_route",
    "fetch_civitai_browser_model_route",
    "fetch_civitai_model_info_route",
    "get_download_job_service",
    "get_download_job_status",
    "router",
    "search_civitai_models_route",
    "start_civitai_file_download",
    "start_huggingface_download",
    "start_huggingface_file_download",
    "start_nltk_download",
    "start_url_download",
]