"""Textual inversion (embedding) and LoRA scan endpoints."""

from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException

from airunner_services.database.models.lora import Lora
from airunner_services.database.session import session_scope
from airunner_services.settings import AIRUNNER_BASE_PATH

router = APIRouter()

EMBEDDING_EXTENSIONS = {".pt", ".safetensors", ".bin", ".pth"}


@router.get("/embeddings")
async def list_embeddings():
    """Scan the models directory for textual inversion embedding files."""
    embed_dirs = [
        os.path.join(AIRUNNER_BASE_PATH, "art", "models", "embeddings"),
        os.path.join(AIRUNNER_BASE_PATH, "text", "models", "llm", "embedding"),
    ]
    found: list[dict[str, object]] = []
    seen: set[str] = set()
    for base_dir in embed_dirs:
        if not os.path.isdir(base_dir):
            continue
        for entry in os.listdir(base_dir):
            full_path = os.path.join(base_dir, entry)
            ext = os.path.splitext(entry)[1].lower()
            if ext in EMBEDDING_EXTENSIONS:
                name = os.path.splitext(entry)[0]
                if name not in seen:
                    seen.add(name)
                    found.append({
                        "name": name,
                        "path": full_path,
                        "file_type": ext,
                    })
    return {"embeddings": found}


@router.get("/loras")
async def list_loras():
    """Scan the art models directory tree for LoRA .safetensors files.
    Merges filesystem results with DB records for enabled/trigger_words.
    """
    models_root = os.path.join(AIRUNNER_BASE_PATH, "art", "models")
    found: list[dict[str, object]] = []
    seen: set[str] = set()

    # Load existing DB records
    db_records: dict[str, dict] = {}
    with session_scope() as session:
        for rec in session.query(Lora).all():
            db_records[rec.name] = {
                "id": rec.id,
                "name": rec.name,
                "enabled": bool(rec.enabled),
                "trigger_words": (
                    (rec.trigger_words or "").split(",")
                    if rec.trigger_words else []
                ),
            }

    if not os.path.isdir(models_root):
        return {"loras": found}

    for root, dirs, _files in os.walk(models_root):
        if os.path.basename(root) != "lora":
            continue
        for entry in sorted(os.listdir(root)):
            full_path = os.path.join(root, entry)
            ext = os.path.splitext(entry)[1].lower()
            if ext == ".safetensors" and os.path.isfile(full_path):
                name = os.path.splitext(entry)[0]
                if name not in seen:
                    seen.add(name)
                    db = db_records.get(name, {})
                    if not db:
                        with session_scope() as session:
                            rec = Lora(
                                name=name,
                                path=full_path,
                                enabled=False,
                                trigger_words="",
                            )
                            session.add(rec)
                            session.flush()
                            db = {
                                "id": rec.id,
                                "name": name,
                                "enabled": False,
                                "trigger_words": [],
                            }
                    found.append({
                        "id": db["id"],
                        "name": name,
                        "path": full_path,
                        "enabled": db["enabled"],
                        "trigger_words": db["trigger_words"],
                    })
    return {"loras": found}


@router.patch("/loras/{lora_id}")
async def update_lora(
    lora_id: int,
    enabled: bool | None = None,
    trigger_words: str | None = None,
):
    """Update one LoRA record's enabled state or trigger words."""
    with session_scope() as session:
        rec = session.query(Lora).filter_by(id=lora_id).first()
        if rec is None:
            raise HTTPException(status_code=404, detail="LoRA not found")
        if enabled is not None:
            rec.enabled = enabled
        if trigger_words is not None:
            rec.trigger_words = trigger_words
        session.commit()
        return {
            "id": rec.id,
            "name": rec.name,
            "enabled": bool(rec.enabled),
            "trigger_words": (
                (rec.trigger_words or "").split(",")
                if rec.trigger_words else []
            ),
        }
