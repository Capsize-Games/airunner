__all__ = [
    "LLMModelManager",
    "LLMRequest",
    "LLMResponse",
    "LLMSettings",
    "OpenrouterMistralRequest",
    "FaraModelManager",
    "FaraController",
    "DualLLMRouter",
]


def __getattr__(name):
    if name == "LLMModelManager":
        from airunner.components.llm.managers.llm_model_manager import (
            LLMModelManager,
        )

        return LLMModelManager
    if name == "LLMRequest":
        from airunner.components.llm.managers.llm_request import LLMRequest

        return LLMRequest
    if name == "LLMResponse":
        from airunner.components.llm.managers.llm_response import LLMResponse

        return LLMResponse
    if name == "LLMSettings":
        from airunner.components.llm.managers.llm_settings import LLMSettings

        return LLMSettings
    if name == "OpenrouterMistralRequest":
        from airunner.components.llm.managers.llm_request import (
            OpenrouterMistralRequest,
        )

        return OpenrouterMistralRequest
    if name == "FaraModelManager":
        from airunner.components.llm.managers.fara_model_manager import (
            FaraModelManager,
        )

        return FaraModelManager
    if name == "FaraController":
        from airunner.components.llm.managers.fara_controller import (
            FaraController,
        )

        return FaraController
    if name == "DualLLMRouter":
        from airunner.components.llm.managers.dual_llm_router import (
            DualLLMRouter,
        )

        return DualLLMRouter
    raise AttributeError(f"module {__name__} has no attribute {name}")
