"""Service-owned base class for tool-manager helpers."""

from __future__ import annotations

from typing import Any

from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.database.models.path_settings import PathSettings
from airunner_services.llm_workflow_events import (
    build_llm_tool_action_handler,
)
from airunner_services.llm_workflow_events import (
    resolve_llm_tool_action_handler,
)
from airunner_services.utils.application.get_logger import get_logger
from airunner_services.utils.application.mediator_mixin import MediatorMixin


class BaseTool(MediatorMixin):
    """Provide shared logger, settings, and action-dispatch helpers."""

    def __init__(self, *args, **kwargs):
        tool_action_handler = kwargs.pop("tool_action_handler", None)
        self.signal_handlers = {}
        self.logger = get_logger(self.__class__.__name__, AIRUNNER_LOG_LEVEL)
        self._tool_action_handler = build_llm_tool_action_handler(
            action_handler=tool_action_handler,
        )
        super().__init__(*args, **kwargs)

    def _load_settings(self, model_cls):
        """Load one persisted settings row or a default instance."""
        try:
            settings = model_cls.objects.first()
            if settings is not None:
                return settings
            settings = model_cls.objects.get_or_create()
            if settings is not None:
                return settings
        except Exception as exc:
            self.logger.debug(
                "Falling back to default %s settings: %s",
                model_cls.__name__,
                exc,
            )
        return model_cls()

    @property
    def path_settings(self) -> PathSettings:
        """Return persisted path settings or a default instance."""
        return self._load_settings(PathSettings)

    def dispatch_tool_action(
        self,
        action: str,
        payload: dict[str, Any] | None = None,
    ) -> bool:
        """Send one tool action through the configured handler."""
        return resolve_llm_tool_action_handler(self).handle_action(
            action,
            dict(payload or {}),
        )


__all__ = ["BaseTool"]
