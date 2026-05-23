"""Reusable lifecycle service for headless runtime supervision."""

from __future__ import annotations

import os
import time
from typing import Any, Callable, Optional

from airunner.components.application.gui.windows.main import (
    LLMGeneratorSettings,
    ModelLoadBalancer,
    WorkerManager,
)
from airunner_model.models.ai_models import AIModels
from airunner_model.session import session_scope
from airunner.enums import ModelService, SignalCode
from airunner.settings import AIRUNNER_DEFAULT_LLM_HF_PATH, AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger
from airunner.utils.application.create_worker import create_worker
from airunner.utils.application.log_hygiene import fingerprint_value

WorkerFactory = Callable[[type[Any]], Any]


class CoreLifecycleService:
    """Manage worker lifecycle for headless and daemon execution."""

    def __init__(
        self,
        signal_source: Any,
        logger: Optional[Any] = None,
        worker_factory: Optional[WorkerFactory] = None,
        balancer_class: type[ModelLoadBalancer] = ModelLoadBalancer,
    ) -> None:
        self.signal_source = signal_source
        self.logger = logger or get_logger(__name__, AIRUNNER_LOG_LEVEL)
        self._worker_factory = worker_factory or create_worker
        self._balancer_class = balancer_class
        self.worker_manager: Optional[Any] = None
        self.model_load_balancer: Optional[ModelLoadBalancer] = None
        self._initialized = False
        self._preloaded_model_path: Optional[str] = None

    def initialize(self) -> None:
        """Initialize workers and shared lifecycle objects."""
        if self._initialized:
            return
        self.worker_manager = self._worker_factory(WorkerManager)
        _ = self.worker_manager.llm_generate_worker
        self._register_rag_handler()
        self.model_load_balancer = self._balancer_class(
            self.worker_manager,
            logger=getattr(self.signal_source, "logger", None),
            api=self.signal_source,
        )
        self._attach_state()
        self._initialized = True
        self.logger.info("Headless lifecycle initialized")

    def preload_llm_model(self) -> None:
        """Preload the configured local LLM when enabled."""
        if os.environ.get("AIRUNNER_NO_PRELOAD") == "1":
            self._log_preload_disabled()
            return
        self._log_preload_environment()
        model_path = self._resolve_preload_model_path()
        if not model_path:
            self.logger.info(
                "No LLM model configured - model will load on first request"
            )
            return
        self._emit_llm_load(model_path)

    def get_status(self) -> dict[str, Any]:
        """Return lifecycle status for daemon and API inspection."""
        return {
            "lifecycle_initialized": self._initialized,
            "worker_manager_ready": self.worker_manager is not None,
            "model_load_balancer_ready": self.model_load_balancer is not None,
            "loaded_models": self._loaded_model_names(),
            "runtime_registry_ready": bool(
                getattr(self.signal_source, "runtime_registry", None)
            ),
            "embedded_api_server_running": bool(
                getattr(self.signal_source, "api_server_thread", None)
            ),
            "preloaded_model_path": self._preloaded_model_path,
        }

    def _register_rag_handler(self) -> None:
        """Register RAG signal forwarding when the signal source supports it."""
        register = getattr(self.signal_source, "register", None)
        handler = getattr(
            self.signal_source,
            "on_rag_load_documents_signal",
            None,
        )
        if callable(register) and callable(handler):
            register(SignalCode.RAG_LOAD_DOCUMENTS, handler)

    def _attach_state(self) -> None:
        """Expose lifecycle objects on the signal source for compatibility."""
        setattr(self.signal_source, "_worker_manager", self.worker_manager)
        setattr(self.signal_source, "_model_load_balancer", self.model_load_balancer)
        setattr(self.signal_source, "model_load_balancer", self.model_load_balancer)

    def _log_preload_disabled(self) -> None:
        """Log that model preloading is disabled."""
        self.logger.info(
            "Model preloading disabled (--no-preload flag or "
            "AIRUNNER_NO_PRELOAD=1)"
        )
        self.logger.info("Models will be loaded on first request")

    def _log_preload_environment(self) -> None:
        """Log best-effort preload environment diagnostics."""
        try:
            from airunner.settings import AIRUNNER_DB_URL, DEV_ENV

            self._log_debug(
                "Preload environment diagnostics: db_url_present=%s "
                "DEV_ENV=%s",
                bool(AIRUNNER_DB_URL),
                DEV_ENV,
            )
        except Exception:
            return

    def _resolve_preload_model_path(self) -> Optional[str]:
        """Resolve and persist the model path used for headless preload."""
        try:
            with session_scope() as session:
                llm_settings = session.query(LLMGeneratorSettings).first()
                cli_model_path = os.environ.get("AIRUNNER_LLM_MODEL_PATH")
                if cli_model_path:
                    return self._upsert_cli_model_path(
                        session,
                        llm_settings,
                        cli_model_path,
                    )
                if llm_settings and llm_settings.model_path:
                    return llm_settings.model_path
                return self._create_default_settings(session)
        except Exception as exc:
            self.logger.info("Warning: Could not pre-load model: %s", exc)
            self.logger.info("Model will load on first request")
            return None

    def _upsert_cli_model_path(
        self,
        session: Any,
        llm_settings: Optional[LLMGeneratorSettings],
        cli_model_path: str,
    ) -> str:
        """Persist a CLI-provided model path into settings."""
        self.logger.info("Using CLI-provided model path for preload")
        self._log_debug(
            "CLI preload path (%s)",
            fingerprint_value(cli_model_path, label="model_path"),
        )
        if llm_settings is None:
            llm_settings = LLMGeneratorSettings()
            session.add(llm_settings)
        llm_settings.model_path = cli_model_path
        llm_settings.model_service = ModelService.LOCAL.value
        session.commit()
        return cli_model_path

    def _create_default_settings(self, session: Any) -> Optional[str]:
        """Create a default LLM settings row when a fallback path exists."""
        default_model_path = self._default_model_path(session)
        if not default_model_path:
            return None
        self.logger.info(
            "No LLM settings row; creating default preload settings",
        )
        self._log_debug(
            "Default preload path (%s)",
            fingerprint_value(default_model_path, label="model_path"),
        )
        new_settings = LLMGeneratorSettings()
        new_settings.model_path = default_model_path
        new_settings.model_service = ModelService.LOCAL.value
        session.add(new_settings)
        session.commit()
        return default_model_path

    def _default_model_path(self, session: Any) -> Optional[str]:
        """Resolve the fallback model path from env or installed models."""
        default_model_path = (
            os.environ.get("AIRUNNER_DEFAULT_LLM_HF_PATH")
            or AIRUNNER_DEFAULT_LLM_HF_PATH
        )
        if default_model_path:
            return default_model_path
        try:
            aimodel = (
                session.query(AIModels)
                .filter(AIModels.model_type == "llm")
                .filter(AIModels.enabled.is_(True))
                .order_by(AIModels.is_default.desc())
                .first()
            )
        except Exception:
            return None
        if aimodel and aimodel.path:
            self.logger.info(
                "No env default model set; using enabled AIModels entry",
            )
            self._log_debug(
                "AIModels preload path (%s)",
                fingerprint_value(aimodel.path, label="model_path"),
            )
            return aimodel.path
        return None

    def _emit_llm_load(self, model_path: str) -> None:
        """Emit the preload signal for the resolved model path."""
        self._preloaded_model_path = model_path
        self.logger.info("Pre-loading LLM model")
        self._log_debug(
            "Preload signal path (%s)",
            fingerprint_value(model_path, label="model_path"),
        )
        self.logger.info("This may take 30-60 seconds...")
        self.signal_source.emit_signal(
            SignalCode.LLM_LOAD_SIGNAL,
            {"model_path": model_path},
        )
        time.sleep(5)
        self.logger.info("Model loading initiated in background")

    def _log_debug(self, message: str, *args: Any) -> None:
        """Log one debug message when the injected logger supports it."""
        debug = getattr(self.logger, "debug", None)
        if callable(debug):
            debug(message, *args)

    def _loaded_model_names(self) -> list[str]:
        """Return the currently loaded model names when known."""
        if self.model_load_balancer is None:
            return []
        return [
            getattr(model_type, "name", str(model_type))
            for model_type in self.model_load_balancer.get_loaded_models()
        ]