"""Startup filesystem-scan helpers for art models, loras, embeddings,
and schedulers.

Each function upserts filesystem data into the corresponding database table,
keeping the DB in sync with the disk.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List

from airunner_services.contract_enums import ArtVersion, Scheduler

logger = logging.getLogger(__name__)


# ── Scheduler seed data ──────────────────────────────────────────────


def _known_schedulers() -> dict[str, list[tuple[str, str]]]:
    """Return mapping: model_version → list of (display_name, internal_name)."""
    flow_match = {
        Scheduler.FLOW_MATCH_EULER,
        Scheduler.FLOW_MATCH_LCM,
    }
    sdxl: list[tuple[str, str]] = [
        (s.value, s.name.lower()) for s in Scheduler if s not in flow_match
    ]
    zimage: list[tuple[str, str]] = [
        (Scheduler.FLOW_MATCH_EULER.value, "flowmatcheulerdiscretescheduler"),
        (Scheduler.FLOW_MATCH_LCM.value, "flowmatchlcmdiscretescheduler"),
    ]
    return {
        ArtVersion.SDXL1_0.value: sdxl,
        ArtVersion.Z_IMAGE_TURBO.value: zimage,
    }


def seed_schedulers(
    Schedulers_model,
    session_scope,
) -> None:
    """Seed the schedulers table if it's empty."""
    from airunner_services.contract_enums import (
        ArtVersion,
    )  # noqa: F811

    schedulers_by_version = _known_schedulers()
    try:
        with session_scope() as session:
            existing = {
                r.display_name
                for r in session.query(Schedulers_model).all()
                if r.display_name
            }
            added = 0
            for model_version, scheduler_list in schedulers_by_version.items():
                for display_name, name in scheduler_list:
                    if display_name not in existing:
                        session.add(
                            Schedulers_model(
                                name=name,
                                display_name=display_name,
                                model_version=model_version,
                            )
                        )
                        added += 1
            # Backfill model_version on rows that lack it.
            for r in session.query(Schedulers_model).all():
                if not r.model_version:
                    r.model_version = (
                        ArtVersion.Z_IMAGE_TURBO.value
                        if r.name and "flowmatch" in (r.name or "").lower()
                        else ArtVersion.SDXL1_0.value
                    )
            if added:
                logger.info("Seeded %d schedulers into database", added)
    except Exception:
        logger.exception("Failed to seed schedulers")


# ── LoRA scan ────────────────────────────────────────────────────────


def scan_loras(
    AIRUNNER_BASE_PATH: str,
    Lora_model,
    session_scope,
) -> None:
    """Scan LoRA directories and upsert found files into the DB."""
    art_models = Path(AIRUNNER_BASE_PATH) / "art" / "models"
    if not art_models.is_dir():
        return
    dirs = [p for p in art_models.glob("**/lora/") if p.is_dir()]
    if not dirs:
        logger.info("No LoRA directories found, skipping scan")
        return

    found = 0
    try:
        with session_scope() as session:
            for d in dirs:
                for f in d.iterdir():
                    if f.suffix.lower() not in (".safetensors",):
                        continue
                    name = f.stem
                    path = str(f)
                    existing = (
                        session.query(Lora_model)
                        .filter(Lora_model.path == path)
                        .first()
                    )
                    if existing:
                        existing.name = name
                    else:
                        session.add(
                            Lora_model(
                                name=name,
                                path=path,
                                enabled=False,
                                trigger_words="",
                                weight=1.0,
                            )
                        )
                        found += 1
        logger.info("LoRA scan complete — %d files synced", found)
    except Exception:
        logger.exception("Failed to scan LoRA files")


# ── Embedding scan ───────────────────────────────────────────────────


def scan_embeddings(
    AIRUNNER_BASE_PATH: str,
    Embedding_model,
    session_scope,
) -> None:
    """Scan embedding directories and upsert found files into the DB."""
    extensions = frozenset({".pt", ".safetensors", ".bin", ".pth"})
    art_models = Path(AIRUNNER_BASE_PATH) / "art" / "models"
    candidates: List[Path] = [
        Path(AIRUNNER_BASE_PATH) / "text" / "models" / "llm" / "embedding",
    ]
    if art_models.is_dir():
        candidates.extend(
            p for p in art_models.glob("**/embeddings/") if p.is_dir()
        )
    dirs = [p for p in candidates if p.is_dir()]
    if not dirs:
        logger.info("No embedding directories found, skipping scan")
        return

    found = 0
    try:
        with session_scope() as session:
            for d in dirs:
                for f in d.iterdir():
                    if f.suffix.lower() not in extensions or f.is_dir():
                        continue
                    name, path = f.stem, str(f)
                    existing = (
                        session.query(Embedding_model)
                        .filter(Embedding_model.path == path)
                        .first()
                    )
                    if existing:
                        existing.name = name
                    else:
                        session.add(
                            Embedding_model(
                                name=name,
                                path=path,
                                enabled=False,
                                trigger_words="",
                            )
                        )
                        found += 1
        logger.info("Embedding scan complete — %d files synced", found)
    except Exception:
        logger.exception("Failed to scan embedding files")
