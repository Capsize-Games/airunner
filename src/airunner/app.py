from typing import Optional, Dict
import glob
import logging
import os.path
import signal
import traceback
from pathlib import Path
from PySide6 import QtCore
from PySide6.QtCore import QObject, QTimer
from PySide6.QtGui import QGuiApplication, Qt, QWindow
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTranslator, QLocale

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
    MATHJAX_VERSION,
    QTWEBENGINE_REMOTE_DEBUGGING,  # Add this import
)
from airunner.components.server.local_http_server import LocalHttpServerThread
from airunner.components.splash_screen.splash_screen import SplashScreen
import os
import subprocess
import sys
from airunner.settings import LOCAL_SERVER_PORT

# Enable LNA mode for local server if AIRUNNER_LNA_ENABLED=1
LNA_ENABLED = os.environ.get("AIRUNNER_LNA_ENABLED", "0") == "1"

os.environ["QTWEBENGINE_REMOTE_DEBUGGING"] = QTWEBENGINE_REMOTE_DEBUGGING

from PySide6.QtWebEngineCore import QWebEngineSettings, QWebEnginePage
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import qVersion


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
        Initialize the application and run as a GUI application or a socket server.
        :param main_window_class: The main window class to use for the application.
        """
        self.main_window_class_ = main_window_class
        self.window_class_params = window_class_params or {}
        self.no_splash = no_splash
        self.app = None
        self.splash = None
        self.initialize_gui = initialize_gui  # Store the flag
        self.http_server_thread = None

        """
        Mediator and Settings mixins are initialized here, enabling the application
        to easily access the application settings dictionary.
        """
        super().__init__()

        self.register(SignalCode.LOG_LOGGED_SIGNAL, self.on_log_logged_signal)
        self.register(SignalCode.UPATE_LOCALE, self.on_update_locale_signal)

        self._ensure_mathjax()

        # Start HTTPS server for static assets (MathJax and content widgets)
        static_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "static")
        )
        # Find all components/**/gui/static directories
        components_static_dirs = glob.glob(
            os.path.join(
                os.path.dirname(__file__), "components", "**", "gui", "static"
            ),
            recursive=True,
        )
        # Add user web dir if it exists
        static_search_dirs = [static_dir] + components_static_dirs
        if os.path.isdir(self.user_web_dir):
            static_search_dirs.append(self.user_web_dir)
        mathjax_dir = os.path.join(
            static_dir, "mathjax", f"MathJax-{MATHJAX_VERSION}", "es5"
        )
        if self.initialize_gui and os.path.isdir(mathjax_dir):
            logging.info("Starting local HTTPS server for static assets.")
            self.http_server_thread = LocalHttpServerThread(
                directory=static_dir,
                additional_directories=static_search_dirs[1:],
                port=LOCAL_SERVER_PORT,
                lna_enabled=LNA_ENABLED,  # Pass LNA mode to server
            )
            self.http_server_thread.start()
            self.start()
            self.set_translations()
            self.run()
        elif self.initialize_gui:
            print(
                f"ERROR: MathJax directory not found: {mathjax_dir}\nPlease run the MathJax setup script or follow the manual instructions in the README."
            )
            raise RuntimeError(
                "MathJax is required for LaTeX rendering. See README.md for setup instructions."
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
        from airunner.components.llm.gui.widgets.message_widget import (
            set_global_tooltip_style,
        )

        set_global_tooltip_style()

    def run(self):
        """
        Run as a GUI application.
        A splash screen is displayed while the application is loading
        and a main window is displayed once the application is ready.
        Override this method to run the application in a different mode.
        """
        if not self.initialize_gui:
            return

        if not self.no_splash and not self.splash:
            self.splash = self.display_splash_screen(self.app)

        QTimer.singleShot(50, self._post_splash_startup)
        sys.exit(self.app.exec())

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
            from airunner.utils.settings import get_qsettings

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
                        settings = widget.settings()
                        settings.setAttribute(
                            QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows,
                            True,
                        )
                        settings.setAttribute(
                            QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls,
                            True,
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
        if self.http_server_thread:
            self.http_server_thread.stop()
            self.http_server_thread.wait()

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
