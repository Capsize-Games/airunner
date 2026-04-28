from typing import Dict, List, Optional
import glob
import os
import os.path
from PySide6.QtCore import QObject
from PySide6.QtGui import QWindow
from PySide6.QtWidgets import QApplication

from airunner.utils.application import get_logger
from airunner.settings import (
    AIRUNNER_LOG_LEVEL,
    LOCAL_SERVER_PORT,
    MATHJAX_VERSION,
)

# CRITICAL: Set PyTorch CUDA memory allocator config BEFORE importing torch.
# PYTORCH_CUDA_ALLOC_CONF was deprecated in favor of PYTORCH_ALLOC_CONF.
os.environ.setdefault("PYTORCH_ALLOC_CONF", "expandable_segments:True")
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", os.environ["PYTORCH_ALLOC_CONF"])

from airunner.app_mixins import (
    HeadlessRuntimeMixin,
    LocalizationMixin,
    UIRuntimeMixin,
)
from airunner.enums import SignalCode
from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.components.application.gui.windows.main.settings_mixin import (
    SettingsMixin,
)
from airunner.components.server.local_http_server import LocalHttpServerThread
from airunner.utils.application.logging_utils import configure_headless_logging
from airunner.daemon_client import GuiDaemonClient
from airunner.runtimes.bootstrap import build_runtime_registry


# Enable LNA mode for local server if AIRUNNER_LNA_ENABLED=1
LNA_ENABLED = os.environ.get("AIRUNNER_LNA_ENABLED", "0") == "1"


def _assert_test_gui_launch_allowed(headless: bool) -> None:
    """Block real GUI startup while automated tests are running."""
    if headless:
        return
    if os.environ.get("AIRUNNER_ALLOW_GUI_TEST_LAUNCH") == "1":
        return
    if os.environ.get("AIRUNNER_TEST_NO_GUI_LAUNCH") != "1":
        return
    raise RuntimeError(
        "GUI AIRunner startup is disabled during automated tests."
    )


class App(
    HeadlessRuntimeMixin,
    LocalizationMixin,
    UIRuntimeMixin,
    MediatorMixin,
    SettingsMixin,
    QObject,
):
    """
    The main application class for AI Runner.
    This class can be run as a GUI application or as a socket server.
    """

    def __init__(
        self,
        no_splash: bool = False,
        main_window_class: QWindow = None,
        window_class_params: Optional[Dict] = None,
        headless: bool = False,
        launcher_splash=None,
        launcher_app=None,
        start_headless_api_server: bool = True,
        initialize_headless_lifecycle: bool = True,
    ):
        """Initialize the application.

        Args:
            no_splash: Skip splash screen display (GUI mode only)
            main_window_class: Custom main window class (GUI mode only)
            window_class_params: Parameters for main window (GUI mode only)
            headless: If True, run in headless mode (no GUI)
            launcher_splash: Splash screen passed from launcher (already showing)
            launcher_app: QApplication passed from launcher
            start_headless_api_server: Start embedded API server in headless mode
            initialize_headless_lifecycle: Initialize workers during headless boot
        """
        _assert_test_gui_launch_allowed(headless)
        self.headless = headless
        self._launcher_splash = launcher_splash
        self._launcher_app = launcher_app
        self._start_headless_api_server = start_headless_api_server
        self._initialize_headless_lifecycle = initialize_headless_lifecycle
        self._init_attributes(
            no_splash, main_window_class, window_class_params
        )
        super().__init__()
        self.runtime_registry = build_runtime_registry(app_instance=self)
        self.daemon_client = None
        if not self.headless:
            self.daemon_client = GuiDaemonClient()
        self._register_signals()
        self._ensure_mathjax()

        # Load explicitly enabled runtime extensions early so they can:
        # - override built-in LLM tools by name (after built-ins are registered)
        # - apply any UI monkey-patches before widgets are constructed
        self._load_optional_extensions()

        if self.headless:
            self._init_headless_mode()
        else:
            self._init_gui_mode()

        self._initialize_knowledge_system()

    def _load_optional_extensions(self) -> None:
        """Load explicitly enabled extensions from local extension roots.

        Extensions are optional and must never prevent Airunner from starting.
        """
        try:
            # Ensure the built-in web tools are registered first.
            # Extensions rely on name-based override semantics.
            try:
                from airunner.components.llm.tools import web_tools  # noqa: F401
            except Exception:
                pass

            from airunner.components.llm.core.extensions_loader import (
                load_extensions,
            )

            stats = load_extensions(force_reload=False)
            if isinstance(stats, dict):
                self.logger.info(
                    "Extensions loaded: loaded=%s failed=%s roots=%s",
                    stats.get("loaded"),
                    stats.get("failed"),
                    stats.get("roots"),
                )
        except Exception as exc:
            try:
                self.logger.debug("Extension loading skipped/failed: %s", exc)
            except Exception:
                pass

    @property
    def static_dir(self) -> str:
        """Get the static directory path.

        Uses user data directory for writable static files (like MathJax),
        falls back to package directory for bundled static assets.
        """
        base_path = os.environ.get(
            "AIRUNNER_DATA_DIR",
            os.path.join(
                os.path.expanduser("~"), ".local", "share", "airunner"
            ),
        )
        user_static = os.path.join(base_path, "static")

        pkg_static = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "static")
        )

        if os.path.isdir(user_static):
            return user_static
        return pkg_static

    @property
    def _package_static_dir(self) -> str:
        """Get the package's bundled static directory (read-only)."""
        return os.path.abspath(
            os.path.join(os.path.dirname(__file__), "static")
        )

    @property
    def static_search_dirs(self) -> List[str]:
        """Get the list of static search directories."""
        # Find all components/**/gui/static directories
        components_static_dirs = glob.glob(
            os.path.join(
                os.path.dirname(__file__), "components", "**", "gui", "static"
            ),
            recursive=True,
        )
        # Include both user static dir and package static dir
        static_search_dirs = [self.static_dir]
        if self._package_static_dir != self.static_dir:
            static_search_dirs.append(self._package_static_dir)
        static_search_dirs.extend(components_static_dirs)
        # Add user web dir if it exists
        if os.path.isdir(self.user_web_dir):
            static_search_dirs.append(self.user_web_dir)
        return static_search_dirs

    def _init_attributes(
        self,
        no_splash: bool,
        main_window_class: QWindow,
        window_class_params: Optional[Dict]
    ) -> None:
        """Initialize instance attributes."""
        if self.headless:
            configure_headless_logging()

        self.logger = get_logger(__name__, level=AIRUNNER_LOG_LEVEL)

        self.main_window_class_ = main_window_class
        self.window_class_params = window_class_params or {}
        self.no_splash = no_splash
        self.app = None
        self.splash = None
        self.http_server_thread = None
        self.api_server_thread = None
        self.is_running = False
        self.lifecycle_service = None
        self.model_load_balancer = None
        self._worker_manager = None
        self._model_load_balancer = None

    def _register_signals(self) -> None:
        """Register signal handlers."""
        self.register(SignalCode.LOG_LOGGED_SIGNAL, self.on_log_logged_signal)
        self.register(SignalCode.UPATE_LOCALE, self.on_update_locale_signal)

    def _init_gui_mode(self) -> None:
        """Initialize GUI mode with static server and main window."""
        mathjax_dir = os.path.join(
            self.static_dir, "mathjax", f"MathJax-{MATHJAX_VERSION}", "es5"
        )
        if not os.path.isdir(mathjax_dir):
            raise RuntimeError(
                "MathJax is required for LaTeX rendering. See README.md for setup instructions."
            )

        self._start_local_http_server()
        self.set_translations()
        self.run()

    def _start_local_http_server(self) -> None:
        self.logger.info("Starting local HTTP server for static assets.")
        self.http_server_thread = LocalHttpServerThread(
            directory=self.static_dir,
            additional_directories=self.static_search_dirs[1:],
            port=LOCAL_SERVER_PORT,
            lna_enabled=LNA_ENABLED,  # Pass LNA mode to server
        )
        self.http_server_thread.start()
        self.start()
