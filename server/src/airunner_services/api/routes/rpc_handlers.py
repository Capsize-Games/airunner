"""RPC handler registrations for the unified /api/v1/events WebSocket.

Each function is decorated with ``@_rpc_register(method, path)`` which
registers it in the dispatch table.  The handler receives a ``body``
dict and returns a dict with ``status`` and ``body`` (and optionally
``headers``, ``binary``, ``error``).

These replace the existing FastAPI HTTP route functions — callers
(React client) now call ``rpcRequest()`` instead of ``fetch()``.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from airunner_services.api.routes.events import _rpc_register
from airunner_services.settings import AIRUNNER_BASE_PATH

logger = logging.getLogger(__name__)


# ── Health ────────────────────────────────────────────────────────────────


# ── Models (active + unload) ─────────────────────────────────────────────


@_rpc_register("GET", "/api/v1/models/active")
async def _rpc_models_active(body: dict, **kwargs: Any) -> dict[str, Any]:
    """Return all currently active models."""
    try:
        from airunner_services.model_management import ModelResourceManager

        resource_mgr = ModelResourceManager()
        models: list[dict[str, Any]] = []
        for m in resource_mgr.get_active_models():
            models.append(
                {
                    "model_id": m.model_id,
                    "model_type": m.model_type,
                    "status": m.state.value,
                    "can_unload": m.can_unload,
                    "vram_gb": m.vram_allocated_gb,
                    "ram_gb": m.ram_allocated_gb,
                    "name": m.name or "",
                }
            )
        return {"status": 200, "body": {"models": models}}
    except Exception as exc:
        logger.warning("Failed to read active models: %s", exc)
        return {"status": 200, "body": {"models": []}}


@_rpc_register("POST", "/api/v1/models/unload")
async def _rpc_models_unload(body: dict, **kwargs: Any) -> dict[str, Any]:
    """Request one model to be unloaded."""
    from airunner_services.contract_enums import SignalCode
    from airunner_services.utils.application.signal_mediator import (
        SignalMediator,
    )

    model_id = str(body.get("model_id", ""))
    model_type = str(body.get("model_type", ""))

    model_type_lower = model_type.strip().lower() or model_id.strip().lower()

    if "embedding" in model_type_lower:
        SignalMediator().emit_signal(
            SignalCode.RAG_INDEX_CANCEL,
            {"unload_embedding": True},
        )
        return {"status": 200, "body": {"status": "accepted"}}

    if "llm" in model_type_lower:
        SignalMediator().emit_signal(
            SignalCode.LLM_UNLOAD_SIGNAL,
            {},
        )
        return {"status": 200, "body": {"status": "accepted"}}

    return {"status": 200, "body": {"status": "accepted"}}


# ── Knowledge Base ───────────────────────────────────────────────────────


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
                    "file_type": str(d.file_type) if d.file_type else "",
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
    # Path param resolution: path is /documents/{doc_id}/toggle-active
    # The path template has {doc_id} — we extract from the actual path
    import re

    path = body.get("_path", "")
    match = re.search(r"/documents/(\d+)/toggle-active", path)
    if not match:
        return {"status": 400, "body": {"error": "Missing document ID"}}
    doc_id = int(match.group(1))

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


# ── Privacy settings ─────────────────────────────────────────────────────


@_rpc_register("GET", "/api/v1/settings/privacy")
async def _rpc_privacy_get(body: dict, **kwargs: Any) -> dict[str, Any]:
    """Return privacy settings."""
    try:
        from airunner_services.data.models import PrivacySetting
        from airunner_services.database.session import session_scope

        with session_scope() as session:
            records = session.query(PrivacySetting).all()
            services = {r.service_name: bool(r.enabled) for r in records}
            return {"status": 200, "body": {"services": services}}
    except Exception:
        return {"status": 200, "body": {"services": {}}}


@_rpc_register("PUT", "/api/v1/settings/privacy")
async def _rpc_privacy_update(body: dict, **kwargs: Any) -> dict[str, Any]:
    """Update privacy settings."""
    services: dict = body.get("services", {})
    try:
        from airunner_services.data.models import PrivacySetting
        from airunner_services.database.session import session_scope

        with session_scope() as session:
            for name, enabled in services.items():
                record = (
                    session.query(PrivacySetting)
                    .filter(
                        PrivacySetting.service_name == name,
                    )
                    .first()
                )
                if record:
                    record.enabled = bool(enabled)
                else:
                    session.add(
                        PrivacySetting(
                            service_name=name,
                            enabled=bool(enabled),
                        )
                    )
            session.commit()
        return {"status": 200, "body": {"services": services}}
    except Exception as exc:
        return {"status": 500, "body": {"error": str(exc)}}


# ── Canvas document ──────────────────────────────────────────────────────


@_rpc_register("GET", "/api/v1/canvas/document")
async def _rpc_canvas_doc_get(body: dict, **kwargs: Any) -> dict[str, Any]:
    """Return the saved canvas document string."""
    try:
        from airunner_services.data.models import CanvasSetting
        from airunner_services.database.session import session_scope

        with session_scope() as session:
            record = session.query(CanvasSetting).first()
            doc = (
                str(record.document) if (record and record.document) else None
            )
            return {"status": 200, "body": {"document": doc}}
    except Exception:
        return {"status": 200, "body": {"document": None}}


@_rpc_register("PUT", "/api/v1/canvas/document")
async def _rpc_canvas_doc_save(body: dict, **kwargs: Any) -> dict[str, Any]:
    """Save the canvas document string."""
    doc_str: str = body.get("document", "")
    try:
        from airunner_services.data.models import CanvasSetting
        from airunner_services.database.session import session_scope

        with session_scope() as session:
            record = session.query(CanvasSetting).first()
            if record:
                record.document = doc_str
            else:
                session.add(CanvasSetting(document=doc_str))
            session.commit()
        return {"status": 200, "body": {"status": "saved"}}
    except Exception as exc:
        return {"status": 500, "body": {"error": str(exc)}}


# ── Canvas layers ────────────────────────────────────────────────────────


@_rpc_register("GET", "/api/v1/canvas/layers")
async def _rpc_canvas_layers_list(body: dict, **kwargs: Any) -> dict[str, Any]:
    """List all canvas layers."""
    try:
        from airunner_services.data.models import Layer
        from airunner_services.database.session import session_scope

        with session_scope() as session:
            layers = session.query(Layer).order_by(Layer.order).all()
            return {
                "status": 200,
                "body": {
                    "layers": [
                        {
                            "id": layer.id,
                            "name": str(layer.name) if layer.name else "",
                            "visible": bool(layer.visible),
                            "locked": bool(layer.locked),
                            "order": int(layer.order),
                            "opacity": float(layer.opacity),
                            "blend_mode": (
                                str(layer.blend_mode)
                                if layer.blend_mode
                                else "normal"
                            ),
                        }
                        for layer in layers
                    ]
                },
            }
    except Exception:
        return {"status": 200, "body": {"layers": []}}


# ── Settings CRUD (resource store) ───────────────────────────────────────


@_rpc_register("GET", "/api/v1/settings/resources/{name}/singleton")
async def _rpc_settings_singleton(body: dict, **kw: Any) -> dict[str, Any]:
    """Get or create a singleton resource."""
    pp: dict = kw.get("path_params", {})
    resource_name = pp.get("name", "")
    try:
        from airunner_services.database.session import session_scope
        from airunner_services.settings import resource_store_table

        table = resource_store_table(resource_name)
        with session_scope() as session:
            item = session.query(table).first()
            if item is None:
                item = table()
                session.add(item)
                session.commit()
            record = {
                c.name: getattr(item, c.name) for c in table.__table__.columns
            }
            return {"status": 200, "body": {"record": record}}
    except Exception:
        return {"status": 200, "body": {"record": {}}}


@_rpc_register("PUT", "/api/v1/settings/resources/{name}/singleton")
async def _rpc_settings_singleton_update(
    body: dict, **kw: Any
) -> dict[str, Any]:
    """Update a singleton resource."""
    pp: dict = kw.get("path_params", {})
    resource_name = pp.get("name", "")
    values: dict = body.get("values", {})
    try:
        from airunner_services.database.session import session_scope
        from airunner_services.settings import resource_store_table

        table = resource_store_table(resource_name)
        with session_scope() as session:
            item = session.query(table).first()
            if item is None:
                item = table()
                session.add(item)
            for key, val in values.items():
                if hasattr(item, key):
                    setattr(item, key, val)
            session.commit()
            record = {
                c.name: getattr(item, c.name) for c in table.__table__.columns
            }
            return {"status": 200, "body": record}
    except Exception as exc:
        return {"status": 500, "body": {"error": str(exc)}}


@_rpc_register("POST", "/api/v1/settings/resources/{name}/query")
async def _rpc_settings_query(body: dict, **kw: Any) -> dict[str, Any]:
    """Query resources."""
    pp: dict = kw.get("path_params", {})
    resource_name = pp.get("name", "")
    try:
        from airunner_services.database.session import session_scope
        from airunner_services.settings import resource_store_table

        table = resource_store_table(resource_name)
        with session_scope() as session:
            items = session.query(table).all()
            records = [
                {
                    c.name: getattr(item, c.name)
                    for c in table.__table__.columns
                }
                for item in items
            ]
            return {"status": 200, "body": {"records": records}}
    except Exception:
        return {"status": 200, "body": {"records": []}}


@_rpc_register("POST", "/api/v1/settings/resources/{name}/first")
async def _rpc_settings_first(body: dict, **kw: Any) -> dict[str, Any]:
    """Query first resource matching filters."""
    pp: dict = kw.get("path_params", {})
    resource_name = pp.get("name", "")
    try:
        from airunner_services.database.session import session_scope
        from airunner_services.settings import resource_store_table

        table = resource_store_table(resource_name)
        with session_scope() as session:
            item = session.query(table).first()
            record = (
                {
                    c.name: getattr(item, c.name)
                    for c in table.__table__.columns
                }
                if item
                else {}
            )
            return {"status": 200, "body": {"record": record}}
    except Exception:
        return {"status": 200, "body": {"record": {}}}


# ── Loras ────────────────────────────────────────────────────────────────


@_rpc_register("GET", "/api/v1/art/loras")
async def _rpc_loras_list(body: dict, **kw: Any) -> dict[str, Any]:
    """List all LoRA models."""
    try:
        from airunner_services.database.models.lora import Lora
        from airunner_services.database.session import session_scope

        with session_scope() as session:
            items = session.query(Lora).all()
            return {
                "status": 200,
                "body": {
                    "loras": [
                        {
                            "id": item.id,
                            "name": item.name or "",
                            "path": item.path or "",
                            "enabled": bool(item.enabled),
                            "trigger_words": item.trigger_words or [],
                            "weight": (
                                float(item.weight) if item.weight else 1.0
                            ),
                        }
                        for item in items
                    ]
                },
            }
    except Exception:
        return {"status": 200, "body": {"loras": []}}


@_rpc_register("PATCH", "/api/v1/art/loras/{lora_id}")
async def _rpc_loras_update(body: dict, **kw: Any) -> dict[str, Any]:
    """Update a LoRA model."""
    pp: dict = kw.get("path_params", {})
    raw_id = pp.get("lora_id", "")
    if not raw_id.isdigit():
        return {"status": 400, "body": {"error": "Invalid ID"}}
    try:
        from airunner_services.database.models.lora import Lora
        from airunner_services.database.session import session_scope

        with session_scope() as session:
            item = session.query(Lora).filter(Lora.id == int(raw_id)).first()
            if not item:
                return {"status": 404, "body": {"error": "Not found"}}
            for key in ("enabled", "trigger_words", "weight"):
                if key in body:
                    setattr(item, key, body[key])
            session.commit()
            return {
                "status": 200,
                "body": {
                    "id": item.id,
                    "name": item.name or "",
                    "enabled": bool(item.enabled),
                    "trigger_words": item.trigger_words or [],
                    "weight": float(item.weight) if item.weight else 1.0,
                },
            }
    except Exception as exc:
        return {"status": 500, "body": {"error": str(exc)}}


# ── Embeddings ───────────────────────────────────────────────────────────


@_rpc_register("GET", "/api/v1/art/embeddings")
async def _rpc_embeddings_list(body: dict, **kw: Any) -> dict[str, Any]:
    """List all embeddings."""
    try:
        from airunner_services.database.models.embedding import Embedding
        from airunner_services.database.session import session_scope

        with session_scope() as session:
            items = session.query(Embedding).all()
            return {
                "status": 200,
                "body": {
                    "embeddings": [
                        {
                            "id": e.id,
                            "name": e.name or "",
                            "path": e.path or "",
                            "enabled": bool(e.enabled),
                            "trigger_words": e.trigger_words or [],
                        }
                        for e in items
                    ]
                },
            }
    except Exception:
        return {"status": 200, "body": {"embeddings": []}}


@_rpc_register("PATCH", "/api/v1/art/embeddings/{embedding_id}")
async def _rpc_embeddings_update(body: dict, **kw: Any) -> dict[str, Any]:
    """Update an embedding."""
    pp: dict = kw.get("path_params", {})
    raw_id = pp.get("embedding_id", "")
    if not raw_id.isdigit():
        return {"status": 400, "body": {"error": "Invalid ID"}}
    try:
        from airunner_services.database.models.embedding import Embedding
        from airunner_services.database.session import session_scope

        with session_scope() as session:
            item = (
                session.query(Embedding)
                .filter(Embedding.id == int(raw_id))
                .first()
            )
            if not item:
                return {"status": 404, "body": {"error": "Not found"}}
            for key in ("enabled", "trigger_words"):
                if key in body:
                    setattr(item, key, body[key])
            session.commit()
            return {
                "status": 200,
                "body": {
                    "id": item.id,
                    "name": item.name or "",
                    "enabled": bool(item.enabled),
                    "trigger_words": item.trigger_words or [],
                },
            }
    except Exception as exc:
        return {"status": 500, "body": {"error": str(exc)}}


# ── Conversations ────────────────────────────────────────────────────────


@_rpc_register("GET", "/api/v1/llm/conversations")
async def _rpc_conversations_list(body: dict, **kw: Any) -> dict[str, Any]:
    """List conversations."""
    try:
        from airunner_services.conversations.conversation_history_manager import (
            ConversationHistoryManager,
        )

        manager = ConversationHistoryManager()
        convs = manager.list_conversations(limit=int(body.get("limit", 50)))
        return {"status": 200, "body": {"conversations": convs}}
    except Exception:
        return {"status": 200, "body": {"conversations": []}}


@_rpc_register("POST", "/api/v1/llm/conversations")
async def _rpc_conversations_create(body: dict, **kw: Any) -> dict[str, Any]:
    """Create a new conversation."""
    try:
        from airunner_services.conversations.conversation_history_manager import (
            ConversationHistoryManager,
        )

        manager = ConversationHistoryManager()
        session = manager.create_conversation(
            max_messages=body.get("max_messages"),
        )
        return {"status": 200, "body": session}
    except Exception as exc:
        return {"status": 500, "body": {"error": str(exc)}}


@_rpc_register("DELETE", "/api/v1/llm/conversations/{conv_id}")
async def _rpc_conversations_delete(body: dict, **kw: Any) -> dict[str, Any]:
    """Delete a conversation."""
    pp: dict = kw.get("path_params", {})
    raw_id = pp.get("conv_id", "")
    if not raw_id.isdigit():
        return {"status": 400, "body": {"error": "Invalid ID"}}
    try:
        from airunner_services.conversations.conversation_history_manager import (
            ConversationHistoryManager,
        )

        manager = ConversationHistoryManager()
        manager.delete_conversation(int(raw_id))
        return {"status": 200, "body": {"status": "deleted"}}
    except Exception as exc:
        return {"status": 500, "body": {"error": str(exc)}}


@_rpc_register("GET", "/api/v1/llm/conversations/session")
async def _rpc_conversations_session(body: dict, **kw: Any) -> dict[str, Any]:
    """Get a conversation session."""
    try:
        from airunner_services.conversations.conversation_history_manager import (
            ConversationHistoryManager,
        )

        manager = ConversationHistoryManager()
        conv_id = body.get("conversation_id")
        session = manager.get_conversation_session(
            conversation_id=int(conv_id) if conv_id else None,
            max_messages=int(body.get("max_messages", 50)),
        )
        return {"status": 200, "body": session}
    except Exception as exc:
        return {"status": 500, "body": {"error": str(exc)}}


@_rpc_register("POST", "/api/v1/llm/conversations/select")
async def _rpc_conversations_select(body: dict, **kw: Any) -> dict[str, Any]:
    """Select a conversation."""
    try:
        from airunner_services.conversations.conversation_history_manager import (
            ConversationHistoryManager,
        )

        manager = ConversationHistoryManager()
        conv_id = body.get("conversation_id")
        if conv_id:
            session = manager.get_conversation_session(
                conversation_id=int(conv_id),
            )
            return {"status": 200, "body": session}
        return {"status": 400, "body": {"error": "Missing conversation_id"}}
    except Exception as exc:
        return {"status": 500, "body": {"error": str(exc)}}


# ── Art options + bootstrap ──────────────────────────────────────────────


@_rpc_register("GET", "/api/v1/art/options")
async def _rpc_art_options(body: dict, **kw: Any) -> dict[str, Any]:
    """Return art model options (versions, precisions)."""
    try:
        from airunner_services.model_management.model_registry import (
            ModelRegistry,
        )

        registry = ModelRegistry()
        versions: list[dict[str, Any]] = []
        for model_id, spec in registry.models.items():
            if (
                getattr(spec, "model_type", None)
                and getattr(spec.model_type, "value", None) == "sd"
            ):
                versions.append(
                    {
                        "name": spec.name or model_id,
                        "models": [
                            {
                                "label": m.get("name", m.get("path", "")),
                                "value": m.get("path", ""),
                            }
                            for m in getattr(spec, "files", []) or []
                        ],
                        "schedulers": [],
                    }
                )
        return {
            "status": 200,
            "body": {
                "versions": versions,
                "precisions": [
                    {"label": "FP16", "value": "fp16"},
                    {"label": "FP32", "value": "fp32"},
                ],
            },
        }
    except Exception:
        return {"status": 200, "body": {"versions": [], "precisions": []}}


@_rpc_register("GET", "/api/v1/art/bootstrap")
async def _rpc_art_bootstrap(body: dict, **kw: Any) -> dict[str, Any]:
    """Return bootstrap data."""
    try:
        from airunner_services.model_management.model_registry import (
            ModelRegistry,
        )

        registry = ModelRegistry()
        models = [
            {
                "name": spec.name,
                "version": model_id,
                "category": (
                    getattr(spec.model_type, "value", "")
                    if spec.model_type
                    else ""
                ),
                "path": getattr(spec, "path", ""),
                "pipeline_action": getattr(spec, "pipeline_action", ""),
            }
            for model_id, spec in registry.models.items()
        ]
        return {
            "status": 200,
            "body": {
                "models": models,
                "pipelines": [],
                "unified_model_files": {},
                "controlnet_bootstrap_data": [],
                "espeak_settings_data": [],
                "llm_file_bootstrap_data": {},
                "openvoice_files": {},
                "openvoice_core_models": [],
                "openvoice_language_models": [],
                "path_settings_data": [],
                "rmbg_files": {},
                "sd_file_bootstrap_data": {},
                "whisper_files": {},
                "imagefilter_bootstrap_data": [],
                "prompt_templates_bootstrap_data": [],
            },
        }
    except Exception:
        return {"status": 200, "body": {"models": []}}


# ── Art images ───────────────────────────────────────────────────────────


@_rpc_register("GET", "/api/v1/art/images/dates")
async def _rpc_images_dates(body: dict, **kw: Any) -> dict[str, Any]:
    """List image date directories."""
    root = Path(AIRUNNER_BASE_PATH) / "art" / "other" / "images"
    dates: list[dict[str, str]] = []
    if root.is_dir():
        for d in sorted(root.iterdir(), reverse=True):
            if d.is_dir() and d.name.isdigit() and len(d.name) == 8:
                label = f"{d.name[:4]}-{d.name[4:6]}-{d.name[6:8]}"
                dates.append({"value": d.name, "label": label})
    return {"status": 200, "body": {"dates": dates}}


@_rpc_register("GET", "/api/v1/art/images/{date}")
async def _rpc_images_list(body: dict, **kw: Any) -> dict[str, Any]:
    """List images for a date."""
    from airunner_services.api.routes.images import (
        _list_image_files,
        _extract_metadata,
    )

    pp: dict = kw.get("path_params", {})
    date = pp.get("date", "")
    if not date.isdigit() or len(date) != 8:
        return {"status": 422, "body": {"error": "Invalid date"}}
    root = Path(AIRUNNER_BASE_PATH) / "art" / "other" / "images" / date
    if not root.is_dir():
        return {"status": 200, "body": {"total": 0, "images": []}}
    files = _list_image_files(root)
    offset = int(body.get("offset", 0))
    limit_val = int(body.get("limit", 20))
    page = files[offset : offset + limit_val]
    images = []
    for p in page:
        meta = _extract_metadata(p) if p.suffix.lower() == ".png" else None
        try:
            st = p.stat()
            fsize, ftm = st.st_size, st.st_mtime
        except OSError:
            fsize, ftm = 0, 0.0
        images.append(
            {
                "id": p.name,
                "file_path": str(p),
                "file_size": fsize,
                "file_timestamp": ftm,
                "metadata": meta,
                "image_url": f"/api/v1/art/images/{date}/full/{p.name}",
                "thumbnail_url": f"/api/v1/art/images/{date}/thumb/{p.name}",
            }
        )
    return {"status": 200, "body": {"total": len(files), "images": images}}


@_rpc_register("GET", "/api/v1/art/images/{date}/info/{filename}")
async def _rpc_images_info(body: dict, **kw: Any) -> dict[str, Any]:
    """Get image info."""
    from airunner_services.api.routes.images import _extract_metadata

    pp: dict = kw.get("path_params", {})
    date, filename = pp.get("date", ""), pp.get("filename", "")
    source = (
        Path(AIRUNNER_BASE_PATH) / "art" / "other" / "images" / date / filename
    )
    if not source.is_file():
        return {"status": 404, "body": {"error": "Not found"}}
    meta = (
        _extract_metadata(source) if source.suffix.lower() == ".png" else None
    )
    try:
        fsize = source.stat().st_size
    except OSError:
        fsize = 0
    return {
        "status": 200,
        "body": {
            "id": source.name,
            "file_path": str(source),
            "file_size": fsize,
            "metadata": meta,
            "image_url": f"/api/v1/art/images/{date}/full/{source.name}",
            "thumbnail_url": f"/api/v1/art/images/{date}/thumb/{source.name}",
        },
    }


@_rpc_register("DELETE", "/api/v1/art/images/{date}/delete/{filename}")
async def _rpc_images_delete(body: dict, **kw: Any) -> dict[str, Any]:
    """Delete an image."""
    pp: dict = kw.get("path_params", {})
    date, filename = pp.get("date", ""), pp.get("filename", "")
    source = (
        Path(AIRUNNER_BASE_PATH) / "art" / "other" / "images" / date / filename
    )
    if not source.is_file():
        return {"status": 404, "body": {"error": "Not found"}}
    try:
        source.unlink()
        return {"status": 200, "body": {"success": True, "deleted": filename}}
    except OSError as exc:
        return {"status": 500, "body": {"error": str(exc)}}


@_rpc_register("GET", "/api/v1/art/images/{date}/full/{filename}")
async def _rpc_images_full(body: dict, **kw: Any) -> dict[str, Any]:
    """Serve full image as binary."""
    pp: dict = kw.get("path_params", {})
    date, filename = pp.get("date", ""), pp.get("filename", "")
    source = (
        Path(AIRUNNER_BASE_PATH) / "art" / "other" / "images" / date / filename
    )
    if not source.is_file():
        return {"status": 404, "body": {"error": "Not found"}}
    try:
        data = source.read_bytes()
        return {
            "status": 200,
            "binary": True,
            "headers": {"Content-Type": "image/png"},
            "body": data,
        }
    except OSError as exc:
        return {"status": 500, "body": {"error": str(exc)}}


@_rpc_register("GET", "/api/v1/art/images/{date}/thumb/{filename}")
async def _rpc_images_thumb(body: dict, **kw: Any) -> dict[str, Any]:
    """Serve thumbnail as binary."""
    from PIL import Image as PILImage
    from io import BytesIO

    pp: dict = kw.get("path_params", {})
    date, filename = pp.get("date", ""), pp.get("filename", "")
    source = (
        Path(AIRUNNER_BASE_PATH) / "art" / "other" / "images" / date / filename
    )
    if not source.is_file():
        return {"status": 404, "body": {"error": "Not found"}}
    try:
        img = PILImage.open(source)
        img.thumbnail((200, 200))
        buf = BytesIO()
        img.save(buf, format="PNG")
        data = buf.getvalue()
        return {
            "status": 200,
            "binary": True,
            "headers": {"Content-Type": "image/png"},
            "body": data,
        }
    except Exception as exc:
        return {"status": 500, "body": {"error": str(exc)}}


# ── LLM settings presets ─────────────────────────────────────────────────


@_rpc_register("GET", "/api/v1/llm/settings-presets")
async def _rpc_llm_presets(body: dict, **kw: Any) -> dict[str, Any]:
    """List LLM settings presets."""
    try:
        from airunner_services.api.routes.llm_settings_presets import (
            load_presets,
        )

        presets = load_presets()
        return {"status": 200, "body": {"presets": presets}}
    except Exception:
        return {"status": 200, "body": {"presets": []}}


# ── Downloads ────────────────────────────────────────────────────────────


@_rpc_register("POST", "/api/v1/downloads/huggingface")
async def _rpc_downloads_hf(body: dict, **kw: Any) -> dict[str, Any]:
    """Start a HuggingFace download."""
    try:
        from airunner_services.downloads.service import DownloadJobService

        service = DownloadJobService()
        job_id = await asyncio.to_thread(
            service.start_huggingface_download,
            repo_id=str(body.get("repo_id", "")),
            model_type=str(body.get("model_type", "llm")),
            output_dir=body.get("output_dir"),
            missing_files=body.get("missing_files"),
            gguf_filename=body.get("gguf_filename"),
            prefer_pre_quantized=body.get("prefer_pre_quantized"),
        )
        return {"status": 200, "body": {"job_id": job_id}}
    except Exception as exc:
        return {"status": 500, "body": {"error": str(exc)}}


@_rpc_register("GET", "/api/v1/downloads/status/{job_id}")
async def _rpc_downloads_status(body: dict, **kw: Any) -> dict[str, Any]:
    """Get download job status."""
    pp: dict = kw.get("path_params", {})
    job_id = pp.get("job_id", "")
    try:
        from airunner_services.downloads.service import DownloadJobService

        service = DownloadJobService()
        state = await asyncio.to_thread(service.get_status, job_id)
        if state is None:
            return {"status": 404, "body": {"error": "Job not found"}}
        return {
            "status": 200,
            "body": {
                "job_id": state.job_id,
                "status": state.status,
                "progress": state.progress,
                "result": state.result,
                "error": state.error,
                "metadata": state.metadata,
            },
        }
    except Exception as exc:
        return {"status": 500, "body": {"error": str(exc)}}


@_rpc_register("DELETE", "/api/v1/downloads/cancel/{job_id}")
async def _rpc_downloads_cancel(body: dict, **kw: Any) -> dict[str, Any]:
    """Cancel a download job."""
    pp: dict = kw.get("path_params", {})
    job_id = pp.get("job_id", "")
    try:
        from airunner_services.downloads.service import DownloadJobService

        service = DownloadJobService()
        cancelled = await asyncio.to_thread(service.cancel, job_id)
        if not cancelled:
            return {"status": 404, "body": {"error": "Job not found"}}
        return {
            "status": 200,
            "body": {"job_id": job_id, "status": "cancelled"},
        }
    except Exception as exc:
        return {"status": 500, "body": {"error": str(exc)}}


@_rpc_register("POST", "/api/v1/downloads/civitai/models")
async def _rpc_downloads_civitai_search(
    body: dict, **kw: Any
) -> dict[str, Any]:
    """Search CivitAI models."""
    try:
        from airunner_services.downloads.service import (
            search_civitai_models as search_fn,
        )

        result = await asyncio.to_thread(
            search_fn,
            str(body.get("query", "")),
            base_models=body.get("base_models"),
            model_types=body.get("model_types"),
            limit=int(body.get("limit", 20)),
            cursor=body.get("cursor"),
            api_key=str(body.get("api_key", "")),
        )
        return {"status": 200, "body": result}
    except Exception as exc:
        return {"status": 500, "body": {"error": str(exc)}}


@_rpc_register("POST", "/api/v1/downloads/civitai/model")
async def _rpc_downloads_civitai_model(
    body: dict, **kw: Any
) -> dict[str, Any]:
    """Get CivitAI model detail."""
    try:
        from airunner_services.downloads.service import (
            fetch_civitai_model_info as fetch_fn,
        )

        result = await asyncio.to_thread(
            fetch_fn,
            str(body.get("model_id", "")),
            base_models=body.get("base_models"),
            model_types=body.get("model_types"),
            api_key=str(body.get("api_key", "")),
        )
        return {"status": 200, "body": result}
    except Exception as exc:
        return {"status": 500, "body": {"error": str(exc)}}


@_rpc_register("POST", "/api/v1/downloads/civitai/file")
async def _rpc_downloads_civitai_file(body: dict, **kw: Any) -> dict[str, Any]:
    """Start a CivitAI file download."""
    try:
        from airunner_services.downloads.service import DownloadJobService

        service = DownloadJobService()
        job_id = await asyncio.to_thread(
            service.start_civitai_file_download,
            str(body.get("url", "")),
            output_path=str(body.get("output_path", "")),
            file_size=int(body.get("file_size", 0)),
            api_key=str(body.get("api_key", "")),
        )
        return {"status": 200, "body": {"job_id": job_id}}
    except Exception as exc:
        return {"status": 500, "body": {"error": str(exc)}}


@_rpc_register("POST", "/api/v1/downloads/civitai/info")
async def _rpc_downloads_civitai_info(body: dict, **kw: Any) -> dict[str, Any]:
    """Get CivitAI model info by URL."""
    try:
        from airunner_services.downloads.service import (
            fetch_civitai_model_info as fetch_fn,
        )

        result = await asyncio.to_thread(
            fetch_fn,
            str(body.get("url", "")),
            str(body.get("api_key", "")),
        )
        return {"status": 200, "body": result}
    except Exception as exc:
        return {"status": 500, "body": {"error": str(exc)}}


@_rpc_register("GET", "/api/v1/downloads/civitai/options")
async def _rpc_downloads_civitai_options(
    body: dict, **kw: Any
) -> dict[str, Any]:
    """Get CivitAI filter options."""
    try:
        from airunner_services.downloads.civitai import (
            _BASE_MODEL_ALIASES,
            _MODEL_TYPE_ALIASES,
        )

        base_models = [
            {"label": label, "value": value}
            for label, value in _BASE_MODEL_ALIASES.items()
        ]
        model_types = sorted(set(_MODEL_TYPE_ALIASES.values()))
        return {
            "status": 200,
            "body": {
                "base_models": base_models,
                "model_types": model_types,
            },
        }
    except Exception:
        return {"status": 200, "body": {"base_models": [], "model_types": []}}
