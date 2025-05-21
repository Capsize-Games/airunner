from typing import Optional, Dict
import os.path
import sys
import signal
import traceback
from pathlib import Path
from PySide6 import QtCore
from PySide6.QtCore import QObject, QTimer
from PySide6.QtGui import QGuiApplication, QPixmap, Qt, QWindow, QPainter
from PySide6.QtWidgets import QApplication, QSplashScreen
from PySide6.QtCore import QTranslator, QLocale

from airunner.data.models.language_settings import LanguageSettings
from airunner.data.models.path_settings import PathSettings
from airunner.enums import (
    LANGUAGE_TO_LOCALE_MAP,
    AVAILABLE_LANGUAGES,
    LOCALE_TO_LANGUAGE_MAP,
    AvailableLanguage,
    SignalCode,
)
from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.gui.windows.main.settings_mixin import SettingsMixin
from airunner.data.models.application_settings import ApplicationSettings
from airunner.settings import (
    AIRUNNER_DISABLE_SETUP_WIZARD,
    AIRUNNER_DISCORD_URL,  # Add this import
)
from airunner.gui.widgets.llm.local_http_server import LocalHttpServerThread
import os
import subprocess
import sys


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

        # Only start HTTP server if MathJax is present
        mathjax_dir = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "static",
                "mathjax",
                "MathJax-3.2.2",
                "es5",
            )
        )
        if self.initialize_gui and os.path.isdir(mathjax_dir):
            self.http_server_thread = LocalHttpServerThread(
                directory=mathjax_dir, port=8765
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
        from airunner.gui.widgets.llm.message_widget import (
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
        Display a splash screen while the application is loading.
        :param app:
        :return:
        """
        if self.no_splash:
            return

        screens = QGuiApplication.screens()
        try:
            screen = screens.at(0)
        except AttributeError:
            screen = screens[0]

        base_dir = Path(os.path.dirname(os.path.realpath(__file__)))
        image_path = base_dir / "gui" / "images" / "splashscreen.png"
        original_pixmap = QPixmap(image_path)

        # Create a new transparent pixmap the size of the screen
        screen_size = screen.geometry().size()
        centered_pixmap = QPixmap(screen_size)
        centered_pixmap.fill(Qt.transparent)

        # Calculate center position for the original pixmap
        x_pos = (screen_size.width() - original_pixmap.width()) // 2
        y_pos = (screen_size.height() - original_pixmap.height()) // 2

        # Draw the original pixmap onto the centered position of the full-screen pixmap
        painter = QPainter(centered_pixmap)
        painter.drawPixmap(x_pos, y_pos, original_pixmap)
        painter.end()

        splash = QSplashScreen(screen, centered_pixmap)
        splash.setMask(centered_pixmap.mask())

        # make splash screen transparent and full size
        splash.setAttribute(Qt.WA_TranslucentBackground)
        splash.setGeometry(
            screen.geometry().x(),
            screen.geometry().y(),
            screen.geometry().width(),
            screen.geometry().height() - original_pixmap.height(),
        )
        splash.setWindowFlags(
            QtCore.Qt.WindowType.FramelessWindowHint
            | QtCore.Qt.WindowType.WindowStaysOnTopHint
            | QtCore.Qt.WindowType.SplashScreen
        )
        splash.show()
        App.update_splash_message(splash, f"Loading AI Runner")
        app.processEvents()
        return splash

    @staticmethod
    def update_splash_message(splash, message: str):
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
            from airunner.gui.windows.main.main_window import MainWindow

            window_class = MainWindow

        if self.splash:
            self.splash.finish(None)

        try:
            window = window_class(app=self, **self.window_class_params)
            app.main_window = window
            window.raise_()
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
            os.path.dirname(__file__),
            "..",
            "static",
            "mathjax",
            "MathJax-3.2.2",
            "es5",
        )
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
