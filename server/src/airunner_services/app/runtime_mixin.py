"""Lifecycle and knowledge-system helpers for App."""

from __future__ import annotations

import os
import signal
from typing import TYPE_CHECKING, Dict, Optional

from airunner_services.knowledge import get_knowledge_base
from airunner_services.lifecycle_service import CoreLifecycleService
from airunner_services.utils.application.runtime_primitives import (
    QCoreApplication,
)
from airunner_services.settings import AIRUNNER_SERVER_HOST
from airunner_services.settings import AIRUNNER_SERVER_PORT

from airunner_services.app.process_manager_mixin import (
    ProcessManagerMixin,
)
from airunner_services.app.knowledge_migration_mixin import (
    KnowledgeMigrationMixin,
)

if TYPE_CHECKING:
    from airunner_services.api.services.art_services import ARTAPIService
    from airunner_services.api.services.llm_services import LLMAPIService

ARTAPIService = None
LLMAPIService = None


def _get_api_service_classes():
    """Return lazily imported API service classes for service mode."""
    global ARTAPIService
    global LLMAPIService

    if LLMAPIService is None:
        from airunner_services.api.services.llm_services import (
            LLMAPIService as _LLMAPIService,
        )

        LLMAPIService = _LLMAPIService

    if ARTAPIService is None:
        from airunner_services.api.services.art_services import (
            ARTAPIService as _ARTAPIService,
        )

        ARTAPIService = _ARTAPIService

    return LLMAPIService, ARTAPIService


class RuntimeMixin(ProcessManagerMixin, KnowledgeMigrationMixin):
    """Provide bootstrapping and knowledge migration helpers."""

    def _init_service_mode(self) -> None:
        """Initialize service mode."""
        self.logger.info("Running in service mode (no GUI)")
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        self._init_services()
        self.is_running = True

    def _init_services(self):
        """Initialize services for service mode."""
        self.app = QCoreApplication.instance()
        if self.app is None:
            self.app = QCoreApplication([])
        self.app.api = self
        self.logger.info("Qt Core event loop initialized (service mode)")

        self._ensure_api_services()

        if self._initialize_lifecycle:
            self.initialize_lifecycle()

        if not self._start_embedded_api_server:
            self.logger.info(
                "Embedded API server disabled for this App instance"
            )
        elif os.environ.get("AIRUNNER_SERVER_RUNNING") != "1":
            from airunner_services.api.server_thread import (
                APIServerThread,
            )

            host = AIRUNNER_SERVER_HOST
            port = AIRUNNER_SERVER_PORT
            self._kill_process_on_port(port)

            self.logger.info("Starting API server on %s:%s", host, port)
            self.api_server_thread = APIServerThread(
                host=host,
                port=port,
                app_instance=self,
            )
            self.api_server_thread.start()
            self.logger.info(
                "API server started - /health, /llm, /art endpoints "
                "available"
            )
            os.environ["AIRUNNER_SERVER_RUNNING"] = "1"
        else:
            self.logger.info(
                "API server already running - skipping initialization"
            )

    def _ensure_api_services(self) -> None:
        """Attach compatibility API services used by legacy daemon routes."""
        llm_service_class, art_service_class = _get_api_service_classes()

        if getattr(self, "llm", None) is None:
            self.llm = llm_service_class()
        if getattr(self, "art", None) is None:
            self.art = art_service_class()

    def ensure_lifecycle_service(self) -> CoreLifecycleService:
        """Return the reusable lifecycle service for this App."""
        if self.lifecycle_service is None:
            self.lifecycle_service = CoreLifecycleService(
                signal_source=self,
                logger=self.logger,
            )
        return self.lifecycle_service

    def initialize_lifecycle(self, preload_llm: bool = False) -> None:
        """Initialize service workers and optionally preload the local LLM."""
        lifecycle_service = self.ensure_lifecycle_service()
        lifecycle_service.initialize()
        if preload_llm:
            lifecycle_service.preload_llm_model()

    def _initialize_knowledge_system(self):
        """Initialize the markdown-based knowledge system."""
        if os.environ.get("AIRUNNER_KNOWLEDGE_ON", "1") == "0":
            self.logger.info("Knowledge system disabled")
            return

        try:
            knowledge_base = get_knowledge_base()
            self.logger.info(
                "Knowledge system initialized: %s",
                knowledge_base.knowledge_dir,
            )
            self._run_knowledge_migration_if_needed()
        except Exception as exc:
            self.logger.error(
                "Failed to initialize knowledge system: %s",
                exc,
                exc_info=True,
            )

    def _initialize_workers(self):
        """Initialize essential workers for service mode."""
        try:
            self.ensure_lifecycle_service().initialize()
        except Exception as exc:
            self.logger.error(
                "Failed to initialize service workers: %s",
                exc,
                exc_info=True,
            )

    def _preload_llm_model(self):
        """Pre-load the local LLM from settings if configured."""
        self.ensure_lifecycle_service().preload_llm_model()

    @property
    def rag_manager(self) -> Optional[object]:
        """Return the RAG-capable LLM manager when workers are available."""
        worker = getattr(self, "_llm_generate_worker", None)
        if worker is not None:
            return worker.model_manager
        if hasattr(self, "_worker_manager") and self._worker_manager:
            return self._worker_manager.llm_generate_worker.model_manager
        return None

    def on_rag_load_documents_signal(self, data: Dict) -> None:
        """Forward RAG document loading to the LLM worker."""
        try:
            self.logger.info("RAG_LOAD_DOCUMENTS signal received in App!")
            self.logger.info(
                "DEBUG: Data keys: %s",
                list(data.keys()) if data else "None",
            )

            worker = getattr(self, "_llm_generate_worker", None)
            if worker is not None:
                self.logger.info(
                    "DEBUG: Forwarding to lifecycle LLM worker..."
                )
                worker.on_rag_load_documents_signal(data)
                self.logger.info("Forwarded RAG load signal to LLM worker")
            elif hasattr(self, "_worker_manager") and self._worker_manager:
                self.logger.info("DEBUG: Forwarding to worker manager...")
                self._worker_manager.llm_generate_worker.on_rag_load_documents_signal(
                    data
                )
                self.logger.info("Forwarded RAG load signal to LLM worker")
            else:
                self.logger.warning(
                    "Worker manager not available for RAG loading"
                )
                self.logger.info("ERROR: Worker manager not available")
        except Exception as exc:
            self.logger.error(
                "Error handling RAG load signal: %s",
                exc,
                exc_info=True,
            )
