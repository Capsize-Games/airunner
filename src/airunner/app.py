"""AI Runner GUI application entry point."""
from typing import Dict, List, Optional
import glob
import json
import os
import os.path
from pathlib import Path

from airunner_startup_env import (
    configure_early_torch_allocator_environment,
)


configure_early_torch_allocator_environment()

from PySide6.QtCore import QObject
from PySide6.QtGui import QWindow

from airunner.utils.application import get_logger
from airunner.utils.application.log_hygiene import summarize_text
from airunner.settings import (
    AIRUNNER_LOG_LEVEL,
    AIRUNNER_USER_DATA_PATH,
    LOCAL_SERVER_PORT,
    MATHJAX_VERSION,
)

from airunner.app_mixins import (
    LocalizationMixin,
    UIRuntimeMixin,
)
from airunner.enums import (
    
    ModelStatus,
    ModelType,
    SignalCode,
)
from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.components.application.gui.windows.main.settings_mixin import (
    SettingsMixin,
)
from airunner.components.server.local_http_server import LocalHttpServerThread
from airunner.daemon_client import GuiDaemonClient
from airunner.components.knowledge import get_knowledge_base
from airunner.daemon_client.resource_store import get_resource_store


# Enable LNA mode for local server if AIRUNNER_LNA_ENABLED=1
LNA_ENABLED = os.environ.get("AIRUNNER_LNA_ENABLED", "0") == "1"


def _assert_test_gui_launch_allowed() -> None:
    """Block real GUI startup while automated tests are running."""
    if os.environ.get("AIRUNNER_ALLOW_GUI_TEST_LAUNCH") == "1":
        return
    if os.environ.get("AIRUNNER_TEST_NO_GUI_LAUNCH") != "1":
        return
    raise RuntimeError(
        "GUI AIRunner startup is disabled during automated tests."
    )


class App(
    LocalizationMixin,
    UIRuntimeMixin,
    MediatorMixin,
    SettingsMixin,
    QObject,
):
    """
    The main application class for AI Runner.
    GUI-only application that communicates with backend services
    via a daemon client.
    """

    def __init__(
        self,
        no_splash: bool = False,
        main_window_class: Optional[QWindow] = None,
        window_class_params: Optional[Dict] = None,
        launcher_splash=None,
        launcher_app=None,
    ):
        """Initialize the application.

        Args:
            no_splash: Skip splash screen display
            main_window_class: Custom main window class
            window_class_params: Parameters for main window
            launcher_splash: Splash screen passed from launcher
            launcher_app: QApplication passed from launcher
        """
        _assert_test_gui_launch_allowed()
        self._launcher_splash = launcher_splash
        self._launcher_app = launcher_app
        self._init_attributes(
            no_splash, main_window_class, window_class_params
        )
        super().__init__()
        self.daemon_client = None
        self.daemon_client = GuiDaemonClient()
        self._init_api_bridge()
        self._register_signals()
        self._ensure_mathjax()
        self._init_gui_mode()
        self._initialize_knowledge_system()

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

    def application_error(
        self,
        exception: Optional[Exception] = None,
        message: Optional[str] = None,
    ) -> None:
        """Emit one application error without requiring the API wrapper."""
        if exception is not None:
            try:
                from airunner.components.application.exceptions import (
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

    # ------------------------------------------------------------------
    # Knowledge system
    # ------------------------------------------------------------------

    @property
    def _resource_store(self):
        return get_resource_store()

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

    def _run_knowledge_migration_if_needed(self):
        """Run one-time migration from JSON to markdown if needed."""
        try:
            settings = self._resource_store.get_singleton(
                "ApplicationSettings",
                create_if_missing=True,
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
                self._resource_store.update_singleton(
                    "ApplicationSettings",
                    {"knowledge_migrated": True},
                )
                return

            self.logger.info(
                "Running one-time knowledge migration from JSON to "
                "markdown..."
            )

            self._migrate_json_to_markdown(json_path)
            self._mark_migration_complete()
        except Exception as exc:
            self.logger.error(
                "Failed to run knowledge migration: %s. Migration NOT "
                "marked complete - will retry on next startup.",
                exc,
                exc_info=True,
            )

    def _migrate_json_to_markdown(self, json_path: Path):
        """Migrate legacy JSON facts to the markdown knowledge base."""
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
            self._resource_store.update_singleton(
                "ApplicationSettings",
                {"knowledge_migrated": True},
            )
        except Exception as exc:
            self.logger.error(
                "Failed to mark migration complete: %s",
                exc,
                exc_info=True,
            )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def static_dir(self) -> str:
        """Get the static directory path.

        Uses user data directory for writable static files (like MathJax),
        falls back to package directory for bundled static assets.
        """
        base_path = os.environ.get(
            "AIRUNNER_DATA_DIR",
            os.path.join(
                os.path.expanduser("~"), ".local", "share", "airunner"
            ),
        )
        user_static = os.path.join(base_path, "static")

        pkg_static = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "static")
        )

        if os.path.isdir(user_static):
            return user_static
        return pkg_static

    @property
    def _package_static_dir(self) -> str:
        """Get the package's bundled static directory (read-only)."""
        return os.path.abspath(
            os.path.join(os.path.dirname(__file__), "static")
        )

    @property
    def static_search_dirs(self) -> List[str]:
        """Get the list of static search directories."""
        components_static_dirs = glob.glob(
            os.path.join(
                os.path.dirname(__file__),
                "components", "**", "gui", "static",
            ),
            recursive=True,
        )
        static_search_dirs = [self.static_dir]
        if self._package_static_dir != self.static_dir:
            static_search_dirs.append(self._package_static_dir)
        static_search_dirs.extend(components_static_dirs)
        if os.path.isdir(self.user_web_dir):
            static_search_dirs.append(self.user_web_dir)
        return static_search_dirs

    @property
    def sounddevice_manager(self):
        """Return the shared sound-device manager."""
        if self._sounddevice_manager is None:
            from airunner.utils.audio.sound_device_manager import (
                SoundDeviceManager,
            )

            self._sounddevice_manager = SoundDeviceManager()
        return self._sounddevice_manager

    @sounddevice_manager.setter
    def sounddevice_manager(self, value) -> None:
        """Store the shared sound-device manager."""
        self._sounddevice_manager = value

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _init_attributes(
        self,
        no_splash: bool,
        main_window_class: Optional[QWindow],
        window_class_params: Optional[Dict],
    ) -> None:
        """Initialize instance attributes."""
        self.logger = get_logger(__name__, level=AIRUNNER_LOG_LEVEL)

        self.main_window_class_ = main_window_class
        self.window_class_params = window_class_params or {}
        self.no_splash = no_splash
        self.app = None
        self.splash = None
        self.http_server_thread = None
        self.model_load_balancer = None
        self._worker_manager = None
        self._sounddevice_manager = None

    def _init_api_bridge(self) -> None:
        """Wire the daemon client's signal emitter and signal-to-API
        handler map so that GUI execution triggers go through the
        daemon client instead of local in-process workers.
        """
        if not self.daemon_client:
            return
        # Register the mediator's emit function as the daemon client's
        # signal emitter so it can dispatch response signals.
        self.daemon_client._emit = self.emit_signal
        self.logger.debug(
            "Daemon client wired for GUI backend signal dispatch"
        )

    def _register_signals(self) -> None:
        """Register signal handlers."""
        self.register(SignalCode.LOG_LOGGED_SIGNAL, self.on_log_logged_signal)
        self.register(SignalCode.UPATE_LOCALE, self.on_update_locale_signal)

    def _init_gui_mode(self) -> None:
        """Initialize GUI mode with static server and main window."""
        mathjax_dir = os.path.join(
            self.static_dir, "mathjax", f"MathJax-{MATHJAX_VERSION}", "es5"
        )
        if not os.path.isdir(mathjax_dir):
            raise RuntimeError(
                "MathJax is required for LaTeX rendering. "
                "See README.md for setup instructions."
            )

        self._start_local_http_server()
        self.set_translations()
        self.run()

    def _start_local_http_server(self) -> None:
        self.logger.info("Starting local HTTP server for static assets.")
        self.http_server_thread = LocalHttpServerThread(
            directory=self.static_dir,
            additional_directories=self.static_search_dirs[1:],
            port=LOCAL_SERVER_PORT,
            lna_enabled=LNA_ENABLED,
        )
        self.http_server_thread.start()
        self.start()
