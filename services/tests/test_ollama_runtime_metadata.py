"""Truthful Ollama model metadata from local artifact and runtime evidence."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from airunner_services.api.routes.ollama_runtime_metadata import (
    VerifiedFileDigest,
    build_ollama_runtime_metadata,
)


def _file_digest_receipt(path: Path, digest: str) -> VerifiedFileDigest:
    info = path.stat()
    return VerifiedFileDigest(
        canonical_path=str(path.resolve()),
        sha256=digest,
        size_bytes=info.st_size,
        device=info.st_dev,
        inode=info.st_ino,
        mtime_ns=info.st_mtime_ns,
    )


def test_known_catalog_model_uses_artifact_and_runtime_facts(
    tmp_path: Path,
) -> None:
    artifact = tmp_path / "Qwen3.5-9B-Q8_0.gguf"
    artifact.write_bytes(b"verified fixture bytes")

    metadata = build_ollama_runtime_metadata(
        artifact,
        runtime_context_length=32768,
        measured_vram_bytes=9_947_733_504,
        expires_at=datetime(2026, 11, 2, 19, 30, tzinfo=timezone.utc),
    )

    assert metadata.model_id == "qwen3.5-9b"
    assert metadata.name == "qwen3.5-9b:latest"
    assert metadata.size_bytes == artifact.stat().st_size
    assert metadata.digest == ""
    assert metadata.modified_at == datetime.fromtimestamp(
        artifact.stat().st_mtime, tz=timezone.utc
    ).isoformat(timespec="microseconds").replace("+00:00", "Z")
    assert metadata.family == "qwen"
    assert metadata.parameter_size == "9B"
    assert metadata.quantization_level == "Q8_0"
    assert metadata.format == "gguf"

    listed = metadata.list_model()
    process = metadata.process_model()
    shown = metadata.show_response()
    assert listed["size"] == artifact.stat().st_size
    assert listed["details"]["quantization_level"] == "Q8_0"
    assert process["size_vram"] == 9_947_733_504
    assert process["context_length"] == 32768
    assert shown["model_info"] == {"context_length": 262144}
    assert shown["model_info"]["context_length"] != process["context_length"]
    assert shown["capabilities"] == ["completion", "tools"]
    assert metadata.expires_at == "2026-11-02T19:30:00.000000Z"


def test_verified_digest_is_used_only_for_unchanged_matching_file(
    tmp_path: Path,
) -> None:
    artifact = tmp_path / "Qwen3.5-9B-Q8_0.gguf"
    artifact.write_bytes(b"small metadata fixture")
    receipt = _file_digest_receipt(
        artifact,
        "b" * 64,
    )

    assert (
        build_ollama_runtime_metadata(
            artifact,
            verified_digest=receipt,
        ).digest
        == "b" * 64
    )

    artifact.write_bytes(b"changed metadata fixture")
    assert (
        build_ollama_runtime_metadata(
            artifact,
            verified_digest=receipt,
        ).digest
        == ""
    )


def test_unknown_catalog_and_runtime_values_are_not_guessed(
    tmp_path: Path,
) -> None:
    artifact = tmp_path / "custom-local.gguf"
    artifact.write_bytes(b"custom model")

    metadata = build_ollama_runtime_metadata(artifact)

    assert metadata.model_id == ""
    assert metadata.name == "custom-local:latest"
    assert metadata.size_bytes == len(b"custom model")
    assert metadata.digest == ""
    assert metadata.family == ""
    assert metadata.parameter_size == ""
    assert metadata.quantization_level == ""
    assert metadata.catalog_context_length is None
    assert metadata.runtime_context_length == 0
    assert metadata.size_vram_bytes == 0
    assert metadata.expires_at == "0001-01-01T00:00:00.000000Z"
    assert metadata.details == {
        "parent_model": "",
        "format": "gguf",
        "family": "",
        "families": [],
        "parameter_size": "",
        "quantization_level": "",
    }
    assert metadata.show_response() == {
        "model_info": {},
        "capabilities": [],
    }
    assert metadata.process_model()["size_vram"] == 0
    assert metadata.process_model()["context_length"] == 0


def test_missing_or_directory_artifact_reports_schema_zeroes(
    tmp_path: Path,
) -> None:
    metadata = build_ollama_runtime_metadata(tmp_path / "missing.gguf")
    assert metadata.name == ""
    assert metadata.size_bytes == 0
    assert metadata.digest == ""
    assert metadata.modified_at == "0001-01-01T00:00:00.000000Z"
    assert metadata.process_model()["expires_at"] == (
        "0001-01-01T00:00:00.000000Z"
    )

    directory = tmp_path / "directory.gguf"
    directory.mkdir()
    directory_metadata = build_ollama_runtime_metadata(directory)
    assert directory_metadata.name == ""
    assert directory_metadata.size_bytes == 0
    assert directory_metadata.digest == ""
    assert directory_metadata.quantization_level == ""
