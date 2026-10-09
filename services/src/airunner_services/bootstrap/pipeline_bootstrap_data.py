"""Service-owned bootstrap rows for pipeline metadata."""

from airunner_common.settings import AIRUNNER_ART_ENABLED


art_pipline_data = [
    {
        "pipeline_action": "upscaler",
        "version": "x4-upscaler",
        "category": "stablediffusion",
        "classname": "transformers.CLIPTextModel",
        "default": False,
    },
    {
        "pipeline_action": "txt2img",
        "version": "Z-Image Turbo",
        "category": "zimage",
        "classname": "diffusers.ZImagePipeline",
        "default": False,
    },
]

llm_pipeline_data = [
    {
        "pipeline_action": "causallm",
        "version": "1",
        "category": "llm",
        "classname": "transformers.AutoModelForCausalLM",
        "default": False,
    },
    {
        "pipeline_action": "causallm",
        "version": "0.1",
        "category": "llm",
        "classname": "transformers.AutoModelForCausalLM",
        "default": False,
    },
    {
        "pipeline_action": "causallm",
        "version": "2",
        "category": "llm",
        "classname": "transformers.AutoModelForCausalLM",
        "default": False,
    },
]

if AIRUNNER_ART_ENABLED:
    pipeline_bootstrap_data = art_pipline_data + llm_pipeline_data
else:
    pipeline_bootstrap_data = llm_pipeline_data


__all__ = ["pipeline_bootstrap_data"]
