"""Service-owned headless application shell for daemon execution."""

from __future__ import annotations

import os
import signal
from typing import Optional

from airunner_services.startup_env import (
    configure_early_torch_allocator_environment,
)


configure_early_torch_allocator_environment()

from airunner_services.contract_enums import (
    EngineResponseCode,
    ModelStatus,
    ModelType,
    SignalCode,
)
from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger
from airunner_services.utils.application.log_hygiene import summarize_text
from airunner_services.utils.application.logging_utils import configure_headless_logging
from airunner_services.utils.application.mediator_mixin import MediatorMixin
from airunner_services.utils.application.runtime_primitives import (
    QCoreApplication,
)

from airunner_services.app.headless_runtime_mixin import HeadlessRuntimeMixin
from airunner_services.runtimes.bootstrap import build_runtime_registry


class ServiceApp(HeadlessRuntimeMixin, MediatorMixin):
    """Minimal headless app shell used by service and daemon flows."""

    def __init__(
        self,
        *,
        headless: bool = True,
        no_splash: bool = True,
        launcher_splash: object = None,
        launcher_app: object = None,
        start_headless_api_server: bool = True,
        initialize_headless_lifecycle: bool = True,
        **_: object,
    ) -> None:
        if not headless:
            raise ValueError("ServiceApp only supports headless mode.")

        self.headless = True
        self.no_splash = no_splash
        self._launcher_splash = launcher_splash
        self._launcher_app = launcher_app
        self._start_headless_api_server = start_headless_api_server
        self._initialize_headless_lifecycle = initialize_headless_lifecycle
        self.signal_handlers = {}
        self._init_attributes()
        super().__init__()
        self.runtime_registry = build_runtime_registry(app_instance=self)

        if self._should_load_optional_extensions():
            self._load_optional_extensions()

        self._init_headless_mode()
        self._initialize_knowledge_system()

    def _init_attributes(self) -> None:
        """Initialize service-owned attributes for headless execution."""
        configure_headless_logging()
        self.logger = get_logger(__name__, level=AIRUNNER_LOG_LEVEL)
        self.app = None
        self.splash = None
        self.http_server_thread = None
        self.api_server_thread = None
        self.is_running = False
        self.lifecycle_service = None
        self.model_load_balancer = None
        self._worker_manager = None
        self._model_load_balancer = None
        self._llm_generate_worker = None
        self.runtime_registry = None
        self.daemon_client = None
        self.llm = None
        self.art = None
        self.tts = None
        self.stt = None
        self._cleaned_up = False

    def change_model_status(
        self,
        model: ModelType,
        status: ModelStatus,
    ) -> None:
        """Emit one model status change for shared worker code."""
        self.emit_signal(
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
            {"model": model, "status": status},
        )

    def worker_response(
        self,
        code: EngineResponseCode,
        message: object,
    ) -> None:
        """Emit one worker response for headless-compatible flows."""
        self.emit_signal(
            SignalCode.ENGINE_RESPONSE_WORKER_RESPONSE_SIGNAL,
            {"code": code, "message": message},
        )

    @staticmethod
    def _should_load_optional_extensions() -> bool:
        """Return whether this process should scan optional extensions."""
        return os.environ.get("AIRUNNER_ART_SIDECAR_PROCESS") != "1"

    def _load_optional_extensions(self) -> None:
        """Load explicitly enabled extensions from local extension roots."""
        try:
            try:
                from airunner_services.tools import web_tools  # noqa: F401
            except Exception:
                pass

            from airunner_services.extensions_loader import (
                load_extensions,
            )

            stats = load_extensions(force_reload=False)
            if isinstance(stats, dict):
                self.logger.info(
                    "Extensions loaded: loaded=%s failed=%s roots=%s",
                    stats.get("loaded"),
                    stats.get("failed"),
                    stats.get("roots"),
                )
        except Exception as exc:
            try:
                self.logger.debug("Extension loading skipped/failed: %s", exc)
            except Exception:
                pass

    def application_error(
        self,
        exception: Optional[Exception] = None,
        message: Optional[str] = None,
    ) -> None:
        """Emit one application error without requiring the GUI app."""
        if exception is not None:
            try:
                from airunner_services.application_exceptions import (
                    InterruptedException,
                )

                if isinstance(exception, InterruptedException):
                    self.logger.debug(
                        "Ignored InterruptedException in application_error"
                    )
                    return
            except Exception:
                pass
            message = str(exception)

        if (
            isinstance(message, str)
            and message.strip().lower() == "interrupted"
        ):
            self.logger.debug(
                "Ignored Interrupted message in application_error: %s",
                message,
            )
            return

        summary = summarize_text(
            str(message) if message is not None else None,
            label="message",
        )
        self.logger.error(f"Application error emitted ({summary})")
        self.emit_signal(
            SignalCode.APPLICATION_STATUS_ERROR_SIGNAL,
            {"message": message},
        )

    def application_status(self, message: str) -> None:
        """Emit one application status update from shared workers."""
        self.emit_signal(
            SignalCode.APPLICATION_STATUS_INFO_SIGNAL,
            {"message": message},
        )

    def application_settings_changed(
        self,
        setting_name: Optional[str],
        column_name: Optional[str],
        val: object,
    ) -> None:
        """Emit one settings-change notification from shared workers."""
        self.emit_signal(
            SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL,
            {
                "setting_name": setting_name,
                "column_name": column_name,
                "val": val,
            },
        )

    def quit_application(self) -> None:
        """Emit the shared quit signal used by legacy service routes."""
        self.emit_signal(SignalCode.QUIT_APPLICATION, {})

    def cleanup(self) -> None:
        """Release headless resources owned by the service app shell."""
        if self._cleaned_up:
            return

        self._cleaned_up = True
        self.is_running = False
        self.logger.info("Cleaning up ServiceApp resources...")

        try:
            self.emit_signal(SignalCode.QUIT_APPLICATION, {})
        except Exception as exc:
            self.logger.debug("Error emitting quit signal: %s", exc)

        server_thread = getattr(self, "api_server_thread", None)
        stopper = getattr(server_thread, "stop", None)
        if callable(stopper):
            try:
                stopper()
            except Exception as exc:
                self.logger.debug("Error stopping API server thread: %s", exc)

        qt_app = self.app or QCoreApplication.instance()
        if qt_app is not None:
            try:
                qt_app.processEvents()
            except Exception:
                pass

        self.logger.info("ServiceApp cleanup complete")

    @staticmethod
    def signal_handler(_signal: int, _frame: object) -> None:
        """Handle SIGINT and SIGTERM without abrupt process exit."""
        try:
            from airunner_services.api.legacy_server import get_api

            api = get_api(create_if_missing=False)
            if api is not None:
                cleanup = getattr(api, "cleanup", None)
                if callable(cleanup):
                    cleanup()
        except Exception:
            pass

        try:
            qt_app = QCoreApplication.instance()
            if qt_app is not None:
                qt_app.quit()
        except Exception:
            pass
