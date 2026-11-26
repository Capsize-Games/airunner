"""Happy/sad/bad tests for VideoService + HTTP routes (fake backend)."""

import time
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from airunner_services.api.routes import video as video_routes
from airunner_services.video.config import VideoConfig
from airunner_services.video.contracts import VideoGenerationRequest
from airunner_services.video.pipeline import VideoResult
from airunner_services.video.service import VideoService


class _FakeBackend:
    def run(self, request, out, on_progress):
        on_progress(0.5)
        Path(out).write_bytes(b"\x00\x00\x00\x18ftypmp42fake")
        return VideoResult(Path(out), 0.01, 1234.0, 512.0)


@pytest.fixture()
def service(tmp_path):
    cfg = VideoConfig(models_dir=str(tmp_path / "m"),
                      output_dir=str(tmp_path / "out"))
    return VideoService(config=cfg, backend=_FakeBackend())


def _wait_done(svc, job_id):
    for _ in range(100):
        if svc.status(job_id).status in (
                "completed", "failed", "cancelled"):
            return svc.status(job_id)
        time.sleep(0.02)
    raise AssertionError("job never finished")


def test_happy_job_completes_with_telemetry(service):
    job_id = service.submit(VideoGenerationRequest(prompt="rain"))
    status = _wait_done(service, job_id)
    assert status.status == "completed"
    assert status.peak_vram_mb == 1234.0
    assert service.result_path(job_id).is_file()


def test_sad_unknown_job_404_via_api(service):
    video_routes.set_service(service)
    app = FastAPI()
    app.include_router(video_routes.router, prefix="/api/v1/video")
    client = TestClient(app)
    assert client.get("/api/v1/video/status/nope").status_code == 404
    ok = client.post("/api/v1/video/generate",
                     json={"prompt": "rain"})
    assert ok.status_code == 202
    bad = client.post("/api/v1/video/generate",
                      json={"prompt": "x", "num_frames": 96})
    assert bad.status_code == 422
    video_routes.set_service(None)


def test_bad_cancel_unknown_job_raises(service):
    with pytest.raises(KeyError):
        service.cancel("missing")
