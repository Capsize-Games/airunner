"""Document listing routes for the knowledge base panel."""

from __future__ import annotations

from fastapi import APIRouter

from airunner_services.database.models.document import Document
from airunner_services.database.session import session_scope

router = APIRouter()


@router.get("/documents")
async def list_documents():
    """Return all document records for the knowledge base panel."""
    with session_scope() as session:
        docs = session.query(Document).order_by(Document.id).all()
        return {
            "documents": [
                {
                    "id": doc.id,
                    "path": doc.path,
                    "active": bool(doc.active),
                    "indexed": bool(doc.indexed),
                    "file_size": doc.file_size,
                }
                for doc in docs
            ],
        }
