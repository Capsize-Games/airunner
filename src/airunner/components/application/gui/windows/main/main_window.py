"""Main application window.

This class is intentionally a thin composition root. Its previous 3,244-line
body has been decomposed into per-concern controllers under
``controllers/``, each of which is composed below and resolves its own
behavior through the window. Keeping ``MainWindow`` small and delegation-only
satisfies the repository's <=250-line class target while preserving every
signal connection and settings-loading semantic.
"""

from typing import Dict, Optional

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtWidgets import QMainWindow

from airunner.components.application.gui.windows.main.controllers import (
    ActionController,
    InputController,
    PanelLayoutController,
    PanelStateController,
    PanelToggleController,
    RuntimeStatusController,
    StartupController,
    WindowStateController,
)
from airunner.components.application.gui.windows.main.model_load_balancer import (
    ModelLoadBalancer,
)
from airunner.components.application.gui.windows.main.settings_mixin import (
    SettingsMixin,
)
from airunner.components.application.gui.windows.main.templates.main_window_ui import (
    Ui_MainWindow,
)
from airunner.components.application.gui.windows.main.worker_manager import (
    WorkerManager,
)
from airunner.components.application.gui.windows.wayland_helper import (
    enable_wayland_window_decorations,
)
from airunner.enums import (
    GeneratorSection,
    ModelStatus,
    ModelType,
    SignalCode,
)
from airunner.gui.styles.styles_mixin import StylesMixin
from airunner.components.application.gui.windows.main.ai_model_mixin import (
    AIModelMixin,
)
from airunner.components.application.gui.windows.main.pipeline_mixin import (
    PipelineMixin,
)
from airunner.utils.application import create_worker
from airunner.utils.application.gui_probe import maybe_create_gui_probe_controller
from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.utils.settings import get_qsettings
from airunner_common.settings import (
    AIRUNNER_STATUS_ERROR_COLOR,
    AIRUNNER_STATUS_NORMAL_COLOR_DARK,
    AIRUNNER_STATUS_NORMAL_COLOR_LIGHT,
)


class MainWindow(
    PanelToggleController,
    PanelStateController,
    PanelLayoutController,
    ActionController,
    InputController,
    WindowStateController,
    StartupController,
    RuntimeStatusController,
    MediatorMixin,
    SettingsMixin,
    StylesMixin,
    PipelineMixin,
    AIModelMixin,
    QMainWindow,
):
    show_grid_toggled = Signal(bool)
    image_generated = Signal(bool)
    generator_tab_changed_signal = Signal()
    load_image = Signal(str)
    load_image_object = Signal(object)
    loaded = Signal()
    window_opened = Signal()
    daemon_runtime_status_ready = Signal(object)
    ui_class_ = Ui_MainWindow

    def __init__(self, *args, **kwargs):
        self._init_state()
        self._init_widgets()
        self._init_content_state()
        self._init_widget_state()
        self._init_theme_colors()
        self._model_status = {
            model_type: ModelStatus.UNLOADED for model_type in ModelType
        }
        self.signal_handlers = self._build_signal_handlers()
        super().__init__()
        self._init_window_services()
        self._init_worker_services()
        self.initialize_ui()
        self._gui_probe_controller = maybe_create_gui_probe_controller(self)
        self._daemon_status_timer.start(1000)
        self.last_tray_click_time = 0
        self.settings_window = None

    def _init_state(self) -> None:
        """Initialize the deferred-startup and daemon refresh state."""
        self._launcher_splash_dismissed = False
        self._post_startup_status_refresh_requested = False
        self._state_restored = None
        self._restore_sidebar_page_after_startup = None
        self._restore_left_panel_page_after_startup = None
        self._daemon_status_refresh_inflight = False
        self._runtime_preference_retry_after = {}

    def _init_widgets(self) -> None:
        """Create the UI object, QSettings, and simple Qt signals."""
        self.ui = self.ui_class_()
        self.qsettings = get_qsettings()
        self.icon_manager: Optional[object] = None
        self.token_signal = Signal(str)
        self.button_clicked_signal = Signal(Dict)

    def _init_content_state(self) -> None:
        """Initialize transient content/generation state."""
        self.quitting = False
        self.update_popup = None
        self._document_path = None
        self.prompt = None
        self.negative_prompt = None
        self.image_path = None
        self.input_event_manager = None
        self.tqdm_callback_triggered = False
        self.action = GeneratorSection.TXT2IMG.value
        self.progress_bar_started = False

    def _init_widget_state(self) -> None:
        """Initialize lazy widget/generator references."""
        self.canvas = None
        self.models = None
        self.client = None
        self._version = None
        self._latest_version = None
        self._themes = None
        self.status_widget = None
        self.header_widget_spacer = None
        self.deterministic_window = None
        self.generator = None
        self._generator = None
        self._generator_settings = None
        self.listening = False
        self.initialized = False

    def _init_theme_colors(self) -> None:
        """Initialize the theme status colors."""
        self.status_error_color = AIRUNNER_STATUS_ERROR_COLOR
        self.status_normal_color_light = AIRUNNER_STATUS_NORMAL_COLOR_LIGHT
        self.status_normal_color_dark = AIRUNNER_STATUS_NORMAL_COLOR_DARK

    def _init_window_services(self) -> None:
        """Wire the window decorator, timers, and initial settings."""
        self.daemon_runtime_status_ready.connect(
            self._on_daemon_runtime_status_ready
        )
        self.logger.debug("Starting AI Runnner")
        enable_wayland_window_decorations(self)
        self.setAutoFillBackground(True)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.update_application_settings(
            sd_enabled=False,
            llm_enabled=False,
            controlnet_enabled=False,
        )
        self._init_single_click_timer()
        self._updating_settings = False

    def _init_worker_services(self) -> None:
        """Create the worker manager, load balancer, and status timer."""
        self.worker_manager = create_worker(
            WorkerManager,
            signal_api_adapter=getattr(self.api, "daemon_client", None),
        )
        self.model_load_balancer = ModelLoadBalancer(
            self.worker_manager,
            logger=getattr(self, "logger", None),
            api=self.api,
        )
        if self.api is not None:
            self.api.model_load_balancer = self.model_load_balancer
        self._daemon_status_timer = QTimer(self)
        self._daemon_status_timer.timeout.connect(
            self._refresh_model_status_from_daemon
        )

    def _init_single_click_timer(self) -> None:
        """Create the tray single-click timer."""
        self.single_click_timer = QTimer(self)
        self.single_click_timer.setSingleShot(True)
        self.single_click_timer.timeout.connect(self.handle_single_click)

    def _build_signal_handlers(self) -> Dict:
        """Return the mediator signal handler table."""
        return {
            SignalCode.SD_SAVE_PROMPT_SIGNAL: self.on_save_stablediffusion_prompt_signal,
            SignalCode.QUIT_APPLICATION: self.handle_quit_application_signal,
            SignalCode.WRITE_FILE: self.on_write_file_signal,
            SignalCode.TOGGLE_FULLSCREEN_SIGNAL: self.on_toggle_fullscreen_signal,
            SignalCode.TOGGLE_TTS_SIGNAL: self.on_toggle_tts,
            SignalCode.TOGGLE_LLM_SIGNAL: self.on_toggle_llm,
            SignalCode.APPLICATION_RESET_SETTINGS_SIGNAL: self._action_reset_settings,
            SignalCode.APPLICATION_RESET_PATHS_SIGNAL: self.on_reset_paths_signal,
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL: self.on_model_status_changed_signal,
            SignalCode.KEYBOARD_SHORTCUTS_UPDATED: self.on_keyboard_shortcuts_updated,
            SignalCode.REFRESH_STYLESHEET_SIGNAL: self.on_theme_changed_signal,
            SignalCode.AI_MODELS_SAVE_OR_UPDATE_SIGNAL: self.on_ai_models_save_or_update_signal,
            SignalCode.MISSING_REQUIRED_MODELS: self.display_missing_models_error,
            SignalCode.RETRANSLATE_UI_SIGNAL: self.on_retranslate_ui_signal,
            SignalCode.APPLICATION_STATUS_ERROR_SIGNAL: self.on_status_error_signal,
            SignalCode.APPLICATION_MAIN_WINDOW_LOADED_SIGNAL: self.on_main_window_loaded_signal,
        }

    @property
    def generator_tab_widget(self):
        return self.ui.generator_widget

    @property
    def version(self):
        from airunner_common.settings import AIRUNNER_VERSION

        return f"v{AIRUNNER_VERSION}"

    @property
    def latest_version(self):
        return self._latest_version

    @latest_version.setter
    def latest_version(self, val):
        self._latest_version = val

    @property
    def document_name(self):
        return "Untitled"

    @property
    def buttons(self) -> Dict:
        return {}

    def _restore_tab(self):
        """Center-tab restoration was removed with the home/art split."""

    def _set_current_button_and_tab(self, button_name: str):
        """Center-tab switching was removed with the home/art split."""
        del button_name
