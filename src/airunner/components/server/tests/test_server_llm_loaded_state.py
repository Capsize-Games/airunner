"""Tests for API server LLM loaded-state detection."""

from types import SimpleNamespace
from unittest.mock import Mock

from airunner.components.server.api import server as server_module
from airunner.components.server.api.server import AIRunnerAPIRequestHandler
from airunner.enums import ModelStatus, ModelType


def _make_handler() -> AIRunnerAPIRequestHandler:
    handler = AIRunnerAPIRequestHandler.__new__(AIRunnerAPIRequestHandler)
    handler.logger = Mock()
    return handler


def test_is_llm_model_loaded_uses_model_load_balancer(monkeypatch):
    api = SimpleNamespace(
        model_load_balancer=SimpleNamespace(
            get_loaded_models=lambda: [ModelType.LLM]
        ),
        _worker_manager=None,
    )

    def fake_get_api(create_if_missing=True):
        del create_if_missing
        return api

    monkeypatch.setattr(server_module, "get_api", fake_get_api)

    assert _make_handler()._is_llm_model_loaded() is True


def test_is_llm_model_loaded_uses_worker_status(monkeypatch):
    worker = SimpleNamespace(
        current_model_status=lambda: ModelStatus.LOADED,
        _model_manager=None,
    )
    api = SimpleNamespace(
        model_load_balancer=None,
        _worker_manager=SimpleNamespace(_llm_generate_worker=worker),
    )

    def fake_get_api(create_if_missing=True):
        del create_if_missing
        return api

    monkeypatch.setattr(server_module, "get_api", fake_get_api)

    assert _make_handler()._is_llm_model_loaded() is True