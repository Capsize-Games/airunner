model_bootstrap_data = [
    {
        "name": "Shap-e",
        "path": "openai/shap-e-img2img",
        "branch": "fp16",
        "version": "SD 1.5",
        "category": "shapegif",
        "pipeline_action": "img2img",
        "enabled": True
    },
    {
        "name": "Stable Diffusion 2.1 512",
        "path": "stabilityai/stable-diffusion-2",
        "branch": "fp16",
        "version": "SD 2.1",
        "category": "stablediffusion",
        "pipeline_action": "txt2img",
        "enabled": True
    },
    {
        "name": "Stable Diffusion 2.1 768",
        "path": "stabilityai/stable-diffusion-2-1",
        "branch": "fp16",
        "version": "SD 2.1",
        "category": "stablediffusion",
        "pipeline_action": "txt2img",
        "enabled": True
    },
    {
        "name": "Stable Diffusion 1.5",
        "path": "runwayml/stable-diffusion-v1-5",
        "branch": "fp16",
        "version": "SD 1.5",
        "category": "stablediffusion",
        "pipeline_action": "txt2img",
        "enabled": True
    },
    {
        "name": "Stable Diffusion XL Base 1.0",
        "path": "stabilityai/stable-diffusion-xl-base-1.0",
        "branch": "fp16",
        "version": "SDXL 1.0",
        "category": "stablediffusion",
        "pipeline_action": "txt2img",
        "enabled": True
    },
    {
        "name": "Kandinsky 2.1",
        "path": "kandinsky-community/kandinsky-2-1",
        "branch": "fp16",
        "version": "K 2.1",
        "category": "kandinsky",
        "pipeline_action": "txt2img",
        "enabled": True
    },
    {
        "name": "Shap-e",
        "path": "openai/shap-e",
        "branch": "fp16",
        "version": "SD 1.5",
        "category": "shapegif",
        "pipeline_action": "txt2img",
        "enabled": True
    },
    {
        "name": "Stable Diffusion Inpaint 2",
        "path": "stabilityai/stable-diffusion-2-inpainting",
        "branch": "fp16",
        "version": "SD 2.1",
        "category": "stablediffusion",
        "pipeline_action": "outpaint",
        "enabled": True
    },
    {
        "name": "Stable Diffusion Inpaint 1.5",
        "path": "runwayml/stable-diffusion-inpainting",
        "branch": "fp16",
        "version": "SD 1.5",
        "category": "stablediffusion",
        "pipeline_action": "outpaint",
        "enabled": True
    },
    {
        "name": "Kandinsky Inpaint 2.1",
        "path": "kandinsky-community/kandinsky-2-1-inpaint",
        "branch": "fp16",
        "version": "K 2.1",
        "category": "kandinsky",
        "pipeline_action": "outpaint",
        "enabled": True
    },
    {
        "name": "Stable Diffusion Depth2Img",
        "path": "stabilityai/stable-diffusion-2-depth",
        "branch": "fp16",
        "version": "SD 2.1",
        "category": "stablediffusion",
        "pipeline_action": "depth2img",
        "enabled": True
    },
    {
        "name": "Stable Diffusion 1.5",
        "path": "runwayml/stable-diffusion-v1-5",
        "branch": "fp16",
        "version": "SD 1.5",
        "category": "stablediffusion",
        "pipeline_action": "controlnet",
        "enabled": True
    },
    {
        "name": "Stability AI 4x resolution",
        "path": "stabilityai/stable-diffusion-x4-upscaler",
        "branch": "fp16",
        "version": "SD 1.5",
        "category": "stablediffusion",
        "pipeline_action": "superresolution",
        "enabled": True
    },
    {
        "name": "Instruct pix2pix",
        "path": "timbrooks/instruct-pix2pix",
        "branch": "fp16",
        "version": "SD 1.5",
        "category": "stablediffusion",
        "pipeline_action": "pix2pix",
        "enabled": True
    },
    {
        "name": "SD Image Variations",
        "path": "lambdalabs/sd-image-variations-diffusers",
        "branch": "v2.0",
        "version": "SD 1.5",
        "category": "stablediffusion",
        "pipeline_action": "vid2vid",
        "enabled": True
    },
    {
        "name": "sd-x2-latent-upscaler",
        "path": "stabilityai/sd-x2-latent-upscaler",
        "branch": "fp16",
        "version": "SD 1.5",
        "category": "stablediffusion",
        "pipeline_action": "upscale",
        "enabled": True
    },
    {
        "name": "CompVis Safety Checker",
        "path": "CompVis/stable-diffusion-safety-checker",
        "branch": "fp16",
        "version": "SD 1.5",
        "category": "stablediffusion",
        "pipeline_action": "safety_checker",
        "enabled": True
    },
    {
        "name": "CompVis Safety Checker",
        "path": "CompVis/stable-diffusion-safety-checker",
        "branch": "fp16",
        "version": "SD 1.5",
        "category": "stablediffusion",
        "pipeline_action": "safety_checker",
        "enabled": True
    },
    {
        "name": "CompVis Safety Checker",
        "path": "CompVis/stable-diffusion-safety-checker",
        "branch": "fp16",
        "version": "SD 2.1",
        "category": "stablediffusion",
        "pipeline_action": "safety_checker",
        "enabled": True
    },
    {
        "name": "OpenAI Text Encoder",
        "path": "openai/clip-vit-large-patch14",
        "branch": "fp16",
        "version": "SD 1.5",
        "category": "stablediffusion",
        "pipeline_action": "text_encoder",
        "enabled": True
    },
    {
        "name": "Inpaint vae",
        "path": "cross-attention/asymmetric-autoencoder-kl-x-1-5",
        "branch": "fp16",
        "version": "SD 1.5",
        "category": "stablediffusion",
        "pipeline_action": "inpaint_vae",
        "enabled": True
    },
    {
        "name": "Flan T5 Small",
        "path": "google/flan-t5-small",
        "branch": "fp16",
        "version": "1",
        "category": "llm",
        "pipeline_action": "seq2seq",
        "enabled": True
    },
    {
        "name": "Flan T5 Large",
        "path": "google/flan-t5-large",
        "branch": "fp16",
        "version": "1",
        "category": "llm",
        "pipeline_action": "seq2seq",
        "enabled": True
    },
    {
        "name": "Flan T5 XL",
        "path": "google/flan-t5-xl",
        "branch": "fp16",
        "version": "1",
        "category": "llm",
        "pipeline_action": "seq2seq",
        "enabled": True
    },
    {
        "name": "Flan T5 XXL",
        "path": "google/flan-t5-xxl",
        "branch": "fp16",
        "version": "1",
        "category": "llm",
        "pipeline_action": "seq2seq",
        "enabled": True
    },
    {
        "name": "Flan T5 UL",
        "path": "google/flan-t5-ul",
        "branch": "fp16",
        "version": "1",
        "category": "llm",
        "pipeline_action": "seq2seq",
        "enabled": True
    },
    {
        "name": "Llama 2 7b",
        "path": "~/.airunner/text/models/txt2txt/llama-2-7b",
        "branch": "fp16",
        "version": "2",
        "category": "llm",
        "pipeline_action": "casuallm",
        "enabled": True
    },
    {
        "name": "Llama 2 7b Chat",
        "path": "~/.airunner/text/models/txt2txt/llama-2-7b-chat",
        "branch": "fp16",
        "version": "2",
        "category": "llm",
        "pipeline_action": "casuallm",
        "enabled": True
    }
]