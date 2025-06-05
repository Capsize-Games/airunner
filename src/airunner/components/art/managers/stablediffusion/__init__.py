__all__ = [
    "CivitAIDownloadWorker",
    "DownloadCivitAI",
    "DownloadHuggingface",
    "DownloadWorker",
    "ImageResponse",
    "PromptWeightBridge",
    "StableDiffusionModelManager",
]


def __getattr__(name):
    if name == "DownloadCivitAI":
        from .download_civitai import DownloadCivitAI

        return DownloadCivitAI
    elif name == "DownloadHuggingface":
        from .download_huggingface import DownloadHuggingface

        return DownloadHuggingface
    elif name == "ImageResponse":
        from .image_response import ImageResponse

        return ImageResponse
    elif name == "PromptWeightBridge":
        from .prompt_weight_bridge import PromptWeightBridge

        return PromptWeightBridge
    elif name == "StableDiffusionModelManager":
        from .stable_diffusion_model_manager import StableDiffusionModelManager

        return StableDiffusionModelManager
    raise AttributeError(f"module {__name__} has no attribute {name}")
