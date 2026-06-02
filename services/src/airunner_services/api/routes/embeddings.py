"""Textual inversion (embedding) scan endpoint."""

from __future__ import annotations

import os

from fastapi import APIRouter

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
