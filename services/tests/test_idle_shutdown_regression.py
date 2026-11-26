"""Regression tests for daemon idle-unload cold-start and stuck-LOADING.

Covers the root causes where an unused daemon held resources for hours:

- Cold start: a model loaded without a prior request left
  ``_last_request_time`` as None, so ``_check_inactivity`` returned early
  forever and never unloaded.
- Stuck LOADING: ``model_is_loaded`` is False while status is LOADING and
  both managers' ``unload()`` no-op when LOADING, pinning VRAM forever.
- Dead config: ``DaemonConfig`` ``models.timeout_minutes`` had no consumer;
  the daemon now exports it as the default worker timeout.
"""

from __future__ import annotations

import logging
import threading
import time as std_time

import pytest

pytest.importorskip("transformers")

from airunner_common.contract_enums import ModelStatus, ModelType
from airunner_services.runtimes.daemon_config import DaemonConfig
from airunner_services.workers.llm_generate_worker import (
    LLMGenerateWorker,
    time as llm_worker_time,
)
from airunner_services.workers.sd_worker import SDWorker
from airunner_services.workers.sd_worker import time as art_worker_time


class _FakeLLMManager:
    """LLM manager double with status and force-aware unload."""

    def __init__(self, status: ModelStatus = ModelStatus.LOADED) -> None:
        self.model_status = {ModelType.LLM: status}
        self.unload_calls = 0
        self.forced = []

    def unload(self, force: bool = False) -> None:
        self.unload_calls += 1
        self.forced.append(force)
        self.model_status[ModelType.LLM] = ModelStatus.UNLOADED


class _FakeArtManager:
    """Art manager double with loaded flag, status, and force unload."""

    def __init__(
        self,
        loaded: bool = True,
        status: ModelStatus = ModelStatus.LOADED,
    ) -> None:
        self.model_is_loaded = loaded
        self.model_type = ModelType.SD
        self.model_status = {ModelType.SD: status}
        self.unload_calls = 0
        self.forced = []

    def unload(self, force: bool = False) -> None:
        self.unload_calls += 1
        self.forced.append(force)
        self.model_is_loaded = False
        self.model_status[self.model_type] = ModelStatus.UNLOADED


def _freeze_llm_clock(monkeypatch: pytest.MonkeyPatch, now: float):
    fake_now = {"value": now}
    monkeypatch.setattr(llm_worker_time, "time", lambda: fake_now["value"])
    return fake_now


def _freeze_art_clock(monkeypatch: pytest.MonkeyPatch, now: float):
    fake_now = {"value": now}
    monkeypatch.setattr(art_worker_time, "time", lambda: fake_now["value"])
    return fake_now


def _make_llm_worker(status: ModelStatus, timeout: int = 300):
    worker = LLMGenerateWorker.__new__(LLMGenerateWorker)
    worker._model_manager = _FakeLLMManager(status=status)
    worker._auto_unload_enabled = True
    worker._inactivity_timeout = timeout
    worker._last_request_time = None
    worker.logger = logging.getLogger("test-llm-idle-regression")
    return worker


def _make_art_worker(
    loaded: bool, status: ModelStatus, timeout: int = 300
):
    worker = SDWorker.__new__(SDWorker)
    worker._model_manager_lock = threading.Lock()
    worker._model_manager = _FakeArtManager(loaded=loaded, status=status)
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
    worker._art_auto_unload_enabled = True
    worker._art_inactivity_timeout = timeout
    worker.logger = logging.getLogger("test-art-idle-regression")
    return worker


class TestLLMColdStartSeedsClock:
    def test_loaded_with_no_timestamp_seeds_instead_of_unloading(
        self, monkeypatch
    ) -> None:
        worker = _make_llm_worker(ModelStatus.LOADED, timeout=300)
        fake_now = _freeze_llm_clock(monkeypatch, 1000.0)

        worker._check_inactivity()

        assert worker._model_manager.unload_calls == 0
        assert worker._last_request_time == fake_now["value"]

    def test_seeded_clock_unloads_after_timeout(self, monkeypatch) -> None:
        worker = _make_llm_worker(ModelStatus.LOADED, timeout=300)
        fake_now = _freeze_llm_clock(monkeypatch, 1000.0)

        worker._check_inactivity()
        assert worker._model_manager.unload_calls == 0

        fake_now["value"] += 301
        worker.unload_llm = lambda data=None: worker._model_manager.unload()
        worker._check_inactivity()

        assert worker._model_manager.unload_calls == 1
        assert worker._last_request_time is None


class TestLLMStuckLoading:
    def test_loading_with_no_timestamp_seeds(self, monkeypatch) -> None:
        worker = _make_llm_worker(ModelStatus.LOADING, timeout=300)
        fake_now = _freeze_llm_clock(monkeypatch, 1000.0)

        worker._check_inactivity()

        assert worker._model_manager.unload_calls == 0
        assert worker._last_request_time == fake_now["value"]

    def test_loading_past_timeout_forces_unload(self, monkeypatch) -> None:
        worker = _make_llm_worker(ModelStatus.LOADING, timeout=300)
        fake_now = _freeze_llm_clock(monkeypatch, 1000.0)
        worker._last_request_time = fake_now["value"] - 301

        worker._check_inactivity()

        assert worker._model_manager.unload_calls == 1
        assert worker._model_manager.forced == [True]
        assert worker._last_request_time is None

    def test_loading_before_timeout_does_nothing(
        self, monkeypatch
    ) -> None:
        worker = _make_llm_worker(ModelStatus.LOADING, timeout=300)
        fake_now = _freeze_llm_clock(monkeypatch, 1000.0)
        worker._last_request_time = fake_now["value"] - 299

        worker._check_inactivity()

        assert worker._model_manager.unload_calls == 0


class TestArtColdStartSeedsClock:
    def test_loaded_with_no_timestamp_seeds(self, monkeypatch) -> None:
        worker = _make_art_worker(
            loaded=True, status=ModelStatus.LOADED, timeout=300
        )
        fake_now = _freeze_art_clock(monkeypatch, 2000.0)

        worker._check_art_inactivity()

        assert worker._model_manager.unload_calls == 0
        assert worker._last_art_request_time == fake_now["value"]

    def test_loading_past_timeout_forces_unload(
        self, monkeypatch
    ) -> None:
        worker = _make_art_worker(
            loaded=False, status=ModelStatus.LOADING, timeout=300
        )
        fake_now = _freeze_art_clock(monkeypatch, 2000.0)
        worker._last_art_request_time = fake_now["value"] - 301
        manager = worker._model_manager

        worker._check_art_inactivity()

        assert manager.unload_calls == 1
        assert worker._last_art_request_time is None

    def test_loading_before_timeout_does_nothing(
        self, monkeypatch
    ) -> None:
        worker = _make_art_worker(
            loaded=False, status=ModelStatus.LOADING, timeout=300
        )
        fake_now = _freeze_art_clock(monkeypatch, 2000.0)
        worker._last_art_request_time = fake_now["value"] - 299

        worker._check_art_inactivity()

        assert worker._model_manager.unload_calls == 0


class TestDaemonConfigTimeout:
    def test_model_idle_timeout_seconds_reads_config(
        self, tmp_path, monkeypatch
    ) -> None:
        import yaml

        config_path = tmp_path / "daemon.yaml"
        config_path.write_text(
            yaml.safe_dump({"models": {"timeout_minutes": 30}}),
            encoding="utf-8",
        )
        monkeypatch.setenv("AIRUNNER_RUNTIME_ROOT", str(tmp_path))
        monkeypatch.setenv("AIRUNNER_RUNTIME_CONFIG_DIR", str(tmp_path))
        monkeypatch.setenv("AIRUNNER_RUNTIME_LOG_DIR", str(tmp_path))
        monkeypatch.setenv("AIRUNNER_RUNTIME_SOCKET_DIR", str(tmp_path))
        monkeypatch.setenv("AIRUNNER_CACHE_DIR", str(tmp_path))
        monkeypatch.setenv("AIRUNNER_MODEL_DIR", str(tmp_path))

        config = DaemonConfig(config_path)

        assert config.model_idle_timeout_seconds() == 1800

    def test_model_idle_timeout_falls_back_on_bad_value(
        self, tmp_path, monkeypatch
    ) -> None:
        import yaml

        config_path = tmp_path / "daemon-bad.yaml"
        config_path.write_text(
            yaml.safe_dump({"models": {"timeout_minutes": 0}}),
            encoding="utf-8",
        )
        monkeypatch.setenv("AIRUNNER_RUNTIME_ROOT", str(tmp_path))
        monkeypatch.setenv("AIRUNNER_RUNTIME_CONFIG_DIR", str(tmp_path))
        monkeypatch.setenv("AIRUNNER_RUNTIME_LOG_DIR", str(tmp_path))
        monkeypatch.setenv("AIRUNNER_RUNTIME_SOCKET_DIR", str(tmp_path))
        monkeypatch.setenv("AIRUNNER_CACHE_DIR", str(tmp_path))
        monkeypatch.setenv("AIRUNNER_MODEL_DIR", str(tmp_path))

        config = DaemonConfig(config_path)

        assert config.model_idle_timeout_seconds() == 300
