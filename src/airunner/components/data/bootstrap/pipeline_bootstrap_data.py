from airunner.settings import AIRUNNER_ART_ENABLED


art_pipline_data = [
    {
        "pipeline_action": "txt2img",
        "version": "SDXL 1.0",
        "category": "stablediffusion",
        "classname": "diffusers.AutoPipelineForText2Image",
        "default": False,
    },
    {
        "pipeline_action": "outpaint",
        "version": "SDXL 1.0",
        "category": "stablediffusion",
        "classname": "diffusers.StableDiffusionXLInpaintPipeline",
        "default": False,
    },
    {
        "pipeline_action": "outpaint",
        "version": "SDXL 1.0",
        "category": "controlnet",
        "classname": "diffusers.StableDiffusionXLControlNetInpaintPipeline",
        "default": False,
    },
    {
        "pipeline_action": "txt2img",
        "version": "SDXL Turbo",
        "category": "stablediffusion",
        "classname": "diffusers.AutoPipelineForText2Image",
        "default": False,
    },
    {
        "pipeline_action": "img2img",
        "version": "SDXL 1.0",
        "category": "stablediffusion",
        "classname": "diffusers.AutoPipelineForImage2Image",
        "default": False,
    },
    {
        "pipeline_action": "text_encoder",
        "version": "SDXL 1.0",
        "category": "stablediffusion",
        "classname": "transformers.CLIPTextModel",
        "default": False,
    },
    {
        "pipeline_action": "upscaler",
        "version": "x4-upscaler",
        "category": "stablediffusion",
        "classname": "transformers.CLIPTextModel",
        "default": False,
    },
    {
        "pipeline_action": "txt2img",
        "version": "Flux.1 S",
        "category": "flux",
        "classname": "transformers.AutoFeatureExtractor",
        "default": False,
    },
    {
        "pipeline_action": "txt2img",
        "version": "Z-Image Turbo",
        "category": "zimage",
        "classname": "diffusers.ZImagePipeline",
        "default": False,
    },
    {
        "pipeline_action": "txt2img",
        "version": "Z-Image Base",
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
