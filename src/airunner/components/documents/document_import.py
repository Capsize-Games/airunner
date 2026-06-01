"""Helpers for importing supported RAG documents into AIRunner."""

from __future__ import annotations

from contextlib import nullcontext
import filecmp
import os
import shutil
from pathlib import Path
from typing import Iterable

from airunner.components.documents.data.document_records import (
    ensure_document_record,
)
from airunner.runtimes.file_policy import (
    normalize_local_path,
    resolve_existing_file,
)

try:
    from facehuggershield.darklock.restrict_os_access import (
        RestrictOSAccess,
    )
except Exception:  # pragma: no cover - darklock may be unavailable in tests
    RestrictOSAccess = None

RAG_DOCUMENT_SUFFIXES = (
    ".epub",
    ".htm",
    ".html",
    ".md",
    ".mobi",
    ".pdf",
    ".txt",
)

CHAT_IMAGE_SUFFIXES = (
    ".bmp",
    ".gif",
    ".jpeg",
    ".jpg",
    ".png",
    ".webp",
)


def rag_document_suffixes() -> tuple[str, ...]:
    """Return the file suffixes AIRunner can import into RAG."""
    return RAG_DOCUMENT_SUFFIXES


def chat_image_suffixes() -> tuple[str, ...]:
    """Return the file suffixes supported for chat image attachments."""
    return CHAT_IMAGE_SUFFIXES


def is_rag_document_path(file_path: str) -> bool:
    """Return True when one path uses a supported RAG document suffix."""
    return Path(str(file_path)).suffix.lower() in RAG_DOCUMENT_SUFFIXES


def is_chat_image_path(file_path: str) -> bool:
    """Return True when one path uses a supported chat image suffix."""
    return Path(str(file_path)).suffix.lower() in CHAT_IMAGE_SUFFIXES


def import_document_to_library(
    file_path: str,
    destination_root: str,
) -> str:
    """Copy one supported document into the local AIRunner document library."""
    source_path = Path(
        resolve_existing_file(
            file_path,
            label="Document import path",
            allowed_suffixes=RAG_DOCUMENT_SUFFIXES,
        )
    )
    destination_dir = Path(
        normalize_local_path(
            destination_root,
            label="Document library path",
        )
    )
    destination_dir.mkdir(parents=True, exist_ok=True)

    with _user_selected_path_override([str(source_path)]):
        destination_path = _resolve_destination_path(
            source_path,
            destination_dir,
        )
        if destination_path != source_path:
            shutil.copy2(source_path, destination_path)

    _ensure_document_record(str(destination_path))
    return str(destination_path)


def _user_selected_path_override(paths: Iterable[str]):
    """Temporarily allow explicit user-selected paths under DarkLock."""
    if RestrictOSAccess is None:
        return nullcontext()

    try:
        return RestrictOSAccess().user_override(paths=list(paths))
    except Exception:
        return nullcontext()


def _resolve_destination_path(
    source_path: Path,
    destination_dir: Path,
) -> Path:
    """Return one stable destination path in the local document library."""
    try:
        if source_path.is_relative_to(destination_dir):
            return source_path
    except AttributeError:
        common = os.path.commonpath(
            [str(source_path), str(destination_dir)]
        )
        if common == str(destination_dir):
            return source_path

    candidate = destination_dir / source_path.name
    if not candidate.exists():
        return candidate
    if filecmp.cmp(source_path, candidate, shallow=False):
        return candidate

    stem = source_path.stem
    suffix = source_path.suffix
    counter = 1
    while True:
        candidate = destination_dir / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        if filecmp.cmp(source_path, candidate, shallow=False):
            return candidate
        counter += 1


def _ensure_document_record(file_path: str) -> None:
    """Create one database record for one imported document when needed."""
    ensure_document_record(
        file_path,
        active=False,
        indexed=False,
    )