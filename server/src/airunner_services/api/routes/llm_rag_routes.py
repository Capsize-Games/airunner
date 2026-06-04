"""RAG control routes for runtime-backed LLM endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from airunner_services.contract_enums import SignalCode
from airunner_services.llm.workers.rag_index_status import (
    rag_index_status_tracker,
)
from airunner_services.utils.application.signal_mediator import SignalMediator

from .llm_contracts import RagIndexRequest

router = APIRouter()


@router.post("/rag/index")
async def start_rag_index(request: RagIndexRequest):
    """Trigger service-owned document indexing through the signal mediator."""
    mediator = SignalMediator()
    if request.file_paths is None:
        mediator.emit_signal(SignalCode.RAG_INDEX_ALL_DOCUMENTS, {})
        return {"status": "accepted", "scope": "all"}
    file_paths = [str(path).strip() for path in request.file_paths if str(path).strip()]
    if not file_paths:
        raise HTTPException(status_code=400, detail="No document paths provided")
    mediator.emit_signal(
        SignalCode.RAG_INDEX_SELECTED_DOCUMENTS,
        {"file_paths": file_paths},
    )
    return {"status": "accepted", "scope": "selected", "count": len(file_paths)}


@router.post("/rag/index/cancel")
async def cancel_rag_index():
    """Request cancellation for the active service-owned indexing flow."""
    SignalMediator().emit_signal(SignalCode.RAG_INDEX_CANCEL, {})
    return {"status": "accepted"}


@router.get("/rag/index/status")
async def rag_index_status() -> dict[str, Any]:
    """Return the current daemon-visible RAG indexing status."""
    return rag_index_status_tracker.snapshot()