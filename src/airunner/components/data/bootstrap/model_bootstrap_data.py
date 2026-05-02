from airunner.settings import AIRUNNER_ART_ENABLED


ai_art_models = [
    {
        "name": "Stable Diffusion XL Base 1.0",
        "path": "stabilityai/stable-diffusion-xl-base-1.0",
        "branch": "main",
        "version": "SDXL 1.0",
        "category": "stablediffusion",
        "pipeline_action": "txt2img",
        "enabled": True,
        "model_type": "art",
        "is_default": True,
    },
    {
        "name": "Stable Diffusion XL Turbo",
        "path": "stabilityai/sdxl-turbo",
        "branch": "main",
        "version": "SDXL Turbo",
        "category": "stablediffusion",
        "pipeline_action": "txt2img",
        "enabled": True,
        "model_type": "art",
        "is_default": True,
    },
    {
        "name": "SDXL Inpaint",
        "path": "diffusers/stable-diffusion-xl-1.0-inpainting-0.1",
        "branch": "fp16",
        "version": "SDXL 1.0",
        "category": "stablediffusion",
        "pipeline_action": "inpaint",
        "enabled": True,
        "model_type": "art",
        "is_default": True,
    },
    {
        "name": "Flux.1 S",
        "path": "black-forest-labs/FLUX.1-schnell",
        "branch": "main",
        "version": "Flux.1 S",
        "category": "flux",
        "pipeline_action": "txt2img",
        "enabled": True,
        "model_type": "art",
        "is_default": True,
    },
    {
        "name": "Z-Image Turbo",
        "path": "Tongyi-MAI/Z-Image-Turbo",
        "branch": "main",
        "version": "Z-Image Turbo",
        "category": "zimage",
        "pipeline_action": "txt2img",
        "enabled": True,
        "model_type": "art",
        "is_default": False,
    },
]

llm_models = [
    {
        "name": "Qwen3 8B",
        "path": "Qwen/Qwen3-8B",
        "branch": "main",
        "version": "3.0",
        "category": "llm",
        "pipeline_action": "causallm",
        "enabled": True,
        "model_type": "llm",
        "is_default": True,  # Supports both thinking and instruct modes
    },
    {
        "name": "Qwen3.5 9B",
        "path": "Qwen/Qwen3.5-9B",
        "branch": "main",
        "version": "3.5",
        "category": "llm",
        "pipeline_action": "causallm",
        "enabled": True,
        "model_type": "llm",
        "is_default": False,
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
