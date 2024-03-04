"""
*******************************************************************************
Do not import anything prior to this block.
OS environment variables must be initialized here before importing any other modules.
This is due to the way huggingface diffusion models are imported.
*******************************************************************************
"""
import os
import torch
torch.backends.cuda.matmul.allow_tf32 = True

hf_cache_path = ""
if hf_cache_path != "":
    # check if hf_cache_path exists
    if os.path.exists(hf_cache_path):
        os.unsetenv("HUGGINGFACE_HUB_CACHE")
        os.environ["HUGGINGFACE_HUB_CACHE"] = hf_cache_path
os.environ["DISABLE_TELEMETRY"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
"""
*******************************************************************************
All remaining imports must be below this block.
*******************************************************************************
"""

import threading
import argparse
import signal
import sys
import traceback
from functools import partial
from PyQt6 import QtCore
from PyQt6.QtWidgets import QApplication, QSplashScreen
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QGuiApplication, QPixmap

from airunner.process_qss import Watcher, process_qss, build_ui
from airunner.windows.main.main_window import MainWindow
from airunner.settings import SERVER
from airunner.utils import get_version

def watch_frontend_files():
    # get absolute path to this file
    here = os.path.abspath(os.path.dirname(__file__))
    directories_to_watch = [
        os.path.join(here, "styles/dark_theme"), 
        # os.path.join(here, "styles/light_theme"),
        os.path.join(here, "widgets"),  # Add the widgets directory
        os.path.join(here, "windows")  # Add the windows directory
    ]  # Add more directories as needed
    scripts_to_run = {".qss": process_qss, ".ui": build_ui}  # Change this to your desired script paths
    ignore_files = ["styles.qss"]          # List of filenames to ignore
    
    watcher = Watcher(directories_to_watch, scripts_to_run, ignore_files)
    watcher_thread = threading.Thread(target=watcher.run)
    watcher_thread.start()
    return watcher


if __name__ == "__main__":
    def signal_handler(_signal, _frame):
        print("\nExiting...")
        try:
            app = QApplication.instance()
            app.quit()
            sys.exit(0)
        except Exception as e:
            print(e)
            sys.exit(0)

    def display_splash_screen(app):
        screens = QGuiApplication.screens()
        try:
            screen = screens.at(0)
        except AttributeError:
            screen = screens[0]
        pixmap = QPixmap("images/splashscreen.png")
        splash = QSplashScreen(screen, pixmap, QtCore.Qt.WindowType.WindowStaysOnTopHint)
        splash.show()
        # make message white
        splash.showMessage(f"Loading AI Runner v{get_version()}", QtCore.Qt.AlignmentFlag.AlignBottom | QtCore.Qt.AlignmentFlag.AlignCenter, QtCore.Qt.GlobalColor.white)
        app.processEvents()
        return splash

    def show_main_application(app, splash, watch_files=False):
        try:
            window = MainWindow()
            if watch_files:
                print("Watching style files for changes...")
                # get existing app
                watcher = watch_frontend_files()
                watcher.emitter.file_changed.connect(window.redraw)
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

    def prepare_argparser():
        parser = argparse.ArgumentParser()
        parser.add_argument("--ss", action="store_true", default=False)
        parser.add_argument("--host", default=SERVER["host"])
        parser.add_argument("--port", default=SERVER["port"])
        parser.add_argument("--keep-alive", action="store_true", default=False)
        parser.add_argument("--packet-size", default=SERVER["port"])
        parser.add_argument("--watch-files", action="store_true", default=False)
        return parser.parse_args()

    args = prepare_argparser()

    if args.ss:
        """
        Run as a socket server if --ss flag is passed.
        This can be used to run the application on a remote machine or
        to be accessed by other applications.
        """
        SocketServer(
            host=args.host,
            port=args.port,
            keep_alive=args.keep_alive,
            packet_size=args.packet_size
        )
    else:
        """
        Run as a GUI application.
        A splash screen is displayed while the application is loading
        and a main window is displayed once the application is ready.
        """
        signal.signal(signal.SIGINT, signal_handler)
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseDesktopOpenGL)
        app = QApplication([])

        splash = display_splash_screen(app)

        QTimer.singleShot(50, partial(show_main_application, app, splash, args.watch_files))

        sys.exit(app.exec())
