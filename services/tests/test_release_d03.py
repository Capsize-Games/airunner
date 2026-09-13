"""Regression tests for release issue D03.

Proves every checked image from a batch art request reaches the caller,
not only the first, while existing single-image callers keep working
unchanged:

- ``art_job_response.apply_art_response`` stores every decoded batch
  image (``images_bytes``), not just the first, while still storing
  ``image_bytes`` (first image) for existing single-image callers.
- ``art_generation_job_routes`` reports how many images are available
  (``image_count``) and serves each one by index
  (``GET /result/{job_id}/{index}``), while ``GET /result/{job_id}``
  keeps returning the first image unchanged.
- ``GuiDaemonClient.wait_art_job`` (existing single-image callers, e.g.
  ``sd_worker.py``/``worker_manager.py``) is unchanged; the new
  ``wait_art_job_images``/``art_job_results`` fetch every batch image,
  in order, and are what the updated Desktop consumer
  (``gui_bridge_mixin.generate_image_async``) now uses.

Uses only small neutral fake image payloads and a fake HTTP layer
(mocked client methods) — never a real model/network/database.
"""

from __future__ import annotations

import asyncio
import base64
from types import SimpleNamespace
from unittest import mock

import pytest

from airunner_services.api.routes.art_contracts import JobStatusResponse
from airunner_services.api.routes.art_generation_job_routes import (
    completed_image_count,
    indexed_png_response,
    png_response,
    status_response,
)
from airunner_services.api.routes.art_job_response import (
    apply_art_response,
    decode_response_images,
)
from airunner_services.daemon_client.gui_daemon_client import GuiDaemonClient
from airunner_services.ipc.messages import EnvelopeStatus, ResponseEnvelope
from airunner_services.utils.job_tracker import JobStatus, JobTracker

_FAKE_IMAGES = [b"image-bytes-0", b"image-bytes-1", b"image-bytes-2"]


def _fake_runtime_response() -> ResponseEnvelope:
    """A neutral fake runtime response carrying three batch images."""
    return ResponseEnvelope(
        request_id="req-1",
        status=EnvelopeStatus.SUCCEEDED,
        payload={
            "images": [
                base64.b64encode(image).decode("ascii")
                for image in _FAKE_IMAGES
            ]
        },
    )


# --- art_job_response: response decoding and job completion ---


def test_decode_response_images_returns_every_image_in_order() -> None:
    assert decode_response_images(_fake_runtime_response()) == _FAKE_IMAGES


def test_apply_art_response_stores_every_image_and_first_image() -> None:
    async def _run() -> None:
        tracker = JobTracker()
        job_id = await tracker.create_job()
        await apply_art_response(tracker, job_id, _fake_runtime_response())
        return tracker, job_id

    tracker, job_id = asyncio.run(_run())

    job = tracker._jobs[job_id]
    assert job.status is JobStatus.COMPLETED
    assert job.result["images_bytes"] == _FAKE_IMAGES
    assert job.result["image_bytes"] == _FAKE_IMAGES[0]


# --- art_generation_job_routes: status/count/indexed retrieval ---


def _fake_job(result: dict, *, status=JobStatus.COMPLETED) -> SimpleNamespace:
    return SimpleNamespace(
        job_id="job-1",
        status=status,
        progress=100.0,
        result=result,
        error=None,
    )


def test_completed_image_count_reflects_batch_size() -> None:
    job = _fake_job({"images_bytes": _FAKE_IMAGES, "image_bytes": _FAKE_IMAGES[0]})
    assert completed_image_count(job) == 3


def test_completed_image_count_falls_back_to_one_for_legacy_result() -> None:
    job = _fake_job({"image_bytes": _FAKE_IMAGES[0]})
    assert completed_image_count(job) == 1


def test_completed_image_count_zero_when_not_completed() -> None:
    job = _fake_job({}, status=JobStatus.RUNNING)
    assert completed_image_count(job) == 0


def test_status_response_includes_image_count() -> None:
    job = _fake_job({"images_bytes": _FAKE_IMAGES, "image_bytes": _FAKE_IMAGES[0]})
    response = status_response("job-1", job)
    assert isinstance(response, JobStatusResponse)
    assert response.image_count == 3
    assert response.image_url == "/api/v1/art/result/job-1"


def test_indexed_png_response_returns_each_image_in_order() -> None:
    result = {"images_bytes": _FAKE_IMAGES, "image_bytes": _FAKE_IMAGES[0]}
    for index, expected in enumerate(_FAKE_IMAGES):
        response = indexed_png_response(result, index)
        assert response.body == expected
        assert response.media_type == "image/png"


def test_indexed_png_response_out_of_range_raises_index_error() -> None:
    result = {"images_bytes": _FAKE_IMAGES}
    with pytest.raises(IndexError):
        indexed_png_response(result, 3)


def test_indexed_png_response_index_zero_falls_back_to_legacy_result() -> None:
    """A result with no images_bytes list (older stored job) still resolves
    index 0 via the existing single-image path."""
    result = {"image_bytes": _FAKE_IMAGES[0]}
    response = indexed_png_response(result, 0)
    assert response.body == _FAKE_IMAGES[0]


def test_get_result_unchanged_returns_first_image() -> None:
    """GET /result/{job_id} (no index) keeps returning the first image."""
    result = {"images_bytes": _FAKE_IMAGES, "image_bytes": _FAKE_IMAGES[0]}
    assert png_response(result).body == _FAKE_IMAGES[0]


# --- GuiDaemonClient: batch fetch and backward-compatible single fetch ---


@pytest.fixture()
def daemon_client(tmp_path) -> GuiDaemonClient:
    return GuiDaemonClient(
        config_path=tmp_path / "daemon.yaml",
        session=mock.MagicMock(),
        auto_start=False,
    )


def test_art_job_results_fetches_every_image_in_order(daemon_client) -> None:
    daemon_client.art_job_status = mock.Mock(
        return_value={"status": "completed", "image_count": 3}
    )
    daemon_client.art_job_result_at = mock.Mock(
        side_effect=lambda job_id, index, auto_start=False: _FAKE_IMAGES[index]
    )

    images = daemon_client.art_job_results("job-1")

    assert images == _FAKE_IMAGES
    assert daemon_client.art_job_result_at.call_count == 3


def test_art_job_results_falls_back_to_single_result_when_count_missing(
    daemon_client,
) -> None:
    daemon_client.art_job_status = mock.Mock(
        return_value={"status": "completed"}
    )
    daemon_client.art_job_result = mock.Mock(return_value=_FAKE_IMAGES[0])

    images = daemon_client.art_job_results("job-1")

    assert images == [_FAKE_IMAGES[0]]


def test_wait_art_job_images_waits_then_fetches_every_image(
    daemon_client,
) -> None:
    daemon_client.art_job_status = mock.Mock(
        return_value={"status": "completed", "progress": 100.0, "image_count": 3}
    )
    daemon_client.art_job_result_at = mock.Mock(
        side_effect=lambda job_id, index, auto_start=False: _FAKE_IMAGES[index]
    )

    images = daemon_client.wait_art_job_images("job-1")

    assert images == _FAKE_IMAGES


def test_wait_art_job_still_returns_only_first_image(daemon_client) -> None:
    """Existing single-image callers (sd_worker.py, worker_manager.py) keep
    their exact prior behavior after the shared-poller refactor."""
    daemon_client.art_job_status = mock.Mock(
        return_value={"status": "completed", "progress": 100.0, "image_count": 3}
    )
    daemon_client.art_job_result = mock.Mock(return_value=_FAKE_IMAGES[0])

    result = daemon_client.wait_art_job("job-1")

    assert result == _FAKE_IMAGES[0]
    daemon_client.art_job_result.assert_called_once()
