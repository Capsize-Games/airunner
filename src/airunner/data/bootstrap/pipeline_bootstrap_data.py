pipeline_bootstrap_data = pipelines = [
    {
        "pipeline_action": "safety_checker",
        "version": "SD 1.5",
        "category": "stablediffusion",
        "classname": "diffusers.pipelines.stable_diffusion.StableDiffusionSafetyChecker",
        "default": True
    },
    {
        "pipeline_action": "safety_checker",
        "version": "SD 2.1",
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
        "singlefile_classname": "diffusers.StableDiffusionPipeline",
        "default": True
    },
    {
        "pipeline_action": "txt2img",
        "version": "SD 1.5",
        "category": "controlnet",
        "classname": "diffusers.StableDiffusionControlNetPipeline"
    },
    {
        "pipeline_action": "txt2img",
        "version": "SD 1.5",
        "category": "shapegif",
        "classname": "diffusers.DiffusionPipeline"
    },
    {
        "pipeline_action": "txt2img",
        "version": "SDXL 1.0",
        "category": "stablediffusion",
        "classname": "diffusers.AutoPipelineForText2Image"
    },
    {
        "pipeline_action": "txt2img",
        "version": "K 2.1",
        "category": "kandinsky",
        "classname": "diffusers.KandinskyPipeline"
    },
    {
        "pipeline_action": "txt2img",
        "version": "SD 2.1",
        "category": "stablediffusion",
        "classname": "diffusers.AutoPipelineForText2Image"
    },
    {
        "pipeline_action": "img2img",
        "version": "SD 1.5",
        "category": "stablediffusion",
        "classname": "diffusers.AutoPipelineForImage2Image",
        "singlefile_classname": "diffusers.StableDiffusionImg2ImgPipeline",
    },
    {
        "pipeline_action": "img2img",
        "version": "SD 1.5",
        "category": "controlnet",
        "classname": "diffusers.StableDiffusionControlNetImg2ImgPipeline",
    },
    {
        "pipeline_action": "img2img",
        "version": "SD 1.5",
        "category": "shapegif",
        "classname": "diffusers.DiffusionPipeline",
    },
    {
        "pipeline_action": "img2img",
        "version": "SD 2.1",
        "category": "stablediffusion",
        "classname": "diffusers.AutoPipelineForImage2Image",
    },
    {
        "pipeline_action": "img2img",
        "version": "K 2.1",
        "category": "kandinsky",
        "classname": "diffusers.KandinskyImg2ImgPipeline",
    },
    {
        "pipeline_action": "img2img",
        "version": "SDXL 1.0",
        "category": "stablediffusion",
        "classname": "diffusers.AutoPipelineForImage2Image",
    },
    {
        "pipeline_action": "pix2pix",
        "version": "SD 1.5",
        "category": "stablediffusion",
        "classname": "diffusers.StableDiffusionInstructPix2PixPipeline",
    },
    {
        "pipeline_action": "outpaint",
        "version": "SD 1.5",
        "category": "stablediffusion",
        "classname": "diffusers.StableDiffusionInpaintPipeline",
        "singlefile_classname": "diffusers.StableDiffusionInpaintPipeline"
    },
    {
        "pipeline_action": "outpaint",
        "version": "SD 1.5",
        "category": "conrolnet",
        "classname": "diffusers.StableDiffusionControlNetInpaintPipeline",
    },
    {
        "pipeline_action": "outpaint",
        "version": "K 2.1",
        "category": "kandinsky",
        "classname": "diffusers.KandinskyInpaintPipeline",
    },
    {
        "pipeline_action": "outpaint",
        "version": "SD 2.1",
        "category": "stablediffusion",
        "classname": "diffusers.AutoPipelineForInpainting",
    },
    {
        "pipeline_action": "inpaint_vae",
        "version": "SD 1.5",
        "category": "stablediffusion",
        "classname": "diffusers.AsymmetricAutoencoderKL",
    },
    {
        "pipeline_action": "inpaint_vae",
        "version": "SD 2.1",
        "category": "stablediffusion",
        "classname": "diffusers.AsymmetricAutoencoderKL",
    },
    {
        "pipeline_action": "depth2img",
        "version": "SD 1.5",
        "category": "stablediffusion",
        "classname": "diffusers.StableDiffusionDepth2ImgPipeline",
    },
    {
        "pipeline_action": "depth2img",
        "version": "SD 2.1",
        "category": "stablediffusion",
        "classname": "diffusers.StableDiffusionDepth2ImgPipeline",
    },
    {
        "pipeline_action": "upscale",
        "version": "SD 1.5",
        "category": "stablediffusion",
        "classname": "diffusers.StableDiffusionLatentUpscalePipeline",
    },
    {
        "pipeline_action": "latent-upscale",
        "version": "SD 1.5",
        "category": "stablediffusion",
        "classname": "diffusers.StableDiffusionLatentUpscalePipeline",
    },
    {
        "pipeline_action": "txt2vid",
        "version": "SD 1.5",
        "category": "stablediffusion",
        "classname": "diffusers.TextToVideoZeroPipeline",
    },
    {
        "pipeline_action": "vid2vid",
        "version": "SD 1.5",
        "category": "stablediffusion",
        "classname": "diffusers.StableDiffusionControlNetPipeline",
    },
    {
        "pipeline_action": "superresolution",
        "version": "SD 1.5",
        "category": "stablediffusion",
        "classname": "diffusers.StableDiffusionUpscalePipeline",
    },
    {
        "pipeline_action": "text_encoder",
        "version": "SD 1.5",
        "category": "stablediffusion",
        "classname": "transformers.CLIPTextModel",
    },
    {
        "pipeline_action": "text_encoder",
        "version": "SD 2.1",
        "category": "stablediffusion",
        "classname": "transformers.CLIPTextModel",
    },
    {
        "pipeline_action": "text_encoder",
        "version": "SDXL 1.0",
        "category": "stablediffusion",
        "classname": "transformers.CLIPTextModel",
    },
    {
        "pipeline_action": "feature_extractor",
        "version": "SD 1.5",
        "category": "stablediffusion",
        "classname": "transformers.AutoFeatureExtractor",
    },
    {
        "pipeline_action": "feature_extractor",
        "version": "SD 2.1",
        "category": "stablediffusion",
        "classname": "transformers.AutoFeatureExtractor",
    },
    {
        "pipeline_action": "seq2seq",
        "version": "1",
        "category": "llm",
        "classname": "transformers.AutoModelForSeq2SeqLM",
    },
    {
        "pipeline_action": "casuallm",
        "version": "1",
        "category": "llm",
        "classname": "transformers.AutoModelForCausalLM",
    },
    {
        "pipeline_action": "casuallm",
        "version": "0.1",
        "category": "llm",
        "classname": "transformers.AutoModelForCausalLM",
    },
    {
        "pipeline_action": "casuallm",
        "version": "2",
        "category": "llm",
        "classname": "transformers.AutoModelForCausalLM",
    }
]