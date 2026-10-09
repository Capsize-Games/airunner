from airunner.enums import ImageGenerator, StableDiffusionVersion


# Mapping from version names to ImageGenerator categories
VERSION_TO_CATEGORY: dict[str, str] = {
    StableDiffusionVersion.Z_IMAGE_TURBO.value: ImageGenerator.ZIMAGE.value,
    StableDiffusionVersion.X4_UPSCALER.value: ImageGenerator.STABLEDIFFUSION.value,
}

SUPPORTED_ZIMAGE_VERSIONS = {StableDiffusionVersion.Z_IMAGE_TURBO.value}

# Valid model file extensions
MODEL_EXTENSIONS = (".ckpt", ".safetensors", ".gguf")

# Folders that indicate a diffusers model directory
DIFFUSERS_REQUIRED_FOLDERS = (
    "scheduler",
    "text_encoder",
    "tokenizer",
    "unet",
    "vae",
)