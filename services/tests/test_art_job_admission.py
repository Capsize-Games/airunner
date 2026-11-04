"""Bounded art-job admission and request-owned cancellation contracts."""

from __future__ import annotations

import asyncio
import importlib
import queue
import threading
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from airunner_services.api.routes.art_contracts import GenerationRequest
from airunner_services.ipc.messages import (
    EnvelopeStatus,
    RequestEnvelope,
    ResponseEnvelope,
)
from airunner_services.runtimes.contracts import RuntimeAction, RuntimeKind
from airunner_services.runtimes.local_fallback import LocalFallbackArtClient
from airunner_services.utils.job_tracker import JobStatus, JobTracker
from airunner_services.workers.sd_worker import SDWorker


def _fresh_tracker() -> JobTracker:
    JobTracker._instance = None
    JobTracker._lock = asyncio.Lock()
    return JobTracker()


def test_http_admission_rejects_full_capacity_until_runner_finishes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        routes = importlib.import_module(
            "airunner_services.api.routes.art_generation_start_routes"
        )
        tracker = _fresh_tracker()
        started = asyncio.Event()
        release = asyncio.Event()
        unloads: list[bool] = []
        client = SimpleNamespace(finish_request=lambda _job_id: None)

        async def unload(*_args, **_kwargs):
            unloads.append(True)

        async def run_job(*_args, **_kwargs):
            started.set()
            await release.wait()

        monkeypatch.setattr(routes, "evaluate_prompt_fields", lambda _fields: SimpleNamespace(allowed=True))
        monkeypatch.setattr(routes, "_screen_request_input_image", lambda _request: None)
        monkeypatch.setattr(routes, "resolve_generation_model", lambda _request: None)
        monkeypatch.setattr(routes, "unload_llm_before_art", unload)
        monkeypatch.setattr(routes, "require_runtime_registry", lambda _req: object())
        monkeypatch.setattr(routes, "resolve_art_client", lambda _registry: client)
        monkeypatch.setattr(routes, "JobTracker", lambda: tracker)
        monkeypatch.setattr(routes, "run_art_job", run_job)

        request = GenerationRequest(prompt="neutral test prompt")
        job_id = await routes.create_generation_job(request, SimpleNamespace())
        await started.wait()
        assert len(unloads) == 1

        with pytest.raises(HTTPException) as rejected:
            await routes.create_generation_job(request, SimpleNamespace())
        assert rejected.value.status_code == 503
        assert rejected.value.headers == {"Retry-After": "1"}
        assert len(unloads) == 1

        assert await tracker.cancel_job(job_id)
        assert (await tracker.get_status(job_id)).execution_finished is False
        with pytest.raises(HTTPException) as still_running:
            await routes.create_generation_job(request, SimpleNamespace())
        assert still_running.value.status_code == 503

        task = tracker._art_tasks[job_id]
        release.set()
        await task
        assert (await tracker.get_status(job_id)).execution_finished is True
        replacement = await tracker.create_art_job(capacity=1)
        assert replacement is not None
        await tracker.finish_art_job(replacement)

    asyncio.run(scenario())


@pytest.mark.parametrize("cancel_point", ["handoff", "start_transition"])
def test_cancel_before_runner_attachment_releases_reservation(
    monkeypatch: pytest.MonkeyPatch, cancel_point: str
) -> None:
    async def scenario() -> None:
        routes = importlib.import_module(
            "airunner_services.api.routes.art_generation_start_routes"
        )
        tracker = _fresh_tracker()
        entered = asyncio.Event()
        never_release = asyncio.Event()
        run_calls: list[bool] = []
        finished: list[str] = []
        client = SimpleNamespace(
            register_request=lambda request_id: None,
            finish_request=finished.append,
        )

        async def unload(*_args, **_kwargs):
            if cancel_point == "handoff":
                entered.set()
                await never_release.wait()

        real_start = tracker.mark_art_job_running

        async def start_transition(job_id: str) -> bool:
            if cancel_point == "start_transition":
                entered.set()
                await never_release.wait()
            return await real_start(job_id)

        async def run_job(*_args, **_kwargs):
            run_calls.append(True)

        monkeypatch.setattr(routes, "evaluate_prompt_fields", lambda _fields: SimpleNamespace(allowed=True))
        monkeypatch.setattr(routes, "_screen_request_input_image", lambda _request: None)
        monkeypatch.setattr(routes, "resolve_generation_model", lambda _request: None)
        monkeypatch.setattr(routes, "unload_llm_before_art", unload)
        monkeypatch.setattr(routes, "require_runtime_registry", lambda _req: object())
        monkeypatch.setattr(routes, "resolve_art_client", lambda _registry: client)
        monkeypatch.setattr(routes, "JobTracker", lambda: tracker)
        monkeypatch.setattr(routes, "run_art_job", run_job)
        monkeypatch.setattr(tracker, "mark_art_job_running", start_transition)

        task = asyncio.create_task(
            routes.create_generation_job(
                GenerationRequest(prompt="neutral test prompt"),
                SimpleNamespace(),
            )
        )
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        assert run_calls == []
        assert finished and len(finished) == 1
        assert tracker._art_slots == set()
        assert tracker._jobs == {}
        replacement = await tracker.create_art_job(capacity=1)
        assert replacement is not None
        await tracker.finish_art_job(replacement)

    asyncio.run(scenario())


def test_cancelled_runner_keeps_slot_until_physical_runner_finishes() -> None:
    async def scenario() -> None:
        tracker = _fresh_tracker()
        job_id = await tracker.create_art_job(capacity=1)
        assert job_id is not None
        started = asyncio.Event()
        release = asyncio.Event()

        async def runner() -> None:
            started.set()
            await release.wait()
            await tracker.finish_art_job(job_id)

        task = asyncio.create_task(runner())
        tracker.attach_art_task(job_id, task, object())
        await started.wait()
        assert await tracker.cancel_job(job_id)
        assert (await tracker.get_status(job_id)).execution_finished is False
        await tracker.update_progress(job_id, 80.0, JobStatus.RUNNING)
        await tracker.complete_job(job_id, {"image_bytes": b"must-not-publish"})
        await tracker.cleanup_old_jobs(max_age_seconds=0)
        assert await tracker.get_status(job_id) is not None
        assert (await tracker.get_status(job_id)).status is JobStatus.CANCELLED
        assert (await tracker.get_status(job_id)).result is None
        assert await tracker.create_art_job(capacity=1) is None

        release.set()
        await task
        assert (await tracker.get_status(job_id)).execution_finished is True
        next_job = await tracker.create_art_job(capacity=1)
        assert next_job is not None
        await tracker.finish_art_job(next_job)

    asyncio.run(scenario())


def test_shutdown_cancels_but_does_not_abandon_or_release_active_runner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def inline_to_thread(function, *args, **kwargs):
        return function(*args, **kwargs)

    monkeypatch.setattr(asyncio, "to_thread", inline_to_thread)

    async def scenario() -> None:
        tracker = _fresh_tracker()
        job_id = await tracker.create_art_job(capacity=1)
        assert job_id is not None
        started = asyncio.Event()
        release = asyncio.Event()
        cancel_calls: list[str] = []

        class Client:
            def cancel(self, request_id: str) -> None:
                cancel_calls.append(request_id)

        async def runner() -> None:
            started.set()
            await release.wait()
            await tracker.finish_art_job(job_id)

        task = asyncio.create_task(runner())
        tracker.attach_art_task(job_id, task, Client())
        await started.wait()
        # A cancelled public state does not mean the physical worker ended.
        assert await tracker.cancel_job(job_id)
        await tracker.shutdown_art_jobs(timeout=0.001)
        assert cancel_calls == [job_id]
        assert not task.cancelled()
        assert await tracker.create_art_job(capacity=1) is None

        release.set()
        await task
        replacement = await tracker.create_art_job(capacity=1)
        assert replacement is not None
        await tracker.finish_art_job(replacement)

    asyncio.run(scenario())


def test_local_fallback_cancel_is_request_owned_and_prestart_safe() -> None:
    client = LocalFallbackArtClient(timeout_seconds=1, signal_source=object())
    emitted: list[tuple[object, dict]] = []
    client._emit_signal = lambda code, payload: emitted.append((code, payload))

    pending_id = "pending-art-request"
    client.register_request(pending_id)
    client.cancel(pending_id)
    request = RequestEnvelope(
        request_id=pending_id,
        runtime=RuntimeKind.ART,
        action=RuntimeAction.INVOKE,
        payload={"prompt": "safe test fixture"},
    )
    response = client.invoke(request)
    assert response.status is EnvelopeStatus.CANCELLED
    assert emitted == []

    active_id = "owned-active-request"
    started = threading.Event()
    release = threading.Event()
    client.register_request(active_id)

    def blocked_runtime(_request, _progress_callback=None):
        started.set()
        assert release.wait(timeout=2)
        return ResponseEnvelope(
            request_id=active_id,
            status=EnvelopeStatus.SUCCEEDED,
            payload={},
        )

    client._generate_image_owned = blocked_runtime
    active_request = RequestEnvelope(
        request_id=active_id,
        runtime=RuntimeKind.ART,
        action=RuntimeAction.INVOKE,
        payload={"prompt": "barrier fixture"},
    )
    result: list[ResponseEnvelope] = []
    thread = threading.Thread(
        target=lambda: result.append(client.invoke(active_request))
    )
    thread.start()
    assert started.wait(timeout=2)
    client.cancel("unrelated-request")
    assert emitted == []
    client.cancel(active_id)
    assert len(emitted) == 1
    assert emitted[0][1] == {"request_id": active_id}
    release.set()
    thread.join(timeout=2)
    assert not thread.is_alive()
    assert result[0].status is EnvelopeStatus.SUCCEEDED
    client.finish_request(active_id)
    client.finish_request("unrelated-request")


def test_local_art_admin_cancel_uses_explicit_global_interrupt() -> None:
    client = LocalFallbackArtClient(timeout_seconds=1, signal_source=object())
    emitted: list[tuple[object, dict]] = []
    client._emit_signal = lambda code, payload: emitted.append((code, payload))

    response = client.cancel_active("admin-cancel-request")
    assert response.request_id == "admin-cancel-request"
    assert response.status is EnvelopeStatus.CANCELLED
    assert response.metadata["administrative"] is True
    assert emitted[-1][1] == {}


def test_daemon_art_cancel_without_id_requires_explicit_admin_support() -> None:
    from airunner_services.api.routes.daemon_runtime_actions import (
        cancel_runtime_action,
    )
    from airunner_services.api.models.runtime_route_request import (
        RuntimeRouteRequest,
    )
    from airunner_services.runtimes.contracts import (
        RuntimeDescriptor,
        RuntimeMode,
        TransportKind,
    )

    class Client:
        descriptor = RuntimeDescriptor(
            runtime=RuntimeKind.ART,
            provider="sidecar",
            mode=RuntimeMode.SIDECAR,
            transport=TransportKind.HTTP,
        )

        def cancel(self, request_id):
            raise AssertionError(f"typed cancellation should not use {request_id}")

    with pytest.raises(HTTPException) as rejected:
        cancel_runtime_action(Client(), RuntimeRouteRequest())
    assert rejected.value.status_code == 409


def test_local_timeout_holds_invocation_until_worker_cancel_ack() -> None:
    client = LocalFallbackArtClient(timeout_seconds=0.01, signal_source=object())
    client._timeout_seconds = 0.01
    client.register_request("timeout-request")
    client._headless_art_worker = lambda create=False: object()
    submitted: list[object] = []
    interrupted = threading.Event()

    def emit(_code, payload):
        if "image_request" in payload:
            submitted.append(payload["image_request"])
        elif payload.get("request_id") == "timeout-request":
            interrupted.set()

    client._emit_signal = emit
    request = RequestEnvelope(
        request_id="timeout-request",
        runtime=RuntimeKind.ART,
        action=RuntimeAction.INVOKE,
        payload={"prompt": "timeout barrier fixture"},
    )
    result: list[ResponseEnvelope] = []
    thread = threading.Thread(
        target=lambda: result.append(client.invoke(request))
    )
    thread.start()
    assert interrupted.wait(timeout=2)
    assert thread.is_alive()
    assert len(submitted) == 1

    submitted[0].callback("cancellation acknowledged")
    thread.join(timeout=2)
    assert not thread.is_alive()
    assert result[0].error is not None
    assert result[0].error.code == "art_timeout"
    client.finish_request("timeout-request")


def test_sd_worker_correlates_queued_and_active_cancellation() -> None:
    worker = SDWorker.__new__(SDWorker)
    worker._model_manager_lock = threading.Lock()
    worker._api_art_request_lock = threading.Lock()
    worker._active_api_art_request_id = None
    worker._cancelled_api_art_request_ids = set()
    worker._queued_api_art_request_ids = {"queued"}
    interrupted: list[bool] = []
    worker._model_manager = SimpleNamespace(
        interrupt_image_generation=lambda: interrupted.append(True)
    )

    worker.on_interrupt_image_generation_signal({"request_id": "queued"})
    callbacks: list[str] = []
    request = SimpleNamespace(callback=callbacks.append)
    worker._generate_image_owned = lambda _message: (_ for _ in ()).throw(
        AssertionError("cancelled queued job must not enter generation")
    )
    worker._generate_image({"request_id": "queued", "image_request": request})
    assert callbacks == ["Art generation cancelled"]
    assert interrupted == []

    worker._active_api_art_request_id = "active"
    worker.on_interrupt_image_generation_signal({"request_id": "other"})
    assert interrupted == []
    assert worker._cancelled_api_art_request_ids == set()
    worker.on_interrupt_image_generation_signal({"request_id": "active"})
    assert interrupted == [True]

    callbacks.clear()
    worker._active_api_art_request_id = "loading"
    worker.on_interrupt_image_generation_signal({"request_id": "loading"})
    worker._finalize_do_generate_signal(
        {
            "request_id": "loading",
            "image_request": SimpleNamespace(callback=callbacks.append),
        }
    )
    assert callbacks == ["Art generation cancelled"]

    worker.api = SimpleNamespace(headless=True, daemon_client=None)
    worker.on_interrupt_image_generation_signal({})
    assert interrupted == [True, True, True]


def _queued_api_worker() -> SDWorker:
    worker = SDWorker.__new__(SDWorker)
    worker._queue_lock = threading.Lock()
    worker.queue = queue.Queue()
    worker.items = {}
    worker.current_index = 0
    worker._api_art_request_lock = threading.Lock()
    worker._active_api_art_request_id = None
    worker._cancelled_api_art_request_ids = set()
    worker._queued_api_art_request_ids = set()
    worker.logger = SimpleNamespace(debug=lambda *_args, **_kwargs: None)
    return worker


def test_control_signal_displacement_acknowledges_pending_api_generation() -> None:
    from airunner_common.contract_enums import ModelType
    from airunner_services.workers.sd_worker import ModelAction

    worker = _queued_api_worker()
    callbacks: list[str] = []
    image_request = SimpleNamespace(callback=callbacks.append)
    worker.on_do_generate_signal(
        {"request_id": "pending-api", "image_request": image_request}
    )
    worker.add_to_queue({"action": ModelAction.LOAD, "type": ModelType.SD})

    assert callbacks == ["Image generation superseded before start"]
    assert worker._queued_api_art_request_ids == set()
    queued = worker.get_last_item()
    assert queued["action"] is ModelAction.LOAD


def test_displaced_pending_cancel_is_acknowledged_as_cancelled() -> None:
    from airunner_common.contract_enums import ModelType
    from airunner_services.workers.sd_worker import ModelAction

    worker = _queued_api_worker()
    callbacks: list[str] = []
    worker.on_do_generate_signal(
        {
            "request_id": "cancelled-before-dispatch",
            "image_request": SimpleNamespace(callback=callbacks.append),
        }
    )
    worker.on_interrupt_image_generation_signal(
        {"request_id": "cancelled-before-dispatch"}
    )
    worker.add_to_queue({"action": ModelAction.LOAD, "type": ModelType.SD})

    assert callbacks == ["Art generation cancelled"]
    assert worker._queued_api_art_request_ids == set()
    assert worker._cancelled_api_art_request_ids == set()


def test_concurrent_dequeue_and_displacement_has_one_callback_owner() -> None:
    from airunner_services.workers.sd_worker import ModelAction

    worker = _queued_api_worker()
    callbacks: list[str] = []
    image_request = SimpleNamespace(callback=callbacks.append)
    worker.on_do_generate_signal(
        {"request_id": "racing-api", "image_request": image_request}
    )
    barrier = threading.Barrier(3)
    dequeued: list[object] = []

    def dequeue() -> None:
        barrier.wait()
        dequeued.append(worker.get_last_item())

    def displace() -> None:
        barrier.wait()
        worker.add_to_queue({"action": ModelAction.LOAD})

    dequeue_thread = threading.Thread(target=dequeue)
    displace_thread = threading.Thread(target=displace)
    dequeue_thread.start()
    displace_thread.start()
    barrier.wait()
    dequeue_thread.join(timeout=2)
    displace_thread.join(timeout=2)
    assert not dequeue_thread.is_alive()
    assert not displace_thread.is_alive()

    if (
        dequeued
        and dequeued[0] is not None
        and dequeued[0]["action"] is ModelAction.GENERATE
    ):
        worker._generate_image_owned = lambda message: message[
            "image_request"
        ].callback("generation completed")
        worker._generate_image(dequeued[0]["message"])
        assert callbacks == ["generation completed"]
    else:
        assert callbacks == ["Image generation superseded before start"]


@pytest.mark.parametrize(
    ("worker_result", "expected"),
    [
        ("raise", "Image generation failed"),
        ("return", "Image generation ended without a result"),
    ],
)
def test_sd_worker_always_terminates_correlated_callback_once(
    worker_result: str, expected: str
) -> None:
    worker = SDWorker.__new__(SDWorker)
    worker._api_art_request_lock = threading.Lock()
    worker._active_api_art_request_id = None
    worker._cancelled_api_art_request_ids = set()
    worker._queued_api_art_request_ids = set()
    callbacks: list[str] = []
    request = SimpleNamespace(callback=callbacks.append)

    def generate(_message):
        if worker_result == "raise":
            raise ValueError("private request detail must not escape")
        return None

    worker._generate_image_owned = generate
    worker._generate_image(
        {"request_id": "terminal-request", "image_request": request}
    )
    # A late callback from an asynchronous cleanup path is harmless too.
    request.callback("late result")
    assert callbacks == [expected]
    assert worker._active_api_art_request_id is None


def test_sd_worker_defers_callback_until_generation_cleanup_finishes() -> None:
    worker = SDWorker.__new__(SDWorker)
    worker._api_art_request_lock = threading.Lock()
    worker._active_api_art_request_id = None
    worker._cancelled_api_art_request_ids = set()
    worker._queued_api_art_request_ids = set()
    cleanup_finished = False
    callback_observations: list[tuple[str, bool, bool]] = []

    def callback(result: str) -> None:
        callback_observations.append(
            (
                result,
                cleanup_finished,
                worker._active_api_art_request_id is None,
            )
        )

    request = SimpleNamespace(callback=callback)

    def generate(_message):
        nonlocal cleanup_finished
        request.callback("generated")
        cleanup_finished = True

    worker._generate_image_owned = generate
    worker._generate_image(
        {"request_id": "cleanup-owned", "image_request": request}
    )

    assert callback_observations == [("generated", True, True)]


def test_sidecar_cancel_before_child_id_is_delivered_after_mapping() -> None:
    from airunner_services.runtimes.art_daemon_runtime_settings import (
        ArtDaemonRuntimeSettings,
    )
    from airunner_services.runtimes.contracts import RuntimeHealthStatus
    from airunner_services.runtimes.sidecar_art_client import SidecarArtClient

    class Launcher:
        endpoint = "http://127.0.0.1:8190"
        api_base_url = "http://127.0.0.1:8190/api/v1/art"

        def start(self):
            return None

        def stop(self):
            return None

        def health_status(self):
            return RuntimeHealthStatus.READY, "ready"

    class Response:
        content = b""

        def raise_for_status(self):
            return None

        def json(self):
            return {}

    class Session:
        def __init__(self):
            self.requests = []

        def request(self, method, url, **_kwargs):
            self.requests.append((method, url))
            return Response()

    settings = ArtDaemonRuntimeSettings(
        host="127.0.0.1",
        port=8190,
        base_daemon_config_path=None,
        art_model_path=None,
        art_model_version=None,
        art_scheduler=None,
        startup_timeout_seconds=1,
        request_timeout_seconds=1,
        invocation_timeout_seconds=1,
        status_poll_interval_seconds=0.01,
    )
    client = SidecarArtClient(
        settings=settings, launcher=Launcher(), session=Session()
    )
    requests: list[tuple[str, str]] = []
    client._request = lambda method, path, **_kwargs: requests.append(  # type: ignore[method-assign]
        (method, path)
    )

    client.register_request("parent-request")
    client.cancel("parent-request")
    assert requests == []
    assert client._track_job("parent-request", "child-job") is True
    client._best_effort_cancel("child-job")
    assert requests == [("DELETE", "/cancel/child-job")]
    client._untrack_job("parent-request")
