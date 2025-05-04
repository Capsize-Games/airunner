from typing import Optional, Dict
import os.path
import sys
import signal
import traceback
from functools import partial
from pathlib import Path
from PySide6 import QtCore
from PySide6.QtCore import QObject, QTimer
from PySide6.QtGui import QGuiApplication, QPixmap, Qt, QWindow
from PySide6.QtWidgets import QApplication, QSplashScreen

from airunner.enums import SignalCode
from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.gui.windows.main.settings_mixin import SettingsMixin
from airunner.data.models.application_settings import ApplicationSettings
from airunner.settings import (
    AIRUNNER_DISCORD_URL,
    AIRUNNER_DISABLE_SETUP_WIZARD,
)


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

        """
        Mediator and Settings mixins are initialized here, enabling the application
        to easily access the application settings dictionary.
        """
        super().__init__()

        self.register(SignalCode.LOG_LOGGED_SIGNAL, self.on_log_logged_signal)

        if self.initialize_gui:
            self.start()
            self.run_setup_wizard()
            self.run()

    @staticmethod
    def run_setup_wizard():
        if AIRUNNER_DISABLE_SETUP_WIZARD:
            return
        application_settings = ApplicationSettings.objects.first()
        if application_settings.run_setup_wizard:
            from airunner.app_installer import AppInstaller

            AppInstaller()

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

    def run(self):
        """
        Run as a GUI application.
        A splash screen is displayed while the application is loading
        and a main window is displayed once the application is ready.
        Override this method to run the application in a different mode.
        """
        if not self.initialize_gui:
            return  # Skip running the GUI if the flag is False

        # Ensure only one splash screen is created
        if not self.no_splash and not self.splash:
            self.splash = self.display_splash_screen(self.app)

        # Show the main application window
        QTimer.singleShot(50, partial(self.show_main_application, self.app))
        sys.exit(self.app.exec())

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
        stylesheet_path = base_dir / "gui" / "images" / "splashscreen.png"
        pixmap = QPixmap(stylesheet_path)
        splash = QSplashScreen(
            screen, pixmap, QtCore.Qt.WindowType.WindowStaysOnTopHint
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
