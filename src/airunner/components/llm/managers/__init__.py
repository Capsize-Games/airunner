__all__ = [
    "HuggingFaceLLM",
    "LLMModelManager",
    "LLMRequest",
    "LLMResponse",
    "LLMSettings",
    "TrainingMixin",
    "OpenrouterMistralRequest",
    "FaraModelManager",
    "FaraController",
    "DualLLMRouter",
]


def __getattr__(name):
    if name == "HuggingFaceLLM":
        from airunner.components.llm.managers.huggingface_llm import (
            HuggingFaceLLM,
        )

        return HuggingFaceLLM
    elif name == "LLMModelManager":
        from airunner.components.llm.managers.llm_model_manager import (
            LLMModelManager,
        )

        return LLMModelManager
    elif name == "LLMRequest":
        from airunner.components.llm.managers.llm_request import LLMRequest

        return LLMRequest
    elif name == "LLMResponse":
        from airunner.components.llm.managers.llm_response import LLMResponse

        return LLMResponse
    elif name == "LLMSettings":
        from airunner.components.llm.managers.llm_settings import LLMSettings

        return LLMSettings
    elif name == "TrainingMixin":
        from airunner.components.llm.managers.training_mixin import (
            TrainingMixin,
        )

        return TrainingMixin
    elif name == "OpenrouterMistralRequest":
        from airunner.components.llm.managers.llm_request import (
            OpenrouterMistralRequest,
        )

        return OpenrouterMistralRequest
    elif name == "FaraModelManager":
        from airunner.components.llm.managers.fara_model_manager import (
            FaraModelManager,
        )

        return FaraModelManager
    elif name == "FaraController":
        from airunner.components.llm.managers.fara_controller import (
            FaraController,
        )

        return FaraController
    elif name == "DualLLMRouter":
        from airunner.components.llm.managers.dual_llm_router import (
            DualLLMRouter,
        )

        return DualLLMRouter
    raise AttributeError(f"module {__name__} has no attribute {name}")
