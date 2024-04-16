####################################################################################################
# SECURITY AND PRIVACY SETTINGS APPLIED HERE. DO NOT MODIFY THIS BLOCK
####################################################################################################
import socket
import sys


####################################################################################################
# NETWORK ACCESS CONTROL
# Completely disable network access
# OS environment variables must be initialized here before importing any other modules.
# This is due to the way huggingface diffusion models are imported.
####################################################################################################
def disable_network():
    def no_network(*args, **kwargs):
        raise RuntimeError("Network access is disabled")
    socket.socket = no_network
    socket.create_connection = no_network
    socket.connect = no_network
    socket.bind = no_network
####################################################################################################
# END OF NETWORK ACCESS CONTROL
####################################################################################################


####################################################################################################
# Set Hugging Face environment variables
####################################################################################################
import os
from airunner.settings import (
    HF_HUB_DISABLE_TELEMETRY,
    HF_HOME,
    HF_ENDPOINT,
    HF_INFERENCE_ENDPOINT,
    HF_HUB_DOWNLOAD_TIMEOUT,
    HF_HUB_ETAG_TIMEOUT,
    HF_HUB_DISABLE_PROGRESS_BARS,
    HF_HUB_DISABLE_SYMLINKS_WARNING,
    HF_HUB_DISABLE_EXPERIMENTAL_WARNING,
    HF_ASSETS_CACHE,
    HF_TOKEN,
    HF_HUB_VERBOSITY,
    HF_HUB_LOCAL_DIR_AUTO_SYMLINK_THRESHOLD,
    HF_HUB_DISABLE_IMPLICIT_TOKEN,
    HF_HUB_OFFLINE,
    HF_DATASETS_OFFLINE,
    TRANSFORMERS_OFFLINE,
    DIFFUSERS_VERBOSITY,
    DEFAULT_HF_INFERENCE_ENDPOINT,
    DEFAULT_HF_HUB_OFFLINE,
    DEFAULT_HF_ENDPOINT,
    DEFAULT_HF_DATASETS_OFFLINE,
    DEFAULT_TRANSFORMERS_OFFLINE,
    TRUST_REMOTE_CODE,
)


def set_huggingface_environment_variables(
    allow_downloads: bool = None,
    allow_remote_inference: bool = None
):
    """
    Set the environment variables for the Hugging Face Hub.
    :param allow_downloads:
    :param allow_remote_inference:
    :return:
    """
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = HF_HUB_DISABLE_TELEMETRY

    """
    Conditionally set environment variables which are used 
    to control the ability of the Hugging Face Hub and other
    related services to access the internet.
    
    We set environment variables so that we can ensure the applications
    are not overridden from any other source.
    """
    hf_hub_offline = HF_HUB_OFFLINE if not allow_downloads else DEFAULT_HF_HUB_OFFLINE
    hf_datasets_offline = HF_DATASETS_OFFLINE if not allow_downloads else DEFAULT_HF_DATASETS_OFFLINE
    transformers_offline = TRANSFORMERS_OFFLINE if not allow_downloads else DEFAULT_TRANSFORMERS_OFFLINE
    hf_endpoint = HF_ENDPOINT if not allow_downloads else DEFAULT_HF_ENDPOINT
    hf_inf_endpoint = HF_INFERENCE_ENDPOINT if not allow_downloads else DEFAULT_HF_INFERENCE_ENDPOINT
    os.environ["HF_ENDPOINT"] = hf_endpoint
    os.environ["HF_DATASETS_OFFLINE"] = hf_datasets_offline
    os.environ["TRANSFORMERS_OFFLINE"] = transformers_offline
    os.environ["HF_INFERENCE_ENDPOINT"] = hf_inf_endpoint
    os.environ["HF_HUB_OFFLINE"] = hf_hub_offline

    """
    Set the remaining environment variables for the Hugging Face Hub.
    """
    os.environ["HF_HOME"] = HF_HOME
    os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = HF_HUB_DISABLE_PROGRESS_BARS
    os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = HF_HUB_DISABLE_SYMLINKS_WARNING
    os.environ["HF_HUB_DISABLE_EXPERIMENTAL_WARNING"] = HF_HUB_DISABLE_EXPERIMENTAL_WARNING
    os.environ["HF_ASSETS_CACHE"] = HF_ASSETS_CACHE
    os.environ["HF_TOKEN"] = HF_TOKEN
    os.environ["HF_HUB_VERBOSITY"] = HF_HUB_VERBOSITY
    os.environ["HF_HUB_LOCAL_DIR_AUTO_SYMLINK_THRESHOLD"] = HF_HUB_LOCAL_DIR_AUTO_SYMLINK_THRESHOLD
    os.environ["HF_HUB_DOWNLOAD_TIMEOUT"] = HF_HUB_DOWNLOAD_TIMEOUT
    os.environ["HF_HUB_ETAG_TIMEOUT"] = HF_HUB_ETAG_TIMEOUT
    os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = HF_HUB_DISABLE_IMPLICIT_TOKEN
    os.environ["DIFFUSERS_VERBOSITY"] = DIFFUSERS_VERBOSITY
    os.environ["TRUST_REMOTE_CODE"] = TRUST_REMOTE_CODE


set_huggingface_environment_variables()
####################################################################################################
# END OF SECURITY AND PRIVACY SETTINGS
####################################################################################################


import signal
import traceback
from functools import partial
from PySide6 import QtCore
from PySide6.QtCore import QObject, QTimer
from PySide6.QtGui import QGuiApplication, QPixmap, Qt, QWindow
from PySide6.QtWidgets import QApplication, QSplashScreen
from airunner.mediator_mixin import MediatorMixin
from airunner.utils import get_version
from airunner.windows.main.main_window import MainWindow
from airunner.windows.main.settings_mixin import SettingsMixin
from airunner.windows.setup_wizard.setup_wizard import SetupWizard


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
        self.wizard = None
        self.app = None

        """
        Disable the network to prevent any network access.
        """
        disable_network()

        """
        Mediator and Settings mixins are initialized here, enabling the application
        to easily access the application settings dictionary.
        """
        MediatorMixin.__init__(self)
        SettingsMixin.__init__(self)
        super(App, self).__init__()

        self.start()

    @property
    def do_show_setup_wizard(self) -> bool:
        """
        This flag is used to determine if the setup wizard should be displayed.
        If the setup wizard has not been dcompleted, various agreements have not been accepted,
        or the paths have not been initialized, the setup wizard will be displayed.
        :return: bool
        """
        return (
            self.settings["run_setup_wizard"] or
            not self.settings["paths_initialized"] or
            not self.settings["agreements"]["user"] or
            not self.settings["agreements"]["stable_diffusion"] or
            not self.settings["agreements"]["airunner"]
        )

    def start(self):
        """
        Conditionally initialize and display the setup wizard.
        :return:
        """
        signal.signal(signal.SIGINT, self.signal_handler)
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseDesktopOpenGL)
        self.app = QApplication([])

        if self.do_show_setup_wizard:
            self.wizard = SetupWizard()
            self.wizard.exec()

        # Quit the application if the setup wizard was not completed
        if self.do_show_setup_wizard:
            sys.exit(0)

    def run(self):
        """
        Run as a GUI application.
        A splash screen is displayed while the application is loading
        and a main window is displayed once the application is ready.

        Override this method to run the application in a different mode.
        """

        # Continue with application execution
        splash = self.display_splash_screen(self.app)

        # Show the main application window
        QTimer.singleShot(
            50,
            partial(
                self.show_main_application,
                self.app,
                splash
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
        pixmap = QPixmap("images/splashscreen.png")
        splash = QSplashScreen(
            screen,
            pixmap,
            QtCore.Qt.WindowType.WindowStaysOnTopHint
        )
        splash.show()
        # make message white
        splash.showMessage(
            f"Loading AI Runner v{get_version()}",
            QtCore.Qt.AlignmentFlag.AlignBottom | QtCore.Qt.AlignmentFlag.AlignCenter,
            QtCore.Qt.GlobalColor.white
        )
        app.processEvents()
        return splash

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
