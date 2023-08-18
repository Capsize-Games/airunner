import os

from airunner.main_window import MainWindow

"""
OS environment variables must be initialized here before importing any other modules.
This is due to the way huggingface diffusion models are imported.
"""
from airunner.aihandler.settings_manager import SettingsManager
settings_manager = SettingsManager()
hf_cache_path = settings_manager.settings.hf_cache_path.get()
if hf_cache_path != "":
    # check if hf_cache_path exists
    if os.path.exists(hf_cache_path):
        os.unsetenv("HUGGINGFACE_HUB_CACHE")
        os.environ["HUGGINGFACE_HUB_CACHE"] = hf_cache_path
os.environ["DISABLE_TELEMETRY"] = "1"

import argparse
import signal
import sys
import traceback
from functools import partial
from PyQt6 import QtCore
from PyQt6.QtWidgets import QApplication, QSplashScreen
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QGuiApplication, QPixmap

from airunner.aihandler.settings import SERVER
from airunner.aihandler.socket_server import SocketServer
from airunner.utils import get_version


if __name__ == "__main__":
    def signal_handler(_signal, _frame):
        print("\nExiting...")
        sys.exit(0)

    def display_splash_screen(app):
        screens = QGuiApplication.screens()
        try:
            screen = screens.at(0)
        except AttributeError:
            screen = screens[0]
        pixmap = QPixmap("src/splashscreen.png")
        splash = QSplashScreen(screen, pixmap, QtCore.Qt.WindowType.WindowStaysOnTopHint)
        splash.show()
        # make message white
        splash.showMessage(f"Loading AI Runner v{get_version()}", QtCore.Qt.AlignmentFlag.AlignBottom | QtCore.Qt.AlignmentFlag.AlignCenter, QtCore.Qt.GlobalColor.white)
        app.processEvents()
        return splash

    def show_main_application(splash):
        try:
            window = MainWindow()
        except Exception as e:
            # print a stacktrace to see where the original error occurred
            # we want to see the original error path using the traceback
            traceback.print_exc()

            print(e)
            splash.finish(None)
            sys.exit("""
                An error occurred while initializing the application. 
                Please report this issue on GitHub or Discord."
            """)
        splash.finish(window)
        window.raise_()

    # argument parsing for socket server
    parser = argparse.ArgumentParser()
    parser.add_argument("--ss", action="store_true", default=False)
    parser.add_argument("--host", default=SERVER["host"])
    parser.add_argument("--port", default=SERVER["port"])
    parser.add_argument("--keep-alive", action="store_true", default=False)
    parser.add_argument("--packet-size", default=SERVER["port"])
    args = parser.parse_args()

    if args.ss:
        SocketServer(
            host=args.host,
            port=args.port,
            keep_alive=args.keep_alive,
            packet_size=args.packet_size
        )
    else:
        signal.signal(signal.SIGINT, signal_handler)
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseDesktopOpenGL)
        app = QApplication([])

        splash = display_splash_screen(app)

        QTimer.singleShot(50, partial(show_main_application, splash))

        sys.exit(app.exec())
