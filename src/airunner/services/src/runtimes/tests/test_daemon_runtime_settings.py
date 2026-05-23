"""Tests for model-owned daemon runtime settings."""

from airunner_model.runtimes.art_daemon_runtime_settings import (
    resolve_art_daemon_runtime_settings,
)
from airunner_model.runtimes.tts_daemon_runtime_settings import (
    resolve_tts_daemon_runtime_settings,
)


def test_art_runtime_settings_keep_remote_bind_local_by_default(
    monkeypatch,
) -> None:
    """Art runtime settings should reject remote binds by default."""
    monkeypatch.setenv("AIRUNNER_ART_RUNTIME_HOST", "10.0.0.8")
    monkeypatch.setenv("AIRUNNER_ART_RUNTIME_PORT", "8200")
    monkeypatch.setenv("AIRUNNER_DAEMON_CONFIG", "/tmp/base.yaml")

    settings = resolve_art_daemon_runtime_settings()

    assert settings.host == "127.0.0.1"
    assert settings.port == 8200
    assert settings.base_daemon_config_path == "/tmp/base.yaml"
    assert settings.endpoint == "http://127.0.0.1:8200"


def test_tts_runtime_settings_allow_explicit_remote_bind(
    monkeypatch,
) -> None:
    """TTS runtime settings should allow remote binds only by opt-in."""
    monkeypatch.setenv("AIRUNNER_ALLOW_REMOTE_RUNTIME_BIND", "1")
    monkeypatch.setenv("AIRUNNER_TTS_RUNTIME_HOST", "10.0.0.9")
    monkeypatch.setenv("AIRUNNER_TTS_RUNTIME_PORT", "8201")
    monkeypatch.setenv(
        "AIRUNNER_TTS_RUNTIME_DAEMON_CONFIG",
        "/tmp/tts.yaml",
    )

    settings = resolve_tts_daemon_runtime_settings()

    assert settings.host == "10.0.0.9"
    assert settings.port == 8201
    assert settings.base_daemon_config_path == "/tmp/tts.yaml"
    assert settings.endpoint == "http://10.0.0.9:8201"