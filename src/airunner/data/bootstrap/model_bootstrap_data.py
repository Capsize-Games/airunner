model_bootstrap_data = [
    {
        "name": "Stable Diffusion 1.5",
        "path": "",  # runwayml/stable-diffusion-v1-5
        "branch": "fp16",
        "version": "SD 1.5",
        "category": "stablediffusion",
        "pipeline_action": "txt2img",
        "enabled": True,
        "model_type": "art",
        "is_default": True
    },
    {
        "name": "Stable Diffusion XL Base 1.0",
        "path": "sd_xl_base_1.0.safetensors",
        "branch": "fp16",
        "version": "SDXL 1.0",
        "category": "stablediffusion",
        "pipeline_action": "txt2img",
        "enabled": True,
        "model_type": "art",
        "is_default": True
    },
    {
        "name": "Stable Diffusion XL Turbo",
        "path": "sd_xl_turbo_1.0_fp16.safetensors",
        "branch": "fp16",
        "version": "SDXL Turbo",
        "category": "stablediffusion",
        "pipeline_action": "txt2img",
        "enabled": True,
        "model_type": "art",
        "is_default": True
    },
    {
        "name": "Stable Diffusion Inpaint 1.5",
        "path": "runwayml/stable-diffusion-inpainting",
        "branch": "fp16",
        "version": "SD 1.5",
        "category": "stablediffusion",
        "pipeline_action": "inpaint",
        "enabled": True,
        "model_type": "art",
        "is_default": True
    },
    {
        "name": "CompVis Safety Checker",
        "path": "CompVis/stable-diffusion-safety-checker",
        "branch": "fp16",
        "version": "SD 1.5",
        "category": "stablediffusion",
        "pipeline_action": "safety_checker",
        "enabled": True,
        "model_type": "art",
        "is_default": True
    },
    {
        "name": "CompVis Feature Extractor",
        "path": "openai/clip-vit-large-patch14",
        "branch": "main",
        "version": "SD 1.5",
        "category": "stablediffusion",
        "pipeline_action": "feature_extractor",
        "enabled": True,
        "model_type": "art",
        "is_default": True
    },
    {
        "name": "Inpaint vae",
        "path": "cross-attention/asymmetric-autoencoder-kl-x-1-5",
        "branch": "fp16",
        "version": "SD 1.5",
        "category": "stablediffusion",
        "pipeline_action": "inpaint_vae",
        "enabled": True,
        "model_type": "art",
        "is_default": True
    },
    {
        "name": "Flan T5 XL",
        "path": "google/flan-t5-xl",
        "branch": "fp16",
        "version": "1",
        "category": "llm",
        "pipeline_action": "seq2seq",
        "enabled": True,
        "model_type": "llm",
        "is_default": True
    },
    {
        "name": "Llama 3 8b",
        "path": "meta-llama/Meta-Llama-3-8B-Instruct",
        "branch": "main",
        "version": "1",
        "category": "llm",
        "pipeline_action": "causallm",
        "enabled": True,
        "model_type": "llm",
        "is_default": True
    },
    {
        "name": "Llama 2 7b Chat",
        "path": "meta-llama/Llama-3-7b-chat-hf",
        "branch": "main",
        "version": "2",
        "category": "llm",
        "pipeline_action": "causallm",
        "enabled": True,
        "model_type": "llm",
        "is_default": True
    },
    {
        "name": "Mistral 7B Instruct v3",
        "path": "mistralai/Mistral-7B-Instruct-v0.3",
        "branch": "main",
        "version": "0.2",
        "category": "llm",
        "pipeline_action": "causallm",
        "enabled": True,
        "model_type": "llm",
        "is_default": True
    },
    {
        "name": "Salesforce InstructBlip Flan T5 XL",
        "path": "Salesforce/instructblip-flan-t5-xl",
        "branch": "main",
        "version": "1",
        "category": "llm",
        "pipeline_action": "visualqa",
        "enabled": True,
        "model_type": "llm",
        "is_default": True
    },
    {
        "name": "Salesforce Blip2 Opt 2.7b",
        "path": "Salesforce/blip2-opt-2.7b",
        "branch": "main",
        "version": "1",
        "category": "llm",
        "pipeline_action": "visualqa",
        "enabled": True,
        "model_type": "llm",
        "is_default": True
    },
    {
        "name": "stablelm-zephyr-3b",
        "path": "/home/joe/Desktop/LLM/stablelm-zephyr-3b",
        "branch": "main",
        "version": "1",
        "category": "llm",
        "pipeline_action": "causallm",
        "enabled": True,
        "model_type": "llm",
        "is_default": True
    },
]
