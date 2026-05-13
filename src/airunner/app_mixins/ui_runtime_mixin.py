"""GUI runtime, splash-screen, and shutdown helpers for App."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
import traceback
import gc
from pathlib import Path
from typing import Optional
from typing import TYPE_CHECKING

from PySide6 import QtCore
from PySide6.QtCore import QCoreApplication, QThread, QTimer, qVersion
from PySide6.QtGui import QGuiApplication, Qt, QSurfaceFormat
from PySide6.QtWidgets import QApplication

from airunner.components.splash_screen.splash_screen import SplashScreen
from airunner.enums import SignalCode
from airunner.qt_runtime_env import configure_early_qt_environment
from airunner.settings import AIRUNNER_BUG_REPORT_LINK
from airunner.settings import MATHJAX_VERSION
from airunner.settings import QTWEBENGINE_REMOTE_DEBUGGING
from airunner.utils.settings import get_qsettings

_AIRUNNER_IS_HEADLESS = os.environ.get("AIRUNNER_HEADLESS", "0") == "1"
_QT_RUNTIME_PREPARED = False
_CAPTURING_WEBENGINE_PAGE_CLASS = None

if TYPE_CHECKING:
    from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
    from PySide6.QtWebEngineWidgets import QWebEngineView


def _prefer_software_rendering() -> bool:
    """Return whether Qt is already configured for software rendering."""
    return any(
        (
            os.environ.get("QT_QUICK_BACKEND") == "software",
            os.environ.get("QT_OPENGL") == "software",
            os.environ.get("QT_XCB_GL_INTEGRATION") == "none",
            os.environ.get("LIBGL_ALWAYS_SOFTWARE") == "1",
        )
    )


def _configure_qt_environment() -> None:
    """Set Qt environment variables before QApplication exists."""
    configure_early_qt_environment()
    os.environ.setdefault(
        "QTWEBENGINE_REMOTE_DEBUGGING",
        QTWEBENGINE_REMOTE_DEBUGGING,
    )
    os.environ.setdefault("LIBGL_ALWAYS_SOFTWARE", "0")
    if _prefer_software_rendering():
        return

    os.environ.setdefault("QT_OPENGL", "desktop")
    if os.environ.get("XDG_SESSION_TYPE") == "x11" or os.environ.get(
        "DISPLAY"
    ):
        os.environ.setdefault("QT_XCB_GL_INTEGRATION", "xcb_glx")
        if os.environ.get("QT_XCB_GL_INTEGRATION") == "xcb_glx":
            print("X11 session detected - enabling GLX")
    elif os.environ.get("WAYLAND_DISPLAY"):
        print("Wayland session detected - using default EGL")


def _configure_qt_surface_format() -> None:
    """Set the default Qt surface format for desktop OpenGL."""
    if _prefer_software_rendering():
        return

    fmt = QSurfaceFormat()
    fmt.setVersion(3, 3)
    fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
    fmt.setSwapBehavior(QSurfaceFormat.SwapBehavior.DoubleBuffer)
    fmt.setDepthBufferSize(24)
    fmt.setStencilBufferSize(8)
    QSurfaceFormat.setDefaultFormat(fmt)


def _configure_qt_attributes() -> None:
    """Set QApplication attributes before any application exists."""
    if QCoreApplication.instance() is not None:
        return
    if _prefer_software_rendering():
        QApplication.setAttribute(
            Qt.ApplicationAttribute.AA_UseSoftwareOpenGL
        )
    else:
        QApplication.setAttribute(
            Qt.ApplicationAttribute.AA_UseDesktopOpenGL
        )
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)


def prepare_qt_runtime() -> None:
    """Configure Qt runtime once before any QApplication is created."""
    global _QT_RUNTIME_PREPARED
    if _AIRUNNER_IS_HEADLESS or _QT_RUNTIME_PREPARED:
        return
    _configure_qt_environment()
    _configure_qt_surface_format()
    _configure_qt_attributes()
    _QT_RUNTIME_PREPARED = True


def _get_webengine_classes():
    """Import WebEngine classes only after Qt runtime setup."""
    if _AIRUNNER_IS_HEADLESS:
        raise RuntimeError("Qt WebEngine is unavailable in headless mode.")

    from PySide6.QtWebEngineCore import QWebEnginePage
    from PySide6.QtWebEngineCore import QWebEngineSettings
    from PySide6.QtWebEngineWidgets import QWebEngineView

    return QWebEnginePage, QWebEngineSettings, QWebEngineView


def _get_capturing_webengine_page_class():
    """Return the lazy WebEngine page subclass used for JS console logs."""
    global _CAPTURING_WEBENGINE_PAGE_CLASS
    if _CAPTURING_WEBENGINE_PAGE_CLASS is not None:
        return _CAPTURING_WEBENGINE_PAGE_CLASS

    qwebengine_page, _settings, _view = _get_webengine_classes()

    class CapturingWebEnginePage(qwebengine_page):
        """Capture JS console messages for diagnostics."""

        def javaScriptConsoleMessage(
            self,
            level: int,
            message: str,
            lineNumber: int,
            sourceID: str,
        ) -> None:
            """Capture JavaScript console messages for diagnostics."""
            log_message = (
                "JSCONSOLE::: Level: "
                f"{level}, Msg: {message}, Src: {sourceID}:{lineNumber}"
            )
            print(log_message)
            super().javaScriptConsoleMessage(
                level,
                message,
                lineNumber,
                sourceID,
            )

    _CAPTURING_WEBENGINE_PAGE_CLASS = CapturingWebEnginePage
    return _CAPTURING_WEBENGINE_PAGE_CLASS


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


class UIRuntimeMixin:
    """Provide GUI startup, splash handling, and shutdown routines."""

    @staticmethod
    def _present_main_window(
        window: object,
        app: QApplication,
    ) -> None:
        """Show and activate the main window after splash handoff."""
        is_visible = getattr(window, "isVisible", None)
        if not callable(is_visible) or not is_visible():
            window.show()
        window.raise_()
        window.activateWindow()
        app.processEvents()

    def _dismiss_splash_screen(
        self,
        window: object,
        app: QApplication,
    ) -> None:
        """Close the splash screen aggressively on X11/Wayland."""
        if not self.splash:
            return

        splash = self.splash
        self.splash = None
        if getattr(self, "_launcher_splash", None) is splash:
            self._launcher_splash = None

        try:
            splash.hide()
        except Exception:
            pass

        try:
            splash.finish(window)
        except Exception:
            pass

        try:
            splash.close()
        except Exception:
            pass

        try:
            splash.deleteLater()
        except Exception:
            pass

        app.processEvents()

    def on_log_logged_signal(self, data: dict) -> None:
        """Handle log message signals."""
        message = data["message"].split(" - ")
        self.update_splash_message(self.splash, message[4])

    def start(self) -> None:
        """Initialize QApplication and OpenGL state for GUI mode."""
        if self.headless:
            return
        signal.signal(signal.SIGINT, self.signal_handler)
        prepare_qt_runtime()

        if self._launcher_app is not None:
            self.app = self._launcher_app
        else:
            self.app = QApplication.instance()
            if self.app is None:
                self.app = QApplication([])
        self.app.api = self
        try:
            from airunner.components.server.api.server import set_api

            set_api(self)
        except Exception:
            pass
        set_global_tooltip_style()

    def run(self) -> None:
        """Run as a GUI application or keep the headless loop alive."""
        if self.headless:
            self.run_headless()
            return

        if self._launcher_splash is not None:
            self.splash = self._launcher_splash
            self.update_splash_message(self.splash, "Loading AI Runner...")
        elif not self.no_splash and not self.splash:
            self.splash = self.display_splash_screen(self.app)

        QTimer.singleShot(50, self._post_splash_startup)
        try:
            ret = self.app.exec()
            self.cleanup()
            sys.exit(ret)
        except KeyboardInterrupt:
            self.logger.info("Interrupted by user")
            self.cleanup()
            sys.exit(0)
        except Exception as exc:
            self.logger.exception("GUI runtime crashed: %s", exc)
            self.cleanup()
            sys.exit(1)

    def run_headless(self):
        """Run in headless mode without GUI."""
        print("run headless function called")
        self.logger.info("AI Runner headless mode - server running")
        self.logger.info("Press Ctrl+C to stop")

        def _timer_tick() -> None:
            return None

        self._headless_timer = QTimer()
        self._headless_timer.timeout.connect(_timer_tick)
        self._headless_timer.start(500)

        try:
            self.logger.info("DEBUG: Starting Qt event loop")
            ret = self.app.exec()
            self.logger.info("DEBUG: Qt event loop returned with %s", ret)
            self.cleanup()
            sys.exit(ret)
        except KeyboardInterrupt:
            self.logger.info("Interrupted by user")
            self.cleanup()
            sys.exit(0)
        except Exception as exc:
            self.logger.exception(
                "CRITICAL: Headless server crashed: %s",
                exc,
            )
            self.cleanup()
            sys.exit(1)

    def _post_splash_startup(self):
        """Continue startup after the splash screen is visible."""
        self.show_main_application(self.app)

    @staticmethod
    def signal_handler(_signal: int, _frame: object) -> None:
        """Handle SIGINT and SIGTERM without abrupt process exit."""
        print("\nExiting...")
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__

        try:
            from airunner.components.server.api import server as server_module

            api = getattr(server_module, "_api", None)
            if api is not None:
                try:
                    api.cleanup()
                except Exception:
                    pass
        except Exception:
            pass

        try:
            qt_app = QCoreApplication.instance() or QApplication.instance()
            if qt_app is not None:
                qt_app.quit()
        except Exception:
            pass

    def display_splash_screen(
        self,
        app: QApplication,
    ) -> Optional[SplashScreen]:
        """Display a splash screen while the application is loading."""
        if self.no_splash:
            return None

        screens = QGuiApplication.screens()
        target_screen = None
        try:
            qsettings = get_qsettings()
            qsettings.beginGroup("window_settings")
            saved_screen_name = qsettings.value(
                "screen_name",
                None,
                type=str,
            )
            qsettings.endGroup()
            if saved_screen_name:
                for screen in screens:
                    if screen.name() == saved_screen_name:
                        target_screen = screen
                        break
        except Exception:
            pass

        if not target_screen:
            try:
                target_screen = QGuiApplication.primaryScreen()
            except Exception:
                pass
        if not target_screen:
            try:
                target_screen = screens.at(0)
            except AttributeError:
                target_screen = screens[0]

        base_dir = Path(os.path.dirname(os.path.realpath(__file__))).parent
        image_path = base_dir / "gui" / "images" / "splashscreen.png"
        splash = SplashScreen(target_screen, image_path)
        splash.show_message("Loading AI Runner")
        app.processEvents()
        return splash

    @staticmethod
    def update_splash_message(
        splash: Optional[SplashScreen],
        message: str,
    ) -> None:
        """Update the splash screen message."""
        if hasattr(splash, "show_message"):
            splash.show_message(message)
        else:
            splash.showMessage(
                message,
                QtCore.Qt.AlignmentFlag.AlignBottom
                | QtCore.Qt.AlignmentFlag.AlignCenter,
                QtCore.Qt.GlobalColor.white,
            )

    def _log_gui_startup_time(self) -> None:
        """Log total GUI startup time once the main window is visible."""
        if getattr(self, "_gui_startup_logged", False):
            return
        started_at = os.environ.get("AIRUNNER_PROCESS_START_TIME")
        if not started_at:
            return
        self._gui_startup_logged = True
        self.logger.info(
            "GUI startup completed in %.2fs",
            time.perf_counter() - float(started_at),
        )

    def _schedule_main_window_loaded(self, window: object) -> None:
        """Emit the post-startup signal after the GUI is visibly ready."""
        scheduler = getattr(window, "_schedule_main_window_loaded_signal", None)
        if callable(scheduler):
            scheduler()
            return
        if getattr(window, "_main_window_loaded_signal_scheduled", False):
            return
        window._main_window_loaded_signal_scheduled = True
        QTimer.singleShot(0, lambda: self._emit_main_window_loaded(window))

    def _emit_main_window_loaded(self, window: object) -> None:
        """Notify widgets that the main window finished startup."""
        emitter = getattr(window, "_emit_main_window_loaded_signal_if_ready", None)
        if callable(emitter):
            emitter()
            return
        if getattr(window, "_main_window_loaded_signal_emitted", False):
            return
        api = getattr(window, "api", None)
        if api is None:
            return
        window._main_window_loaded_signal_emitted = True
        api.main_window_loaded(window)

    @staticmethod
    def _prewarm_daemon_art_runtime(window: object) -> None:
        """Kick off art daemon prewarm as soon as the window exists."""
        worker_manager = getattr(window, "worker_manager", None)
        starter = getattr(worker_manager, "_start_art_runtime_prewarm", None)
        if callable(starter):
            starter()

    def show_main_application(self, app: QApplication) -> None:
        """Show the main application window."""
        if self.headless:
            return

        window_class = self.main_window_class_
        if not window_class:
            from airunner.components.application.gui.windows.main.main_window import (
                MainWindow,
            )

            window_class = MainWindow

        try:
            self.update_splash_message(
                self.splash,
                "Initializing main window...",
            )
            window = window_class(app=self, **self.window_class_params)
            app.main_window = window
            self._prewarm_daemon_art_runtime(window)
            self._present_main_window(window, app)

            if self.splash:
                self._dismiss_splash_screen(window, app)
                QTimer.singleShot(
                    0,
                    lambda: self._present_main_window(window, app),
                )
            self._log_gui_startup_time()
            self._schedule_main_window_loaded(window)

            print(f"Qt Version: {qVersion()}")
            if hasattr(window, "ui") and not _AIRUNNER_IS_HEADLESS:
                (
                    _qwebengine_page,
                    qwebengine_settings,
                    qwebengine_view,
                ) = _get_webengine_classes()
                capturing_page = _get_capturing_webengine_page_class()
                for attr in dir(window.ui):
                    widget = getattr(window.ui, attr)
                    if not isinstance(widget, qwebengine_view):
                        continue
                    current_page = widget.page()
                    if current_page and type(current_page).__name__ != (
                        "QWebEnginePage"
                    ):
                        print(
                            "[App] Skipping page override for "
                            f"{attr}, already has custom page: "
                            f"{type(current_page)}"
                        )
                        continue

                    settings = widget.settings()
                    settings.setAttribute(
                        qwebengine_settings.WebAttribute.
                        JavascriptCanOpenWindows,
                        True,
                    )
                    settings.setAttribute(
                        qwebengine_settings.WebAttribute.
                        LocalContentCanAccessRemoteUrls,
                        True,
                    )
                    print(f"[App] Setting CapturingWebEnginePage for {attr}")
                    widget.setPage(capturing_page(widget))
        except Exception as exc:
            traceback.print_exc()
            print(exc)
            try:
                self.cleanup()
            except Exception:
                pass
            sys.exit(
                "\n                An error occurred while initializing the "
                "application.\n                Please report this issue on "
                f"GitHub {AIRUNNER_BUG_REPORT_LINK}."
            )

    def quit(self):
        """Stop background servers and cleanup resources."""
        if self.http_server_thread:
            self.http_server_thread.stop()
            self.http_server_thread.wait()

        if self.api_server_thread:
            self.api_server_thread.stop()

    def cleanup(self):
        """Cleanup resources when shutting down."""
        if getattr(self, "_cleaned_up", False):
            return
        self._cleaned_up = True

        self.logger.info("Cleaning up App resources...")
        try:
            self.is_running = False

            def _log_running_qthreads(stage: str) -> None:
                """Log any Python-visible QThread wrappers still running."""
                try:
                    def _find_thread_owners(thread: QThread) -> list[dict[str, object]]:
                        owners: list[dict[str, object]] = []
                        seen: set[tuple[str, str]] = set()
                        for referrer in gc.get_referrers(thread):
                            if not isinstance(referrer, dict):
                                continue

                            try:
                                attr_names = [
                                    key
                                    for key, value in referrer.items()
                                    if value is thread and isinstance(key, str)
                                ]
                            except Exception:
                                attr_names = []

                            if not attr_names:
                                continue

                            try:
                                container_refs = gc.get_referrers(referrer)
                            except Exception:
                                container_refs = []

                            for container in container_refs:
                                try:
                                    if getattr(container, "__dict__", None) is not referrer:
                                        continue
                                    owner_type = type(container).__name__
                                    for attr_name in attr_names:
                                        marker = (owner_type, attr_name)
                                        if marker in seen:
                                            continue
                                        seen.add(marker)
                                        owners.append(
                                            {
                                                "owner_type": owner_type,
                                                "attr": attr_name,
                                            }
                                        )
                                except Exception:
                                    continue
                        return owners

                    running_threads = []
                    for obj in gc.get_objects():
                        try:
                            if not isinstance(obj, QThread):
                                continue
                            if not obj.isRunning():
                                continue
                            parent = obj.parent()
                            running_threads.append(
                                {
                                    "type": type(obj).__name__,
                                    "name": obj.objectName(),
                                    "parent": (
                                        type(parent).__name__
                                        if parent is not None
                                        else None
                                    ),
                                    "owners": _find_thread_owners(obj),
                                }
                            )
                        except Exception:
                            continue

                    if not running_threads:
                        self.logger.info(
                            "No live QThread wrappers at %s",
                            stage,
                        )
                        return

                    self.logger.warning(
                        "Live QThread wrappers at %s: %s",
                        stage,
                        running_threads,
                    )
                except Exception as exc:
                    self.logger.warning(
                        "Error inspecting live QThreads at %s: %s",
                        stage,
                        exc,
                    )

            _log_running_qthreads("cleanup:start")

            if hasattr(self, "http_server_thread") and self.http_server_thread:
                self.logger.info("Stopping local HTTP server...")
                try:
                    self.http_server_thread.stop()
                    if not self.http_server_thread.wait(2000):
                        self.logger.warning(
                            "Local HTTP server thread did not stop within timeout"
                        )
                    else:
                        self.logger.info("Local HTTP server stopped")
                except Exception as exc:
                    self.logger.warning(
                        "Error stopping local HTTP server: %s",
                        exc,
                    )

            if hasattr(self, "api_server_thread") and self.api_server_thread:
                self.logger.info("Stopping API server...")
                try:
                    self.api_server_thread.stop()
                    self.api_server_thread.join(timeout=2.0)
                    self.logger.info("API server stopped")
                except Exception as exc:
                    self.logger.warning(
                        "Error stopping API server: %s",
                        exc,
                    )

            try:
                self.emit_signal(SignalCode.QUIT_APPLICATION, {})
            except Exception as exc:
                self.logger.warning(
                    "Error emitting quit signal: %s",
                    exc,
                )

            try:
                QCoreApplication.sendPostedEvents(
                    None,
                    QtCore.QEvent.Type.DeferredDelete,
                )
                QCoreApplication.processEvents()
            except Exception as exc:
                self.logger.warning(
                    "Error flushing deferred Qt events during cleanup: %s",
                    exc,
                )

            try:
                from airunner.utils.application.create_worker import (
                    THREADS,
                    WORKERS,
                )

                for worker in WORKERS:
                    try:
                        worker.stop()
                    except Exception:
                        continue
                for index, thread in enumerate(list(THREADS)):
                    try:
                        worker_name = "unknown"
                        if index < len(WORKERS):
                            worker_name = type(WORKERS[index]).__name__
                        thread.quit()
                        thread.wait(2000)
                        if thread.isRunning():
                            self.logger.warning(
                                "Worker thread still running after quit: worker=%s thread_name=%s",
                                worker_name,
                                thread.objectName(),
                            )
                            thread.terminate()
                            thread.wait(500)
                        if thread.isRunning():
                            self.logger.warning(
                                "Worker thread still running after terminate: worker=%s thread_name=%s",
                                worker_name,
                                thread.objectName(),
                            )
                    except Exception:
                        continue

                _log_running_qthreads("cleanup:after_worker_shutdown")

                try:
                    WORKERS.clear()
                    THREADS.clear()
                except Exception:
                    pass
            except Exception as exc:
                self.logger.warning(
                    "Error stopping workers/threads: %s",
                    exc,
                )

            _log_running_qthreads("cleanup:before_complete")

            self.logger.info("App cleanup complete")
        except Exception as exc:
            self.logger.error(
                "Error during App cleanup: %s",
                exc,
                exc_info=True,
            )

    def _ensure_mathjax(self):
        """Ensure MathJax assets are installed in the writable data dir."""
        if os.environ.get("AIRUNNER_FLATPAK") == "1":
            xdg_data_home = os.environ.get(
                "XDG_DATA_HOME",
                os.path.expanduser("~/.local/share"),
            )
            base_path = os.path.join(xdg_data_home, "airunner")
        else:
            base_path = os.environ.get(
                "AIRUNNER_DATA_DIR",
                os.path.join(
                    os.path.expanduser("~"),
                    ".local",
                    "share",
                    "airunner",
                ),
            )

        mathjax_dir = os.path.join(
            base_path,
            "static",
            "mathjax",
            f"MathJax-{MATHJAX_VERSION}",
            "es5",
        )
        os.makedirs(
            os.path.dirname(os.path.dirname(mathjax_dir)),
            exist_ok=True,
        )
        entry = os.path.join(mathjax_dir, "tex-mml-chtml.js")
        if os.path.exists(entry):
            return

        print("MathJax not found, attempting to download and set up...")
        try:
            env = os.environ.copy()
            env["MATHJAX_INSTALL_DIR"] = os.path.dirname(
                os.path.dirname(mathjax_dir)
            )
            subprocess.check_call(
                [
                    sys.executable,
                    os.path.join(
                        os.path.dirname(__file__),
                        "..",
                        "bin",
                        "setup_mathjax.py",
                    ),
                ],
                env=env,
            )
        except Exception as exc:
            print("ERROR: MathJax setup failed:", exc)
            raise RuntimeError(
                "MathJax is required but could not be set up. See README.md "
                "for instructions."
            )