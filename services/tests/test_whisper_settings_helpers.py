"""Unit tests for the whisper settings extraction helpers.

_clamped_env_int and _resolve_whisper_model were extracted to keep
resolve_whisper_cpp_runtime_settings within the long-function
threshold. These tests pin the env reading/clamping and the model
path resolution.
"""

from types import SimpleNamespace

import pytest

from airunner_services.runtimes import whisper_cpp_runtime_settings as ws


def test_clamped_env_int_reads_env_value(monkeypatch):
    monkeypatch.setenv("AIRUNNER_TEST_INT", "42")
    assert ws._clamped_env_int("x", "AIRUNNER_TEST_INT", 10, 1, 100) == 42


def test_clamped_env_int_uses_default_when_unset(monkeypatch):
    monkeypatch.delenv("AIRUNNER_TEST_INT_UNSET", raising=False)
    assert ws._clamped_env_int("x", "AIRUNNER_TEST_INT_UNSET", 10, 1, 100) == 10


def test_clamped_env_int_out_of_range_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("AIRUNNER_TEST_INT", "0")
    assert ws._clamped_env_int("x", "AIRUNNER_TEST_INT", 10, 5, 100) == 10
    monkeypatch.setenv("AIRUNNER_TEST_INT", "999")
    assert ws._clamped_env_int("x", "AIRUNNER_TEST_INT", 10, 1, 100) == 10


def test_resolve_model_extracts_id_from_path(monkeypatch):
    monkeypatch.setattr(ws, "_candidate_model_path", lambda b, s: "/m/model.bin")
    path_settings = SimpleNamespace(base_path="/base")
    model_path, model_id, threads = ws._resolve_whisper_model(path_settings)
    assert model_path == "/m/model.bin"
    assert model_id == "model.bin"
    assert 1 <= threads <= 8


def test_resolve_model_none_path_yields_none_id(monkeypatch):
    monkeypatch.setattr(ws, "_candidate_model_path", lambda b, s: None)
    path_settings = SimpleNamespace(base_path="/base")
    model_path, model_id, _ = ws._resolve_whisper_model(path_settings)
    assert model_path is None
    assert model_id is None


def test_resolve_model_uses_base_path_default(monkeypatch):
    seen = {}
    monkeypatch.setattr(
        ws,
        "_candidate_model_path",
        lambda base, settings: seen.setdefault("base", base) and None,
    )
    ws._resolve_whisper_model(SimpleNamespace())
    assert seen["base"] == ws.AIRUNNER_BASE_PATH
