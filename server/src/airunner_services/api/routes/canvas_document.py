"""Canvas document persistence endpoints for Konva JSON serialization."""

from __future__ import annotations

from typing import Optional, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from airunner_services.database.models.canvas_document import CanvasDocument
from airunner_services.database.session import session_scope
from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger

router = APIRouter()
logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)

# Track all connected clients for broadcasting.
_connected_clients: Set[WebSocket] = set()


class CanvasDocumentResponse(BaseModel):
    """Response payload for the canvas document."""

    document: Optional[str] = None


class CanvasDocumentPutRequest(BaseModel):
    """Request payload to store the canvas document."""

    document: str


class CanvasDocumentPutResponse(BaseModel):
    """Response payload after storing the canvas document."""

    status: str


async def _broadcast_document(document: str, sender: WebSocket) -> None:
    """Send a document update to all connected clients except the sender."""
    payload = {"type": "document", "document": document}
    stale: list[WebSocket] = []
    for client in _connected_clients:
        if client is sender:
            continue
        try:
            await client.send_json(payload)
        except Exception:
            stale.append(client)
    for s in stale:
        _connected_clients.discard(s)


@router.websocket("/ws")
async def canvas_document_websocket(websocket: WebSocket):
    """WebSocket endpoint for instant canvas document sync.

    On connect, sends the current stored document.
    On each JSON message with {"document": "..."}, persists immediately
    and broadcasts to all other connected clients.
    """
    await websocket.accept()
    _connected_clients.add(websocket)
    logger.info(
        "Canvas WebSocket connected (%d total)", len(_connected_clients)
    )

    try:
        # Send current document on connect
        with session_scope() as session:
            record = (
                session.query(CanvasDocument)
                .order_by(CanvasDocument.id.desc())
                .first()
            )
            current_doc = record.document if record is not None else None
            await websocket.send_json(
                {
                    "type": "document",
                    "document": current_doc,
                }
            )

        while True:
            data = await websocket.receive_json()
            doc = data.get("document")
            if doc is None:
                continue

            with session_scope() as session:
                record = (
                    session.query(CanvasDocument)
                    .order_by(CanvasDocument.id.desc())
                    .first()
                )
                if record is None:
                    record = CanvasDocument(document=doc)
                    session.add(record)
                else:
                    record.document = doc
                session.flush()

            # Broadcast to all other connected clients.
            await _broadcast_document(doc, websocket)
    except WebSocketDisconnect:
        logger.info(
            "Canvas WebSocket disconnected (%d remaining)",
            len(_connected_clients) - 1,
        )
    except Exception as exc:
        logger.error("Canvas document WebSocket error: %s", exc)
    finally:
        _connected_clients.discard(websocket)
        try:
            await websocket.close()
        except Exception:
            pass


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
