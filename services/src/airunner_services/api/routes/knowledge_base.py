"""Document listing and toggle routes for the knowledge base panel.

Scans configured document directories for files, and merges
filesystem results with DB records (mirroring the LoRA/embedding
scan pattern). New files found on disk are automatically added
to the database.
"""

from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException

from airunner_services.database.models.document import Document
from airunner_services.database.session import session_scope
from airunner_services.settings import AIRUNNER_BASE_PATH

router = APIRouter()

DOCUMENT_EXTENSIONS = frozenset({
    ".mobi", ".pdf", ".epub", ".html", ".htm",
    ".md", ".txt", ".zim", ".doc", ".docx", ".odt",
})


def _discover_doc_dirs() -> list[str]:
    """Return knowledge-base directories to scan for documents."""
    candidates = [
        os.path.join(AIRUNNER_BASE_PATH, "text", "other", "documents"),
        os.path.join(AIRUNNER_BASE_PATH, "text", "other", "ebooks"),
        os.path.join(AIRUNNER_BASE_PATH, "text", "other", "webpages"),
        os.path.join(AIRUNNER_BASE_PATH, "knowledge_base"),
    ]
    return [p for p in candidates if os.path.isdir(p)]


@router.get("/documents")
async def list_documents():
    """Return document records for the knowledge base panel.

    Scans configured directories for supported document files and
    merges with DB records. New files are added to the DB on-the-fly.
    Stale DB records (deleted files) are omitted.
    """
    # Load existing DB records keyed by path
    db_records: dict[str, dict] = {}
    with session_scope() as session:
        for rec in session.query(Document).all():
            db_records[rec.path] = {
                "id": rec.id,
                "path": rec.path,
                "active": bool(rec.active),
                "indexed": bool(rec.indexed),
                "file_size": rec.file_size,
            }

    seen_paths: set[str] = set()

    # Scan directories for document files
    for doc_dir in _discover_doc_dirs():
        for root, _dirs, files in os.walk(doc_dir):
            for entry in files:
                ext = os.path.splitext(entry)[1].lower()
                if ext not in DOCUMENT_EXTENSIONS:
                    continue
                full_path = os.path.join(root, entry)
                if full_path in seen_paths:
                    continue
                seen_paths.add(full_path)

    # Merge: keep existing DB records that still exist, create new ones
    found: list[dict[str, object]] = []
    for path in seen_paths:
        if not os.path.isfile(path):
            continue
        db = db_records.get(path, {})
        if not db:
            with session_scope() as session:
                try:
                    file_size = os.path.getsize(path)
                except OSError:
                    file_size = 0
                rec = Document(
                    path=path,
                    file_size=file_size,
                    active=False,
                    indexed=False,
                )
                session.add(rec)
                session.flush()
                db = {
                    "id": rec.id,
                    "path": path,
                    "active": False,
                    "indexed": False,
                    "file_size": file_size,
                }
        found.append({
            "id": db["id"],
            "path": db["path"],
            "active": db["active"],
            "indexed": db["indexed"],
            "file_size": db["file_size"],
        })

    return {"documents": found}


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
