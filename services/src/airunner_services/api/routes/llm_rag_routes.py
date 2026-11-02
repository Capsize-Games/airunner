"""RAG control routes for runtime-backed LLM endpoints."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException

from airunner_common.contract_enums import SignalCode
from airunner_services.llm.workers.rag_index_status import (
    rag_index_status_tracker,
)
from airunner_services.llm.workers.rag_index_admission import (
    ACK_TIMEOUT_SECONDS,
    finish_rag_index_dispatch,
    get_rag_index_job_ack,
    reserve_rag_index_job,
)
from airunner_services.utils.application.signal_mediator import SignalMediator

from .llm_contracts import RagIndexRequest

router = APIRouter()


async def _dispatch_index_job(signal: SignalCode, payload: dict[str, Any]) -> str:
    """Reserve the worker slot before acknowledging background indexing."""
    token = reserve_rag_index_job()
    if token is None:
        raise HTTPException(status_code=409, detail="rag_index_busy")
    try:
        SignalMediator().emit_signal(
            signal, {**payload, "_job_token": token}
        )
    except Exception:
        if finish_rag_index_dispatch(token):
            return token
        raise
    try:
        deadline = asyncio.get_running_loop().time() + ACK_TIMEOUT_SECONDS
        while (
            get_rag_index_job_ack(token) is None
            and asyncio.get_running_loop().time() < deadline
        ):
            await asyncio.sleep(0.01)
    except BaseException:
        finish_rag_index_dispatch(token)
        raise
    if not finish_rag_index_dispatch(token):
        raise HTTPException(
            status_code=503, detail="rag_index_worker_unavailable"
        )
    return token


@router.post("/rag/index")
async def start_rag_index(request: RagIndexRequest):
    """Trigger service-owned document indexing through the signal mediator."""
    if request.file_paths is None:
        await _dispatch_index_job(SignalCode.RAG_INDEX_ALL_DOCUMENTS, {})
        return {"status": "accepted", "scope": "all"}
    file_paths = [str(path).strip() for path in request.file_paths if str(path).strip()]
    if not file_paths:
        raise HTTPException(status_code=400, detail="No document paths provided")
    await _dispatch_index_job(
        SignalCode.RAG_INDEX_SELECTED_DOCUMENTS,
        {"file_paths": file_paths},
    )
    return {"status": "accepted", "scope": "selected", "count": len(file_paths)}


@router.post("/rag/reindex")
async def start_rag_reindex(request: RagIndexRequest):
    """Explicitly rebuild selected persisted indexes with staged replacement."""
    file_paths = request.file_paths or []
    file_paths = [str(path).strip() for path in file_paths if str(path).strip()]
    if not file_paths:
        raise HTTPException(status_code=400, detail="No document paths provided")
    await _dispatch_index_job(
        SignalCode.RAG_INDEX_SELECTED_DOCUMENTS,
        {"file_paths": file_paths, "reindex": True},
    )
    return {"status": "accepted", "scope": "reindex", "count": len(file_paths)}


@router.post("/rag/index/cancel")
async def cancel_rag_index():
    """Request cancellation for the active service-owned indexing flow."""
    SignalMediator().emit_signal(SignalCode.RAG_INDEX_CANCEL, {})
    return {"status": "accepted"}


@router.get("/rag/index/status")
async def rag_index_status() -> dict[str, Any]:
    """Return the current daemon-visible RAG indexing status."""
    return rag_index_status_tracker.snapshot()
