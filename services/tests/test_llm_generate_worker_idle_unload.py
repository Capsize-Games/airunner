"""Tests for the env-configurable LLM idle auto-unload (issue #128).

The LAN daemon deployment unloads the local GGUF model after 10 minutes of
inactivity. The worker keeps that behavior opt-in and env-configurable:

- ``AIRUNNER_LLM_AUTO_UNLOAD`` (default "0") turns auto-unload on when "1".
- ``AIRUNNER_LLM_INACTIVITY_TIMEOUT_SECONDS`` (default 300) sets the idle
  timeout in seconds; the daemon deployment sets 600 (10 minutes).
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

# llm_generate_worker imports the LLM runtime stack (transformers et al.),
# which is only present with the llm-native extra. Skip cleanly on the lean
# `development` CI install rather than erroring at collection time.
pytest.importorskip("transformers")

from airunner_common.contract_enums import ModelStatus, ModelType
from airunner_services.utils.application.runtime_primitives import QTimer
from airunner_services.workers.llm_generate_worker import (
    LLMGenerateWorker,
    time as worker_time,
)
from airunner_services.workers.worker import QueueType

_ENV_AUTO_UNLOAD = "AIRUNNER_LLM_AUTO_UNLOAD"
_ENV_TIMEOUT = "AIRUNNER_LLM_INACTIVITY_TIMEOUT_SECONDS"


class _FakeModelManager:
    """Minimal model-manager double with only the status/unload surface."""

    def __init__(self, status: ModelStatus = ModelStatus.LOADED) -> None:
        self.model_status = {ModelType.LLM: status}
        self.unload_calls = 0

    def unload(self) -> None:
        """Record one unload call."""
        self.unload_calls += 1


def _make_worker(
    auto_unload: bool = True,
    timeout: int = 300,
    status: ModelStatus = ModelStatus.LOADED,
) -> LLMGenerateWorker:
    """Return one worker wired to a fake model manager and idle knobs."""
    worker = LLMGenerateWorker()
    worker._model_manager = _FakeModelManager(status=status)
    worker._auto_unload_enabled = auto_unload
    worker._inactivity_timeout = timeout
    return worker


def _freeze_clock(
    monkeypatch: pytest.MonkeyPatch, now: float
) -> dict[str, float]:
    """Replace ``time.time`` in the worker module with a fixed clock."""
    fake_now = {"value": now}
    monkeypatch.setattr(
        worker_time,
        "time",
        lambda: fake_now["value"],
    )
    return fake_now


class TestEnvParsing:
    """The idle knobs read from the environment with safe defaults."""

    def test_unset_env_defaults_to_off_and_300(self, monkeypatch) -> None:
        """Unset vars keep auto-unload off with the 5-minute default."""
        monkeypatch.delenv(_ENV_AUTO_UNLOAD, raising=False)
        monkeypatch.delenv(_ENV_TIMEOUT, raising=False)

        worker = LLMGenerateWorker()

        assert worker._auto_unload_enabled is False
        assert worker._inactivity_timeout == 300

    def test_env_enables_auto_unload_with_600_second_timeout(
        self, monkeypatch
    ) -> None:
        """``AIRUNNER_LLM_AUTO_UNLOAD=1`` + 600s yields on/600."""
        monkeypatch.setenv(_ENV_AUTO_UNLOAD, "1")
        monkeypatch.setenv(_ENV_TIMEOUT, "600")

        worker = LLMGenerateWorker()

        assert worker._auto_unload_enabled is True
        assert worker._inactivity_timeout == 600

    def test_env_zero_keeps_auto_unload_off(self, monkeypatch) -> None:
        """An explicit ``0`` behaves like the default (off)."""
        monkeypatch.setenv(_ENV_AUTO_UNLOAD, "0")
        monkeypatch.delenv(_ENV_TIMEOUT, raising=False)

        worker = LLMGenerateWorker()

        assert worker._auto_unload_enabled is False
        assert worker._inactivity_timeout == 300


class TestInactivityCheck:
    """``_check_inactivity`` unloads exactly at the timeout boundary."""

    def test_unloads_at_exact_timeout_boundary(self, monkeypatch) -> None:
        """inactive_time == timeout fires ``unload_llm()``."""
        worker = _make_worker(auto_unload=True, timeout=600)
        fake_now = _freeze_clock(monkeypatch, 1000.0)
        worker._last_request_time = fake_now["value"] - 600

        worker._check_inactivity()

        assert worker._model_manager.unload_calls == 1
        assert worker._last_request_time is None

    def test_does_not_unload_one_second_before_timeout(
        self, monkeypatch
    ) -> None:
        """inactive_time just below the timeout does not fire."""
        worker = _make_worker(auto_unload=True, timeout=600)
        fake_now = _freeze_clock(monkeypatch, 1000.0)
        worker._last_request_time = fake_now["value"] - 599

        worker._check_inactivity()

        assert worker._model_manager.unload_calls == 0
        assert worker._last_request_time == fake_now["value"] - 599

    def test_skips_when_auto_unload_disabled(self, monkeypatch) -> None:
        """Disabled auto-unload never unloads, even past the timeout."""
        worker = _make_worker(auto_unload=False, timeout=600)
        fake_now = _freeze_clock(monkeypatch, 1000.0)
        worker._last_request_time = fake_now["value"] - 99999

        worker._check_inactivity()

        assert worker._model_manager.unload_calls == 0

    def test_skips_when_no_request_timestamp(self, monkeypatch) -> None:
        """No prior request means nothing to measure inactivity against."""
        worker = _make_worker(auto_unload=True, timeout=600)
        _freeze_clock(monkeypatch, 1000.0)
        worker._last_request_time = None

        worker._check_inactivity()

        assert worker._model_manager.unload_calls == 0

    def test_skips_when_model_not_loaded(self, monkeypatch) -> None:
        """An unloaded model is not auto-unloaded again."""
        worker = _make_worker(
            auto_unload=True,
            timeout=600,
            status=ModelStatus.UNLOADED,
        )
        fake_now = _freeze_clock(monkeypatch, 1000.0)
        worker._last_request_time = fake_now["value"] - 99999

        worker._check_inactivity()

        assert worker._model_manager.unload_calls == 0


class TestActivityTimestamp:
    """Every request that reaches the worker refreshes the idle clock."""

    def test_on_llm_request_signal_refreshes_timestamp(
        self, monkeypatch
    ) -> None:
        """The signal handler resets ``_last_request_time`` per request."""
        fake_now = _freeze_clock(monkeypatch, 1000.0)
        worker = LLMGenerateWorker()

        worker.on_llm_request_signal({"request_data": {}})

        assert worker._last_request_time == fake_now["value"]

    def test_update_activity_timestamp_sets_now(self, monkeypatch) -> None:
        """``_update_activity_timestamp`` records the current time."""
        fake_now = _freeze_clock(monkeypatch, 1234.0)
        worker = LLMGenerateWorker()
        worker._last_request_time = None

        worker._update_activity_timestamp()

        assert worker._last_request_time == fake_now["value"]


class TestTimerStart:
    """The inactivity timer starts when enabled and logs the real timeout."""

    def test_start_inactivity_timer_logs_configured_timeout(
        self, monkeypatch
    ) -> None:
        """The log message reports the configured (not hardcoded) timeout."""
        monkeypatch.setenv(_ENV_AUTO_UNLOAD, "1")
        monkeypatch.setenv(_ENV_TIMEOUT, "600")
        worker = LLMGenerateWorker()
        logger = Mock()
        worker.logger = logger

        worker._start_inactivity_timer()
        try:
            assert isinstance(worker._inactivity_timer, QTimer)
            logged = " ".join(
                str(call) for call in logger.info.call_args_list
            )
            assert "10 minute timeout" in logged
        finally:
            if worker._inactivity_timer is not None:
                worker._inactivity_timer.stop()

    def test_start_worker_thread_starts_timer_when_enabled(
        self, monkeypatch
    ) -> None:
        """The daemon start hook turns the timer on with auto-unload."""
        monkeypatch.setenv(_ENV_AUTO_UNLOAD, "1")
        worker = LLMGenerateWorker()
        worker._load_settings = Mock(
            return_value=SimpleNamespace(llm_enabled=False)
        )
        worker._start_inactivity_timer = Mock(
            wraps=worker._start_inactivity_timer
        )

        worker.start_worker_thread()

        worker._start_inactivity_timer.assert_called_once()

    def test_start_worker_thread_skips_timer_when_disabled(
        self, monkeypatch
    ) -> None:
        """Auto-unload off leaves the timer unstarted."""
        monkeypatch.delenv(_ENV_AUTO_UNLOAD, raising=False)
        worker = LLMGenerateWorker()
        worker._load_settings = Mock(
            return_value=SimpleNamespace(llm_enabled=False)
        )

        worker.start_worker_thread()

        assert worker._inactivity_timer is None


class TestLifecycleWiring:
    """The timer starts through the real daemon bootstrap paths.

    Regression coverage for issue #128 rework: no production code calls
    ``start_worker_thread()`` - ``create_worker`` connects
    ``worker_thread.started`` directly to ``worker.run()``, so the timer must
    start from the worker's own ``run()`` and from
    ``CoreLifecycleService.initialize()``.
    """

    def test_run_starts_inactivity_timer_when_enabled(self, monkeypatch) -> None:
        """``run()`` (the real daemon entry point) starts the timer."""
        monkeypatch.setenv(_ENV_AUTO_UNLOAD, "1")
        worker = LLMGenerateWorker()
        worker.queue_type = QueueType.NONE  # keep run() from looping forever

        worker.run()

        try:
            assert isinstance(worker._inactivity_timer, QTimer)
        finally:
            if worker._inactivity_timer is not None:
                worker._inactivity_timer.stop()

    def test_run_skips_inactivity_timer_when_disabled(self, monkeypatch) -> None:
        """``run()`` leaves the timer unstarted when auto-unload is off."""
        monkeypatch.delenv(_ENV_AUTO_UNLOAD, raising=False)
        worker = LLMGenerateWorker()
        worker.queue_type = QueueType.NONE

        worker.run()

        assert worker._inactivity_timer is None

    def test_start_inactivity_timer_is_idempotent(self, monkeypatch) -> None:
        """A second start keeps the existing timer instead of stacking."""
        monkeypatch.setenv(_ENV_AUTO_UNLOAD, "1")
        worker = LLMGenerateWorker()

        worker._start_inactivity_timer()
        first_timer = worker._inactivity_timer
        try:
            worker._start_inactivity_timer()
            assert worker._inactivity_timer is first_timer
        finally:
            if first_timer is not None:
                first_timer.stop()

    def test_create_worker_bootstrap_starts_inactivity_timer(
        self, monkeypatch
    ) -> None:
        """The real ``create_worker`` bootstrap starts the timer on the worker."""
        from airunner_services.utils.application.create_worker import (
            create_worker,
        )

        monkeypatch.setenv(_ENV_AUTO_UNLOAD, "1")
        worker = create_worker(LLMGenerateWorker)
        try:
            assert isinstance(worker._inactivity_timer, QTimer)
        finally:
            worker._inactivity_timer.stop()

    def test_lifecycle_service_initialize_starts_inactivity_timer(
        self, monkeypatch
    ) -> None:
        """The headless daemon lifecycle starts the timer on its worker."""
        from airunner_services.lifecycle_service import CoreLifecycleService

        monkeypatch.setenv(_ENV_AUTO_UNLOAD, "1")
        lifecycle = CoreLifecycleService(signal_source=SimpleNamespace())
        lifecycle.initialize()
        worker = lifecycle.llm_generate_worker
        try:
            assert worker is not None
            assert isinstance(worker._inactivity_timer, QTimer)
        finally:
            if worker is not None and worker._inactivity_timer is not None:
                worker._inactivity_timer.stop()
