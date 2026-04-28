"""Tests for daemon-backed SD worker behavior."""

import base64
from types import SimpleNamespace

from airunner.components.art.managers.stablediffusion.image_request import (
    ImageRequest,
)
from airunner.components.art.workers.sd_worker import SDWorker
from airunner.enums import EngineResponseCode, GeneratorSection

PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4"
    "//8/AwAI/AL+KDvWyAAAAABJRU5ErkJggg=="
)


class FakeDaemonClient:
    """Minimal daemon client double for SD worker tests."""

    def __init__(self):
        self.calls = []

    def start_art_generation(self, **kwargs):
        self.calls.append(("start", kwargs))
        return {"job_id": "art-job-1", "status": "running"}

    def wait_art_job(self, job_id, **kwargs):
        self.calls.append(("wait", job_id, kwargs))
        return PNG_BYTES

    def cancel_art_job(self, job_id, **kwargs):
        self.calls.append(("cancel", job_id, kwargs))
        return {"status": "cancelled"}


class FakeExportWorker:
    """Image export worker double."""

    def __init__(self):
        self.queued = []

    def add_to_queue(self, payload):
        self.queued.append(payload)


def _worker(client):
    export_worker = FakeExportWorker()
    canvas_calls = []
    worker_responses = []
    alerts = []
    errors = []
    fake = SimpleNamespace(
        _active_daemon_job_id=None,
        image_export_worker=export_worker,
        api=SimpleNamespace(
            art=SimpleNamespace(
                canvas=SimpleNamespace(
                    send_image_to_canvas=lambda response: canvas_calls.append(response)
                )
            ),
            worker_response=lambda code, message: worker_responses.append(
                (code, message)
            ),
        ),
        application_settings=SimpleNamespace(auto_export_images=False),
        path_settings=SimpleNamespace(image_path="/tmp"),
        metadata_settings=SimpleNamespace(export_metadata=False),
        controlnet_settings=SimpleNamespace(controlnet="canny"),
        logger=SimpleNamespace(
            debug=lambda *args, **kwargs: None,
            error=lambda *args, **kwargs: None,
        ),
        handle_error=lambda message: errors.append(message),
        send_missing_model_alert=lambda message: alerts.append(message),
        _daemon_client=lambda: client,
    )
    fake._daemon_result_data = SDWorker._daemon_result_data.__get__(fake, SimpleNamespace)
    fake._publish_daemon_art_result = SDWorker._publish_daemon_art_result.__get__(fake, SimpleNamespace)
    fake._handle_daemon_art_error = SDWorker._handle_daemon_art_error.__get__(fake, SimpleNamespace)
    fake._generate_image_via_daemon = SDWorker._generate_image_via_daemon.__get__(fake, SimpleNamespace)
    return fake, export_worker, canvas_calls, worker_responses, alerts, errors


def test_generate_image_via_daemon_publishes_canvas_and_worker_response():
    client = FakeDaemonClient()
    worker, export_worker, canvas_calls, worker_responses, alerts, errors = _worker(client)
    request = ImageRequest(
        prompt="A mountain",
        negative_prompt="",
        model_path="/tmp/art-model",
        version="Flux.1 S",
        scheduler="DDIM",
        generator_section=GeneratorSection.TXT2IMG,
    )

    worker._generate_image_via_daemon({"image_request": request})

    assert not alerts
    assert not errors
    assert export_worker.queued
    assert canvas_calls
    assert worker_responses[0][0] is EngineResponseCode.IMAGE_GENERATED
    assert client.calls[0][0] == "start"
    assert client.calls[1][0] == "wait"
    assert worker._active_daemon_job_id is None


def test_interrupt_image_generation_cancels_active_daemon_job():
    client = FakeDaemonClient()
    worker = SimpleNamespace(
        _active_daemon_job_id="art-job-1",
        _daemon_client=lambda: client,
        model_manager=None,
    )

    SDWorker.on_interrupt_image_generation_signal(worker)

    assert client.calls[0][0] == "cancel"