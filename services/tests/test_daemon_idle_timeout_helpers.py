"""Unit tests for the daemon idle-timeout helpers.

_export_idle_timeout_env, _refresh_llm_inactivity, and
_refresh_art_inactivity were extracted to keep
_apply_model_persistence_config within the long-function threshold.
These tests pin the explicit-env precedence and the live refresh
behavior.
"""

import os
from types import SimpleNamespace
from unittest.mock import MagicMock

from airunner_services.daemon import AIRunnerDaemon


def _make_daemon():
    return AIRunnerDaemon.__new__(AIRunnerDaemon)


def test_export_sets_defaults_once(monkeypatch):
    monkeypatch.delenv("AIRUNNER_LLM_INACTIVITY_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("AIRUNNER_ART_INACTIVITY_TIMEOUT_SECONDS", raising=False)
    daemon = _make_daemon()
    daemon._export_idle_timeout_env(600)
    assert os.environ["AIRUNNER_LLM_INACTIVITY_TIMEOUT_SECONDS"] == "600"
    assert os.environ["AIRUNNER_ART_INACTIVITY_TIMEOUT_SECONDS"] == "600"
    assert daemon._explicit_idle_env == {
        "AIRUNNER_LLM_INACTIVITY_TIMEOUT_SECONDS": False,
        "AIRUNNER_ART_INACTIVITY_TIMEOUT_SECONDS": False,
    }


def test_export_preserves_explicit_env(monkeypatch):
    monkeypatch.setenv("AIRUNNER_LLM_INACTIVITY_TIMEOUT_SECONDS", "900")
    monkeypatch.delenv("AIRUNNER_ART_INACTIVITY_TIMEOUT_SECONDS", raising=False)
    daemon = _make_daemon()
    daemon._export_idle_timeout_env(600)
    assert os.environ["AIRUNNER_LLM_INACTIVITY_TIMEOUT_SECONDS"] == "900"
    assert os.environ["AIRUNNER_ART_INACTIVITY_TIMEOUT_SECONDS"] == "600"
    assert (
        daemon._explicit_idle_env[
            "AIRUNNER_LLM_INACTIVITY_TIMEOUT_SECONDS"
        ]
        is True
    )


def test_refresh_llm_skips_explicit(monkeypatch):
    monkeypatch.setenv("AIRUNNER_LLM_INACTIVITY_TIMEOUT_SECONDS", "900")
    worker = SimpleNamespace(_inactivity_timeout=1)
    AIRunnerDaemon._refresh_llm_inactivity(
        worker,
        {"AIRUNNER_LLM_INACTIVITY_TIMEOUT_SECONDS": True},
        600,
    )
    assert worker._inactivity_timeout == 1


def test_refresh_llm_updates_live_worker(monkeypatch):
    monkeypatch.delenv("AIRUNNER_LLM_INACTIVITY_TIMEOUT_SECONDS", raising=False)
    worker = SimpleNamespace(_inactivity_timeout=1)
    AIRunnerDaemon._refresh_llm_inactivity(worker, {}, 600)
    assert worker._inactivity_timeout == 600
    assert os.environ["AIRUNNER_LLM_INACTIVITY_TIMEOUT_SECONDS"] == "600"


def test_refresh_llm_noop_without_worker(monkeypatch):
    monkeypatch.setenv("AIRUNNER_LLM_INACTIVITY_TIMEOUT_SECONDS", "900")
    AIRunnerDaemon._refresh_llm_inactivity(None, {}, 600)
    assert os.environ["AIRUNNER_LLM_INACTIVITY_TIMEOUT_SECONDS"] == "900"


def test_refresh_art_updates_live_manager(monkeypatch):
    monkeypatch.delenv("AIRUNNER_ART_INACTIVITY_TIMEOUT_SECONDS", raising=False)
    manager = SimpleNamespace(_art_inactivity_timeout=1)
    AIRunnerDaemon._refresh_art_inactivity(manager, {}, 450)
    assert manager._art_inactivity_timeout == 450
    assert os.environ["AIRUNNER_ART_INACTIVITY_TIMEOUT_SECONDS"] == "450"


def test_refresh_art_skips_explicit(monkeypatch):
    monkeypatch.setenv("AIRUNNER_ART_INACTIVITY_TIMEOUT_SECONDS", "900")
    manager = SimpleNamespace(_art_inactivity_timeout=1)
    AIRunnerDaemon._refresh_art_inactivity(
        manager,
        {"AIRUNNER_ART_INACTIVITY_TIMEOUT_SECONDS": True},
        450,
    )
    assert manager._art_inactivity_timeout == 1
