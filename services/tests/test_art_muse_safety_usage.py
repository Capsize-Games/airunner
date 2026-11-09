"""Muse usage-ledger and cloud-image gate regression tests."""

from __future__ import annotations

import dataclasses
import inspect
import io
from concurrent.futures import ThreadPoolExecutor

import pytest
from PIL import Image

from airunner_services.api.routes import art_job_response
from airunner_services.api.routes.art_job_response import (
    gate_response_images,
)
from airunner_services.content_safety.image_verdict import (
    ImageBatchVerdict,
    ImageVerdict,
)
from airunner_services.runtimes.muse_usage import (
    DEFAULT_MAX_IMAGES_PER_JOB,
    ENV_MAX_IMAGES_PER_JOB,
    MuseUsageLedger,
    MuseUsageLimitError,
    MuseUsageRecord,
    enforce_max_images_per_job,
    resolve_max_images_per_job,
)


@pytest.fixture(autouse=True)
def _clean_muse_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolate the per-job limit env override per test."""
    monkeypatch.delenv(ENV_MAX_IMAGES_PER_JOB, raising=False)


def _count(ledger: MuseUsageLedger, job_id: str) -> int:
    """Return the recorded count, asserting the job exists."""
    record = ledger.get(job_id)
    assert record is not None
    return record.image_count


def _tiny_png() -> bytes:
    """Return bytes of one tiny valid PNG image."""
    buffer = io.BytesIO()
    Image.new("RGB", (2, 2), (10, 20, 30)).save(buffer, "PNG")
    return buffer.getvalue()


def _allowed_batch(count: int) -> ImageBatchVerdict:
    """Return a batch verdict allowing ``count`` images."""
    return ImageBatchVerdict(
        verdicts=tuple(ImageVerdict.allow() for _ in range(count))
    )


def _withheld_batch(count: int) -> ImageBatchVerdict:
    """Return a batch verdict withholding ``count`` images."""
    return ImageBatchVerdict(
        verdicts=tuple(
            ImageVerdict.withhold("image_flagged") for _ in range(count)
        )
    )


# ------------------------------------------------------------------
# Ledger: happy paths
# ------------------------------------------------------------------


def test_record_get_and_total_images() -> None:
    ledger = MuseUsageLedger()
    record = ledger.record("job-1", "muse-image-1.0", 2)
    assert record == MuseUsageRecord("job-1", "muse-image-1.0", 2)
    assert ledger.get("job-1") == record
    assert _count(ledger, "job-1") == 2
    assert int(ledger.total_images) == 2
    assert ledger.total_images() == 2
    assert ledger.total_for("job-1") == 2


def test_record_accumulates_per_job_and_totals() -> None:
    ledger = MuseUsageLedger()
    ledger.record("job-1", "muse-image-1.0", 2)
    ledger.record("job-1", "muse-image-1.0", 1)
    ledger.record("job-2", "muse-image-1.0", 3)
    assert _count(ledger, "job-1") == 3
    assert int(ledger.total_images) == 6
    assert len(ledger) == 2
    assert "job-1" in ledger
    assert set(ledger.snapshot()) == {"job-1", "job-2"}


def test_ledger_is_thread_safe_under_concurrency() -> None:
    ledger = MuseUsageLedger(max_images_per_job=1000)

    def _record(index: int) -> None:
        ledger.record("job-1", "muse-image-1.0", 1)

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(_record, range(64)))
    assert _count(ledger, "job-1") == 64
    assert int(ledger.total_images) == 64


def test_clear_resets_ledger() -> None:
    ledger = MuseUsageLedger()
    ledger.record("job-1", "muse-image-1.0", 1)
    ledger.clear()
    assert len(ledger) == 0
    assert int(ledger.total_images) == 0
    assert ledger.get("job-1") is None


# ------------------------------------------------------------------
# Ledger: sad and bad paths
# ------------------------------------------------------------------


def test_get_missing_job_returns_none() -> None:
    ledger = MuseUsageLedger()
    assert ledger.get("missing") is None
    assert ledger.total_for("missing") == 0
    assert int(ledger.total_images) == 0


@pytest.mark.parametrize(
    "job_id,model,count,error",
    [
        ("", "muse-image-1.0", 1, ValueError),
        ("  ", "muse-image-1.0", 1, ValueError),
        (None, "muse-image-1.0", 1, TypeError),
        ("job-1", "", 1, ValueError),
        ("job-1", None, 1, TypeError),
        ("job-1", "muse-image-1.0", -1, ValueError),
        ("job-1", "muse-image-1.0", True, TypeError),
        ("job-1", "muse-image-1.0", 1.5, TypeError),
        ("job-1", "muse-image-1.0", "1", TypeError),
    ],
)
def test_record_rejects_invalid_input(
    job_id: str, model: str, count: int, error: type[Exception]
) -> None:
    ledger = MuseUsageLedger()
    with pytest.raises(error):
        ledger.record(job_id, model, count)  # invalid on purpose
    assert int(ledger.total_images) == 0


def test_ledger_stores_no_prompt_or_key() -> None:
    fields = {f.name for f in dataclasses.fields(MuseUsageRecord)}
    assert fields == {"job_id", "model", "image_count"}
    params = list(inspect.signature(MuseUsageLedger.record).parameters)
    assert params == ["self", "job_id", "model", "image_count"]
    record = MuseUsageLedger().record("j", "muse-image-1.0", 1)
    assert not hasattr(record, "prompt")
    assert not hasattr(record, "api_key")


# ------------------------------------------------------------------
# Per-job guard helper
# ------------------------------------------------------------------


def test_guard_defaults_to_eight() -> None:
    assert DEFAULT_MAX_IMAGES_PER_JOB == 8
    assert resolve_max_images_per_job() == 8
    assert enforce_max_images_per_job(8) == 8
    with pytest.raises(MuseUsageLimitError):
        enforce_max_images_per_job(9)


def test_guard_env_override_and_invalid_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(ENV_MAX_IMAGES_PER_JOB, "2")
    assert resolve_max_images_per_job() == 2
    assert enforce_max_images_per_job(2) == 2
    with pytest.raises(MuseUsageLimitError):
        enforce_max_images_per_job(3)
    monkeypatch.setenv(ENV_MAX_IMAGES_PER_JOB, "not-a-number")
    assert resolve_max_images_per_job() == 8


def test_record_over_limit_is_withheld_atomically() -> None:
    ledger = MuseUsageLedger(max_images_per_job=2)
    ledger.record("job-1", "muse-image-1.0", 2)
    with pytest.raises(MuseUsageLimitError):
        ledger.record("job-1", "muse-image-1.0", 1)
    assert _count(ledger, "job-1") == 2
    assert ledger.enforce_limit("job-1", 0) == 2
    with pytest.raises(MuseUsageLimitError):
        ledger.enforce_limit("job-1", 1)


def test_guard_rejects_invalid_counts() -> None:
    with pytest.raises(ValueError):
        enforce_max_images_per_job(-1)
    with pytest.raises(TypeError):
        enforce_max_images_per_job(True)  # bool is not a count


# ------------------------------------------------------------------
# Cloud-image gate regression (existing gate, not weakened)
# ------------------------------------------------------------------


def test_undecodable_cloud_image_is_withheld(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[object] = []

    def _fake(images: object) -> tuple:
        calls.append(images)
        return ([], [], _allowed_batch(1))

    monkeypatch.setattr(art_job_response, "check_images_mandatory", _fake)
    assert gate_response_images([b"not-a-decodable-image"]) is False
    assert gate_response_images([_tiny_png(), b"junk"]) is False
    assert calls == []


def test_valid_png_passes_only_via_mandatory_seam(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[list[Image.Image]] = []

    def _allow(images: list[Image.Image]) -> tuple:
        seen.append(list(images))
        return (list(images), [False], _allowed_batch(len(images)))

    monkeypatch.setattr(art_job_response, "check_images_mandatory", _allow)
    assert gate_response_images([_tiny_png()]) is True
    assert len(seen) == 1
    assert len(seen[0]) == 1
    assert isinstance(seen[0][0], Image.Image)


def test_valid_png_fails_when_mandatory_seam_withholds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _withhold(images: list[Image.Image]) -> tuple:
        return (list(images), [True], _withheld_batch(len(images)))

    monkeypatch.setattr(art_job_response, "check_images_mandatory", _withhold)
    assert gate_response_images([_tiny_png()]) is False
