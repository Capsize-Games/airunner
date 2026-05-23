"""Tests for legacy-server art loaded-state detection."""

from types import SimpleNamespace
from unittest.mock import Mock

import airunner_services.api.legacy_server as server_module
from airunner_services.api.legacy_server import AIRunnerAPIRequestHandler
from airunner_services.contract_enums import ModelStatus, ModelType


def _make_handler() -> AIRunnerAPIRequestHandler:
    handler = AIRunnerAPIRequestHandler.__new__(AIRunnerAPIRequestHandler)
    handler.logger = Mock()
    return handler


def test_art_model_status_uses_worker_manager_state(monkeypatch):
    manager = SimpleNamespace(
        model_type=ModelType.SD,
        model_status={ModelType.SD: ModelStatus.LOADING},
        sd_is_loading=True,
        model_is_loaded=False,
    )
    api = SimpleNamespace(
        _worker_manager=SimpleNamespace(
            _sd_worker=SimpleNamespace(_model_manager=manager)
        )
    )

    def fake_get_api(create_if_missing=True):
        del create_if_missing
        return api

    monkeypatch.setattr(server_module, "get_api", fake_get_api)

    assert _make_handler()._art_model_status() == "loading"


def test_handle_health_reports_art_model_status(monkeypatch):
    captured = {}
    handler = _make_handler()
    handler._send_json_response = lambda payload: captured.update(payload)
    monkeypatch.setenv("AIRUNNER_SD_ON", "1")
    monkeypatch.setenv("AIRUNNER_LLM_ON", "0")
    monkeypatch.setenv("AIRUNNER_TTS_ON", "0")
    monkeypatch.setenv("AIRUNNER_STT_ON", "0")
    monkeypatch.setattr(
        AIRunnerAPIRequestHandler,
        "_art_model_status",
        lambda self: "loaded",
    )

    handler._handle_health()

    assert captured["art_model_status"] == "loaded"
    assert captured["art_model_loaded"] is True