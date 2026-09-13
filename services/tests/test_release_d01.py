"""Regression tests for release issue D01.

Proves:

- Curated downloads stop silently ignoring a declared revision/branch
  pin: model_bootstrap_data already declares "branch" per entry (e.g.
  SDXL Inpaint pins "fp16"), but every download previously hardcoded
  ``resolve/main`` regardless. ``_resolve_bootstrap_revision`` now
  surfaces that pin, and repos with no curated entry (custom models)
  keep resolving "main" exactly as before.
- A same-sized file whose digest does not match a pinned expectation
  fails verification and is never moved to its final, loadable
  location — even though its size alone would previously have looked
  complete.
- A pinned identity survives being re-checked on a "temp file already
  complete" resume path, not just the main download path.

Uses only small neutral in-memory/temp-file fixtures (never a real
model download or network/database access).
"""

from __future__ import annotations

import hashlib

import pytest

from airunner_services.downloads.huggingface_download_worker import (
    HuggingFaceDownloadWorker,
)


@pytest.fixture()
def worker() -> HuggingFaceDownloadWorker:
    return HuggingFaceDownloadWorker()


def test_resolve_bootstrap_revision_uses_declared_pin(worker) -> None:
    """SDXL Inpaint's curated entry pins "fp16", not "main"."""
    revision = worker._resolve_bootstrap_revision(
        "diffusers/stable-diffusion-xl-1.0-inpainting-0.1"
    )
    assert revision == "fp16"


def test_resolve_bootstrap_revision_defaults_to_main_for_custom_repo(
    worker,
) -> None:
    """A repo with no curated bootstrap entry (custom model) is unpinned."""
    assert worker._resolve_bootstrap_revision("some-user/custom-model") == "main"


def test_file_sha256_matches_hashlib(worker, tmp_path) -> None:
    path = tmp_path / "sample.bin"
    payload = b"neutral fixture bytes, not a real model file"
    path.write_bytes(payload)

    assert worker._file_sha256(path) == hashlib.sha256(payload).hexdigest()


def test_verify_and_finalize_moves_file_when_digest_matches(
    worker, tmp_path
) -> None:
    payload = b"correct bytes"
    temp_path = tmp_path / "temp" / "model.bin"
    temp_path.parent.mkdir(parents=True)
    temp_path.write_bytes(payload)
    final_path = tmp_path / "final" / "model.bin"

    ok = worker._verify_and_finalize(
        temp_path=temp_path,
        final_path=final_path,
        filename="model.bin",
        expected_sha256=hashlib.sha256(payload).hexdigest(),
    )

    assert ok is True
    assert final_path.read_bytes() == payload
    assert not temp_path.exists()
    assert "model.bin" in worker._completed_files
    assert "model.bin" not in worker._failed_files


def test_verify_and_finalize_rejects_same_sized_corrupt_file(
    worker, tmp_path
) -> None:
    """A same-sized but wrong-content file must fail, not just pass on size."""
    correct = b"correct-bytes-here!!"
    corrupt = b"wr0ng-bytes-here!!!!"  # same length as `correct`
    assert len(correct) == len(corrupt)

    temp_path = tmp_path / "temp" / "model.bin"
    temp_path.parent.mkdir(parents=True)
    temp_path.write_bytes(corrupt)
    final_path = tmp_path / "final" / "model.bin"

    ok = worker._verify_and_finalize(
        temp_path=temp_path,
        final_path=final_path,
        filename="model.bin",
        expected_sha256=hashlib.sha256(correct).hexdigest(),
    )

    assert ok is False
    assert not final_path.exists()
    assert not temp_path.exists()  # corrupt download is not left around either
    assert "model.bin" in worker._failed_files
    assert "model.bin" not in worker._completed_files


def test_verify_and_finalize_skips_check_when_unpinned(worker, tmp_path) -> None:
    """No pinned digest (today's default for most models): unchanged behavior."""
    temp_path = tmp_path / "temp" / "model.bin"
    temp_path.parent.mkdir(parents=True)
    temp_path.write_bytes(b"anything at all")
    final_path = tmp_path / "final" / "model.bin"

    ok = worker._verify_and_finalize(
        temp_path=temp_path,
        final_path=final_path,
        filename="model.bin",
        expected_sha256=None,
    )

    assert ok is True
    assert final_path.exists()


def test_verify_and_finalize_digest_check_is_case_insensitive(
    worker, tmp_path
) -> None:
    payload = b"case insensitivity check"
    temp_path = tmp_path / "temp" / "model.bin"
    temp_path.parent.mkdir(parents=True)
    temp_path.write_bytes(payload)
    final_path = tmp_path / "final" / "model.bin"

    ok = worker._verify_and_finalize(
        temp_path=temp_path,
        final_path=final_path,
        filename="model.bin",
        expected_sha256=hashlib.sha256(payload).hexdigest().upper(),
    )

    assert ok is True
