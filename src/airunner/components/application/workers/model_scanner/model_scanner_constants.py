from airunner.enums import ImageGenerator, StableDiffusionVersion


# Mapping from version names to ImageGenerator categories
VERSION_TO_CATEGORY: dict[str, str] = {
    StableDiffusionVersion.Z_IMAGE_TURBO.value: ImageGenerator.ZIMAGE.value,
    StableDiffusionVersion.SDXL1_0.value: ImageGenerator.STABLEDIFFUSION.value,
    StableDiffusionVersion.SDXL_TURBO.value: ImageGenerator.STABLEDIFFUSION.value,
    StableDiffusionVersion.SDXL_LIGHTNING.value: ImageGenerator.STABLEDIFFUSION.value,
    StableDiffusionVersion.SDXL_HYPER.value: ImageGenerator.STABLEDIFFUSION.value,
    StableDiffusionVersion.X4_UPSCALER.value: ImageGenerator.STABLEDIFFUSION.value,
}

SUPPORTED_ZIMAGE_VERSIONS = {StableDiffusionVersion.Z_IMAGE_TURBO.value}

# Valid model file extensions
MODEL_EXTENSIONS = (".ckpt", ".safetensors", ".gguf")

# Folders that indicate a diffusers model directory
DIFFUSERS_REQUIRED_FOLDERS = ("scheduler", "text_encoder", "tokenizer", "unet", "vae")

# Folders to skip during scanning
SKIP_FOLDERS = ("controlnet_processors",)