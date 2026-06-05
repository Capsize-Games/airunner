"""Reusable lifecycle service for runtime supervision."""

from __future__ import annotations

import os
import time
from typing import Any, Callable, Optional

from airunner_services.contract_enums import ModelStatus, SignalCode
from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger
from airunner_services.utils.application.create_worker import create_worker
from airunner_services.utils.application.log_hygiene import fingerprint_value

from airunner_services.model_management.model_load_balancer import (
    ModelLoadBalancer,
)
from airunner_services.preload_settings_store import (
    LLMPreloadSettingsStore,
)
from airunner_services.service_worker_manager import ServiceWorkerManager

WorkerFactory = Callable[[type[Any]], Any]
WorkerManagerFactory = Callable[[], Any]


class CoreLifecycleService:
    """Manage worker lifecycle for daemon execution."""

    def __init__(
        self,
        signal_source: Any,
        logger: Optional[Any] = None,
        worker_factory: Optional[WorkerFactory] = None,
        worker_manager_factory: Optional[WorkerManagerFactory] = None,
        balancer_class: type[ModelLoadBalancer] = ModelLoadBalancer,
        preload_settings_store: Optional[LLMPreloadSettingsStore] = None,
    ) -> None:
        self.signal_source = signal_source
        self.logger = logger or get_logger(__name__, AIRUNNER_LOG_LEVEL)
        self._worker_factory = worker_factory or create_worker
        self._worker_manager_factory = (
            worker_manager_factory or self._create_worker_manager
        )
        self._balancer_class = balancer_class
        self._preload_settings_store = (
            preload_settings_store
            or LLMPreloadSettingsStore(logger=self.logger)
        )
        self.worker_manager: Optional[Any] = None
        self.model_load_balancer: Optional[ModelLoadBalancer] = None
        self._initialized = False
        self._preloaded_model_path: Optional[str] = None

    def initialize(self) -> None:
        """Initialize workers and shared lifecycle objects."""
        if self._initialized:
            return
        self.worker_manager = self._worker_manager_factory()
        _ = self.llm_generate_worker
        self._register_rag_handler()
        self.model_load_balancer = self._balancer_class(
            self.worker_manager,
            logger=getattr(self.signal_source, "logger", None),
            api=self.signal_source,
        )
        self._attach_state()
        self._initialized = True
        self.logger.info("Lifecycle initialized")

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

    @property
    def llm_generate_worker(self) -> Any:
        """Return the service-owned LLM worker when initialized."""
        if self.worker_manager is None:
            return None
        return getattr(
            self.worker_manager,
            "_llm_generate_worker",
            None,
        ) or getattr(self.worker_manager, "llm_generate_worker", None)

    def sync_selected_conversation(self, conversation_id: int) -> bool:
        """Forward one selected conversation to the service-owned LLM worker."""
        return self._call_llm_worker_handler(
            "on_llm_load_conversation",
            {"conversation_id": conversation_id},
        )

    def sync_deleted_conversation(self, conversation_id: int) -> bool:
        """Forward one deleted conversation to the service-owned LLM worker."""
        return self._call_llm_worker_handler(
            "on_conversation_deleted_signal",
            {"conversation_id": conversation_id},
        )

    def queue_llm_unload(self, source: str = "daemon_admin_unload") -> bool:
        """Queue one LLM unload through lifecycle-owned worker orchestration."""
        worker = self.llm_generate_worker
        if worker is None:
            return False

        payload = {"source": source}
        request_unload = getattr(
            worker, "request_unload_after_interrupt", None
        )
        if callable(request_unload):
            return bool(request_unload(payload))

        return self._interrupt_and_queue_llm_unload(worker, payload)

    def current_llm_model_status(self) -> Any:
        """Return the best known local LLM status from the lifecycle worker."""
        worker = self.llm_generate_worker
        if worker is None:
            return None

        status = self._read_llm_worker_status(worker)
        if status is not None:
            return status

        model_manager = getattr(worker, "_model_manager", None)
        if (
            model_manager is not None
            and getattr(model_manager, "_chat_model", None) is not None
        ):
            return ModelStatus.LOADED
        return None

    def _create_worker_manager(self) -> ServiceWorkerManager:
        """Build the default service-owned worker container."""
        return ServiceWorkerManager(worker_factory=self._worker_factory)

    def _call_llm_worker_handler(
        self,
        handler_name: str,
        payload: dict[str, Any],
    ) -> bool:
        """Call one named handler on the lifecycle-owned LLM worker."""
        worker = self.llm_generate_worker
        handler = getattr(worker, handler_name, None)
        if not callable(handler):
            return False
        handler(payload)
        return True

    def _interrupt_and_queue_llm_unload(
        self,
        worker: Any,
        payload: dict[str, Any],
    ) -> bool:
        """Interrupt one worker request and queue the unload message."""
        interrupt = getattr(worker, "llm_on_interrupt_process_signal", None)
        queue_unload = getattr(worker, "add_to_queue", None)
        if not callable(interrupt) or not callable(queue_unload):
            return False
        interrupt(payload)
        queue_unload({"_message_type": "llm_unload", "data": payload})
        return True

    def _read_llm_worker_status(self, worker: Any) -> Any:
        """Read the worker-reported LLM model status when available."""
        status_getter = getattr(worker, "current_model_status", None)
        if not callable(status_getter):
            return None
        try:
            return status_getter()
        except Exception:
            return None

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
        setattr(
            self.signal_source,
            "_model_load_balancer",
            self.model_load_balancer,
        )
        setattr(
            self.signal_source, "model_load_balancer", self.model_load_balancer
        )
        setattr(
            self.signal_source,
            "_llm_generate_worker",
            self.llm_generate_worker,
        )

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
            from airunner_services.settings import AIRUNNER_DB_URL, DEV_ENV

            self._log_debug(
                "Preload environment diagnostics: db_url_present=%s "
                "DEV_ENV=%s",
                bool(AIRUNNER_DB_URL),
                DEV_ENV,
            )
        except Exception:
            return

    def _resolve_preload_model_path(self) -> Optional[str]:
        """Resolve and persist the model path used for preload."""
        try:
            return self._preload_settings_store.resolve_model_path()
        except Exception as exc:
            self.logger.info("Warning: Could not pre-load model: %s", exc)
            self.logger.info("Model will load on first request")
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

    def _loaded_model_names(self) -> list[str]:
        """Return lifecycle-owned loaded model names for status inspection."""
        if self.worker_manager is not None:
            loaded_model_names = getattr(
                self.worker_manager,
                "loaded_model_names",
                None,
            )
            if callable(loaded_model_names):
                return loaded_model_names()
        if self.model_load_balancer is None:
            return []
        try:
            loaded = self.model_load_balancer.get_loaded_models()
        except Exception:
            return []
        return [model.name for model in loaded]

    def _log_debug(self, message: str, *args: Any) -> None:
        """Log one debug message when the injected logger supports it."""
        debug = getattr(self.logger, "debug", None)
        if callable(debug):
            debug(message, *args)
