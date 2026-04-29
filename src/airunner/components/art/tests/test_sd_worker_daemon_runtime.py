"""Tests for daemon-backed SD worker behavior."""

import base64
from types import SimpleNamespace

from airunner.components.art.managers.stablediffusion.image_request import (
    ImageRequest,
)
from airunner.components.art.workers.sd_worker import SDWorker
from airunner.enums import (
    EngineResponseCode,
    GeneratorSection,
    ModelStatus,
    ModelType,
)

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
            info=lambda *args, **kwargs: None,
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
    assert canvas_calls
    assert export_worker.queued == []
    assert callable(canvas_calls[0].post_display_callback)
    canvas_calls[0].post_display_callback()
    assert export_worker.queued
    assert worker_responses[0][0] is EngineResponseCode.IMAGE_GENERATED
    assert client.calls[0][0] == "start"
    assert client.calls[0][1]["skip_auto_export"] is True
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


def test_finalize_do_generate_signal_reports_failures_via_callback():
    callback_results = []
    handled_errors = []
    alerts = []
    request = ImageRequest(
        prompt="A mountain",
        model_path="/tmp/art-model",
        callback=lambda result: callback_results.append(result),
    )
    worker = SimpleNamespace(
        model_manager=SimpleNamespace(
            model_is_loaded=True,
            handle_generate_signal=lambda _message: (_ for _ in ()).throw(
                TypeError("pipeline result is invalid")
            ),
        ),
        logger=SimpleNamespace(
            debug=lambda *args, **kwargs: None,
            info=lambda *args, **kwargs: None,
        ),
        handle_error=lambda message: handled_errors.append(message),
        send_missing_model_alert=lambda message: alerts.append(message),
        _pending_scheduler=None,
        _apply_scheduler_change=lambda _scheduler: None,
        _is_generating=False,
    )

    SDWorker._finalize_do_generate_signal(worker, {"image_request": request})

    assert callback_results == ["Image model failed to load"]
    assert handled_errors == ["pipeline result is invalid"]
    assert alerts == ["Image model failed to load"]


def test_load_model_manager_calls_callback_for_terminal_load_failure():
    callback_payloads = []
    request = ImageRequest(prompt="A mountain", model_path="")
    model_manager = SimpleNamespace(
        model_is_loaded=False,
        model_type=ModelType.SD,
        model_status={ModelType.SD: ModelStatus.FAILED},
        load=lambda: None,
        image_request=None,
    )
    worker = SimpleNamespace(
        generator_settings=SimpleNamespace(),
        model_manager=model_manager,
        logger=SimpleNamespace(debug=lambda *args, **kwargs: None),
        _process_image_request=lambda data: data,
        _current_model=None,
        _current_version=None,
        _current_pipeline=None,
    )
    worker._has_terminal_model_load_failure = (
        SDWorker._has_terminal_model_load_failure
    )
    worker._get_model_path_from_image_request = (
        SDWorker._get_model_path_from_image_request.__get__(
            worker,
            SimpleNamespace,
        )
    )
    worker._requested_model_signature = (
        SDWorker._requested_model_signature.__get__(
            worker,
            SimpleNamespace,
        )
    )
    worker._record_loaded_model_signature = (
        SDWorker._record_loaded_model_signature.__get__(
            worker,
            SimpleNamespace,
        )
    )

    SDWorker.load_model_manager(
        worker,
        {
            "image_request": request,
            "callback": lambda payload: callback_payloads.append(payload),
        },
    )

    assert model_manager.image_request is request
    assert len(callback_payloads) == 1
    assert callback_payloads[0]["image_request"] is request


def test_finalize_do_generate_signal_reports_failed_load_via_callback():
    callback_results = []
    alerts = []
    request = ImageRequest(
        prompt="A mountain",
        model_path="",
        callback=lambda result: callback_results.append(result),
    )
    model_manager = SimpleNamespace(
        model_is_loaded=False,
        model_type=ModelType.SD,
        model_status={ModelType.SD: ModelStatus.FAILED},
    )
    worker = SimpleNamespace(
        model_manager=model_manager,
        logger=SimpleNamespace(
            debug=lambda *args, **kwargs: None,
            info=lambda *args, **kwargs: None,
        ),
        send_missing_model_alert=lambda message: alerts.append(message),
        _pending_scheduler=None,
        _apply_scheduler_change=lambda _scheduler: None,
        _is_generating=False,
    )
    worker._has_terminal_model_load_failure = (
        SDWorker._has_terminal_model_load_failure
    )
    worker._notify_failed_model_load = SDWorker._notify_failed_model_load.__get__(
        worker,
        SimpleNamespace,
    )

    SDWorker._finalize_do_generate_signal(worker, {"image_request": request})

    assert callback_results == [
        "You must select a model before generating images."
    ]
    assert alerts == ["You must select a model before generating images."]


def test_load_model_manager_reloads_when_requested_model_changes():
    reload_calls = []
    load_calls = []
    request = ImageRequest(
        prompt="A mountain",
        model_path="/tmp/new-model",
        version="Z-Image Turbo",
        pipeline_action="txt2img",
    )
    model_manager = SimpleNamespace(
        model_is_loaded=True,
        reload=lambda: reload_calls.append(True),
        load=lambda: load_calls.append(True),
        image_request=None,
    )
    worker = SimpleNamespace(
        generator_settings=SimpleNamespace(
            version="Z-Image Turbo",
            pipeline_action="txt2img",
            custom_path="",
            model=None,
        ),
        model_manager=model_manager,
        logger=SimpleNamespace(debug=lambda *args, **kwargs: None),
        _process_image_request=lambda data: data,
        _current_model="/tmp/old-model",
        _current_version="Z-Image Turbo",
        _current_pipeline="txt2img",
    )
    worker._get_model_path_from_image_request = (
        SDWorker._get_model_path_from_image_request.__get__(
            worker,
            SimpleNamespace,
        )
    )
    worker._requested_model_signature = (
        SDWorker._requested_model_signature.__get__(
            worker,
            SimpleNamespace,
        )
    )
    worker._record_loaded_model_signature = (
        SDWorker._record_loaded_model_signature.__get__(
            worker,
            SimpleNamespace,
        )
    )

    SDWorker.load_model_manager(worker, {"image_request": request})

    assert reload_calls == [True]
    assert load_calls == []
    assert worker._current_model == "/tmp/new-model"


def test_unload_model_manager_clears_zimage_instance_and_signature():
    unloaded = []
    stopped = []

    class FakeWorker(SimpleNamespace):
        @property
        def model_manager(self):
            return self._model_manager

        @model_manager.setter
        def model_manager(self, value):
            self._model_manager = value

    manager = SimpleNamespace(
        unload=lambda: unloaded.append(True),
        image_export_worker=SimpleNamespace(stop=lambda: stopped.append(True)),
    )
    worker = FakeWorker(
        _model_manager=manager,
        _flux=None,
        _sd=None,
        _sdxl=None,
        _zimage=manager,
        _x4_upscaler=None,
        _current_model="/tmp/model",
        _current_version="Z-Image Turbo",
        _current_pipeline="txt2img",
        logger=SimpleNamespace(info=lambda *args, **kwargs: None),
    )
    worker._clear_loaded_model_signature = (
        SDWorker._clear_loaded_model_signature.__get__(
            worker,
            FakeWorker,
        )
    )

    SDWorker.unload_model_manager(worker)

    assert unloaded == [True]
    assert stopped == [True]
    assert worker._model_manager is None
    assert worker._zimage is None
    assert worker._current_model is None
    assert worker._current_version is None
    assert worker._current_pipeline is None