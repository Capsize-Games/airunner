"""Headless lifecycle and knowledge-system helpers for App."""

from __future__ import annotations

import os
import signal
import subprocess
import time
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Optional

from airunner_services.knowledge import get_knowledge_base
from airunner_services.database.models.application_settings import (
    ApplicationSettings,
)
from airunner_services.database.session import session_scope
from airunner_services.lifecycle_service import CoreLifecycleService
from airunner_services.utils.application.runtime_primitives import (
    QCoreApplication,
)
from airunner_services.settings import AIRUNNER_HEADLESS_SERVER_HOST
from airunner_services.settings import AIRUNNER_HEADLESS_SERVER_PORT
from airunner_services.settings import AIRUNNER_USER_DATA_PATH

if TYPE_CHECKING:
    from airunner_services.api.services.art_services import ARTAPIService
    from airunner_services.api.services.llm_services import LLMAPIService

ARTAPIService = None
LLMAPIService = None


def _get_headless_api_service_classes():
    """Return lazily imported API service classes for headless mode."""
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


class HeadlessRuntimeMixin:
    """Provide headless bootstrapping and knowledge migration helpers."""

    def _init_headless_mode(self) -> None:
        """Initialize headless mode."""
        self.logger.info("Running in headless mode (no GUI)")
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        self._init_headless_services()
        self.is_running = True

    def _kill_via_lsof(self, port: int) -> bool:
        """Try to kill a process using lsof."""
        try:
            result = subprocess.run(
                ["lsof", "-ti", f":{port}"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0 or not result.stdout.strip():
                return False

            for pid in result.stdout.strip().split("\n"):
                try:
                    self.logger.info(
                        "Killing process %s using port %s",
                        pid,
                        port,
                    )
                    subprocess.run(
                        ["kill", "-9", pid],
                        timeout=5,
                        check=False,
                    )
                    time.sleep(0.5)
                except Exception as exc:
                    self.logger.warning(
                        "Failed to kill process %s: %s",
                        pid,
                        exc,
                    )
            return True
        except FileNotFoundError:
            return False
        except Exception as exc:
            self.logger.debug(
                "Could not kill process on port %s: %s",
                port,
                exc,
            )
            return False

    def _kill_via_netstat(self, port: int) -> None:
        """Try to kill a process using netstat."""
        try:
            result = subprocess.run(
                ["netstat", "-tlnp"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            for line in result.stdout.split("\n"):
                if f":{port}" not in line or "LISTEN" not in line:
                    continue
                parts = line.split()
                if len(parts) <= 6:
                    continue
                pid_program = parts[6]
                if "/" not in pid_program:
                    continue
                pid = pid_program.split("/")[0]
                try:
                    self.logger.info(
                        "Killing process %s using port %s",
                        pid,
                        port,
                    )
                    subprocess.run(
                        ["kill", "-9", pid],
                        timeout=5,
                        check=False,
                    )
                except Exception as exc:
                    self.logger.warning(
                        "Failed to kill process %s: %s",
                        pid,
                        exc,
                    )
        except Exception as exc:
            self.logger.debug(
                "Could not check for processes on port %s: %s",
                port,
                exc,
            )

    def _kill_process_on_port(self, port: int) -> None:
        """Kill any process using the specified port."""
        if not self._kill_via_lsof(port):
            self._kill_via_netstat(port)

    def _init_headless_services(self):
        """Initialize services for headless mode."""
        self.app = QCoreApplication.instance()
        if self.app is None:
            self.app = QCoreApplication([])
        self.app.api = self
        self.logger.info("Qt Core event loop initialized (headless mode)")

        from airunner_services.api.legacy_server import set_api

        set_api(self)
        self._ensure_headless_api_services()
        self.logger.info("API instance registered globally")

        if self._initialize_headless_lifecycle:
            self.initialize_headless_lifecycle()

        if not self._start_headless_api_server:
            self.logger.info(
                "Embedded headless API server disabled for this App instance"
            )
        elif os.environ.get("AIRUNNER_SERVER_RUNNING") != "1":
            from airunner_services.api.server_thread import (
                APIServerThread,
            )

            host = AIRUNNER_HEADLESS_SERVER_HOST
            port = AIRUNNER_HEADLESS_SERVER_PORT
            self._kill_process_on_port(port)

            self.logger.info("Starting API server on %s:%s", host, port)
            self.api_server_thread = APIServerThread(host=host, port=port)
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

    def _ensure_headless_api_services(self) -> None:
        """Attach compatibility API services used by legacy daemon routes."""
        llm_service_class, art_service_class = (
            _get_headless_api_service_classes()
        )

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

    def initialize_headless_lifecycle(self, preload_llm: bool = True) -> None:
        """Initialize headless workers and optionally preload the local LLM."""
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

    def _initialize_headless_workers(self):
        """Initialize essential workers for headless mode."""
        try:
            self.ensure_lifecycle_service().initialize()
        except Exception as exc:
            self.logger.error(
                "Failed to initialize headless workers: %s",
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
        """Forward RAG document loading to the headless LLM worker."""
        try:
            self.logger.info("✓✓✓ RAG_LOAD_DOCUMENTS signal received in App!")
            self.logger.info(
                "DEBUG: Data keys: %s",
                list(data.keys()) if data else "None",
            )

            worker = getattr(self, "_llm_generate_worker", None)
            if worker is not None:
                self.logger.info("DEBUG: Forwarding to lifecycle LLM worker...")
                worker.on_rag_load_documents_signal(data)
                self.logger.info("✓ Forwarded RAG load signal to LLM worker")
            elif hasattr(self, "_worker_manager") and self._worker_manager:
                self.logger.info("DEBUG: Forwarding to worker manager...")
                self._worker_manager.llm_generate_worker.on_rag_load_documents_signal(
                    data
                )
                self.logger.info("✓ Forwarded RAG load signal to LLM worker")
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

    def _run_knowledge_migration_if_needed(self):
        """Run one-time migration from JSON to markdown if needed."""
        try:
            with session_scope() as session:
                settings = (
                    session.query(ApplicationSettings)
                    .filter_by(id=1)
                    .with_for_update()
                    .first()
                )

                if not settings:
                    self.logger.info("Creating default application settings")
                    settings = ApplicationSettings(
                        id=1,
                        knowledge_migrated=False,
                    )
                    session.add(settings)
                    session.commit()
                    settings = (
                        session.query(ApplicationSettings)
                        .filter_by(id=1)
                        .with_for_update()
                        .first()
                    )

                if settings.knowledge_migrated:
                    self.logger.debug(
                        "Knowledge migration already completed"
                    )
                    return

                knowledge_dir = Path(AIRUNNER_USER_DATA_PATH) / "knowledge"
                json_path = knowledge_dir / "user_facts.json"
                if not json_path.exists():
                    self.logger.info(
                        "No legacy knowledge data found, skipping migration"
                    )
                    settings.knowledge_migrated = True
                    session.commit()
                    return

                self.logger.info(
                    "Running one-time knowledge migration from JSON to "
                    "markdown..."
                )

            self._migrate_json_to_markdown(json_path)
            self._mark_migration_complete()
        except Exception as exc:
            self.logger.error(
                "Failed to run knowledge migration: %s. Migration NOT marked "
                "complete - will retry on next startup.",
                exc,
                exc_info=True,
            )

    def _migrate_json_to_markdown(self, json_path: Path):
        """Migrate legacy JSON facts to the markdown knowledge base."""
        import json

        try:
            with open(json_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)

            knowledge_base = get_knowledge_base()
            migrated = 0
            facts = data if isinstance(data, list) else data.get("facts", [])
            section_map = {
                "identity": "Identity",
                "personal": "Identity",
                "work": "Work & Projects",
                "project": "Work & Projects",
                "hobby": "Interests & Hobbies",
                "interest": "Interests & Hobbies",
                "preference": "Preferences",
                "health": "Health & Wellness",
                "relationship": "Relationships",
                "goal": "Goals",
                "other": "Notes",
                "notes": "Notes",
            }

            for fact_data in facts:
                if isinstance(fact_data, str):
                    fact_text = fact_data
                    category = "Notes"
                elif isinstance(fact_data, dict):
                    fact_text = fact_data.get(
                        "text",
                        fact_data.get("content", ""),
                    )
                    category = fact_data.get("category", "Notes")
                else:
                    continue

                if not fact_text:
                    continue
                section = section_map.get(category.lower(), "Notes")
                knowledge_base.add_fact(fact_text, section=section)
                migrated += 1

            self.logger.info(
                "Knowledge migration successful: %s facts migrated to "
                "markdown",
                migrated,
            )
            backup_path = json_path.with_suffix(".json.migrated")
            json_path.rename(backup_path)
            self.logger.info("Legacy JSON backed up to: %s", backup_path)
        except Exception as exc:
            self.logger.error(
                "Error during JSON to markdown migration: %s",
                exc,
            )
            raise

    def _mark_migration_complete(self):
        """Mark knowledge migration as complete in settings."""
        try:
            with session_scope() as session:
                settings = (
                    session.query(ApplicationSettings).filter_by(id=1).first()
                )
                if settings:
                    settings.knowledge_migrated = True
                    session.commit()
        except Exception as exc:
            self.logger.error(
                "Failed to mark migration complete: %s",
                exc,
                exc_info=True,
            )