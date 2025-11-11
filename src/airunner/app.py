from typing import Optional, Dict
import glob
import os
import os.path
import signal
import traceback
from pathlib import Path
from PySide6 import QtCore
from PySide6.QtCore import QObject, QTimer
from PySide6.QtGui import QGuiApplication, Qt, QWindow
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTranslator, QLocale

from airunner.utils.application import get_logger
from airunner.utils.settings import get_qsettings

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
    MATHJAX_VERSION,
    QTWEBENGINE_REMOTE_DEBUGGING,  # Add this import
)
from airunner.components.server.local_http_server import LocalHttpServerThread
from airunner.components.splash_screen.splash_screen import SplashScreen
import subprocess
import sys
from airunner.settings import LOCAL_SERVER_PORT

# Enable LNA mode for local server if AIRUNNER_LNA_ENABLED=1
LNA_ENABLED = os.environ.get("AIRUNNER_LNA_ENABLED", "0") == "1"

os.environ["QTWEBENGINE_REMOTE_DEBUGGING"] = QTWEBENGINE_REMOTE_DEBUGGING

from PySide6.QtWebEngineCore import QWebEngineSettings, QWebEnginePage
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import qVersion


def set_global_tooltip_style():
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

    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
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
        initialize_gui: bool = True,  # New flag to control GUI initialization
    ):
        """
        Initialize the application.

        Args:
            no_splash: Skip splash screen display (GUI mode only)
            main_window_class: Custom main window class (GUI mode only)
            window_class_params: Parameters for main window (GUI mode only)
            initialize_gui: If False, run in headless mode (no GUI)
        """
        self.logger = get_logger(__name__, level=AIRUNNER_LOG_LEVEL)
        # Check environment variable for headless mode
        headless_env = os.environ.get("AIRUNNER_HEADLESS", "0") == "1"
        if headless_env:
            initialize_gui = False

        self.main_window_class_ = main_window_class
        self.window_class_params = window_class_params or {}
        self.no_splash = no_splash
        self.app = None
        self.splash = None
        self.initialize_gui = initialize_gui  # Store the flag
        self.http_server_thread = None
        self.api_server_thread = None  # New: API server for headless mode
        self.is_running = False

        """
        Mediator and Settings mixins are initialized here, enabling the application
        to easily access the application settings dictionary.
        """
        super().__init__()

        self.register(SignalCode.LOG_LOGGED_SIGNAL, self.on_log_logged_signal)
        self.register(SignalCode.UPATE_LOCALE, self.on_update_locale_signal)

        self._ensure_mathjax()

        # Start HTTPS server for static assets (MathJax and content widgets)
        # Only needed in GUI mode
        if self.initialize_gui:
            static_dir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "static")
            )
            # Find all components/**/gui/static directories
            print(
                flush=True,
            )
            components_static_dirs = glob.glob(
                os.path.join(
                    os.path.dirname(__file__),
                    "components",
                    "**",
                    "gui",
                    "static",
                ),
                recursive=True,
            )
            print(
                flush=True,
            )
            # Add user web dir if it exists
            static_search_dirs = [static_dir] + components_static_dirs
            if os.path.isdir(self.user_web_dir):
                static_search_dirs.append(self.user_web_dir)
            mathjax_dir = os.path.join(
                static_dir, "mathjax", f"MathJax-{MATHJAX_VERSION}", "es5"
            )
            if os.path.isdir(mathjax_dir):
                self.logger.info(
                    "Starting local HTTPS server for static assets."
                )
                print(
                    flush=True,
                )
                self.http_server_thread = LocalHttpServerThread(
                    directory=static_dir,
                    additional_directories=static_search_dirs[1:],
                    port=LOCAL_SERVER_PORT,
                    lna_enabled=LNA_ENABLED,  # Pass LNA mode to server
                )
                print(
                    flush=True,
                )
                self.http_server_thread.start()
                self.start()
                print(
                    flush=True,
                )
                self.set_translations()
                self.run()
            else:
                print(
                    f"ERROR: MathJax directory not found: {mathjax_dir}\nPlease run the MathJax setup script or follow the manual instructions in the README."
                )
                raise RuntimeError(
                    "MathJax is required for LaTeX rendering. See README.md for setup instructions."
                )
        else:
            # Headless mode - just initialize core systems
            self.logger.info("Running in headless mode (no GUI)")
            self._init_headless_services()
            # Note: Call run() after __init__ to start headless event loop
            self.is_running = True

        # Initialize knowledge extraction system (works in both GUI and headless modes)
        self._initialize_knowledge_system()

    def _init_headless_services(self):
        """Initialize services for headless mode (no GUI).

        Creates minimal Qt event loop and starts HTTP API server.
        """
        # Create QCoreApplication for Qt event loop (needed by workers)
        # This is minimal Qt without any GUI components
        from PySide6.QtCore import QCoreApplication

        self.app = QCoreApplication.instance()
        if self.app is None:
            self.app = QCoreApplication([])
        self.app.api = self
        self.logger.info("Qt Core event loop initialized (headless mode)")

        # Initialize workers BEFORE starting HTTP server
        # so they're ready to handle requests immediately
        self._initialize_headless_workers()

        # Start API server for /llm, /art, /stt, /tts endpoints
        # Skip if we're being created from within an HTTP request handler
        # (server is already running in that case)
        if os.environ.get("AIRUNNER_SERVER_RUNNING") != "1":
            from airunner.components.server.api.api_server_thread import (
                APIServerThread,
            )

            host = os.environ.get("AIRUNNER_HTTP_HOST", "0.0.0.0")
            port = int(os.environ.get("AIRUNNER_HTTP_PORT", "8080"))

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
        """Initialize the automatic knowledge extraction system."""
        # Skip if knowledge system is disabled (e.g., in headless mode)
        if os.environ.get("AIRUNNER_KNOWLEDGE_ON", "1") == "0":
            self.logger.info("Knowledge system disabled")
            return

        try:
            from airunner.components.knowledge import (
                initialize_knowledge_system,
            )

            initialize_knowledge_system()
            self.logger.info("Knowledge extraction system initialized")

            # Run one-time knowledge migration if needed
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
            from airunner.utils.application.create_worker import (
                create_worker,
            )
            from airunner.components.application.gui.windows.main.worker_manager import (
                WorkerManager,
            )
            from airunner.components.application.gui.windows.main.model_load_balancer import (
                ModelLoadBalancer,
            )

            # Create WorkerManager - it registers LLM_TEXT_GENERATE_REQUEST_SIGNAL
            # and lazily creates workers (LLMGenerateWorker, SDWorker, etc.) as needed
            self._worker_manager = create_worker(WorkerManager)

            # CRITICAL: Eagerly initialize LLM worker so it's ready to receive signals
            # The worker must be created BEFORE any LLM requests are sent
            _ = self._worker_manager.llm_generate_worker
            self.logger.info("LLM worker initialized and ready")

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

    def _run_knowledge_migration_if_needed(self):
        """Run one-time migration from JSON to database if not already done.

        Uses database-level locking to prevent race conditions when multiple
        instances start simultaneously.
        """
        try:
            from pathlib import Path
            from airunner.settings import AIRUNNER_USER_DATA_PATH
            from airunner.components.data.session_manager import session_scope

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
                    self.logger.error("Application settings not found")
                    return

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
                    "Running one-time knowledge migration from JSON to database..."
                )

            # Migration runs outside the locked transaction
            from airunner.bin.airunner_migrate_knowledge import (
                KnowledgeMigrator,
            )

            migrator = KnowledgeMigrator(json_path=json_path)
            stats = migrator.migrate_all(dry_run=False, skip_backup=False)

            # Only mark complete if migration was successful
            if stats["errors"] > 0:
                self.logger.error(
                    f"Knowledge migration completed with {stats['errors']} errors. "
                    f"Migration NOT marked complete - will retry on next startup."
                )
                return

            self.logger.info(
                f"Knowledge migration successful: {stats['migrated']} facts migrated"
            )

            # Mark migration as complete (only if no errors)
            self._mark_migration_complete()

        except Exception as e:
            self.logger.error(
                f"Failed to run knowledge migration: {e}. "
                f"Migration NOT marked complete - will retry on next startup.",
                exc_info=True,
            )

    def _mark_migration_complete(self):
        """Mark knowledge migration as complete in settings."""
        try:
            from airunner.components.data.session_manager import session_scope

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

    def on_update_locale_signal(self, data: dict):
        self.set_translations(data)

    def set_translations(self, data: Optional[Dict] = None):
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
    def run_setup_wizard():
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
            from airunner.app_installer import AppInstaller

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
        translator = QTranslator()
        language_map = {
            QLocale.English: "english",
            QLocale.Japanese: "japanese",
        }
        base_name = language_map.get(locale.language(), "english")
        qm_path = os.path.join(translations_dir, f"{base_name}.qm")
        self.app.removeTranslator(translator)
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

    def on_log_logged_signal(self, data: dict):
        message = data["message"].split(" - ")
        self.update_splash_message(self.splash, message[4])

    def start(self):
        """
        Conditionally initialize and display the setup wizard.
        :return:
        """
        if not self.initialize_gui:
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
        from PySide6.QtGui import QSurfaceFormat

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
        self.app = QApplication.instance()
        if self.app is None:
            self.app = QApplication([])
        self.app.api = self
        # Set global tooltip style ONCE at startup
        set_global_tooltip_style()

    def run(self):
        """
        Run as a GUI application.
        A splash screen is displayed while the application is loading
        and a main window is displayed once the application is ready.
        Override this method to run the application in a different mode.
        """
        if not self.initialize_gui:
            # Headless mode - keep server running
            self.run_headless()
            return

        if not self.no_splash and not self.splash:
            self.splash = self.display_splash_screen(self.app)

        QTimer.singleShot(50, self._post_splash_startup)
        sys.exit(self.app.exec())

    def run_headless(self):
        """Run in headless mode without GUI.

        Uses Qt event loop to process worker signals while server runs.
        """
        from PySide6.QtCore import QTimer

        # Workers are already initialized in _init_headless_services()
        # No need to initialize again here

        self.logger.info("AI Runner headless mode - server running")
        self.logger.info("Press Ctrl+C to stop")

        # Qt event loop blocks Python signal handlers, so we need to
        # periodically allow Python to process signals
        # This timer does nothing but allows KeyboardInterrupt to be caught
        timer = QTimer()
        timer.start(500)  # Wake up every 500ms
        timer.timeout.connect(lambda: None)

        try:
            # Run Qt event loop (processes worker signals)
            sys.exit(self.app.exec())
        except KeyboardInterrupt:
            self.logger.info("Interrupted by user")
            self.cleanup()
            sys.exit(0)

    def _post_splash_startup(self):
        self.show_main_application(self.app)

    @staticmethod
    def signal_handler(_signal, _frame):
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

    def display_splash_screen(self, app):
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
    def update_splash_message(splash, message: str):
        if hasattr(splash, "show_message"):
            splash.show_message(message)
        else:
            splash.showMessage(
                message,
                QtCore.Qt.AlignmentFlag.AlignBottom
                | QtCore.Qt.AlignmentFlag.AlignCenter,
                QtCore.Qt.GlobalColor.white,
            )

    def show_main_application(self, app):
        """
        Show the main application window.
        :param app:
        :param splash:
        :return:
        """
        if not self.initialize_gui:
            return  # Skip showing the main application window if GUI is disabled

        window_class = self.main_window_class_
        if not window_class:
            from airunner.components.application.gui.windows.main.main_window import (
                MainWindow,
            )

            window_class = MainWindow

        if self.splash:
            self.splash.finish(None)

        try:
            window = window_class(app=self, **self.window_class_params)
            app.main_window = window
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

            # Emit shutdown signal for components to cleanup
            try:
                self.emit_signal(SignalCode.APPLICATION_SHUTDOWN_SIGNAL, {})
            except Exception as e:
                self.logger.warning(f"Error emitting shutdown signal: {e}")

            self.logger.info("App cleanup complete")

        except Exception as e:
            self.logger.error(f"Error during App cleanup: {e}", exc_info=True)

    def _ensure_mathjax(self):
        # Only run setup if MathJax is not present
        mathjax_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "static",
            "mathjax",
            f"MathJax-{MATHJAX_VERSION}",
            "es5",
        )
        os.makedirs(mathjax_dir, exist_ok=True)
        entry = os.path.join(mathjax_dir, "tex-mml-chtml.js")
        if not os.path.exists(entry):
            print("MathJax not found, attempting to download and set up...")
            try:
                subprocess.check_call(
                    [
                        sys.executable,
                        os.path.join(
                            os.path.dirname(__file__),
                            "bin",
                            "setup_mathjax.py",
                        ),
                    ]
                )
            except Exception as e:
                print("ERROR: MathJax setup failed:", e)
                raise RuntimeError(
                    "MathJax is required but could not be set up. See README.md for instructions."
                )

    def retranslate_ui_signal(self):
        pass


# Dummy classes for test patching
class AppInstaller:
    pass


class MainWindow:
    pass
