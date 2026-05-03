"""Tests for thread-safe Melo runtime helpers."""

import os
from types import SimpleNamespace

from airunner.settings import AIRUNNER_BASE_PATH
from airunner.vendor.melo import runtime_support


def test_resolve_tts_model_path_uses_configured_tts_root(monkeypatch):
    monkeypatch.setattr(
        runtime_support,
        "_get_path_settings",
        lambda: SimpleNamespace(tts_model_path="/tmp/tts-models"),
    )

    resolved = runtime_support.resolve_tts_model_path(
        "myshell-ai/MeloTTS-English-v3"
    )

    assert resolved == "/tmp/tts-models/myshell-ai/MeloTTS-English-v3"


def test_resolve_tts_model_path_falls_back_to_default_root(monkeypatch):
    monkeypatch.setattr(runtime_support, "_get_path_settings", lambda: None)

    resolved = runtime_support.resolve_tts_model_path(
        "myshell-ai/MeloTTS-English-v3"
    )

    assert resolved == os.path.join(
        AIRUNNER_BASE_PATH,
        "text/models/tts",
        "myshell-ai/MeloTTS-English-v3",
    )