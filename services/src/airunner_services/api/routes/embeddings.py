"""Textual inversion (embedding) and LoRA scan endpoints."""

from __future__ import annotations

import os

from fastapi import APIRouter

from airunner_services.settings import AIRUNNER_BASE_PATH

router = APIRouter()

EMBEDDING_EXTENSIONS = {".pt", ".safetensors", ".bin", ".pth"}
LORA_DIR = os.path.join(AIRUNNER_BASE_PATH, "art", "models", "lora")


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
    """Scan the art models directory for LoRA .safetensors files."""
    found: list[dict[str, object]] = []
    if not os.path.isdir(LORA_DIR):
        return {"loras": found}
    for entry in sorted(os.listdir(LORA_DIR)):
        full_path = os.path.join(LORA_DIR, entry)
        ext = os.path.splitext(entry)[1].lower()
        if ext == ".safetensors" and os.path.isfile(full_path):
            name = os.path.splitext(entry)[0]
            found.append({
                "name": name,
                "path": full_path,
            })
    return {"loras": found}
