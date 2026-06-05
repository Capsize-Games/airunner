"""Service-owned application shell for daemon execution."""

from __future__ import annotations

from typing import Optional

from airunner_services.startup_env import (
    configure_early_torch_allocator_environment,
)


configure_early_torch_allocator_environment()

from airunner_services.contract_enums import (  # noqa: E402
    EngineResponseCode,
    ModelStatus,
    ModelType,
    SignalCode,
)
from airunner_services.settings import AIRUNNER_LOG_LEVEL  # noqa: E402
from airunner_services.utils.application import get_logger  # noqa: E402
from airunner_services.utils.application.log_hygiene import summarize_text  # noqa: E402
from airunner_services.utils.application.logging_utils import configure_service_logging  # noqa: E402
from airunner_services.utils.application.mediator_mixin import MediatorMixin  # noqa: E402
from airunner_services.utils.application.runtime_primitives import (  # noqa: E402
    QCoreApplication,
)

from airunner_services.app.runtime_mixin import RuntimeMixin  # noqa: E402
from airunner_services.runtimes.bootstrap import build_runtime_registry  # noqa: E402


class ServiceApp(RuntimeMixin, MediatorMixin):
    """Minimal app shell used by service and daemon flows."""

    def __init__(
        self,
        **_: object,
    ) -> None:
        self.signal_handlers = {}
        self._init_attributes()
        super().__init__()
        self.runtime_registry = build_runtime_registry(app_instance=self)

        self._init_service_mode()
        self._initialize_knowledge_system()

    def _init_attributes(self) -> None:
        """Initialize service-owned attributes ."""
        configure_service_logging()
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
        """Emit one worker response for  flows."""
        self.emit_signal(
            SignalCode.ENGINE_RESPONSE_WORKER_RESPONSE_SIGNAL,
            {"code": code, "message": message},
        )

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
        """Release resources owned by the service app shell."""
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
            qt_app = QCoreApplication.instance()
            if qt_app is not None:
                qt_app.quit()
        except Exception:
            pass
