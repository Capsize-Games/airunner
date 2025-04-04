__all__ = [
    "HuggingFaceLLM",
    "LLMModelManager",
    "LLMRequest",
    "LLMResponse",
    "LLMSettings",
    "TrainingMixin",
    "OpenrouterMistralRequest",
]


def __getattr__(name):
    if name == "HuggingFaceLLM":
        from .huggingface_llm import HuggingFaceLLM

        return HuggingFaceLLM
    elif name == "LLMModelManager":
        from .llm_model_manager import LLMModelManager

        return LLMModelManager
    elif name == "LLMRequest":
        from .llm_request import LLMRequest

        return LLMRequest
    elif name == "LLMResponse":
        from .llm_response import LLMResponse

        return LLMResponse
    elif name == "LLMSettings":
        from .llm_settings import LLMSettings

        return LLMSettings
    elif name == "TrainingMixin":
        from .training_mixin import TrainingMixin

        return TrainingMixin
    elif name == "OpenrouterMistralRequest":
        from .llm_request import OpenrouterMistralRequest

        return OpenrouterMistralRequest
    raise AttributeError(f"module {__name__} has no attribute {name}")
