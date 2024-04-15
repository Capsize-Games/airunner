####################################################################################################
# SECURITY AND PRIVACY SETTINGS APPLIED HERE. DO NOT MODIFY THIS BLOCK
####################################################################################################
import argparse
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
    HF_HUB_DISABLE_IMPLICIT_TOKEN, HF_ALLOW_DOWNLOADS,
    HF_HUB_OFFLINE,
    HF_DATASETS_OFFLINE,
    TRANSFORMERS_OFFLINE,
    DIFFUSERS_VERBOSITY,
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
    allow_downloads = HF_ALLOW_DOWNLOADS if allow_downloads is None else allow_downloads

    if allow_downloads:
        os.environ["HF_ALLOW_DOWNLOADS"] = "1"

    os.environ["HF_HUB_DISABLE_TELEMETRY"] = HF_HUB_DISABLE_TELEMETRY
    os.environ["HF_HUB_OFFLINE"] = HF_HUB_OFFLINE
    os.environ["HF_HOME"] = HF_HOME
    os.environ["HF_ENDPOINT"] = HF_ENDPOINT
    os.environ["HF_INFERENCE_ENDPOINT"] = HF_INFERENCE_ENDPOINT
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
    os.environ["HF_DATASETS_OFFLINE"] = HF_DATASETS_OFFLINE
    os.environ["TRANSFORMERS_OFFLINE"] = TRANSFORMERS_OFFLINE
    os.environ["DIFFUSERS_VERBOSITY"] = DIFFUSERS_VERBOSITY


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
from airunner.settings import SERVER
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
        self.args = self.prepare_argument_parser()

        """
        If the --enable-network flag is passed then network access is enabled.
        By default we are disabling network access.
        """
        if not self.args.enable_network:
            disable_network()

        """
        Mediator and Settings mixins are initialized here, enabling the application
        to easily access the application settings dictionary.
        """
        MediatorMixin.__init__(self)
        SettingsMixin.__init__(self)
        super(App, self).__init__()

        """
        If the --ss flag is passed, we will start a socket server.
        By default the application is loaded as a GUI.
        """
        if self.args.ss:
            self.run_socket_server()
        else:
            self.run_gui_application()

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

    def run_socket_server(self):
        """
        Run as a socket server if --ss flag is passed.
        This can be used to run the application on a remote machine or
        to be accessed by other applications.
        The old socket server implementation has been removed so this method is empty.
        """
        # SocketServer(
        #     host=args.host,
        #     port=args.port,
        #     keep_alive=args.keep_alive,
        #     packet_size=args.packet_size
        # )
        pass

    def run_gui_application(self):
        """
        Run as a GUI application.
        A splash screen is displayed while the application is loading
        and a main window is displayed once the application is ready.
        """
        signal.signal(signal.SIGINT, self.signal_handler)
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseDesktopOpenGL)
        app = QApplication([])

        # Initialize and conditionally display the setup wizard
        if self.do_show_setup_wizard:
            self.wizard = SetupWizard()
            self.wizard.exec()

        # Quit the application if the setup wizard was not completed
        if self.do_show_setup_wizard:
            sys.exit(0)

        # Continue with application execution
        splash = self.display_splash_screen(app)

        # Show the main application window
        QTimer.singleShot(
            50,
            partial(
                self.show_main_application,
                app,
                splash
            )
        )
        sys.exit(app.exec())

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

    @staticmethod
    def prepare_argument_parser():
        """
        Prepare the argument parser for the application.
        :return:
        """
        parser = argparse.ArgumentParser()
        parser.add_argument("--enable-network", action="store_true", default=False)
        parser.add_argument("--ss", action="store_true", default=False)
        parser.add_argument("--host", default=SERVER["host"])
        parser.add_argument("--port", default=SERVER["port"])
        parser.add_argument("--keep-alive", action="store_true", default=False)
        parser.add_argument("--packet-size", default=SERVER["port"])
        return parser.parse_args()
