"""Service adapter for the model-owned resource manager."""

from __future__ import annotations

from airunner_model.model_management.model_resource_manager import (
    ModelResourceManager as _ModelResourceManager,
)
from airunner_model.model_management.model_resource_manager import ModelState
from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.model_management.mixins.model_loading_mixin import (
    unload_service_model_for_swap,
)
from airunner_services.utils.application import get_logger
from airunner_services.utils.application.signal_mediator import SignalMediator


class ModelResourceManager(_ModelResourceManager):
    """Service-wired resource manager with signal-based unload hooks."""

    def __init__(self) -> None:
        if hasattr(self, "_initialized"):
            return
        self.signal_mediator = SignalMediator()
        super().__init__(
            logger=get_logger(__name__, AIRUNNER_LOG_LEVEL),
            unload_model_callback=self._unload_service_model,
        )

    def _unload_service_model(self, model_id: str, model_type: str) -> None:
        """Unload one model through service-managed side effects."""
        del model_id
        unload_service_model_for_swap(
            self.logger,
            self.signal_mediator.emit,
            model_type,
        )


__all__ = ["ModelResourceManager", "ModelState"]