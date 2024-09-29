pipeline_bootstrap_data = [
    {
        "pipeline_action": "safety_checker",
        "version": "SD 1.5",
        "category": "stablediffusion",
        "classname": "diffusers.pipelines.stable_diffusion.StableDiffusionSafetyChecker",
        "default": True
    },
    {
        "pipeline_action": "controlnet",
        "version": "SD 1.5",
        "category": "stablediffusion",
        "classname": "diffusers.ControlNetModel",
        "default": True
    },
    {
        "pipeline_action": "txt2img",
        "version": "SD 1.5",
        "category": "stablediffusion",
        "classname": "diffusers.AutoPipelineForText2Image",
        "default": True
    },
    {
        "pipeline_action": "txt2img",
        "version": "SD 1.5",
        "category": "controlnet",
        "classname": "diffusers.StableDiffusionControlNetPipeline",
        "default": False
    },
    {
        "pipeline_action": "txt2img",
        "version": "SDXL 1.0",
        "category": "stablediffusion",
        "classname": "diffusers.AutoPipelineForText2Image",
        "default": False
    },
    {
        "pipeline_action": "txt2img",
        "version": "SDXL Turbo",
        "category": "stablediffusion",
        "classname": "diffusers.AutoPipelineForText2Image",
        "default": False
    },
    {
        "pipeline_action": "img2img",
        "version": "SD 1.5",
        "category": "stablediffusion",
        "classname": "diffusers.AutoPipelineForImage2Image",
        "default": False
    },
    {
        "pipeline_action": "img2img",
        "version": "SD 1.5",
        "category": "controlnet",
        "classname": "diffusers.StableDiffusionControlNetImg2ImgPipeline",
        "default": False
    },
    {
        "pipeline_action": "img2img",
        "version": "SDXL 1.0",
        "category": "stablediffusion",
        "classname": "diffusers.AutoPipelineForImage2Image",
        "default": False
    },
    {
        "pipeline_action": "outpaint",
        "version": "SD 1.5",
        "category": "stablediffusion",
        "classname": "diffusers.StableDiffusionInpaintPipeline",
        "default": False
    },
    {
        "pipeline_action": "outpaint",
        "version": "SD 1.5",
        "category": "conrolnet",
        "classname": "diffusers.StableDiffusionControlNetInpaintPipeline",
        "default": False
    },
    {
        "pipeline_action": "inpaint_vae",
        "version": "SD 1.5",
        "category": "stablediffusion",
        "classname": "diffusers.AsymmetricAutoencoderKL",
        "default": False
    },
    {
        "pipeline_action": "text_encoder",
        "version": "SD 1.5",
        "category": "stablediffusion",
        "classname": "transformers.CLIPTextModel",
        "default": False
    },
    {
        "pipeline_action": "text_encoder",
        "version": "SDXL 1.0",
        "category": "stablediffusion",
        "classname": "transformers.CLIPTextModel",
        "default": False
    },
    {
        "pipeline_action": "feature_extractor",
        "version": "SD 1.5",
        "category": "stablediffusion",
        "classname": "transformers.AutoFeatureExtractor",
        "default": False
    },
    {
        "pipeline_action": "seq2seq",
        "version": "1",
        "category": "llm",
        "classname": "transformers.AutoModelForSeq2SeqLM",
        "default": False
    },
    {
        "pipeline_action": "causallm",
        "version": "1",
        "category": "llm",
        "classname": "transformers.AutoModelForCausalLM",
        "default": False
    },
    {
        "pipeline_action": "causallm",
        "version": "0.1",
        "category": "llm",
        "classname": "transformers.AutoModelForCausalLM",
        "default": False
    },
    {
        "pipeline_action": "causallm",
        "version": "2",
        "category": "llm",
        "classname": "transformers.AutoModelForCausalLM",
        "default": False
    }
]
