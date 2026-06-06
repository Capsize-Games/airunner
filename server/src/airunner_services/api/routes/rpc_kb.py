"""RPC handlers: knowledge-base documents."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from airunner_services.api.routes.events import _rpc_register


@_rpc_register("GET", "/api/v1/knowledge-base/documents")
async def _rpc_kb_documents(body: dict, **kwargs: Any) -> dict[str, Any]:
    """List all knowledge base documents."""
    try:
        from airunner_services.database.models.document import Document
        from airunner_services.database.session import session_scope

        with session_scope() as session:
            docs = session.query(Document).all()
            documents = [
                {
                    "id": d.id,
                    "name": Path(str(d.path)).name if d.path else "",
                    "path": str(d.path) if d.path else "",
                    "indexed": bool(d.indexed),
                    "active": bool(d.active),
                }
                for d in docs
            ]
            return {"status": 200, "body": {"documents": documents}}
    except Exception:
        return {"status": 200, "body": {"documents": []}}


@_rpc_register(
    "PATCH", "/api/v1/knowledge-base/documents/{doc_id}/toggle-active"
)
async def _rpc_kb_toggle_active(body: dict, **kwargs: Any) -> dict[str, Any]:
    """Toggle a document's active state."""
    pp: dict = kwargs.get("path_params", {})
    raw_id = pp.get("doc_id", "")
    if not raw_id:
        return {"status": 400, "body": {"error": "Missing document ID"}}
    doc_id = int(raw_id)
    try:
        from airunner_services.database.models.document import Document
        from airunner_services.database.session import session_scope

        with session_scope() as session:
            doc = session.query(Document).filter(Document.id == doc_id).first()
            if doc is None:
                return {"status": 404, "body": {"error": "Document not found"}}
            doc.active = not doc.active
            session.commit()
            return {
                "status": 200,
                "body": {"id": doc.id, "active": bool(doc.active)},
            }
    except Exception as exc:
        return {"status": 500, "body": {"error": str(exc)}}


@_rpc_register("POST", "/api/v1/knowledge-base/documents/index-all")
async def _rpc_kb_index_all(body: dict, **kwargs: Any) -> dict[str, Any]:
    """Trigger indexing of all documents."""
    from airunner_services.contract_enums import SignalCode
    from airunner_services.utils.application.signal_mediator import (
        SignalMediator,
    )

    SignalMediator().emit_signal(
        SignalCode.RAG_INDEX_ALL_DOCUMENTS,
        {},
    )
    return {"status": 200, "body": {"status": "started"}}


@_rpc_register("POST", "/api/v1/knowledge-base/documents/index-cancel")
async def _rpc_kb_index_cancel(body: dict, **kwargs: Any) -> dict[str, Any]:
    """Cancel indexing."""
    from airunner_services.contract_enums import SignalCode
    from airunner_services.utils.application.signal_mediator import (
        SignalMediator,
    )

    SignalMediator().emit_signal(SignalCode.RAG_INDEX_CANCEL, {})
    return {"status": 200, "body": {"status": "cancelled"}}
