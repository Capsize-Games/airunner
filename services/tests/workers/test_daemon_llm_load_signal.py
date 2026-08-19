"""Regression test for daemon-side LLM load-on-demand (issue #140).

Verifies that in the headless daemon process the ``LLM_LOAD_SIGNAL`` emit
performed by ``ensure_llm_model_loaded`` has a registered handler that
dispatches the load through the lifecycle LLM worker, so the 120s poll in
``ensure_llm_model_loaded`` completes instead of timing out with 503.

No real GGUF model is loaded - the worker's ``load()`` is stubbed.
"""

from __future__ import annotations

import os
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from airunner_common.contract_enums import ModelStatus, SignalCode
from airunner_services.lifecycle_service import CoreLifecycleService


class _SignalSource:
    """Minimal signal source mirroring the ServiceApp surface."""

    def __init__(self) -> None:
        from airunner_services.utils.application.signal_mediator import (
            SignalMediator,
        )

        self._mediator = SignalMediator()
        self.logger = None

    def register(self, code, handler) -> None:
        """Register one handler on the shared mediator."""
        self._mediator.register(code, handler)

    def emit_signal(self, code, data=None) -> None:
        """Emit one signal through the shared mediator."""
        self._mediator.emit_signal(code, data)


class _FakeWorker:
    """Stand-in for the lifecycle-owned LLMGenerateWorker."""

    def __init__(self) -> None:
        self.load_calls = 0
        self._status = ModelStatus.UNLOADED

    def load(self) -> None:
        """Record one load dispatch and mark the model loaded."""
        self.load_calls += 1
        self._status = ModelStatus.LOADED


class _FakeWorkerManager:
    """Stand-in for ServiceWorkerManager exposing the LLM worker."""

    def __init__(self, worker: _FakeWorker) -> None:
        self._llm_generate_worker = worker


def _build_lifecycle() -> (
    tuple[CoreLifecycleService, _SignalSource, _FakeWorker]
):
    """Build a lifecycle service with a stubbed worker and signal source."""
    signal_source = _SignalSource()
    worker = _FakeWorker()

    lifecycle = CoreLifecycleService(
        signal_source=signal_source,
        worker_factory=lambda _cls: worker,
    )
    # Patch the default worker-manager factory to expose our fake worker.
    lifecycle._worker_manager_factory = lambda: _FakeWorkerManager(worker)
    lifecycle.initialize()
    return lifecycle, signal_source, worker


def test_llm_load_signal_registered_by_lifecycle_initialize() -> None:
    """Lifecycle initialize() registers an LLM_LOAD_SIGNAL handler."""
    _lifecycle, signal_source, _worker = _build_lifecycle()

    mediator = signal_source._mediator
    signal_key = mediator._find_signal_key(SignalCode.LLM_LOAD_SIGNAL)
    assert signal_key is not None
    assert len(mediator.signals[signal_key]) == 1


def test_llm_load_signal_dispatches_worker_load() -> None:
    """Emitting LLM_LOAD_SIGNAL invokes the worker's load() once."""
    _lifecycle, signal_source, worker = _build_lifecycle()

    assert worker.load_calls == 0
    signal_source.emit_signal(
        SignalCode.LLM_LOAD_SIGNAL,
        {"model_path": "/fake/model.gguf"},
    )
    assert worker.load_calls == 1


def test_ensure_llm_model_loaded_poll_completes_after_signal() -> None:
    """The 120s poll in ensure_llm_model_loaded goes green post-dispatch."""
    from airunner_services.api.routes import legacy_llm_compat

    lifecycle, signal_source, worker = _build_lifecycle()

    class _FakeApp:
        """App surface consumed by ensure_llm_model_loaded."""

        def __init__(self) -> None:
            self.model_load_balancer = None
            self._model_load_balancer = None
            self._worker_manager = _FakeWorkerManager(worker)

        def emit_signal(self, code, data=None) -> None:
            """Forward one emit to the shared signal source."""
            signal_source.emit_signal(code, data)

    fake_app = _FakeApp()

    class _FakeReq:
        """Minimal FastAPI request carrying app state."""

        class _State:
            def __init__(self) -> None:
                self.airunner_app = fake_app
                self.lifecycle_service = lifecycle

        def __init__(self) -> None:
            self.app = type("FakeStarlette", (), {"state": self._State()})()

    req = _FakeReq()

    def _fake_validate() -> tuple[bool, str]:
        return True, "/fake/model.gguf"

    def _loaded_with_status(app, lifecycle=None):
        """Report loaded once the dispatch has flipped worker status."""
        if worker._status in (ModelStatus.LOADED, ModelStatus.READY):
            return True
        return False

    with (
        patch.object(
            legacy_llm_compat,
            "_validate_model_available",
            side_effect=_fake_validate,
        ),
        patch.object(
            legacy_llm_compat,
            "is_llm_model_loaded",
            side_effect=_loaded_with_status,
        ),
        patch.object(legacy_llm_compat, "time") as fake_time,
    ):
        fake_time.time.return_value = 0.0
        result = legacy_llm_compat.ensure_llm_model_loaded(req)

    assert result is fake_app
    assert worker.load_calls == 1
