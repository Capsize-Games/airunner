"""Model registry helpers for daemon-backed persistence routes."""

from __future__ import annotations

from fastapi import HTTPException

from airunner_services.database import models as database_models

DOMAIN_MODELS = {
    "settings": {
        "AIRunnerSettings",
        "ActiveGridSettings",
        "ApplicationSettings",
        "BrushSettings",
        "CanvasLayer",
        "Chatbot",
        "ControlnetSettings",
        "DrawingPadSettings",
        "EspeakSettings",
        "FontSetting",
        "GeneratorSettings",
        "GridSettings",
        "ImageToImageSettings",
        "LanguageSettings",
        "LLMGeneratorSettings",
        "MemorySettings",
        "MetadataSettings",
        "OpenVoiceSettings",
        "OutpaintSettings",
        "PathSettings",
        "PromptTemplate",
        "RAGSettings",
        "SavedPrompt",
        "ShortcutKeys",
        "SoundSettings",
        "STTSettings",
        "TargetDirectories",
        "TargetFiles",
        "User",
        "VoiceSettings",
        "WhisperSettings",
    },
    "catalog": {
        "AIModels",
        "ControlnetModel",
        "Embedding",
        "FineTunedModel",
        "ImageFilter",
        "ImageFilterValue",
        "Lora",
        "PipelineModel",
        "Schedulers",
    },
    "library": {"Document", "ZimFile"},
    "workspace": {
        "AgentConfig",
        "DecisionMemory",
        "LLMTool",
        "ProgressEntry",
        "ProjectFeature",
        "ProjectState",
        "SessionState",
    },
}
MODEL_BY_NAME = {
    model_name: getattr(database_models, model_name)
    for model_names in DOMAIN_MODELS.values()
    for model_name in model_names
}


def model_class(domain: str, model_name: str):
    """Return one registered service model class for a state domain."""
    if model_name not in DOMAIN_MODELS.get(domain, set()):
        raise HTTPException(status_code=404, detail="Model not found")
    model_cls = MODEL_BY_NAME.get(model_name)
    if model_cls is None:
        raise HTTPException(status_code=404, detail="Model not found")
    return model_cls