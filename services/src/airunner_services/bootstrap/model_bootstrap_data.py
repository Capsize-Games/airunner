"""Service-owned bootstrap metadata for built-in model records."""

from airunner_common.settings import AIRUNNER_ART_ENABLED


ai_art_models = [
    {
        "name": "Z-Image Turbo",
        "path": "Tongyi-MAI/Z-Image-Turbo",
        "branch": "main",
        "version": "Z-Image Turbo",
        "category": "zimage",
        "pipeline_action": "txt2img",
        "enabled": True,
        "model_type": "art",
        "is_default": True,
    },
]

llm_models = [
    {
        "name": "Qwen3.5 9B",
        "path": "Qwen/Qwen3.5-9B",
        "branch": "main",
        "version": "3.5",
        "category": "llm",
        "pipeline_action": "causallm",
        "enabled": True,
        "model_type": "llm",
        "is_default": True,
    },
    {
        "name": "GPT-OSS 20B",
        "path": "openai/gpt-oss-20b",
        "branch": "main",
        "version": "20B",
        "category": "llm",
        "pipeline_action": "causallm",
        "enabled": True,
        "model_type": "llm",
        "is_default": False,
    },
    {
        "name": "Intfloat E5 Large",
        "path": "intfloat/e5-large",
        "branch": "main",
        "version": "llm",
        "category": "llm",
        "pipeline_action": "embedding",
        "enabled": True,
        "model_type": "llm",
        "is_default": True,
    },
]

if AIRUNNER_ART_ENABLED:
    model_bootstrap_data = ai_art_models + llm_models
else:
    model_bootstrap_data = llm_models


__all__ = ["ai_art_models", "llm_models", "model_bootstrap_data"]