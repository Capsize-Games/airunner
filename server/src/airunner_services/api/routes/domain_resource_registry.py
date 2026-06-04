"""Resource registry helpers for resource-oriented domain routes."""

from __future__ import annotations

from fastapi import HTTPException

SINGLETON_RESOURCES = {
    "settings": {
        "AIRunnerSettings",
        "ActiveGridSettings",
        "ApplicationSettings",
        "BrushSettings",
        "EspeakSettings",
        "GeneratorSettings",
        "GridSettings",
        "LanguageSettings",
        "LLMGeneratorSettings",
        "MemorySettings",
        "OpenVoiceSettings",
        "PathSettings",
        "RAGSettings",
        "SoundSettings",
        "STTSettings",
        "User",
        "WhisperSettings",
    },
}

LAYER_RESOURCES = {
    "settings": {
        "ControlnetSettings",
        "DrawingPadSettings",
        "ImageToImageSettings",
        "MetadataSettings",
        "OutpaintSettings",
    },
}


def assert_singleton(domain: str, resource: str) -> None:
    """Validate that one resource is registered as a singleton."""
    if resource not in SINGLETON_RESOURCES.get(domain, set()):
        raise HTTPException(status_code=404, detail="Singleton not found")


def assert_layer_resource(domain: str, resource: str) -> None:
    """Validate that one resource is registered as layer-scoped."""
    if resource not in LAYER_RESOURCES.get(domain, set()):
        raise HTTPException(status_code=404, detail="Layer resource not found")