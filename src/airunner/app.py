################################################################
# Importing this module sets the Hugging Face environment
# variables for the application.
################################################################
import os.path
import sys
import signal
import traceback
from functools import partial
from pathlib import Path
from importlib.metadata import version

from PySide6 import QtCore
from PySide6.QtCore import (
    QObject,
    QTimer
)
from PySide6.QtGui import (
    QGuiApplication,
    QPixmap,
    Qt,
    QWindow
)
from PySide6.QtWidgets import (
    QApplication,
    QSplashScreen
)

from airunner.app_installer import AppInstaller
from airunner.enums import SignalCode
from airunner.mediator_mixin import MediatorMixin
from airunner.windows.main.settings_mixin import SettingsMixin
from airunner.data.models import ApplicationSettings
from airunner.windows.main.main_window import MainWindow


class App(
    QObject,
    SettingsMixin,
    MediatorMixin
):
    """
    The main application class for AI Runner.
    This class can be run as a GUI application or as a socket server.
    """
    def __init__(
        self,
        main_window_class: QWindow = None
    ):
        """
        Initialize the application and run as a GUI application or a socket server.
        :param main_window_class: The main window class to use for the application.
        """
        self.main_window_class_ = main_window_class or MainWindow
        self.app = None
        self.splash = None

        """
        Mediator and Settings mixins are initialized here, enabling the application
        to easily access the application settings dictionary.
        """
        MediatorMixin.__init__(self)
        super(App, self).__init__()

        self.register(SignalCode.LOG_LOGGED_SIGNAL, self.on_log_logged_signal)

        self.start()
        self.run_setup_wizard()

        current_version = version("airunner")
        if self.do_upgrade(current_version):
            self.handle_upgrade(current_version)
        self.run()
    
    def do_upgrade(self, current_version) -> bool:
        current_version_tuple = tuple(map(int, current_version.split(".")))
        try:
            app_version_tuple = tuple(map(int, self.application_settings.app_version.split(".")))
        except ValueError:
            return True
        except AttributeError:
            return True
        return app_version_tuple < current_version_tuple


    def handle_upgrade(self, current_version):
        from airunner.data.bootstrap.pipeline_bootstrap_data import pipeline_bootstrap_data
        from airunner.data.models import PipelineModel
        for model in pipeline_bootstrap_data:
            pipelinemodel = PipelineModel.objects.filter_by(
                pipeline_action= model["pipeline_action"],
                version=model["version"],
                category=model["category"],
                classname=model["classname"],
                default=model["default"]
            ).first()
            if pipelinemodel:
                continue
            pipelinemodel = PipelineModel()
            pipelinemodel.pipeline_action = model["pipeline_action"]
            pipelinemodel.version = model["version"]
            pipelinemodel.category = model["category"]
            pipelinemodel.classname = model["classname"]
            pipelinemodel.default = model["default"]
            pipelinemodel.save()
        try:
            app_version_tuple = tuple(map(int, self.application_settings.app_version.split(".")))
        except ValueError:
            app_version_tuple = None
        except AttributeError:
            app_version_tuple = None
        if app_version_tuple is None or app_version_tuple < (3, 1, 10):
            turbo_paths = (
                os.path.expanduser(os.path.join(
                    self.path_settings.base_path, "art/models", "SDXL 1.0", "txt2img", "turbo_models"
                )),
                os.path.expanduser(os.path.join(
                    self.path_settings.base_path, "art/models", "SDXL 1.0", "inpaint", "turbo_models"
                ))
            )
            for turbo_path in turbo_paths:
                if not os.path.exists(turbo_path):
                    os.makedirs(turbo_path)
                    with open(os.path.join(turbo_path, "README.txt"), "w") as f:
                        f.write("Place Stable Diffusion XL Turbo, Lightning and Hyper models here")
            self.application_settings.run_setup_wizard = True
            self.run_setup_wizard()
            self.application_settings.app_version = current_version
            self.llm_generator_settings.model_version = "w4ffl35/Ministral-8B-Instruct-2410-doublequant"
            self.application_settings.save()
            self.llm_generator_settings.save()

    def run_setup_wizard(self):
        application_settings = ApplicationSettings.objects.first()
        if application_settings.run_setup_wizard:
            AppInstaller()

    def on_log_logged_signal(self, data: dict):
        message = data["message"].split(" - ")
        self.update_splash_message(self.splash, message[4])

    def start(self):
        """
        Conditionally initialize and display the setup wizard.
        :return:
        """
        signal.signal(signal.SIGINT, self.signal_handler)
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseDesktopOpenGL)
        self.app = QApplication([])

    def run(self):
        """
        Run as a GUI application.
        A splash screen is displayed while the application is loading
        and a main window is displayed once the application is ready.

        Override this method to run the application in a different mode.
        """
        # Continue with application execution
        self.splash = self.display_splash_screen(self.app)

        # Show the main application window
        QTimer.singleShot(
            50,
            partial(
                self.show_main_application,
                self.app,
                self.splash
            )
        )
        sys.exit(self.app.exec())

    @staticmethod
    def signal_handler(
        _signal,
        _frame
    ):
        """
        Handle the SIGINT signal in a clean way.
        :param _signal:
        :param _frame:
        :return: None
        """
        print("\nExiting...")
        try:
            app = QApplication.instance()
            app.quit()
            sys.exit(0)
        except Exception as e:
            print(e)
            sys.exit(0)

    @staticmethod
    def display_splash_screen(app):
        """
        Display a splash screen while the application is loading.
        :param app:
        :return:
        """
        screens = QGuiApplication.screens()
        try:
            screen = screens.at(0)
        except AttributeError:
            screen = screens[0]

        base_dir = Path(os.path.dirname(os.path.realpath(__file__)))
        stylesheet_path = base_dir / "images" / "splashscreen.png"
        pixmap = QPixmap(stylesheet_path)
        splash = QSplashScreen(
            screen,
            pixmap,
            QtCore.Qt.WindowType.WindowStaysOnTopHint
        )
        splash.show()
        App.update_splash_message(splash, f"Loading AI Runner")
        app.processEvents()
        return splash

    @staticmethod
    def update_splash_message(splash, message: str):
        splash.showMessage(
            message,
            QtCore.Qt.AlignmentFlag.AlignBottom | QtCore.Qt.AlignmentFlag.AlignCenter,
            QtCore.Qt.GlobalColor.white
        )

    def show_main_application(
        self,
        app,
        splash
    ):
        """
        Show the main application window.
        :param app:
        :param splash:
        :return:
        """
        try:
            window = self.main_window_class_()
        except Exception as e:
            traceback.print_exc()
            print(e)
            splash.finish(None)
            sys.exit("""
                An error occurred while initializing the application.
                Please report this issue on GitHub or Discord."
            """)
        app.main_window = window
        splash.finish(window)
        window.raise_()
