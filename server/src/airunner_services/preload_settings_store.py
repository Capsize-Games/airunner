"""Service-owned persistence helpers for headless LLM preload settings."""

from __future__ import annotations

import os
from typing import Any, Callable, Optional

from airunner_services.database.models.ai_models import AIModels
from airunner_services.database.models.llm_generator_settings import (
    LLMGeneratorSettings,
)
from airunner_services.database.session import session_scope
from airunner_services.contract_enums import ModelService
from airunner_services.settings import AIRUNNER_DEFAULT_LLM_HF_PATH
from airunner_services.utils.application.log_hygiene import fingerprint_value

SessionFactory = Callable[[], Any]


class LLMPreloadSettingsStore:
    """Resolve and persist the model path used for daemon preload."""

    def __init__(
        self,
        logger: Optional[Any] = None,
        session_factory: SessionFactory = session_scope,
    ) -> None:
        """Initialize one store for daemon preload settings access."""
        self.logger = logger
        self._session_factory = session_factory

    def resolve_model_path(self) -> Optional[str]:
        """Return the configured preload path, creating defaults as needed."""
        with self._session_factory() as session:
            return self._resolve_model_path(session)

    def _resolve_model_path(self, session: Any) -> Optional[str]:
        """Resolve one preload path from CLI, persisted settings, or defaults."""
        llm_settings = session.query(LLMGeneratorSettings).first()
        cli_model_path = os.environ.get("AIRUNNER_LLM_MODEL_PATH")
        if cli_model_path:
            self._log_info("Using CLI-provided model path for preload")
            return self._store_model_path(session, llm_settings, cli_model_path)
        if llm_settings and llm_settings.model_path:
            return llm_settings.model_path
        return self._create_default_settings(session)

    def _store_model_path(
        self,
        session: Any,
        llm_settings: Optional[LLMGeneratorSettings],
        model_path: str,
    ) -> str:
        """Persist one resolved model path into generator settings."""
        self._log_debug(
            "Persisting preload path (%s)",
            fingerprint_value(model_path, label="model_path"),
        )
        settings_row = llm_settings or LLMGeneratorSettings()
        if llm_settings is None:
            session.add(settings_row)
        settings_row.model_path = model_path
        settings_row.model_service = ModelService.LOCAL.value
        session.commit()
        return model_path

    def _create_default_settings(self, session: Any) -> Optional[str]:
        """Create one default settings row when a fallback path exists."""
        default_model_path = self._default_model_path(session)
        if not default_model_path:
            return None
        self._log_info("No LLM settings row; creating default preload settings")
        return self._store_model_path(session, None, default_model_path)

    def _default_model_path(self, session: Any) -> Optional[str]:
        """Resolve a fallback preload path from env or enabled AI models."""
        default_model_path = (
            os.environ.get("AIRUNNER_DEFAULT_LLM_HF_PATH")
            or AIRUNNER_DEFAULT_LLM_HF_PATH
        )
        if default_model_path:
            return default_model_path
        aimodel = self._first_enabled_llm_model(session)
        if aimodel and aimodel.path:
            self._log_info(
                "No env default model set; using enabled AIModels entry"
            )
            self._log_debug(
                "AIModels preload path (%s)",
                fingerprint_value(aimodel.path, label="model_path"),
            )
            return aimodel.path
        return None

    def _first_enabled_llm_model(self, session: Any) -> Optional[AIModels]:
        """Return the highest-priority enabled local LLM model, if any."""
        try:
            return (
                session.query(AIModels)
                .filter(AIModels.model_type == "llm")
                .filter(AIModels.enabled.is_(True))
                .order_by(AIModels.is_default.desc())
                .first()
            )
        except Exception:
            return None

    def _log_info(self, message: str, *args: Any) -> None:
        """Log one info message when the injected logger supports it."""
        info = getattr(self.logger, "info", None)
        if callable(info):
            info(message, *args)

    def _log_debug(self, message: str, *args: Any) -> None:
        """Log one debug message when the injected logger supports it."""
        debug = getattr(self.logger, "debug", None)
        if callable(debug):
            debug(message, *args)