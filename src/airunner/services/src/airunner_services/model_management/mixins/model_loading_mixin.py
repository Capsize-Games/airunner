"""Service adapter for the model-owned loading mixin."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from airunner_model.model_management.mixins.model_loading_mixin import (
    ModelLoadingMixin as _ModelLoadingMixin,
)
from airunner_services.contract_enums import SignalCode


def unload_service_model_for_swap(
    logger: Any,
    emit_signal: Callable[[SignalCode, dict[str, Any]], None],
    model_type: str,
) -> None:
    """Unload one service-managed model for an automatic swap."""
    if model_type == "llm":
        from airunner_services.model_management.llm_model_manager import (
            LLMModelManager,
        )

        LLMModelManager().unload()
        logger.info("LLM unloaded synchronously for auto-swap")
        return
    signal_map = {
        "text_to_image": SignalCode.SD_UNLOAD_SIGNAL,
        "tts": SignalCode.TTS_DISABLE_SIGNAL,
        "stt": SignalCode.STT_DISABLE_SIGNAL,
    }
    signal_code = signal_map.get(model_type)
    if signal_code is None:
        return
    emit_signal(signal_code, {})
    logger.info("%s unload requested for auto-swap", model_type)


class ModelLoadingMixin(_ModelLoadingMixin):
    """Service-specific unload behavior layered on the model mixin."""

    def _unload_model_for_swap(self, model_id: str, model_type: str) -> None:
        """Unload one active model through service-owned coordination."""
        del model_id
        unload_service_model_for_swap(
            self.logger,
            self.signal_mediator.emit,
            model_type,
        )


__all__ = ["ModelLoadingMixin"]