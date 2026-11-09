"""End-to-end Muse job flow: envelope -> client -> tracked result."""

from __future__ import annotations

import asyncio
import base64
import io
from types import SimpleNamespace
from typing import Any

from PIL import Image

from airunner_services.api.routes import art_job_response
from airunner_services.api.routes.art_contracts import GenerationRequest
from airunner_services.api.routes.art_job_response import run_art_job
from airunner_services.api.routes.art_runtime_registry import (
    resolve_art_client,
)
from airunner_services.runtimes.muse_art_client import (
    MuseArtClient, register_muse_art_client,
)
from airunner_services.runtimes.muse_art_helpers import MuseArtSettings
from airunner_services.runtimes.registry import RuntimeRegistry
from airunner_services.utils.job_tracker import JobTracker


def _png_b64() -> str:
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), color=(10, 20, 30)).save(buffer, "PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


class _Resp:
    def __init__(self, payload: Any) -> None:
        self._payload = payload
        self.status_code = 200
        self.content = b""

    def json(self) -> Any:
        return self._payload


class _Session:
    def __init__(self) -> None:
        self.posts: list[dict[str, Any]] = []

    def post(self, url: str, **kwargs: Any) -> _Resp:
        self.posts.append({"url": url, **kwargs})
        return _Resp({"data": [{"b64_json": _png_b64()}]})

    def get(self, url: str, **kwargs: Any) -> _Resp:
        raise AssertionError("no URL fetch expected")


def test_muse_job_flow_completes_with_png_result(
    monkeypatch: Any,
) -> None:
    monkeypatch.setattr(
        art_job_response, "check_images_mandatory",
        lambda images: (images, [False] * len(images),
            SimpleNamespace(all_allowed=True, reasons=[])),
    )
    session = _Session()
    settings = MuseArtSettings(api_key="test-only", base_url="https://x/v1")
    client = MuseArtClient(settings=settings, session=session)
    registry = register_muse_art_client(RuntimeRegistry(), client)
    resolved = resolve_art_client(registry, provider="muse")
    assert resolved is client
    tracker = JobTracker()
    request = GenerationRequest(prompt="a red square", provider="muse")

    async def _flow() -> Any:
        job_id = await tracker.create_art_job(
            metadata={"provider": "muse"}, capacity=99)
        assert job_id is not None
        await tracker.mark_art_job_running(job_id)
        await run_art_job(tracker, job_id, request, resolved)
        job = await tracker.get_status(job_id)
        await tracker.finish_art_job(job_id)
        return job

    job = asyncio.run(_flow())
    assert job.status.value == "completed"
    images = job.result["images_bytes"]
    assert len(images) == 1
    Image.open(io.BytesIO(images[0])).load()
    assert session.posts[0]["json"]["model"] == "muse-image-1.0"
    assert client.usage_ledger.total_for(job.job_id) == 1
