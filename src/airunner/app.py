from typing import List, Optional, Dict
import glob
import logging
import os
import os.path
import signal
import sys
import subprocess
import time
import traceback
from pathlib import Path
from PySide6 import QtCore
from PySide6.QtCore import QObject, QTimer, QCoreApplication
from PySide6.QtGui import QGuiApplication, Qt, QWindow, QSurfaceFormat
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTranslator, QLocale, qVersion
from PySide6.QtWebEngineCore import QWebEngineSettings, QWebEnginePage
from PySide6.QtWebEngineWidgets import QWebEngineView

from airunner.utils.application import get_logger
from airunner.utils.settings import get_qsettings
from airunner.settings import (
    AIRUNNER_HEADLESS_SERVER_HOST,
    AIRUNNER_HEADLESS_SERVER_PORT,
)

# CRITICAL: Set PyTorch CUDA memory allocator config BEFORE importing torch
# This prevents fragmentation issues when loading large quantized models
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

from airunner.components.settings.data.language_settings import (
    LanguageSettings,
)
from airunner.components.settings.data.path_settings import PathSettings
from airunner.enums import (
    LANGUAGE_TO_LOCALE_MAP,
    AVAILABLE_LANGUAGES,
    LOCALE_TO_LANGUAGE_MAP,
    AvailableLanguage,
    SignalCode,
)
from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.components.application.gui.windows.main.settings_mixin import (
    SettingsMixin,
)
from airunner.components.settings.data.application_settings import (
    ApplicationSettings,
)
from airunner.settings import (
    AIRUNNER_DISABLE_SETUP_WIZARD,
    AIRUNNER_DISCORD_URL,
    AIRUNNER_LOG_LEVEL,
    AIRUNNER_USER_DATA_PATH,
    MATHJAX_VERSION,
    QTWEBENGINE_REMOTE_DEBUGGING,
    LOCAL_SERVER_PORT,
)
from airunner.components.server.local_http_server import LocalHttpServerThread
from airunner.components.splash_screen.splash_screen import SplashScreen

# NOTE: set_api, APIServerThread, and MainWindow imports are inline to avoid circular dependency with API class
from airunner.components.knowledge import get_knowledge_base
from airunner.utils.application.create_worker import create_worker
from airunner.components.application.gui.windows.main import (
    WorkerManager,
    ModelLoadBalancer,
    LLMGeneratorSettings,
)
from airunner.components.data.session_manager import session_scope
from airunner.app_installer import AppInstaller
from airunner.utils.application.logging_utils import configure_headless_logging
from airunner.settings import AIRUNNER_DEFAULT_LLM_HF_PATH
from airunner.enums import ModelService
from airunner.components.art.data.ai_models import AIModels


# Enable LNA mode for local server if AIRUNNER_LNA_ENABLED=1
LNA_ENABLED = os.environ.get("AIRUNNER_LNA_ENABLED", "0") == "1"

os.environ["QTWEBENGINE_REMOTE_DEBUGGING"] = QTWEBENGINE_REMOTE_DEBUGGING


def set_global_tooltip_style() -> None:
    """Set global tooltip style for the application."""
    app = QApplication.instance()
    if app is not None:
        app.setStyleSheet(
            app.styleSheet()
            + """
            QToolTip {
                color: #fff;
                background-color: #222;
                border: 1px solid #555;
                padding: 4px 8px;
                font-size: 13px;
                border-radius: 4px;
            }
            """
        )


class CapturingWebEnginePage(QWebEnginePage):
    """QWebEnginePage subclass to capture JS console messages for diagnostics."""

    def javaScriptConsoleMessage(
        self, level: int, message: str, lineNumber: int, sourceID: str
    ) -> None:
        """Capture JavaScript console messages for diagnostics."""
        log_message = f"JSCONSOLE::: Level: {level}, Msg: {message}, Src: {sourceID}:{lineNumber}"
        print(log_message)
        super().javaScriptConsoleMessage(level, message, lineNumber, sourceID)


class App(MediatorMixin, SettingsMixin, QObject):
    """
    The main application class for AI Runner.
    This class can be run as a GUI application or as a socket server.
    """

    def __init__(
        self,
        no_splash: bool = False,
        main_window_class: QWindow = None,
        window_class_params: Optional[Dict] = None,
        headless: bool = False,
        launcher_splash=None,
        launcher_app=None,
    ):
        """Initialize the application.

        Args:
            no_splash: Skip splash screen display (GUI mode only)
            main_window_class: Custom main window class (GUI mode only)
            window_class_params: Parameters for main window (GUI mode only)
            headless: If True, run in headless mode (no GUI)
            launcher_splash: Splash screen passed from launcher (already showing)
            launcher_app: QApplication passed from launcher
        """
        self.headless = headless
        self._launcher_splash = launcher_splash
        self._launcher_app = launcher_app
        self._init_attributes(
            no_splash, main_window_class, window_class_params
        )
        super().__init__()
        self._register_signals()
        self._ensure_mathjax()

        if self.headless:
            self._init_headless_mode()
        else:
            self._init_gui_mode()

        self._initialize_knowledge_system()

    @property
    def static_dir(self) -> str:
        """Get the static directory path.
        
        Uses user data directory for writable static files (like MathJax),
        falls back to package directory for bundled static assets.
        """
        # User-writable static directory
        base_path = os.environ.get(
            "AIRUNNER_DATA_DIR",
            os.path.join(os.path.expanduser("~"), ".local", "share", "airunner")
        )
        user_static = os.path.join(base_path, "static")
        
        # Package static directory (read-only, bundled assets)
        pkg_static = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "static")
        )
        
        # Return user static if it exists, otherwise package static
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
        # Find all components/**/gui/static directories
        components_static_dirs = glob.glob(
            os.path.join(
                os.path.dirname(__file__), "components", "**", "gui", "static"
            ),
            recursive=True,
        )
        # Include both user static dir and package static dir
        static_search_dirs = [self.static_dir]
        if self._package_static_dir != self.static_dir:
            static_search_dirs.append(self._package_static_dir)
        static_search_dirs.extend(components_static_dirs)
        # Add user web dir if it exists
        if os.path.isdir(self.user_web_dir):
            static_search_dirs.append(self.user_web_dir)
        return static_search_dirs

    def _init_attributes(
        self,
        no_splash: bool,
        main_window_class: QWindow,
        window_class_params: Optional[Dict]
    ) -> None:
        """Initialize instance attributes."""
        if self.headless:
            configure_headless_logging()

        self.logger = get_logger(__name__, level=AIRUNNER_LOG_LEVEL)

        self.main_window_class_ = main_window_class
        self.window_class_params = window_class_params or {}
        self.no_splash = no_splash
        self.app = None
        self.splash = None
        self.http_server_thread = None
        self.api_server_thread = None
        self.is_running = False

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
                "MathJax is required for LaTeX rendering. See README.md for setup instructions."
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
            lna_enabled=LNA_ENABLED,  # Pass LNA mode to server
        )
        self.http_server_thread.start()
        self.start()

    def _init_headless_mode(self) -> None:
        """Initialize headless mode."""
        self.logger.info("Running in headless mode (no GUI)")
        signal.signal(signal.SIGINT, self.signal_handler)
        self._init_headless_services()
        self.is_running = True

    def _kill_via_lsof(self, port: int) -> bool:
        """Try to kill process using lsof. Returns True if successful."""
        try:
            result = subprocess.run(
                ["lsof", "-ti", f":{port}"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split("\n")
                for pid in pids:
                    try:
                        self.logger.info(
                            f"Killing process {pid} using port {port}"
                        )
                        subprocess.run(
                            ["kill", "-9", pid], timeout=5, check=False
                        )
                        time.sleep(0.5)
                    except Exception as e:
                        self.logger.warning(
                            f"Failed to kill process {pid}: {e}"
                        )
                return True
        except FileNotFoundError:
            return False
        except Exception as e:
            self.logger.debug(f"Could not kill process on port {port}: {e}")
        return False

    def _kill_via_netstat(self, port: int) -> None:
        """Try to kill process using netstat."""
        try:
            result = subprocess.run(
                ["netstat", "-tlnp"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            for line in result.stdout.split("\n"):
                if f":{port}" in line and "LISTEN" in line:
                    parts = line.split()
                    if len(parts) > 6:
                        pid_program = parts[6]
                        if "/" in pid_program:
                            pid = pid_program.split("/")[0]
                            try:
                                self.logger.info(
                                    f"Killing process {pid} using port {port}"
                                )
                                subprocess.run(
                                    ["kill", "-9", pid], timeout=5, check=False
                                )
                            except Exception as e:
                                self.logger.warning(
                                    f"Failed to kill process {pid}: {e}"
                                )
        except Exception as e:
            self.logger.debug(
                f"Could not check for processes on port {port}: {e}"
            )

    def _kill_process_on_port(self, port: int) -> None:
        """Kill any process using the specified port.

        Args:
            port: Port number to check and clear
        """
        if not self._kill_via_lsof(port):
            self._kill_via_netstat(port)

    def _init_headless_services(self):
        """Initialize services for headless mode (no GUI).

        Creates minimal Qt event loop and starts HTTP API server.
        """
        # Create QCoreApplication for Qt event loop (needed by workers)
        # This is minimal Qt without any GUI components
        self.app = QCoreApplication.instance()
        if self.app is None:
            self.app = QCoreApplication([])
        self.app.api = self
        self.logger.info("Qt Core event loop initialized (headless mode)")

        # Register this API instance globally for tools to access
        # Import here to avoid circular dependency with API class
        from airunner.components.server.api.server import set_api

        set_api(self)
        self.logger.info("API instance registered globally")

        # Initialize workers BEFORE starting HTTP server
        # so they're ready to handle requests immediately
        self._initialize_headless_workers()

        # Pre-load LLM model if configured in settings
        self._preload_llm_model()

        # Start API server for /llm, /art, /stt, /tts endpoints
        # Skip if we're being created from within an HTTP request handler
        # (server is already running in that case)
        if os.environ.get("AIRUNNER_SERVER_RUNNING") != "1":
            # Import here to avoid circular dependency with API class
            from airunner.components.server.api.api_server_thread import (
                APIServerThread,
            )

            host = AIRUNNER_HEADLESS_SERVER_HOST
            port = AIRUNNER_HEADLESS_SERVER_PORT

            # Kill any existing process using this port
            self._kill_process_on_port(port)

            self.logger.info(f"Starting API server on {host}:{port}")
            self.api_server_thread = APIServerThread(host=host, port=port)
            self.api_server_thread.start()
            self.logger.info(
                f"API server started - /health, /llm, /art endpoints available"
            )
            # Mark that server is now running
            os.environ["AIRUNNER_SERVER_RUNNING"] = "1"
        else:
            self.logger.info(
                "API server already running - skipping initialization"
            )

    def _initialize_knowledge_system(self):
        """Initialize the markdown-based knowledge system."""
        # Skip if knowledge system is disabled (e.g., in headless mode)
        if os.environ.get("AIRUNNER_KNOWLEDGE_ON", "1") == "0":
            self.logger.info("Knowledge system disabled")
            return

        try:
            # Initialize the knowledge base (creates directory if needed)
            kb = get_knowledge_base()
            self.logger.info(f"Knowledge system initialized: {kb.knowledge_dir}")

            # Run one-time knowledge migration if needed (from old JSON to markdown)
            self._run_knowledge_migration_if_needed()
        except Exception as e:
            self.logger.error(
                f"Failed to initialize knowledge system: {e}", exc_info=True
            )

    def _initialize_headless_workers(self):
        """Initialize essential workers for headless mode.

        Creates WorkerManager which handles signal routing to all workers
        and ModelLoadBalancer for model lifecycle management.
        """
        try:
            # Create WorkerManager - it registers LLM_TEXT_GENERATE_REQUEST_SIGNAL
            # and lazily creates workers (LLMGenerateWorker, SDWorker, etc.) as needed
            self._worker_manager = create_worker(WorkerManager)

            # CRITICAL: Eagerly initialize LLM worker so it's ready to receive signals
            # The worker must be created BEFORE any LLM requests are sent
            _ = self._worker_manager.llm_generate_worker
            self.logger.info("LLM worker initialized and ready")

            # Register RAG signal handler for headless mode
            # In GUI mode, this is handled by WorkerManager
            self.register(
                SignalCode.RAG_LOAD_DOCUMENTS,
                self.on_rag_load_documents_signal,
            )
            self.logger.info("RAG signal handler registered")

            # Create ModelLoadBalancer to manage model loading/unloading
            self._model_load_balancer = ModelLoadBalancer(
                self._worker_manager,
                logger=getattr(self, "logger", None),
                api=self,
            )

            self.logger.info("Headless workers initialized (LLM)")
        except Exception as e:
            self.logger.error(
                f"Failed to initialize headless workers: {e}", exc_info=True
            )

    def _preload_llm_model(self):
        """Pre-load LLM model from settings if configured.

        This speeds up first request by loading model at startup.
        Respects AIRUNNER_NO_PRELOAD environment variable to skip preloading.
        Uses AIRUNNER_LLM_MODEL_PATH if provided to override settings.
        """
        # Check if preloading is disabled
        if os.environ.get("AIRUNNER_NO_PRELOAD") == "1":
            self.logger.info(
                "Model preloading disabled (--no-preload flag or AIRUNNER_NO_PRELOAD=1)"
            )
            self.logger.info("Models will be loaded on first request")
            return

        try:
            # Log which database we're using and dev/prod mode for debugging
            try:
                from airunner.settings import AIRUNNER_DB_URL, DEV_ENV

                self.logger.info(
                    f"DEBUG: Preload LLM - DB URL: {AIRUNNER_DB_URL} DEV_ENV={DEV_ENV}"
                )
            except Exception:
                # Best-effort; not critical if we can't fetch settings
                pass

            # Check for CLI-provided model path first
            cli_model_path = os.environ.get("AIRUNNER_LLM_MODEL_PATH")
            
            with session_scope() as session:
                llm_settings = session.query(LLMGeneratorSettings).first()
                
                # Determine model path priority:
                # 1. CLI-provided path (AIRUNNER_LLM_MODEL_PATH)
                # 2. Existing settings from database
                # 3. Default path from environment
                # 4. AIModels table fallback
                model_path_to_use = None
                
                if cli_model_path:
                    # CLI path takes highest priority
                    model_path_to_use = cli_model_path
                    self.logger.info(f"Using CLI-provided model path: {cli_model_path}")
                    
                    # Update or create settings with CLI path
                    if llm_settings:
                        llm_settings.model_path = cli_model_path
                        session.commit()
                    else:
                        new_settings = LLMGeneratorSettings()
                        new_settings.model_path = cli_model_path
                        new_settings.model_service = ModelService.LOCAL.value
                        session.add(new_settings)
                        session.commit()
                        llm_settings = new_settings
                elif llm_settings and llm_settings.model_path:
                    model_path_to_use = llm_settings.model_path
                else:
                    # Try to find a default model path
                    default_model_path = (
                        os.environ.get("AIRUNNER_DEFAULT_LLM_HF_PATH")
                        or AIRUNNER_DEFAULT_LLM_HF_PATH
                    )
                    # If no default path from env, try to find an installed AI model
                    # for LLMs in the AIModels table and use that as a fallback.
                    if not default_model_path:
                        try:
                            aimodel = (
                                session.query(AIModels)
                                .filter(AIModels.model_type == "llm")
                                .filter(AIModels.enabled.is_(True))
                                .order_by(AIModels.is_default.desc())
                                .first()
                            )
                            if aimodel and aimodel.path:
                                default_model_path = aimodel.path
                                self.logger.info(
                                    f"No env default model set; using AIModels path: {default_model_path}"
                                )
                        except Exception:
                            # Not critical if we can't access AIModels
                            pass
                    if default_model_path:
                        self.logger.info(
                            f"No LLM settings row; creating default settings for model: {default_model_path}"
                        )
                        new_settings = LLMGeneratorSettings()
                        new_settings.model_path = default_model_path
                        new_settings.model_service = ModelService.LOCAL.value
                        session.add(new_settings)
                        session.commit()
                        model_path_to_use = default_model_path

                if model_path_to_use:
                    self.logger.info(
                        f"Pre-loading LLM model: {model_path_to_use}"
                    )
                    self.logger.info("This may take 30-60 seconds...")

                    # Emit model load signal - WorkerManager will handle it
                    self.emit_signal(
                        SignalCode.LLM_LOAD_SIGNAL,
                        {"model_path": model_path_to_use},
                    )

                    # Wait a bit for loading to start
                    time.sleep(5)
                    self.logger.info("Model loading initiated in background")
                else:
                    self.logger.info(
                        "No LLM model configured - model will load on first request"
                    )
        except Exception as e:
            self.logger.info(f"Warning: Could not pre-load model: {e}")
            self.logger.info("Model will load on first request")

    @property
    def rag_manager(self) -> Optional[object]:
        """Get the RAG manager (model manager) for tool access.

        This property exposes the LLM model manager which has RAG capabilities.
        It's used by tools that need to search documents via rag_search.

        Returns:
            LLMModelManager instance or None if not available
        """
        if hasattr(self, "_worker_manager") and self._worker_manager:
            return self._worker_manager.llm_generate_worker.model_manager
        return None

    def on_rag_load_documents_signal(self, data: Dict) -> None:
        """Handle RAG_LOAD_DOCUMENTS signal in headless mode.

        This forwards the signal to the LLM worker which has the model_manager
        with RAG capabilities.

        Args:
            data: Dictionary containing documents and clear_documents flag
        """
        try:
            self.logger.info("✓✓✓ RAG_LOAD_DOCUMENTS signal received in App!")
            self.logger.info("✓✓✓ RAG_LOAD_DOCUMENTS signal received in App!")
            self.logger.info(
                f"DEBUG: Data keys: {list(data.keys()) if data else 'None'}"
            )

            if hasattr(self, "_worker_manager") and self._worker_manager:
                self.logger.info("DEBUG: Forwarding to worker manager...")
                self._worker_manager.llm_generate_worker.on_rag_load_documents_signal(
                    data
                )
                self.logger.info("✓ Forwarded RAG load signal to LLM worker")
                self.logger.info("✓ Forwarded RAG load signal to LLM worker")
            else:
                self.logger.warning(
                    "Worker manager not available for RAG loading"
                )
                self.logger.info("ERROR: Worker manager not available")
        except Exception as e:
            self.logger.error(
                f"Error handling RAG load signal: {e}", exc_info=True
            )

    def _run_knowledge_migration_if_needed(self):
        """Run one-time migration from JSON to markdown if not already done.

        Uses database-level locking to prevent race conditions when multiple
        instances start simultaneously.
        """
        try:
            # Use database transaction to check and set migration flag atomically
            with session_scope() as session:
                # Lock the settings row to prevent concurrent migrations
                settings = (
                    session.query(ApplicationSettings)
                    .filter_by(id=1)
                    .with_for_update()  # Database-level lock
                    .first()
                )

                if not settings:
                    # Create default settings if they don't exist yet
                    self.logger.info("Creating default application settings")
                    settings = ApplicationSettings(
                        id=1, knowledge_migrated=False
                    )
                    session.add(settings)
                    session.commit()
                    # Re-query to get the locked row
                    settings = (
                        session.query(ApplicationSettings)
                        .filter_by(id=1)
                        .with_for_update()
                        .first()
                    )

                # Check if migration already completed (within transaction)
                if settings.knowledge_migrated:
                    self.logger.debug("Knowledge migration already completed")
                    return

                # Check if legacy JSON file exists
                knowledge_dir = Path(AIRUNNER_USER_DATA_PATH) / "knowledge"
                json_path = knowledge_dir / "user_facts.json"

                if not json_path.exists():
                    # No legacy data to migrate
                    self.logger.info(
                        "No legacy knowledge data found, skipping migration"
                    )
                    settings.knowledge_migrated = True
                    session.commit()
                    return

                # Run migration (outside transaction to avoid long locks)
                self.logger.info(
                    "Running one-time knowledge migration from JSON to markdown..."
                )

            # Migration runs outside the locked transaction
            self._migrate_json_to_markdown(json_path)

            # Mark migration as complete
            self._mark_migration_complete()

        except Exception as e:
            self.logger.error(
                f"Failed to run knowledge migration: {e}. "
                f"Migration NOT marked complete - will retry on next startup.",
                exc_info=True,
            )

    def _migrate_json_to_markdown(self, json_path: Path):
        """Migrate legacy JSON facts to new markdown format.
        
        Args:
            json_path: Path to the legacy user_facts.json file
        """
        import json
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            kb = get_knowledge_base()
            migrated = 0
            
            # Handle different JSON formats
            facts = data if isinstance(data, list) else data.get('facts', [])
            
            for fact_data in facts:
                if isinstance(fact_data, str):
                    fact_text = fact_data
                    category = "Notes"
                elif isinstance(fact_data, dict):
                    fact_text = fact_data.get('text', fact_data.get('content', ''))
                    category = fact_data.get('category', 'Notes')
                else:
                    continue
                
                if fact_text:
                    # Map old categories to new sections
                    section_map = {
                        'identity': 'Identity',
                        'personal': 'Identity',
                        'work': 'Work & Projects',
                        'project': 'Work & Projects',
                        'hobby': 'Interests & Hobbies',
                        'interest': 'Interests & Hobbies',
                        'preference': 'Preferences',
                        'health': 'Health & Wellness',
                        'relationship': 'Relationships',
                        'goal': 'Goals',
                        'other': 'Notes',
                        'notes': 'Notes',
                    }
                    section = section_map.get(category.lower(), 'Notes')
                    kb.add_fact(fact_text, section=section)
                    migrated += 1
            
            self.logger.info(f"Knowledge migration successful: {migrated} facts migrated to markdown")
            
            # Rename the old file to mark as migrated
            backup_path = json_path.with_suffix('.json.migrated')
            json_path.rename(backup_path)
            self.logger.info(f"Legacy JSON backed up to: {backup_path}")
            
        except Exception as e:
            self.logger.error(f"Error during JSON to markdown migration: {e}")
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
        except Exception as e:
            self.logger.error(
                f"Failed to mark migration complete: {e}", exc_info=True
            )

    def on_update_locale_signal(self, data: dict) -> None:
        """Handle locale update signal."""
        self.set_translations(data)

    def set_translations(self, data: Optional[Dict] = None) -> None:
        """Set application translations based on language settings."""
        locale_language = None

        # Get the locale language from the data dictionary
        locale_language_string = (
            data.get("gui_language", None) if data else None
        )
        if locale_language_string:
            locale_language = LANGUAGE_TO_LOCALE_MAP[
                AvailableLanguage(locale_language_string)
            ]

        # If no locale language is provided, use the default from LanguageSettings
        if not locale_language:
            settings = LanguageSettings.objects.first()
            if settings:
                try:
                    lang = AvailableLanguage(settings.gui_language)
                except ValueError:
                    lang = AvailableLanguage.EN

                try:
                    locale_language = LANGUAGE_TO_LOCALE_MAP[lang]
                except KeyError:
                    locale_language = LANGUAGE_TO_LOCALE_MAP.get(
                        AvailableLanguage.EN
                    )

        # If still no locale language, use the system locale
        if not locale_language:
            locale_language = QLocale.system().language()

        if locale_language not in LANGUAGE_TO_LOCALE_MAP:
            locale_language = None

        # If we have a locale but it's not in the available languages, set it to None
        if locale_language is not None and (
            LOCALE_TO_LANGUAGE_MAP[locale_language]
            not in AVAILABLE_LANGUAGES["gui_language"]
        ):
            locale_language = None

        # If still no locale language, use English as default
        if not locale_language:
            locale_language = locale_language or QLocale.English

        # Set the locale language in the LanguageSettings model
        self._load_translations(locale=QLocale(locale_language))

    @staticmethod
    def run_setup_wizard() -> None:
        """Run the application setup wizard if needed."""
        if AIRUNNER_DISABLE_SETUP_WIZARD:
            return
        application_settings = ApplicationSettings.objects.first()
        path_settings = PathSettings.objects.first()
        if path_settings is None:
            PathSettings.objects.create()
            path_settings = PathSettings.objects.first()
        if application_settings is None:
            ApplicationSettings.objects.create()
            application_settings = ApplicationSettings.objects.first()
        base_path = path_settings.base_path
        if (
            not os.path.exists(base_path)
            or application_settings.run_setup_wizard
        ):
            AppInstaller()

    def _load_translations(self, locale: Optional[QLocale] = None):
        """
        Loads and installs the appropriate translation file.
        If locale is None, uses the system locale.
        """
        if not locale:
            locale = QLocale.system()
        translations_dir = os.path.join(
            os.path.dirname(__file__), "translations"
        )
        # Remove the previously installed translator if any
        old_translator = getattr(self.app, 'translator', None)
        if old_translator is not None:
            self.app.removeTranslator(old_translator)
            self.app.translator = None

        translator = QTranslator()
        language_map = {
            QLocale.English: "english",
            QLocale.Japanese: "japanese",
        }
        base_name = language_map.get(locale.language(), "english")
        qm_path = os.path.join(translations_dir, f"{base_name}.qm")
        if os.path.exists(qm_path) and translator.load(qm_path):
            self.app.installTranslator(translator)
            self.app.translator = translator
            self.retranslate_ui_signal()
        else:
            if base_name != "english":
                english_qm_path = os.path.join(translations_dir, "english.qm")
                fallback_translator = QTranslator()
                if os.path.exists(
                    english_qm_path
                ) and fallback_translator.load(english_qm_path):
                    self.app.installTranslator(fallback_translator)
                    self.app.translator = fallback_translator
                    self.retranslate_ui_signal()
                else:
                    self.app.translator = None

    def on_log_logged_signal(self, data: dict) -> None:
        """Handle log message signal."""
        message = data["message"].split(" - ")
        self.update_splash_message(self.splash, message[4])

    def start(self) -> None:
        """
        Conditionally initialize and display the setup wizard.
        :return:
        """
        if self.headless:
            return  # Skip GUI initialization if the flag is False
        signal.signal(signal.SIGINT, self.signal_handler)

        # Set up OpenGL environment before Qt initialization
        # This fixes "QXcbIntegration: Cannot create platform OpenGL context, neither GLX nor EGL are enabled"
        os.environ["QT_OPENGL"] = "desktop"

        # Let Qt choose the appropriate platform (don't force X11)
        # Only set GLX integration for X11 sessions
        if os.environ.get("XDG_SESSION_TYPE") == "x11" or os.environ.get(
            "DISPLAY"
        ):
            os.environ["QT_XCB_GL_INTEGRATION"] = (
                "xcb_glx"  # Enable GLX for X11
            )
            print("X11 session detected - enabling GLX")
        elif os.environ.get("WAYLAND_DISPLAY"):
            print("Wayland session detected - using default EGL")

        os.environ["LIBGL_ALWAYS_SOFTWARE"] = (
            "0"  # Ensure hardware acceleration
        )

        # Set up OpenGL surface format before creating QApplication
        fmt = QSurfaceFormat()
        fmt.setVersion(3, 3)
        fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
        fmt.setSwapBehavior(QSurfaceFormat.SwapBehavior.DoubleBuffer)
        fmt.setDepthBufferSize(24)
        fmt.setStencilBufferSize(8)
        QSurfaceFormat.setDefaultFormat(fmt)

        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseDesktopOpenGL)
        QApplication.setAttribute(
            Qt.ApplicationAttribute.AA_EnableHighDpiScaling
        )
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)
        
        # Use launcher's QApplication if available, otherwise create new
        if self._launcher_app is not None:
            self.app = self._launcher_app
        else:
            self.app = QApplication.instance()
            if self.app is None:
                self.app = QApplication([])
        self.app.api = self
        # Set global tooltip style ONCE at startup
        set_global_tooltip_style()

    def run(self) -> None:
        """
        Run as a GUI application.
        A splash screen is displayed while the application is loading
        and a main window is displayed once the application is ready.
        Override this method to run the application in a different mode.
        """
        if self.headless:
            # Headless mode - keep server running
            self.run_headless()
            return

        # Use launcher's splash if available, otherwise create new
        if self._launcher_splash is not None:
            self.splash = self._launcher_splash
            self.update_splash_message(self.splash, "Loading AI Runner...")
        elif not self.no_splash and not self.splash:
            self.splash = self.display_splash_screen(self.app)

        QTimer.singleShot(50, self._post_splash_startup)
        sys.exit(self.app.exec())

    def run_headless(self):
        """Run in headless mode without GUI.

        Uses Qt event loop to process worker signals while server runs.
        """
        print("run headless function called")
        # Workers are already initialized in _init_headless_services()
        # No need to initialize again here
        self.logger.info("AI Runner headless mode - server running")
        self.logger.info("Press Ctrl+C to stop")

        # Qt event loop blocks Python signal handlers, so we need to
        # periodically allow Python to process signals
        # This timer does nothing but allows KeyboardInterrupt to be caught
        # We use a simple no-op function instead of lambda to avoid issues
        def _timer_tick():
            pass

        self._headless_timer = QTimer()
        self._headless_timer.timeout.connect(_timer_tick)
        self._headless_timer.start(500)  # Wake up every 500ms

        try:
            # Run Qt event loop (processes worker signals)
            self.logger.info("DEBUG: Starting Qt event loop")
            ret = self.app.exec()
            self.logger.info(f"DEBUG: Qt event loop returned with {ret}")
            sys.exit(ret)
        except KeyboardInterrupt:
            self.logger.info("Interrupted by user")
            self.cleanup()
            sys.exit(0)
        except Exception as e:
            self.logger.exception(f"CRITICAL: Headless server crashed: {e}")
            self.cleanup()
            sys.exit(1)

    def _post_splash_startup(self):
        self.show_main_application(self.app)

    @staticmethod
    def signal_handler(_signal: int, _frame: object) -> None:
        """
        Handle the SIGINT signal in a clean way.
        :param _signal:
        :param _frame:
        :return: None
        """
        print("\nExiting...")
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        try:
            app = QApplication.instance()
            app.quit()
            sys.exit(0)
        except Exception as e:
            print(e)
            sys.exit(0)

    def display_splash_screen(
        self, app: QApplication
    ) -> Optional[SplashScreen]:
        """
        Display a splash screen while the application is loading using the SplashScreen class.
        :param app:
        :return:
        """
        if self.no_splash:
            return

        # Try to use the saved screen preference, otherwise use primary screen
        screens = QGuiApplication.screens()
        target_screen = None

        # Load saved screen preference
        try:
            qsettings = get_qsettings()
            qsettings.beginGroup("window_settings")
            saved_screen_name = qsettings.value("screen_name", None, type=str)
            qsettings.endGroup()

            # Try to find screen by name
            if saved_screen_name:
                for s in screens:
                    if s.name() == saved_screen_name:
                        target_screen = s
                        break
        except Exception:
            pass

        # Fallback to primary screen if no saved screen found
        if not target_screen:
            try:
                target_screen = QGuiApplication.primaryScreen()
            except Exception:
                pass

        # Final fallback to first screen
        if not target_screen:
            try:
                target_screen = screens.at(0)
            except AttributeError:
                target_screen = screens[0]

        base_dir = Path(os.path.dirname(os.path.realpath(__file__)))
        image_path = base_dir / "gui" / "images" / "splashscreen.png"
        splash = SplashScreen(target_screen, image_path)
        splash.show_message("Loading AI Runner")
        app.processEvents()
        return splash

    @staticmethod
    def update_splash_message(
        splash: Optional[SplashScreen], message: str
    ) -> None:
        """Update splash screen message."""
        if hasattr(splash, "show_message"):
            splash.show_message(message)
        else:
            splash.showMessage(
                message,
                QtCore.Qt.AlignmentFlag.AlignBottom
                | QtCore.Qt.AlignmentFlag.AlignCenter,
                QtCore.Qt.GlobalColor.white,
            )

    def show_main_application(self, app: QApplication) -> None:
        """
        Show the main application window.
        :param app:
        :param splash:
        :return:
        """
        if self.headless:
            return  # Skip showing the main application window if GUI is disabled

        window_class = self.main_window_class_
        if not window_class:
            # Import here to avoid circular dependency with API class
            from airunner.components.application.gui.windows.main.main_window import (
                MainWindow,
            )

            window_class = MainWindow

        try:
            # Update splash message during window creation
            self.update_splash_message(self.splash, "Initializing main window...")
            window = window_class(app=self, **self.window_class_params)
            app.main_window = window
            
            # Close splash screen AFTER window is created and shown
            # This ensures the splash stays visible during the entire loading process
            if self.splash:
                self.splash.finish(window)
            
            window.raise_()
            # --- LNA/diagnostics: log Qt version, enable dev tools, set custom page if QWebEngineView present ---
            print(f"Qt Version: {qVersion()}")
            if hasattr(window, "ui"):
                for attr in dir(window.ui):
                    widget = getattr(window.ui, attr)
                    if isinstance(widget, QWebEngineView):
                        # Check if a custom page has already been set
                        current_page = widget.page()
                        if (
                            current_page
                            and type(current_page).__name__ != "QWebEnginePage"
                        ):
                            # A custom page is already set, don't override it
                            print(
                                f"[App] Skipping page override for {attr}, already has custom page: {type(current_page)}"
                            )
                            continue

                        settings = widget.settings()
                        settings.setAttribute(
                            QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows,
                            True,
                        )
                        settings.setAttribute(
                            QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls,
                            True,
                        )
                        print(
                            f"[App] Setting CapturingWebEnginePage for {attr}"
                        )
                        widget.setPage(CapturingWebEnginePage(widget))
        except Exception as e:
            traceback.print_exc()
            print(e)
            sys.exit(
                f"""
                An error occurred while initializing the application.
                Please report this issue on GitHub or Discord {AIRUNNER_DISCORD_URL}."""
            )

    def quit(self):
        """Stop HTTP server and cleanup resources."""
        if self.http_server_thread:
            self.http_server_thread.stop()
            self.http_server_thread.wait()

        if self.api_server_thread:
            self.api_server_thread.stop()
            # API server thread is daemon, no need to join

    def cleanup(self):
        """
        Cleanup resources when shutting down.
        Safe to call in both GUI and headless mode.
        """
        self.logger.info("Cleaning up App resources...")

        try:
            # Mark as not running first to stop loops
            self.is_running = False

            # Stop HTTP server if running
            if hasattr(self, "api_server_thread") and self.api_server_thread:
                self.logger.info("Stopping API server...")
                try:
                    self.api_server_thread.shutdown()
                    self.api_server_thread.join(timeout=2.0)
                    self.logger.info("API server stopped")
                except Exception as e:
                    self.logger.warning(f"Error stopping API server: {e}")

            # Emit quit signal for components to cleanup (workers listen for QUIT_APPLICATION)
            try:
                self.emit_signal(SignalCode.QUIT_APPLICATION, {})
            except Exception as e:
                self.logger.warning(f"Error emitting quit signal: {e}")

            # Stop and join all worker threads created by create_worker()
            try:
                from airunner.utils.application.create_worker import (
                    WORKERS,
                    THREADS,
                )

                # Ask each worker to stop (this will emit finished and quit their QThread)
                for w in WORKERS:
                    try:
                        w.stop()
                    except Exception:
                        pass

                # Ensure threads exit and join them
                for t in THREADS:
                    try:
                        # Quit and wait for termination; if wait fails, force terminate
                        t.quit()
                        t.wait(2000)
                        if t.isRunning():
                            t.terminate()
                            t.wait(500)
                    except Exception:
                        pass

                # Clear global lists so future create_worker runs start fresh
                try:
                    WORKERS.clear()
                    THREADS.clear()
                except Exception:
                    pass
            except Exception as e:
                self.logger.warning(f"Error stopping workers/threads: {e}")

            self.logger.info("App cleanup complete")

        except Exception as e:
            self.logger.error(f"Error during App cleanup: {e}", exc_info=True)

    def _ensure_mathjax(self):
        # Only run setup if MathJax is not present
        # Use user data directory instead of package directory (read-only in flatpak)
        if os.environ.get("AIRUNNER_FLATPAK") == "1":
            xdg_data_home = os.environ.get(
                "XDG_DATA_HOME",
                os.path.expanduser("~/.local/share")
            )
            base_path = os.path.join(xdg_data_home, "airunner")
        else:
            base_path = os.environ.get(
                "AIRUNNER_DATA_DIR",
                os.path.join(os.path.expanduser("~"), ".local", "share", "airunner")
            )
        mathjax_dir = os.path.join(
            base_path,
            "static",
            "mathjax",
            f"MathJax-{MATHJAX_VERSION}",
            "es5",
        )
        os.makedirs(os.path.dirname(os.path.dirname(mathjax_dir)), exist_ok=True)  # Create .../static/mathjax
        entry = os.path.join(mathjax_dir, "tex-mml-chtml.js")
        if not os.path.exists(entry):
            print("MathJax not found, attempting to download and set up...")
            try:
                # Set environment variable so setup script knows where to install
                # Pass .../static/mathjax (parent of MathJax-{VERSION})
                env = os.environ.copy()
                env["MATHJAX_INSTALL_DIR"] = os.path.dirname(os.path.dirname(mathjax_dir))
                subprocess.check_call(
                    [
                        sys.executable,
                        os.path.join(
                            os.path.dirname(__file__),
                            "bin",
                            "setup_mathjax.py",
                        ),
                    ],
                    env=env,
                )
            except Exception as e:
                print("ERROR: MathJax setup failed:", e)
                raise RuntimeError(
                    "MathJax is required but could not be set up. See README.md for instructions."
                )

    def retranslate_ui_signal(self) -> None:
        """Emit signal to retranslate all UI elements."""
        self.emit_signal(SignalCode.RETRANSLATE_UI_SIGNAL)


# Dummy classes for test patching
class AppInstaller:
    """Dummy AppInstaller class for test patching."""

    pass


class MainWindow:
    """Dummy MainWindow class for test patching."""

    pass
