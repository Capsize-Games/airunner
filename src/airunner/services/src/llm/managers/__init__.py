__all__ = [
    "LLMModelManager",
    "LLMRequest",
    "LLMResponse",
    "LLMSettings",
    "OpenrouterMistralRequest",
]


def __getattr__(name):
    if name == "LLMModelManager":
        from airunner_services.llm.managers.llm_model_manager import (
            LLMModelManager,
        )

        return LLMModelManager
    if name == "LLMRequest":
        from airunner_services.llm.managers.llm_request import LLMRequest

        return LLMRequest
    if name == "LLMResponse":
        from airunner_services.llm.managers.llm_response import LLMResponse

        return LLMResponse
    if name == "LLMSettings":
        from airunner_services.llm.managers.llm_settings import LLMSettings

        return LLMSettings
    if name == "OpenrouterMistralRequest":
        from airunner_services.llm.managers.llm_request import (
            OpenrouterMistralRequest,
        )

        return OpenrouterMistralRequest
    raise AttributeError(f"module {__name__} has no attribute {name}")
