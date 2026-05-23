"""Tests for runtime registry bootstrap wiring."""

from __future__ import annotations

from airunner_model.runtimes.sidecar_art_client import SidecarArtClient
from airunner_model.runtimes.sidecar_llm_client import SidecarLLMClient
from airunner_model.runtimes.sidecar_stt_client import SidecarSTTClient
from airunner_model.runtimes.sidecar_tts_client import SidecarTTSClient
from airunner_services.runtimes.bootstrap import build_runtime_registry
from airunner_services.runtimes.contracts import RuntimeKind


def test_build_runtime_registry_imports_model_sidecar_registrations() -> None:
    register_art = build_runtime_registry.__globals__["register_sidecar_art_client"]
    register_llm = build_runtime_registry.__globals__["register_sidecar_llm_client"]
    register_stt = build_runtime_registry.__globals__["register_sidecar_stt_client"]
    register_tts = build_runtime_registry.__globals__["register_sidecar_tts_client"]

    assert register_art.__module__ == "airunner_model.runtimes.sidecar_art_client"
    assert register_llm.__module__ == "airunner_model.runtimes.sidecar_llm_client"
    assert register_stt.__module__ == "airunner_model.runtimes.sidecar_stt_client"
    assert register_tts.__module__ == "airunner_model.runtimes.sidecar_tts_client"


def test_build_runtime_registry_registers_expected_sidecar_routes(
    monkeypatch,
) -> None:
    monkeypatch.delenv("AIRUNNER_ART_SIDECAR_PROCESS", raising=False)
    monkeypatch.delenv("AIRUNNER_TTS_SIDECAR_PROCESS", raising=False)

    registry = build_runtime_registry()

    assert isinstance(
        registry.resolve(
            RuntimeKind.LLM,
            provider="local",
            deployment_mode="sidecar",
        ),
        SidecarLLMClient,
    )
    assert isinstance(
        registry.resolve(
            RuntimeKind.STT,
            provider="local",
            deployment_mode="sidecar",
        ),
        SidecarSTTClient,
    )
    assert isinstance(
        registry.resolve(
            RuntimeKind.ART,
            provider="local",
            deployment_mode="sidecar",
        ),
        SidecarArtClient,
    )
    assert isinstance(
        registry.resolve(
            RuntimeKind.TTS,
            provider="local",
            deployment_mode="sidecar",
        ),
        SidecarTTSClient,
    )