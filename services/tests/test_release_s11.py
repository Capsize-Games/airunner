"""Release regression tests for issue #2115 (S11).

The mandatory image verdict gates every art output sink -- GUI
signals, previews/canvas, auto-export, thumbnails (via the export
queue), and API results -- on both the direct (local generation and
API response) and sidecar (daemon publish) paths. Blocked,
uncertain, erroring, or unavailable batches never reach those sinks;
allowed batches preserve ordering, metadata, and all images. The
optional NSFW preference stays independent: the mandatory gate runs
regardless of it, and allowed batches still reach the optional
filter. Cancellation and backend-error paths surface no images.

Every image here is a tiny synthetic solid-colour PIL image created
in-process, and every evaluator is a synthetic double. No real
imagery, prompt, or policy term is used. No model is loaded and no
network is used.
"""

from __future__ import annotations

import asyncio
import base64
import io
from types import SimpleNamespace

import pytest
from PIL import Image

from airunner_services.art.managers.stablediffusion.image_response import (
    ImageResponse,
)
from airunner_services.art.managers.stablediffusion.mixins import (
    sd_image_generation_mixin as mixin_mod,
)
from airunner_services.art.runtime_enums import EngineResponseCode
from airunner_services.api.routes import art_job_response as resp_mod
from airunner_services.application_exceptions import InterruptedException
from airunner_services.content_safety import image_verdict
from airunner_services.utils.job_tracker import JobStatus

_COLORS = [(200, 30, 30), (30, 200, 30), (30, 30, 200)]
_SAFE = "a calm neutral landscape"


def _synthetic_images(count: int) -> list[Image.Image]:
    """Return tiny solid-colour in-memory images (never saved)."""
    return [Image.new("RGB", (8, 8), _COLORS[i]) for i in range(count)]


def _synthetic_png(color) -> bytes:
    """Return one synthetic PNG payload for byte-level contracts."""
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), color).save(buffer, format="PNG")
    return buffer.getvalue()


def _pixels(images) -> list:
    """Return the probe pixel of each image, in order."""
    return [img.convert("RGB").getpixel((0, 0)) for img in images]


def _allow_all(images):
    return [False] * len(list(images))


def _flag_all(images):
    return [True] * len(list(images))


def _flag_middle(images):
    flags = [False] * len(list(images))
    if len(flags) > 1:
        flags[1] = True
    return flags


def _boom(images):
    raise RuntimeError("synthetic evaluator failure")


class _StubLogger:
    """Recording stand-in for the production logger wrapper."""

    def __init__(self) -> None:
        self.messages: list[str] = []

    def _record(self, message: str, *args) -> None:
        if args:
            message = message % args
        self.messages.append(message)

    def debug(self, message: str, *args, **_kwargs) -> None:
        """Record one debug message."""
        self._record(message, *args)

    def info(self, message: str, *args, **_kwargs) -> None:
        """Record one info message."""
        self._record(message, *args)

    def warning(self, message: str, *args, **_kwargs) -> None:
        """Record one warning message."""
        self._record(message, *args)

    def error(self, message: str, *args, **_kwargs) -> None:
        """Record one error message."""
        self._record(message, *args)


@pytest.fixture(autouse=True)
def _clean_state(monkeypatch: pytest.MonkeyPatch):
    image_verdict.set_evaluator(None)
    monkeypatch.setattr(mixin_mod, "clear_memory", lambda *a, **k: None)
    yield
    image_verdict.set_evaluator(None)


class _FakeArtApi:
    """Minimal app/api surface used by the generation tests."""

    def __init__(self) -> None:
        self.canvas_sent: list = []
        self.responses: list = []
        self.art = SimpleNamespace(
            final_progress_update=self._progress,
            canvas=SimpleNamespace(
                send_image_to_canvas=self.canvas_sent.append
            ),
        )

    def _progress(self, *args, **kwargs) -> None:
        """Ignore progress updates during gate tests."""

    def worker_response(self, code, message) -> None:
        """Record one worker response."""
        self.responses.append((code, message))


class _FakeGenerator(mixin_mod.SDImageGenerationMixin):
    """Direct-path harness with fake runtime boundaries."""

    def __init__(self, batches: list) -> None:
        self._batches = batches
        self._pipe = object()
        self.logger = _StubLogger()
        self.api = _FakeArtApi()
        self.callbacks: list = []
        self.exported: list = []
        self.optional_calls: list = []
        self.image_export_worker = SimpleNamespace(
            add_to_queue=self.exported.append
        )
        self.active_rect = None
        self.image_request = SimpleNamespace(
            steps=4, callback=self.callbacks.append, node_id=None
        )
        self._current_prompt = _SAFE
        self._current_prompt_2 = ""
        self._current_negative_prompt = ""
        self._current_negative_prompt_2 = ""
        self.model_path = "synthetic-model"
        self.version = "synthetic"
        self.scheduler_name = "synthetic"
        self._loaded_lora: list = []
        self._loaded_embeddings: list = []
        self.controlnet_enabled = False
        self.is_txt2img = True
        self.is_img2img = False
        self.is_inpaint = False
        self.is_outpaint = False
        self.mask_blur = 0
        self._memory_settings_flags: dict = {}
        self.application_settings = SimpleNamespace()
        self.path_settings = SimpleNamespace()
        self.metadata_settings = SimpleNamespace()
        self.controlnet_settings = SimpleNamespace()
        self.use_safety_checker = False

    def _load_prompt_embeds(self) -> None:
        """Skip prompt embedding work during gate tests."""

    def _prepare_data(self, _rect) -> dict:
        """Return empty generation parameters during gate tests."""
        return {}

    def _get_results(self, _data):
        """Yield one fake pipeline result per configured batch."""
        for batch in self._batches:
            yield {"images": batch}

    def _check_and_mark_nsfw_images(self, images):
        """Stand in for the optional filter; pass everything through."""
        self.optional_calls.append(list(images))
        return list(images), [False] * len(images)


class _InterruptingGenerator(_FakeGenerator):
    """Direct-path harness whose backend raises interruption."""

    def _get_results(self, _data):
        """Raise instead of yielding any pipeline result."""
        raise InterruptedException("synthetic interrupt")


class _FakeTracker:
    """Recording stand-in for the API-path JobTracker."""

    def __init__(self, cancelled: bool = False) -> None:
        self._cancelled = cancelled
        self.completed: dict = {}
        self.failed: dict = {}
        self.cancel_calls: list = []

    async def cancel_job(self, job_id: str) -> None:
        """Record one cancellation."""
        self.cancel_calls.append(job_id)

    async def fail_job(self, job_id: str, message: str) -> None:
        """Record one job failure."""
        self.failed[job_id] = message

    async def complete_job(self, job_id: str, result) -> None:
        """Record one job completion."""
        self.completed[job_id] = result

    async def get_status(self, job_id: str):
        """Report a cancelled or running job state."""
        if self._cancelled:
            return SimpleNamespace(status=JobStatus.CANCELLED)
        return SimpleNamespace(status=JobStatus.RUNNING)


def _api_response(payloads, status: str = "succeeded", error=None):
    """Return one fake envelope-like art response."""
    return SimpleNamespace(
        status=status, payload={"images": payloads}, error=error
    )


def _b64(raw: bytes) -> str:
    """Encode one payload for the response contract."""
    return base64.b64encode(raw).decode("ascii")


def _make_daemon_worker():
    """Return an SDWorker with fake sidecar boundaries."""
    from airunner_services.workers.sd_worker import SDWorker

    class _Harness(SDWorker):
        """SDWorker with neutral in-memory settings stand-ins."""

        @property
        def application_settings(self):
            """Return neutral settings without touching the database."""
            return SimpleNamespace()

        @property
        def path_settings(self):
            """Return neutral settings without touching the database."""
            return SimpleNamespace()

        @property
        def metadata_settings(self):
            """Return neutral settings without touching the database."""
            return SimpleNamespace()

        @property
        def controlnet_settings(self):
            """Return neutral settings without touching the database."""
            return SimpleNamespace()

    worker = object.__new__(_Harness)
    worker.logger = _StubLogger()
    worker.canvas_sent = []
    worker.responses = []
    worker.exported = []
    worker.errors = []
    worker.callbacks = []
    worker.api = SimpleNamespace(
        art=SimpleNamespace(
            canvas=SimpleNamespace(
                send_image_to_canvas=worker.canvas_sent.append
            )
        ),
        worker_response=lambda code, message: worker.responses.append(
            (code, message)
        ),
    )
    worker.handle_error = worker.errors.append
    worker.image_export_worker = SimpleNamespace(
        add_to_queue=worker.exported.append
    )
    return worker


def _daemon_request(worker):
    """Return a real ImageRequest bound to the fake callback."""
    from airunner_services.art.managers.stablediffusion.image_request import (
        ImageRequest,
    )

    return ImageRequest(prompt=_SAFE, callback=worker.callbacks.append)


# --------------------------------------------------------------------------
# Direct path: local generation mixin
# --------------------------------------------------------------------------


def test_mixin_allows_batch_preserving_order_and_metadata() -> None:
    image_verdict.set_evaluator(_allow_all)
    originals = _synthetic_images(3)
    generator = _FakeGenerator([originals])
    generator._generate()
    assert len(generator.exported) == 1
    assert generator.exported[0]["images"] == originals
    assert _pixels(generator.exported[0]["images"]) == _COLORS
    data = generator.exported[0]["data"]
    assert data["image_request"] is generator.image_request
    assert data["current_prompt"] == _SAFE
    assert len(generator.api.canvas_sent) == 1
    assert generator.api.canvas_sent[0].images == originals
    assert len(generator.callbacks) == 1
    assert isinstance(generator.callbacks[0], ImageResponse)
    code, _message = generator.api.responses[-1]
    assert code is EngineResponseCode.IMAGE_GENERATED
    assert generator.optional_calls == [originals]


def test_mixin_withholds_flagged_batch_from_all_sinks() -> None:
    image_verdict.set_evaluator(_flag_all)
    generator = _FakeGenerator([_synthetic_images(2)])
    generator._generate()
    assert generator.exported == []
    assert generator.api.canvas_sent == []
    assert generator.callbacks == [mixin_mod.OUTPUT_WITHHELD_MESSAGE]
    assert generator.api.responses == [
        (EngineResponseCode.ERROR, mixin_mod.OUTPUT_WITHHELD_MESSAGE)
    ]
    assert generator.optional_calls == []
    logs = generator.logger.messages
    assert any("image_flagged" in message for message in logs)


def test_mixin_withholds_batch_when_one_member_flagged() -> None:
    image_verdict.set_evaluator(_flag_middle)
    generator = _FakeGenerator([_synthetic_images(3)])
    generator._generate()
    assert generator.exported == []
    assert generator.api.canvas_sent == []
    assert generator.callbacks == [mixin_mod.OUTPUT_WITHHELD_MESSAGE]
    assert generator.api.responses == [
        (EngineResponseCode.ERROR, mixin_mod.OUTPUT_WITHHELD_MESSAGE)
    ]


def test_mixin_withholds_batch_when_evaluator_unavailable() -> None:
    assert image_verdict.get_evaluator() is None
    generator = _FakeGenerator([_synthetic_images(2)])
    generator._generate()
    assert generator.exported == []
    assert generator.api.canvas_sent == []
    assert generator.callbacks == [mixin_mod.OUTPUT_WITHHELD_MESSAGE]
    assert generator.api.responses == [
        (EngineResponseCode.ERROR, mixin_mod.OUTPUT_WITHHELD_MESSAGE)
    ]
    logs = generator.logger.messages
    assert any("image_unavailable" in message for message in logs)


def test_mixin_withholds_batch_when_evaluator_raises() -> None:
    image_verdict.set_evaluator(_boom)
    generator = _FakeGenerator([_synthetic_images(2)])
    generator._generate()
    assert generator.exported == []
    assert generator.api.canvas_sent == []
    assert generator.callbacks == [mixin_mod.OUTPUT_WITHHELD_MESSAGE]
    assert generator.api.responses == [
        (EngineResponseCode.ERROR, mixin_mod.OUTPUT_WITHHELD_MESSAGE)
    ]


def test_mixin_interrupt_surfaces_no_images() -> None:
    image_verdict.set_evaluator(_allow_all)
    generator = _InterruptingGenerator([_synthetic_images(2)])
    generator._generate()
    assert generator.exported == []
    assert generator.api.canvas_sent == []
    assert generator.callbacks == []
    assert generator.api.responses == [
        (EngineResponseCode.INTERRUPTED, "Image generation interrupted")
    ]


def test_mixin_backend_error_surfaces_no_images(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image_verdict.set_evaluator(_allow_all)
    originals = _synthetic_images(2)
    generator = _FakeGenerator([originals])

    def _fail(*_args, **_kwargs):
        raise RuntimeError("synthetic backend failure")

    monkeypatch.setattr(mixin_mod, "ImageResponse", _fail)
    generator._generate()
    assert generator.api.canvas_sent == []
    assert len(generator.callbacks) == 1
    assert isinstance(generator.callbacks[0], str)
    code, message = generator.api.responses[-1]
    assert code is EngineResponseCode.ERROR
    assert isinstance(message, str)
    assert generator.exported[0]["images"] == originals


# --------------------------------------------------------------------------
# Direct path: API job response
# --------------------------------------------------------------------------


def test_api_allows_batch_preserving_order() -> None:
    image_verdict.set_evaluator(_allow_all)
    raws = [_synthetic_png(color) for color in _COLORS[:2]]
    payloads = [_b64(raw) for raw in raws]
    tracker = _FakeTracker()
    asyncio.run(
        resp_mod.apply_art_response(tracker, "job-1", _api_response(payloads))
    )
    assert tracker.failed == {}
    result = tracker.completed["job-1"]
    assert result["images_bytes"] == raws
    assert result["image_bytes"] == raws[0]


def test_api_withholds_flagged_batch(
    caplog: pytest.LogCaptureFixture,
) -> None:
    image_verdict.set_evaluator(_flag_all)
    raws = [_synthetic_png(color) for color in _COLORS[:2]]
    payloads = [_b64(raw) for raw in raws]
    tracker = _FakeTracker()
    with caplog.at_level("WARNING", logger=resp_mod.logger.name):
        asyncio.run(
            resp_mod.apply_art_response(
                tracker, "job-1", _api_response(payloads)
            )
        )
    assert tracker.completed == {}
    assert tracker.failed == {"job-1": resp_mod.OUTPUT_WITHHELD_MESSAGE}
    assert "image_flagged" not in tracker.failed["job-1"]
    assert any("image_flagged" in record.message for record in caplog.records)


def test_api_withholds_batch_when_evaluator_unavailable() -> None:
    assert image_verdict.get_evaluator() is None
    payloads = [_b64(_synthetic_png(_COLORS[0]))]
    tracker = _FakeTracker()
    asyncio.run(
        resp_mod.apply_art_response(tracker, "job-1", _api_response(payloads))
    )
    assert tracker.completed == {}
    assert tracker.failed == {"job-1": resp_mod.OUTPUT_WITHHELD_MESSAGE}


def test_api_withholds_undecodable_payload() -> None:
    image_verdict.set_evaluator(_allow_all)
    payloads = [_b64(b"not-an-image" * 8)]
    tracker = _FakeTracker()
    asyncio.run(
        resp_mod.apply_art_response(tracker, "job-1", _api_response(payloads))
    )
    assert tracker.completed == {}
    assert tracker.failed == {"job-1": resp_mod.OUTPUT_WITHHELD_MESSAGE}


def test_api_cancelled_job_stores_nothing() -> None:
    image_verdict.set_evaluator(_allow_all)
    payloads = [_b64(_synthetic_png(_COLORS[0]))]
    tracker = _FakeTracker(cancelled=True)
    asyncio.run(
        resp_mod.apply_art_response(tracker, "job-1", _api_response(payloads))
    )
    assert tracker.completed == {}
    assert tracker.failed == {}


def test_api_failed_status_fails_without_images() -> None:
    image_verdict.set_evaluator(_allow_all)
    error = SimpleNamespace(message="synthetic backend failure")
    tracker = _FakeTracker()
    asyncio.run(
        resp_mod.apply_art_response(
            tracker, "job-1", _api_response([], status="failed", error=error)
        )
    )
    assert tracker.completed == {}
    assert tracker.failed == {"job-1": "synthetic backend failure"}


# --------------------------------------------------------------------------
# Sidecar path: daemon result publication
# --------------------------------------------------------------------------


def test_daemon_allows_result_to_all_sinks() -> None:
    from airunner_common.contract_enums import EngineResponseCode as Code

    image_verdict.set_evaluator(_allow_all)
    worker = _make_daemon_worker()
    raw = _synthetic_png(_COLORS[0])
    request = _daemon_request(worker)
    worker._publish_daemon_art_result({"active_rect": None}, request, raw)
    assert len(worker.canvas_sent) == 1
    response = worker.canvas_sent[0]
    assert isinstance(response, ImageResponse)
    assert _pixels(response.images) == [_COLORS[0]]
    assert worker.callbacks == [response]
    assert worker.responses == [(Code.IMAGE_GENERATED, response)]
    assert worker.exported == []
    response.post_display_callback()
    assert len(worker.exported) == 1
    assert _pixels(worker.exported[0]["images"]) == [_COLORS[0]]
    assert worker.exported[0]["data"]["image_request"] is request


def test_daemon_withholds_flagged_result() -> None:
    from airunner_common.contract_enums import EngineResponseCode as Code
    from airunner_services.workers import sd_worker as worker_mod

    image_verdict.set_evaluator(_flag_all)
    worker = _make_daemon_worker()
    request = _daemon_request(worker)
    worker._publish_daemon_art_result(
        {"active_rect": None}, request, _synthetic_png(_COLORS[0])
    )
    assert worker.canvas_sent == []
    assert worker.exported == []
    assert worker.callbacks == [worker_mod.OUTPUT_WITHHELD_MESSAGE]
    assert worker.responses == [
        (Code.ERROR, worker_mod.OUTPUT_WITHHELD_MESSAGE)
    ]
    assert worker.errors == [worker_mod.OUTPUT_WITHHELD_MESSAGE]
    logs = worker.logger.messages
    assert any("image_flagged" in message for message in logs)


def test_daemon_withholds_result_when_evaluator_unavailable() -> None:
    from airunner_common.contract_enums import EngineResponseCode as Code
    from airunner_services.workers import sd_worker as worker_mod

    assert image_verdict.get_evaluator() is None
    worker = _make_daemon_worker()
    request = _daemon_request(worker)
    worker._publish_daemon_art_result(
        {"active_rect": None}, request, _synthetic_png(_COLORS[0])
    )
    assert worker.canvas_sent == []
    assert worker.exported == []
    assert worker.callbacks == [worker_mod.OUTPUT_WITHHELD_MESSAGE]
    assert worker.responses == [
        (Code.ERROR, worker_mod.OUTPUT_WITHHELD_MESSAGE)
    ]
    logs = worker.logger.messages
    assert any("image_unavailable" in message for message in logs)


def test_daemon_withholds_undecodable_result() -> None:
    from airunner_common.contract_enums import EngineResponseCode as Code
    from airunner_services.workers import sd_worker as worker_mod

    image_verdict.set_evaluator(_allow_all)
    worker = _make_daemon_worker()
    request = _daemon_request(worker)
    worker._publish_daemon_art_result(
        {"active_rect": None}, request, b"\x00\x01not-a-png"
    )
    assert worker.canvas_sent == []
    assert worker.exported == []
    assert worker.callbacks == [worker_mod.OUTPUT_WITHHELD_MESSAGE]
    assert worker.responses == [
        (Code.ERROR, worker_mod.OUTPUT_WITHHELD_MESSAGE)
    ]
