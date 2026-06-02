"""Document listing and toggle routes for the knowledge base panel."""

from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException

from airunner_services.database.models.document import Document
from airunner_services.database.session import session_scope

router = APIRouter()


@router.get("/documents")
async def list_documents():
    """Return document records for the knowledge base panel.

    Only includes documents whose file still exists on disk. Stale DB
    records (deleted files) are omitted.
    """
    with session_scope() as session:
        docs = session.query(Document).order_by(Document.id).all()
        valid = []
        for doc in docs:
            if os.path.isfile(doc.path):
                valid.append({
                    "id": doc.id,
                    "path": doc.path,
                    "active": bool(doc.active),
                    "indexed": bool(doc.indexed),
                    "file_size": doc.file_size,
                })
        return {"documents": valid}


@router.patch("/documents/{doc_id}/toggle-active")
async def toggle_document_active(doc_id: int):
    """Toggle the active state of one knowledge base document."""
    with session_scope() as session:
        doc = session.query(Document).filter_by(id=doc_id).first()
        if doc is None:
            raise HTTPException(status_code=404, detail="Document not found")
        doc.active = not doc.active
        session.commit()
        return {
            "id": doc.id,
            "active": bool(doc.active),
        }
