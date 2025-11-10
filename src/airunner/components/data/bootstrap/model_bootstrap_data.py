from airunner.settings import AIRUNNER_ART_ENABLED


ai_art_models = [
    {
        "name": "Flux.1 S",
        "path": "black-forest-labs/FLUX.1-schnell",
        "branch": "main",
        "version": "FLUX",
        "category": "flux",
        "pipeline_action": "txt2img",
        "enabled": True,
        "model_type": "art",
        "is_default": True,
    },
]

llm_models = [
    {
        "name": "Llama 3.1 8B Instruct",
        "path": "meta-llama/Llama-3.1-8B-Instruct",
        "branch": "main",
        "version": "3.1",
        "category": "llm",
        "pipeline_action": "causallm",
        "enabled": True,
        "model_type": "llm",
        "is_default": True,
    },
    {
        "name": "Qwen 2.5 7B Instruct",
        "path": "Qwen/Qwen2.5-7B-Instruct",
        "branch": "main",
        "version": "2.5",
        "category": "llm",
        "pipeline_action": "causallm",
        "enabled": True,
        "model_type": "llm",
        "is_default": False,
    },
    {
        "name": "Command R 8B",
        "path": "CohereForAI/c4ai-command-r-08-2024",
        "branch": "main",
        "version": "08-2024",
        "category": "llm",
        "pipeline_action": "causallm",
        "enabled": True,
        "model_type": "llm",
        "is_default": False,
    },
    {
        "name": "Ministral 8B Instruct",
        "path": "mistralai/Ministral-8B-Instruct-2410",
        "branch": "main",
        "version": "8B-2410",
        "category": "llm",
        "pipeline_action": "causallm",
        "enabled": True,
        "model_type": "llm",
        "is_default": False,
    },
    {
        "name": "Ministral 8B Instruct (Quantized)",
        "path": "w4ffl35/Ministral-8B-Instruct-2410-doublequant",
        "branch": "main",
        "version": "8B-2410-4bit",
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
