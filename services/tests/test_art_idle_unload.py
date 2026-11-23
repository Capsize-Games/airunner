"""Tests for the env-configurable art idle auto-unload.

The art worker unloads the Z-Image/SD model after 5 minutes of
inactivity by default:

- ``AIRUNNER_ART_AUTO_UNLOAD`` (default "1") turns auto-unload on.
- ``AIRUNNER_ART_INACTIVITY_TIMEOUT_SECONDS`` (default 300) sets
  the idle timeout in seconds.

Unloading goes through ``unload_model_manager``, whose manager
``unload()`` path aggressively clears RAM and VRAM, so an idle
daemon frees the GPU without a restart.
"""

from __future__ import annotations

import logging
import queue
import threading

import pytest

from airunner_services.workers.sd_worker import SDWorker
from airunner_services.workers.sd_worker import time as worker_time

_ENV_AUTO_UNLOAD = "AIRUNNER_ART_AUTO_UNLOAD"
_ENV_TIMEOUT = "AIRUNNER_ART_INACTIVITY_TIMEOUT_SECONDS"


class _FakeArtManager:
    """Minimal model-manager double with the unload contract."""

    def __init__(self, loaded: bool = True) -> None:
        self.model_is_loaded = loaded
        self.unload_calls = 0

    def unload(self) -> None:
        """Record one unload call (the RAM+VRAM clearing path)."""
        self.unload_calls += 1


def _make_worker(
    auto_unload: bool = True,
    timeout: int = 300,
    loaded: bool = True,
) -> SDWorker:
    """Return one worker double without running the real __init__."""
    worker = SDWorker.__new__(SDWorker)
    worker._model_manager_lock = threading.Lock()
    worker._model_manager = _FakeArtManager(loaded=loaded)
    worker._sd = None
    worker._zimage = None
    worker._x4_upscaler = None
    worker._current_model = None
    worker._current_version = None
    worker._current_pipeline = None
    worker._is_generating = False
    worker._active_api_art_request_id = None
    worker._queued_api_art_request_ids = set()
    worker._last_art_request_time = None
    worker._art_auto_unload_enabled = auto_unload
    worker._art_inactivity_timeout = timeout
    worker._art_inactivity_timer = None
    worker.logger = logging.getLogger("test-art-idle")
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


class TestTimeoutParsing:
    """The idle timeout reads from the environment with safe defaults."""

    def test_unset_env_defaults_to_300(self, monkeypatch) -> None:
        """Unset timeout var parses to the 5-minute default."""
        monkeypatch.delenv(_ENV_TIMEOUT, raising=False)

        assert SDWorker._parse_art_timeout() == 300

    def test_env_override_is_honored(self, monkeypatch) -> None:
        """An explicit timeout value is used as-is."""
        monkeypatch.setenv(_ENV_TIMEOUT, "600")

        assert SDWorker._parse_art_timeout() == 600

    def test_invalid_and_nonpositive_fall_back(self, monkeypatch) -> None:
        """Garbage, zero, and negative values fall back to 300."""
        for bad in ("nope", "0", "-5"):
            monkeypatch.setenv(_ENV_TIMEOUT, bad)

            assert SDWorker._parse_art_timeout() == 300


class TestInactivityCheck:
    """``_check_art_inactivity`` unloads exactly at the timeout."""

    def test_unloads_at_exact_timeout_boundary(
        self, monkeypatch
    ) -> None:
        """inactive_time == timeout unloads and clears the timestamp."""
        worker = _make_worker(auto_unload=True, timeout=300)
        fake_now = _freeze_clock(monkeypatch, 1000.0)
        worker._last_art_request_time = fake_now["value"] - 300
        manager = worker._model_manager

        worker._check_art_inactivity()

        assert manager.unload_calls == 1
        assert worker._model_manager is None
        assert worker._last_art_request_time is None

    def test_does_not_unload_one_second_before_timeout(
        self, monkeypatch
    ) -> None:
        """inactive_time just below the timeout does not fire."""
        worker = _make_worker(auto_unload=True, timeout=300)
        fake_now = _freeze_clock(monkeypatch, 1000.0)
        worker._last_art_request_time = fake_now["value"] - 299

        worker._check_art_inactivity()

        assert worker._model_manager.unload_calls == 0
        assert worker._last_art_request_time == fake_now["value"] - 299

    def test_skips_when_auto_unload_disabled(
        self, monkeypatch
    ) -> None:
        """Disabled auto-unload never unloads, even past the timeout."""
        worker = _make_worker(auto_unload=False, timeout=300)
        fake_now = _freeze_clock(monkeypatch, 1000.0)
        worker._last_art_request_time = fake_now["value"] - 99999

        worker._check_art_inactivity()

        assert worker._model_manager.unload_calls == 0

    def test_skips_when_no_request_timestamp(
        self, monkeypatch
    ) -> None:
        """No prior request means nothing to measure inactivity on."""
        worker = _make_worker(auto_unload=True, timeout=300)
        _freeze_clock(monkeypatch, 1000.0)
        worker._last_art_request_time = None

        worker._check_art_inactivity()

        assert worker._model_manager.unload_calls == 0

    def test_skips_while_generating(self, monkeypatch) -> None:
        """An active generation is never unloaded from under itself."""
        worker = _make_worker(auto_unload=True, timeout=300)
        fake_now = _freeze_clock(monkeypatch, 1000.0)
        worker._last_art_request_time = fake_now["value"] - 99999
        worker._is_generating = True

        worker._check_art_inactivity()

        assert worker._model_manager.unload_calls == 0

    def test_skips_with_active_api_request(
        self, monkeypatch
    ) -> None:
        """A tracked API request counts as activity, not idleness."""
        worker = _make_worker(auto_unload=True, timeout=300)
        fake_now = _freeze_clock(monkeypatch, 1000.0)
        worker._last_art_request_time = fake_now["value"] - 99999
        worker._active_api_art_request_id = "job-1"

        worker._check_art_inactivity()

        assert worker._model_manager.unload_calls == 0

    def test_skips_with_queued_api_request(
        self, monkeypatch
    ) -> None:
        """Queued API work counts as activity, not idleness."""
        worker = _make_worker(auto_unload=True, timeout=300)
        fake_now = _freeze_clock(monkeypatch, 1000.0)
        worker._last_art_request_time = fake_now["value"] - 99999
        worker._queued_api_art_request_ids = {"job-queued"}

        worker._check_art_inactivity()

        assert worker._model_manager.unload_calls == 0
        assert worker._last_art_request_time == fake_now["value"] - 99999

    def test_unloads_at_timeout_with_empty_queue(
        self, monkeypatch
    ) -> None:
        """Empty queue still unloads at the timeout (no deadlock)."""
        worker = _make_worker(auto_unload=True, timeout=300)
        fake_now = _freeze_clock(monkeypatch, 1000.0)
        worker._last_art_request_time = fake_now["value"] - 300
        worker._queued_api_art_request_ids = set()
        manager = worker._model_manager

        worker._check_art_inactivity()

        assert manager.unload_calls == 1
        assert worker._model_manager is None
        assert worker._last_art_request_time is None

    def test_skips_when_no_manager_loaded(
        self, monkeypatch
    ) -> None:
        """An already-unloaded worker is not unloaded again."""
        worker = _make_worker(auto_unload=True, timeout=300)
        fake_now = _freeze_clock(monkeypatch, 1000.0)
        worker._last_art_request_time = fake_now["value"] - 99999
        worker._model_manager = None

        worker._check_art_inactivity()

        assert worker._last_art_request_time == fake_now["value"] - 99999

    def test_skips_when_manager_reports_unloaded(
        self, monkeypatch
    ) -> None:
        """A manager that is already unloaded is left alone."""
        worker = _make_worker(
            auto_unload=True, timeout=300, loaded=False
        )
        fake_now = _freeze_clock(monkeypatch, 1000.0)
        worker._last_art_request_time = fake_now["value"] - 99999

        worker._check_art_inactivity()

        assert worker._model_manager.unload_calls == 0


class TestActivityTimestamp:
    """Art activity refreshes the idle clock."""

    def test_update_activity_timestamp_sets_now(
        self, monkeypatch
    ) -> None:
        """``_update_art_activity_timestamp`` records the time."""
        fake_now = _freeze_clock(monkeypatch, 1234.0)
        worker = _make_worker()
        worker._last_art_request_time = None

        worker._update_art_activity_timestamp()

        assert worker._last_art_request_time == fake_now["value"]

    def test_generate_signal_refreshes_timestamp(
        self, monkeypatch
    ) -> None:
        """Queuing a generation marks the worker as recently used."""
        fake_now = _freeze_clock(monkeypatch, 1000.0)
        worker = _make_worker()
        worker.queue = queue.Queue()
        worker.items = {}
        worker.current_index = 0
        worker._queue_lock = threading.Lock()
        worker._api_art_request_lock = threading.Lock()
        worker._queued_api_art_request_ids = set()
        worker._cancelled_api_art_request_ids = set()
        worker._last_art_request_time = None

        worker.on_do_generate_signal({"request_id": "r1"})

        assert worker._last_art_request_time == fake_now["value"]


class TestTimerStart:
    """The inactivity timer starts when enabled and stays singular."""

    def test_start_timer_is_idempotent(self) -> None:
        """A second start keeps the existing timer instead of stacking."""
        worker = _make_worker(auto_unload=True, timeout=300)

        worker._start_art_inactivity_timer()
        first_timer = worker._art_inactivity_timer
        try:
            worker._start_art_inactivity_timer()
            assert worker._art_inactivity_timer is first_timer
        finally:
            if first_timer is not None:
                first_timer.stop()

    def test_start_timer_skips_when_disabled(self) -> None:
        """Auto-unload off leaves the timer unstarted."""
        worker = _make_worker(auto_unload=False, timeout=300)

        worker._start_art_inactivity_timer()

        assert worker._art_inactivity_timer is None
