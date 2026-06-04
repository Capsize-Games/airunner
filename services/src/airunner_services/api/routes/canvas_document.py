"""Canvas document persistence endpoints for Konva JSON serialization."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from airunner_services.database.models.canvas_document import CanvasDocument
from airunner_services.database.session import session_scope

router = APIRouter()


class CanvasDocumentResponse(BaseModel):
    """Response payload for the canvas document."""

    document: Optional[str] = None


class CanvasDocumentPutRequest(BaseModel):
    """Request payload to store the canvas document."""

    document: str


class CanvasDocumentPutResponse(BaseModel):
    """Response payload after storing the canvas document."""

    status: str


@router.get("/document", response_model=CanvasDocumentResponse)
async def get_canvas_document():
    """Return the stored Konva canvas document JSON blob."""
    with session_scope() as session:
        record = (
            session.query(CanvasDocument)
            .order_by(CanvasDocument.id.desc())
            .first()
        )
        if record is None:
            return CanvasDocumentResponse(document=None)
        return CanvasDocumentResponse(document=record.document)


@router.put("/document", response_model=CanvasDocumentPutResponse)
async def put_canvas_document(body: CanvasDocumentPutRequest):
    """Store the Konva canvas document JSON blob."""
    with session_scope() as session:
        record = (
            session.query(CanvasDocument)
            .order_by(CanvasDocument.id.desc())
            .first()
        )
        if record is None:
            record = CanvasDocument(document=body.document)
            session.add(record)
        else:
            record.document = body.document
        session.flush()
    return CanvasDocumentPutResponse(status="ok")
