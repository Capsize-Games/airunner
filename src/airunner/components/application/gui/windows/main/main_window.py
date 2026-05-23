import os
import sys
import threading
import time
import webbrowser
from functools import partial
from typing import Dict, Optional

from airunner.components.about.gui.windows.about.about import AboutWindow
from airunner.components.model_management import ModelResourceManager
from airunner.components.model_management.gui.model_status_widget import (
    ModelStatusWidget,
)
from airunner.components.model_management.types import ModelState
from airunner.components.application.gui.widgets.status.status_widget import (
    StatusWidget,
)
from airunner.components.application.gui.windows.main.download_model_dialog import (
    show_download_model_dialog,
)
from airunner.components.application.gui.windows.main.nsfw_warning_dialog import (
    show_nsfw_warning_dialog,
)
from airunner.components.art.gui.windows.prompt_browser.prompt_browser import (
    PromptBrowser,
)
from airunner.components.settings.gui.windows.settings.airunner_settings import (
    SettingsWindow,
)
from airunner.components.application.gui.windows.main.model_load_balancer import (
    ModelLoadBalancer,
)
from airunner.components.application.gui.windows.main.worker_manager import (
    WorkerManager,
)
from airunner.components.application.gui.windows.wayland_helper import (
    enable_wayland_window_decorations,
)
from PIL import Image
from PySide6.QtCore import (
    Slot,
    Signal,
    QProcess,
    QTimer,
    Qt,
)
from PySide6.QtGui import QGuiApplication, QKeySequence, QAction, QCursor
from PySide6.QtWidgets import (
    QApplication,
    QGridLayout,
    QMainWindow,
    QMessageBox,
    QMenu,
    QPushButton,
    QTabWidget,
    QWidget,
)
from PySide6.QtGui import QIcon

from airunner.settings import (
    AIRUNNER_STATUS_ERROR_COLOR,
    AIRUNNER_STATUS_NORMAL_COLOR_LIGHT,
    AIRUNNER_STATUS_NORMAL_COLOR_DARK,
    AIRUNNER_DISCUSSIONS_URL,
    AIRUNNER_BUG_REPORT_LINK,
    AIRUNNER_VULNERABILITY_REPORT_LINK,
    AIRUNNER_ART_ENABLED,
)
from airunner.utils.application import create_worker
from airunner.utils.application.log_hygiene import summarize_mapping_keys
from airunner.utils.settings import get_qsettings
from airunner.components.application.data.shortcut_keys import ShortcutKeys
from airunner.components.art.data.image_filter import ImageFilter
from airunner.app_installer import AppInstaller
from airunner.enums import (
    SignalCode,
    GeneratorSection,
    ModelType,
    ModelStatus,
)
from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.utils.application.get_version import get_version
from airunner.utils.widgets import (
    save_splitter_settings,
    load_splitter_settings,
)
from airunner.utils.image import convert_image_to_binary
from airunner.gui.styles.styles_mixin import StylesMixin
from airunner.components.art.gui.windows.filter_window.filter_window import (
    FilterWindow,
)
from airunner.components.application.gui.windows.main.ai_model_mixin import (
    AIModelMixin,
)
from airunner.components.application.gui.windows.main.pipeline_mixin import (
    PipelineMixin,
)
from airunner.components.application.gui.windows.main.settings_mixin import (
    SettingsMixin,
)
from airunner.components.application.gui.windows.main.templates.main_window_ui import (
    Ui_MainWindow,
)
from airunner.components.update.gui.windows.update.update_window import (
    UpdateWindow,
)
from airunner.components.icons.managers.icon_manager import IconManager


# Utility functions moved from deleted agent.actions
def bash_execute(command: str) -> str:
    """
    Execute a bash command and return the output.

    Args:
        command: The bash command to execute

    Returns:
        The command output or error message
    """
    import subprocess

    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=30
        )
        return result.stdout if result.returncode == 0 else result.stderr
    except subprocess.TimeoutExpired:
        return "Command timed out after 30 seconds"
    except Exception as e:
        return f"Error executing command: {str(e)}"


def show_path(path: str) -> None:
    """
    Open the given path in the system file manager.

    Args:
        path: The file or directory path to show
    """
    import subprocess
    import platform
    import os

    if not os.path.exists(path):
        return

    system = platform.system()
    try:
        if system == "Windows":
            startfile = getattr(os, "startfile", None)
            if callable(startfile):
                startfile(path)
        elif system == "Darwin":  # macOS
            subprocess.run(["open", path])
        else:  # Linux
            subprocess.run(["xdg-open", path])
    except Exception:
        pass  # Silently fail if we can't open the path


class MainWindow(
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
    _window_title = f"AI Runner"
    _daemon_status_request_timeout_seconds = 0.75
    _runtime_preference_retry_seconds = 5.0
    _documents_splitter_index = 0
    _chat_splitter_index = 1
    _center_splitter_index = 2
    _stats_splitter_index = 3
    _canvas_panel_index = 0
    _prompt_panel_index = 1
    _left_panel_target_width = 360
    _chat_panel_target_width = 250
    _stats_sidebar_index = 0
    _art_tools_sidebar_index = 1
    _art_tools_model_tab_index = 0
    _art_tools_lora_tab_index = 1
    _art_tools_embeddings_tab_index = 2
    _art_tools_layers_tab_index = 3
    _art_tools_grid_tab_index = 4
    _art_tools_image_browser_tab_index = 5
    _left_documents_panel_index = 0
    _left_history_panel_index = 1
    _left_llm_settings_panel_index = 2
    icons = [
        ("settings", "actionSettings"),
        ("image", "menuArt"),
        ("message-circle", "menuChat"),
        ("refresh-cw", "actionReset_Settings_2"),
        ("x-circle", "actionQuit"),
        ("plus-circle", "artActionNew"),
        ("upload-icon", "actionImport_image"),
        ("download-icon", "actionExport_image_button"),
        ("message-circle", "actionNew_Conversation"),
        ("trash-2", "actionDelete_conversation"),
        ("scissors", "actionCut"),
        ("copy", "actionCopy"),
        ("clipboard", "actionPaste"),
        ("delete", "actionClear_all_prompts"),
        ("settings", "actionSettings"),
        ("book-open", "actionPrompt_Browser"),
        ("folder", "actionBrowse_AI_Runner_Path"),
        ("folder", "actionBrowse_Images_Path_2"),
        ("image", "menuStable_Diffusion"),
        ("zap", "actionRun_setup_wizard_2"),
        ("external-link", "actionBug_report"),
        ("external-link", "actionReport_vulnerability"),
        ("message-square", "actionDiscussions"),
        ("download", "actionImport_image"),
        ("upload", "actionExport_image_button"),
        ("settings", "settings_button"),
        ("message-square-text", "chat_button"),
        ("speaker", "text_to_speech_button"),
        ("mic", "speech_to_text_button"),
        ("arrow-down-circle", "actionDownload_Model"),
        ("book", "knowledgebase_button"),
        ("history", "history_sidebar_button"),
        ("settings-2", "llm_settings_sidebar_button"),
        ("message-square-heart", "prompt_editor_button"),
        ("sparkles", "art_model_button"),
        ("activity", "stats_button"),
        ("image", "canvas_button"),
        ("puzzle", "lora_button"),
        ("scan-text", "embeddings_button"),
        ("layers", "layers_button"),
        ("grid-2x2-check", "grid_button"),
        ("images", "image_browser_button"),
    ]
    _last_reload_time = 0
    _reload_debounce_seconds = 1.0

    def __init__(self, *args, **kwargs):
        self.quitting = False
        self._launcher_splash_dismissed = False
        self._post_startup_status_refresh_requested = False
        self._state_restored = None
        self._restore_sidebar_page_after_startup = None
        self._restore_left_panel_page_after_startup = None
        self._daemon_status_refresh_inflight = False
        self._runtime_preference_retry_after = {}
        self.ui = self.ui_class_()
        self.qsettings = get_qsettings()
        self.icon_manager: Optional[IconManager] = None
        self.quitting = False
        self.update_popup = None
        self._document_path = None
        self.prompt = None
        self.negative_prompt = None
        self.image_path = None
        self.token_signal = Signal(str)
        self.input_event_manager = None
        self.tqdm_callback_triggered = False
        self.action = GeneratorSection.TXT2IMG.value
        self.progress_bar_started = False
        self.canvas = None
        self.models = None
        self.client = None
        self._version = None
        self._latest_version = None
        self.status_error_color = AIRUNNER_STATUS_ERROR_COLOR
        self.status_normal_color_light = AIRUNNER_STATUS_NORMAL_COLOR_LIGHT
        self.status_normal_color_dark = AIRUNNER_STATUS_NORMAL_COLOR_DARK
        self._themes = None
        self.button_clicked_signal = Signal(Dict)
        self.status_widget = None
        self.header_widget_spacer = None
        self.deterministic_window = None
        self.generator = None
        self._generator = None
        self._generator_settings = None
        self.listening = False
        self.initialized = False
        self._model_status = {
            model_type: ModelStatus.UNLOADED for model_type in ModelType
        }
        self.signal_handlers = {
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
        super().__init__()
        self.daemon_runtime_status_ready.connect(
            self._on_daemon_runtime_status_ready
        )
        self.logger.debug("Starting AI Runnner")
        enable_wayland_window_decorations(self)
        
        # Fix for black background flash during window drag on Linux
        # This ensures the window has a proper background brush during move/resize
        self.setAutoFillBackground(True)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        
        self.update_application_settings(
            sd_enabled=False,
            llm_enabled=False,
            controlnet_enabled=False,
        )
        self.single_click_timer = QTimer(self)
        self.single_click_timer.setSingleShot(True)
        self.single_click_timer.timeout.connect(self.handle_single_click)
        self._updating_settings = True
        self._updating_settings = False
        self.worker_manager = create_worker(
            WorkerManager,
            signal_api_adapter=getattr(self.api, "api_adapter", None),
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
        self.initialize_ui()
        self._daemon_status_timer.start(1000)
        self.last_tray_click_time = 0
        self.settings_window = None

    @property
    def generator_tab_widget(self):
        return self.ui.generator_widget

    @property
    def version(self):
        if self._version is None:
            self._version = get_version()
        return f"v{self._version}"

    @property
    def latest_version(self):
        return self._latest_version

    @latest_version.setter
    def latest_version(self, val):
        self._latest_version = val

    @property
    def document_name(self):
        return "Untitled"

    """
    Slot functions
    
    The following functions are defined in and connected to the appropriate
    signals in the corresponding ui file.
    """

    @Slot(bool)
    def on_chat_button_toggled(self, val: bool):
        self._toggle_splitter_section(
            val,
            self._chat_splitter_index,
            self.ui.main_window_splitter,
            50,
        )

    @Slot(bool)
    def on_knowledgebase_button_toggled(self, val: bool):
        self._toggle_left_panel_page(self._left_documents_panel_index, val)

    @Slot(bool)
    def on_history_sidebar_button_toggled(self, val: bool):
        self._toggle_left_panel_page(self._left_history_panel_index, val)

    @Slot(bool)
    def on_llm_settings_sidebar_button_toggled(self, val: bool):
        self._toggle_left_panel_page(
            self._left_llm_settings_panel_index,
            val,
        )

    @Slot(bool)
    def on_canvas_button_toggled(self, val: bool):
        self._toggle_canvas_panel(val)

    @Slot(bool)
    def on_prompt_editor_button_toggled(self, val: bool):
        self._toggle_prompt_panel(val)

    @Slot(bool)
    def on_art_model_button_toggled(self, val: bool):
        self._toggle_art_tools_tab(self._art_tools_model_tab_index, val)

    @Slot(bool)
    def on_lora_button_toggled(self, val: bool):
        self._toggle_art_tools_tab(self._art_tools_lora_tab_index, val)

    @Slot(bool)
    def on_embeddings_button_toggled(self, val: bool):
        self._toggle_art_tools_tab(
            self._art_tools_embeddings_tab_index,
            val,
        )

    @Slot(bool)
    def on_layers_button_toggled(self, val: bool):
        self._toggle_art_tools_tab(self._art_tools_layers_tab_index, val)

    @Slot(bool)
    def on_grid_button_toggled(self, val: bool):
        self._toggle_art_tools_tab(self._art_tools_grid_tab_index, val)

    @Slot(bool)
    def on_image_browser_button_toggled(self, val: bool):
        self._toggle_art_tools_tab(
            self._art_tools_image_browser_tab_index,
            val,
        )

    @Slot(bool)
    def on_stats_button_toggled(self, val: bool):
        self._toggle_sidebar_page(self._stats_sidebar_index, val)

    def on_main_window_loaded_signal(self, _data=None) -> None:
        """Restore deferred startup UI once the main window is visible."""
        self._ensure_canvas_loaded()
        if self._prompt_panel_is_visible():
            self._ensure_art_prompt_loaded()

        if self._restore_left_panel_page_after_startup is not None:
            page_index = int(self._restore_left_panel_page_after_startup)
            self._restore_left_panel_page_after_startup = None
            self._ensure_left_panel_page_loaded(page_index)
            self.ui.left_panel_tab.setCurrentIndex(page_index)
            self._sync_left_panel_button_states()

        if self._restore_sidebar_page_after_startup is not None:
            page_index = int(self._restore_sidebar_page_after_startup)
            self._restore_sidebar_page_after_startup = None
            self._ensure_sidebar_page_loaded(page_index)
            self.ui.sidebar_tab.setCurrentIndex(page_index)
            self._sync_sidebar_button_states()

        if self._post_startup_status_refresh_requested:
            return
        self._post_startup_status_refresh_requested = True
        self._refresh_model_status_from_daemon()

    def _schedule_main_window_loaded_signal(self) -> None:
        """Schedule the post-startup signal once after the window is shown."""
        if getattr(self, "_main_window_loaded_signal_scheduled", False):
            return
        self._main_window_loaded_signal_scheduled = True
        QTimer.singleShot(0, self._emit_main_window_loaded_signal_if_ready)

    def _emit_main_window_loaded_signal_if_ready(self) -> None:
        """Emit the post-startup signal when a live API is available."""
        if getattr(self, "_main_window_loaded_signal_emitted", False):
            return
        api = getattr(self, "api", None)
        if api is None:
            api = self.refresh_api_reference()
        if api is None:
            self._main_window_loaded_signal_scheduled = False
            return
        self._main_window_loaded_signal_emitted = True
        api.main_window_loaded(self)

    def on_splitter_changed_sizes(self):
        if self._sidebar_is_visible():
            self._ensure_sidebar_page_loaded(
                self._current_sidebar_index()
            )
        if self._prompt_panel_is_visible():
            self._ensure_art_prompt_loaded()
        if self._left_panel_is_visible():
            self._ensure_left_panel_page_loaded(
                self.ui.left_panel_tab.currentIndex()
            )
        self.set_chat_button_checked()
        self._sync_left_panel_button_states()
        self._sync_sidebar_button_states()

        canvas = getattr(self, "canvas", None)
        refresh_layout = getattr(
            canvas,
            "refresh_layout_after_host_resize",
            None,
        )
        if callable(refresh_layout):
            refresh_layout()

    def on_left_panel_tab_current_changed(self, index: int) -> None:
        """Persist the active left panel page and refresh toggle state."""
        self._ensure_left_panel_page_loaded(index)
        self._store_active_left_panel_tab_index(index)
        self._sync_left_panel_button_states()

    def on_sidebar_tab_current_changed(self, index: int) -> None:
        """Persist the active sidebar page and refresh toggle state."""
        self._ensure_sidebar_page_loaded(index)
        self._store_active_sidebar_tab_index(index)
        self._sync_sidebar_button_states()

    def _sidebar_is_visible(self) -> bool:
        """Return True when the right sidebar splitter area is visible."""
        sizes = self.ui.main_window_splitter.sizes()
        return len(sizes) > self._stats_splitter_index and (
            sizes[self._stats_splitter_index] > 0
        )

    def _center_section_is_visible(self) -> bool:
        """Return True when the shared center splitter area is visible."""
        sizes = self.ui.main_window_splitter.sizes()
        return len(sizes) > self._center_splitter_index and (
            sizes[self._center_splitter_index] > 0
        )

    def _canvas_panel_is_visible(self) -> bool:
        """Return True when the canvas panel is visible."""
        splitter = getattr(self.ui, "center_splitter", None)
        if splitter is None or not self._center_section_is_visible():
            return False
        sizes = splitter.sizes()
        return len(sizes) > self._canvas_panel_index and (
            sizes[self._canvas_panel_index] > 0
        )

    def _prompt_panel_is_visible(self) -> bool:
        """Return True when the prompt panel is visible."""
        splitter = getattr(self.ui, "center_splitter", None)
        if splitter is None or not self._center_section_is_visible():
            return False
        sizes = splitter.sizes()
        return len(sizes) > self._prompt_panel_index and (
            sizes[self._prompt_panel_index] > 0
        )

    def _knowledgebase_panel_is_visible(self) -> bool:
        """Return True when the left documents splitter area is visible."""
        return self._left_panel_is_visible()

    def _left_panel_is_visible(self) -> bool:
        """Return True when the shared left splitter area is visible."""
        sizes = self.ui.main_window_splitter.sizes()
        return len(sizes) > self._documents_splitter_index and (
            sizes[self._documents_splitter_index] > 0
        )

    def _current_left_panel_index(self) -> int:
        """Return the active left panel page index."""
        tab_widget = getattr(self.ui, "left_panel_tab", None)
        if tab_widget is None:
            return self._left_documents_panel_index
        return tab_widget.currentIndex()

    def _current_sidebar_index(self) -> int:
        """Return the active right panel page index."""
        tab_widget = getattr(self.ui, "sidebar_tab", None)
        if tab_widget is None:
            return self._stats_sidebar_index
        return tab_widget.currentIndex()

    def _saved_left_panel_tab_index(self) -> int:
        """Return the persisted left panel page index."""
        self.qsettings.beginGroup("window_settings")
        index = self.qsettings.value(
            "active_left_panel_tab_index",
            self._left_documents_panel_index,
            type=int,
        )
        self.qsettings.endGroup()
        if isinstance(index, int):
            return index
        return self._left_documents_panel_index

    def _saved_sidebar_tab_index(self) -> int:
        """Return the persisted sidebar page index."""
        self.qsettings.beginGroup("window_settings")
        index = self.qsettings.value(
            "active_sidebar_tab_index",
            self._stats_sidebar_index,
            type=int,
        )
        self.qsettings.endGroup()
        if not isinstance(index, int):
            return self._stats_sidebar_index
        return max(
            self._stats_sidebar_index,
            min(index, self._art_tools_sidebar_index),
        )

    def _clamp_art_tools_tab_index(self, index: int) -> int:
        """Clamp the nested art-tools tab index to the supported range."""
        return max(
            self._art_tools_model_tab_index,
            min(index, self._art_tools_image_browser_tab_index),
        )

    def _saved_art_tools_tab_index(self) -> int:
        """Return the persisted nested art-tools tab index."""
        index = self.qsettings.value(
            "tabs/stablediffusion_tool_tab/active_index",
            self._art_tools_model_tab_index,
            type=int,
        )
        if not isinstance(index, int):
            return self._art_tools_model_tab_index
        return self._clamp_art_tools_tab_index(index)

    def _current_art_tools_tab_index(self) -> int:
        """Return the active nested tab inside the art tools sidebar."""
        widget = getattr(self.ui, "art_tools_widget", None)
        if widget is None:
            return self._saved_art_tools_tab_index()

        current_index = getattr(widget, "current_tool_page_index", None)
        if callable(current_index):
            value = current_index()
            if isinstance(value, int):
                return self._clamp_art_tools_tab_index(value)
            return self._saved_art_tools_tab_index()

        tab_widget = getattr(
            getattr(widget, "ui", None),
            "tool_tab_widget_container",
            None,
        )
        if tab_widget is None:
            return self._saved_art_tools_tab_index()
        return self._clamp_art_tools_tab_index(tab_widget.currentIndex())

    def _store_active_left_panel_tab_index(self, index: int) -> None:
        """Persist the current left panel page index."""
        self.qsettings.beginGroup("window_settings")
        self.qsettings.setValue(
            "active_left_panel_tab_index",
            int(index),
        )
        self.qsettings.endGroup()
        self.qsettings.sync()

    def _store_active_sidebar_tab_index(self, index: int) -> None:
        """Persist the current sidebar page index."""
        self.qsettings.beginGroup("window_settings")
        self.qsettings.setValue(
            "active_sidebar_tab_index",
            int(index),
        )
        self.qsettings.endGroup()
        self.qsettings.sync()

    def _ensure_left_panel_page_loaded(self, page_index: int) -> None:
        """Load left-panel content lazily for the requested page."""
        if page_index == self._left_documents_panel_index:
            self._ensure_knowledgebase_loaded()
        elif page_index == self._left_history_panel_index:
            self._ensure_left_history_loaded()
        elif page_index == self._left_llm_settings_panel_index:
            self._ensure_left_llm_settings_loaded()

    def _ensure_sidebar_page_loaded(self, page_index: int) -> None:
        """Load sidebar content lazily for the requested page."""
        if page_index == self._stats_sidebar_index:
            self._ensure_stats_loaded()
        elif page_index == self._art_tools_sidebar_index:
            self._ensure_art_tools_loaded()

    def _toggle_sidebar_page(self, page_index: int, visible: bool) -> None:
        """Switch or hide the VS Code style right sidebar page."""
        if visible:
            self._ensure_sidebar_page_loaded(page_index)
            self.ui.sidebar_tab.setCurrentIndex(page_index)
            self._toggle_splitter_section(
                True,
                self._stats_splitter_index,
                self.ui.main_window_splitter,
                self._sidebar_page_min_size(page_index),
            )
        elif (
            self._sidebar_is_visible()
            and self._current_sidebar_index() == page_index
        ):
            self._toggle_splitter_section(
                False,
                self._stats_splitter_index,
                self.ui.main_window_splitter,
                self._sidebar_page_min_size(page_index),
            )

        self._sync_sidebar_button_states()

    def _toggle_art_tools_tab(self, tab_index: int, visible: bool) -> None:
        """Show or hide one nested art-tools tab from the right sidebar."""
        tab_index = self._clamp_art_tools_tab_index(tab_index)
        if visible:
            widget = self._ensure_art_tools_loaded()
            show_tool_page = getattr(widget, "show_tool_page", None)
            if callable(show_tool_page):
                show_tool_page(tab_index)
            self._toggle_sidebar_page(self._art_tools_sidebar_index, True)
            return

        if (
            self._sidebar_is_visible()
            and self._current_sidebar_index() == self._art_tools_sidebar_index
            and self._current_art_tools_tab_index() == tab_index
        ):
            self._toggle_sidebar_page(self._art_tools_sidebar_index, False)
            return

        self._sync_sidebar_button_states()

    def _sidebar_page_min_size(self, page_index: int) -> int:
        """Return a sensible opening width for one right-panel page."""
        if page_index == self._art_tools_sidebar_index:
            return 320
        return 280

    def _toggle_canvas_panel(self, visible: bool) -> None:
        """Show or hide the canvas panel within the center splitter."""
        min_size = 320
        if visible:
            if not self._center_section_is_visible():
                self._toggle_splitter_section(
                    True,
                    self._center_splitter_index,
                    self.ui.main_window_splitter,
                    min_size,
                )
            self._maximize_canvas_workspace()
            self._maximize_canvas_panel()
        elif self._canvas_panel_is_visible():
            self._toggle_splitter_section(
                False,
                self._canvas_panel_index,
                self.ui.center_splitter,
                min_size,
            )
            if not self._prompt_panel_is_visible():
                self._toggle_splitter_section(
                    False,
                    self._center_splitter_index,
                    self.ui.main_window_splitter,
                    min_size,
                )
        self._sync_sidebar_button_states()

    def _maximize_canvas_workspace(self) -> None:
        """Shrink visible left panels so the center workspace can expand."""
        splitter = getattr(self.ui, "main_window_splitter", None)
        if splitter is None:
            return

        sizes = splitter.sizes()
        if len(sizes) <= self._center_splitter_index:
            return

        total_width = sum(max(size, 0) for size in sizes)
        if total_width <= 0:
            return

        target_sizes = list(sizes)
        fixed_width = 0

        if self._left_panel_is_visible():
            target_sizes[self._documents_splitter_index] = (
                self._left_panel_target_width
            )
        else:
            target_sizes[self._documents_splitter_index] = 0
        fixed_width += target_sizes[self._documents_splitter_index]

        if len(sizes) > self._chat_splitter_index and (
            sizes[self._chat_splitter_index] > 0
        ):
            target_sizes[self._chat_splitter_index] = (
                self._chat_panel_target_width
            )
        else:
            target_sizes[self._chat_splitter_index] = 0
        fixed_width += target_sizes[self._chat_splitter_index]

        if len(sizes) > self._stats_splitter_index and (
            sizes[self._stats_splitter_index] <= 0
        ):
            target_sizes[self._stats_splitter_index] = 0
        fixed_width += target_sizes[self._stats_splitter_index]

        target_sizes[self._center_splitter_index] = max(
            1,
            total_width - fixed_width,
        )
        splitter.setSizes(target_sizes)

    def _maximize_canvas_panel(self) -> None:
        """Let the canvas take the remaining width in the center splitter."""
        splitter = getattr(self.ui, "center_splitter", None)
        if splitter is None:
            return
        prompt_size = 1 if self._prompt_panel_is_visible() else 0
        splitter.setSizes([10000, prompt_size])

    def _toggle_prompt_panel(self, visible: bool) -> None:
        """Show or hide the dedicated prompt panel."""
        min_size = 350
        if visible:
            self._ensure_art_prompt_loaded()
            if not self._center_section_is_visible():
                self._toggle_splitter_section(
                    True,
                    self._center_splitter_index,
                    self.ui.main_window_splitter,
                    min_size,
                )
            self._toggle_splitter_section(
                True,
                self._prompt_panel_index,
                self.ui.center_splitter,
                min_size,
            )
        elif self._prompt_panel_is_visible():
            self._toggle_splitter_section(
                False,
                self._prompt_panel_index,
                self.ui.center_splitter,
                min_size,
            )
            if not self._canvas_panel_is_visible():
                self._toggle_splitter_section(
                    False,
                    self._center_splitter_index,
                    self.ui.main_window_splitter,
                    min_size,
                )
        self._sync_sidebar_button_states()

    def _toggle_left_panel_page(self, page_index: int, visible: bool) -> None:
        """Switch or hide the shared left splitter panel page."""
        if visible:
            self._ensure_left_panel_page_loaded(page_index)
            self.ui.left_panel_tab.setCurrentIndex(page_index)
            if not self._left_panel_is_visible():
                self._toggle_splitter_section(
                    True,
                    self._documents_splitter_index,
                    self.ui.main_window_splitter,
                    self._left_panel_target_width,
                )
        elif (
            self._left_panel_is_visible()
            and self._current_left_panel_index() == page_index
        ):
            self._toggle_splitter_section(
                False,
                self._documents_splitter_index,
                self.ui.main_window_splitter,
                self._left_panel_target_width,
            )

        self._sync_left_panel_button_states()

    def _sync_left_panel_button_states(self) -> None:
        """Update left-panel toggle buttons from current panel state."""
        self.set_knowledgebase_button_checked()
        self.set_history_sidebar_button_checked()
        self.set_llm_settings_sidebar_button_checked()

    def _sync_sidebar_button_states(self) -> None:
        """Update the canvas and sidebar toggle buttons from panel state."""
        self.set_canvas_button_checked()
        self.set_prompt_editor_button_checked()
        self.set_art_model_button_checked()
        self.set_lora_button_checked()
        self.set_embeddings_button_checked()
        self.set_layers_button_checked()
        self.set_grid_button_checked()
        self.set_image_browser_button_checked()
        self.set_stats_button_checked()

    def set_chat_button_checked(self):
        self.ui.chat_button.blockSignals(True)
        self.ui.chat_button.setChecked(
            len(self.ui.main_window_splitter.sizes())
            > self._chat_splitter_index
            and self.ui.main_window_splitter.sizes()[
                self._chat_splitter_index
            ]
            > 0
        )
        self.ui.chat_button.blockSignals(False)

    def set_knowledgebase_button_checked(self):
        self.ui.knowledgebase_button.blockSignals(True)
        self.ui.knowledgebase_button.setChecked(
            self._left_panel_is_visible()
            and self._current_left_panel_index()
            == self._left_documents_panel_index
        )
        self.ui.knowledgebase_button.blockSignals(False)

    def set_canvas_button_checked(self):
        button = getattr(self.ui, "canvas_button", None)
        if button is None:
            return
        button.blockSignals(True)
        button.setChecked(self._canvas_panel_is_visible())
        button.blockSignals(False)

    def set_history_sidebar_button_checked(self):
        button = getattr(self.ui, "history_sidebar_button", None)
        if button is None:
            return
        button.blockSignals(True)
        button.setChecked(
            self._left_panel_is_visible()
            and self._current_left_panel_index()
            == self._left_history_panel_index
        )
        button.blockSignals(False)

    def set_llm_settings_sidebar_button_checked(self):
        button = getattr(self.ui, "llm_settings_sidebar_button", None)
        if button is None:
            return
        button.blockSignals(True)
        button.setChecked(
            self._left_panel_is_visible()
            and self._current_left_panel_index()
            == self._left_llm_settings_panel_index
        )
        button.blockSignals(False)

    def set_prompt_editor_button_checked(self):
        button = getattr(self.ui, "prompt_editor_button", None)
        if button is None:
            return
        button.blockSignals(True)
        button.setChecked(self._prompt_panel_is_visible())
        button.blockSignals(False)

    def set_art_model_button_checked(self):
        self._set_art_tools_button_checked(
            "art_model_button",
            self._art_tools_model_tab_index,
        )

    def set_lora_button_checked(self):
        self._set_art_tools_button_checked(
            "lora_button",
            self._art_tools_lora_tab_index,
        )

    def set_embeddings_button_checked(self):
        self._set_art_tools_button_checked(
            "embeddings_button",
            self._art_tools_embeddings_tab_index,
        )

    def set_layers_button_checked(self):
        self._set_art_tools_button_checked(
            "layers_button",
            self._art_tools_layers_tab_index,
        )

    def set_grid_button_checked(self):
        self._set_art_tools_button_checked(
            "grid_button",
            self._art_tools_grid_tab_index,
        )

    def set_image_browser_button_checked(self):
        self._set_art_tools_button_checked(
            "image_browser_button",
            self._art_tools_image_browser_tab_index,
        )

    def _set_art_tools_button_checked(
        self,
        button_name: str,
        tab_index: int,
    ) -> None:
        """Sync one right-rail art-tools button with sidebar state."""
        button = getattr(self.ui, button_name, None)
        if button is None:
            return
        button.blockSignals(True)
        button.setChecked(
            self._sidebar_is_visible()
            and self._current_sidebar_index()
            == self._art_tools_sidebar_index
            and self._current_art_tools_tab_index() == tab_index
        )
        button.blockSignals(False)
    
    def set_stats_button_checked(self):
        self.ui.stats_button.blockSignals(True)
        self.ui.stats_button.setChecked(
            self._sidebar_is_visible()
            and self._current_sidebar_index() == self._stats_sidebar_index
        )
        self.ui.stats_button.blockSignals(False)

    @Slot()
    def on_actionQuit_triggered(self):
        self.handle_close()

    @Slot()
    def on_actionReset_Settings_2_triggered(self):
        self._action_reset_settings()

    @Slot()
    def on_actionExport_image_button_triggered(self):
        if (
            not self.api
            or not hasattr(self.api, "art")
            or not hasattr(self.api.art, "canvas")
        ):
            self.logger.warning(
                "MainWindow: self.api.art.canvas is missing. Cannot export image."
            )
            return
        self.api.art.canvas.export_image()

    @Slot()
    def on_actionImport_image_triggered(self):
        if (
            not self.api
            or not hasattr(self.api, "art")
            or not hasattr(self.api.art, "canvas")
        ):
            self.logger.warning(
                "MainWindow: self.api.art.canvas is missing. Cannot import image."
            )
            return
        self.api.art.canvas.import_image()

    @Slot()
    def on_artActionNew_triggered(self):
        self._ensure_canvas_loaded()
        canvas = getattr(self, "canvas", None)
        if canvas is None or not hasattr(canvas, "start_new_document_flow"):
            self.logger.warning(
                "MainWindow: canvas widget is missing. Cannot create "
                "a new document."
            )
            return
        canvas.start_new_document_flow()

    @Slot()
    def on_actionCopy_triggered(self):
        if (
            not self.api
            or not hasattr(self.api, "art")
            or not hasattr(self.api.art, "canvas")
        ):
            self.logger.warning(
                "MainWindow: self.api.art.canvas is missing. Cannot copy image."
            )
            return
        self.api.art.canvas.copy_image()

    @Slot()
    def on_actionClear_all_prompts_triggered(self):
        self.clear_all_prompts()

    @Slot()
    def on_actionBrowse_AI_Runner_Path_triggered(self):
        # Note: show_path functionality removed with old agent system
        # path = self.path_settings.base_path
        # if path == "":
        #     path = AIRUNNER_BASE_PATH
        # TODO: Implement file browser opening if needed
        pass

    @Slot()
    def on_actionDownload_Model_triggered(self):
        show_download_model_dialog(
            self, self.path_settings, self.application_settings
        )

    @Slot()
    def action_show_model_path_txt2img(self):
        self.show_settings_path("txt2img_model_path")

    @Slot()
    def action_show_model_path_inpaint(self):
        self.show_settings_path("inpaint_model_path")

    @Slot()
    def action_show_model_path_embeddings(self):
        self.show_settings_path("embeddings_model_path")

    @Slot()
    def action_show_model_path_lora(self):
        self.show_settings_path("lora_model_path")

    @Slot()
    def action_show_llm(self):
        pass

    @Slot()
    def on_actionReport_vulnerability_triggered(self):
        webbrowser.open(AIRUNNER_VULNERABILITY_REPORT_LINK)

    @Slot()
    def on_actionBug_report_triggered(self):
        webbrowser.open(AIRUNNER_BUG_REPORT_LINK)

    @Slot()
    def on_actionDiscussions_triggered(self):
        if AIRUNNER_DISCUSSIONS_URL:
            webbrowser.open(AIRUNNER_DISCUSSIONS_URL)

    @Slot(bool)
    def action_outpaint_toggled(self, val: bool):
        self.update_outpaint_settings(enabled=val)

    @Slot()
    def action_outpaint_export(self):
        pass

    @Slot()
    def action_outpaint_import(self):
        pass

    @Slot()
    def on_actionRun_setup_wizard_2_triggered(self):
        self.show_setup_wizard()

    @Slot()
    def on_actionSettings_triggered(self):
        self._show_settings_window()

    @Slot()
    def on_actionBrowse_Images_Path_2_triggered(self):
        self.show_settings_path("image_path")

    @Slot()
    def on_actionPrompt_Browser_triggered(self):
        PromptBrowser()

    @Slot(bool)
    def on_speech_to_text_button_toggled(self, val: bool):
        if self._model_status[ModelType.STT] is ModelStatus.LOADING:
            val = not val
        self._update_action_button(
            ModelType.STT,
            getattr(self.ui, "speech_to_text_button", None),
            val,
            SignalCode.STT_LOAD_SIGNAL,
            SignalCode.STT_UNLOAD_SIGNAL,
            "stt_enabled",
        )

    @Slot(bool)
    def on_text_to_speech_button_toggled(self, val: bool):
        self.on_toggle_tts(val=val)

    @Slot(bool)
    def on_actionSafety_Checker_toggled(self, val: bool):
        """Handle safety checker toggle action."""
        # If disabling the safety checker, show warning dialog
        if not val:
            # Check if we should show the warning (user hasn't chosen to hide it)
            settings = get_qsettings()
            show_warning = settings.value(
                "nsfw_warning/show_again", True, type=bool
            )

            if show_warning:
                confirmed, do_not_show_again = show_nsfw_warning_dialog(
                    self, show_again_default=bool(show_warning)
                )

                # Save the "do not show again" preference
                if do_not_show_again:
                    settings.setValue("nsfw_warning/show_again", False)

                # If user cancelled, revert the checkbox
                if not confirmed:
                    if hasattr(self.ui, "actionSafety_Checker"):
                        self.ui.actionSafety_Checker.blockSignals(True)
                        self.ui.actionSafety_Checker.setChecked(True)
                        self.ui.actionSafety_Checker.blockSignals(False)
                    return

        # Update the setting
        self.update_application_settings(nsfw_filter=val)
        self.set_nsfw_filter_tooltip()

        # Emit signal to load or unload the safety checker worker
        from airunner.enums import SignalCode

        if val:
            self.emit_signal(SignalCode.SAFETY_CHECKER_LOAD_SIGNAL, {})
        else:
            self.emit_signal(SignalCode.SAFETY_CHECKER_UNLOAD_SIGNAL, {})

    def set_nsfw_filter_tooltip(self):
        """Update the safety checker button tooltip based on current state."""
        nsfw_filter = self.application_settings.nsfw_filter
        if hasattr(self.ui, "actionSafety_Checker"):
            self.ui.actionSafety_Checker.setToolTip(
                f"Click to {'enable' if not nsfw_filter else 'disable'} NSFW filter"
            )

    def _add_legal_menu_items(self):
        """Add Terms of Service, Privacy Policy, and Age Agreement menu items to Help menu."""
        from PySide6.QtGui import QAction
        
        # Add separator before legal items
        self.ui.menuAbout.addSeparator()
        
        # Age Agreement action
        self.actionAgeAgreement = QAction("Age Restriction Policy", self)
        self.actionAgeAgreement.triggered.connect(self._show_age_agreement)
        self.ui.menuAbout.addAction(self.actionAgeAgreement)
        
        # Terms of Service action
        self.actionTermsOfService = QAction("Terms of Service", self)
        self.actionTermsOfService.triggered.connect(self._show_terms_of_service)
        self.ui.menuAbout.addAction(self.actionTermsOfService)
        
        # Privacy Policy action
        self.actionPrivacyPolicy = QAction("Privacy Policy", self)
        self.actionPrivacyPolicy.triggered.connect(self._show_privacy_policy)
        self.ui.menuAbout.addAction(self.actionPrivacyPolicy)

    def _add_download_models_menu_item(self):
        """Add Download Models action to Tools menu."""
        from PySide6.QtGui import QAction
        
        # Add separator before download models
        self.ui.menuTools.addSeparator()
        
        # Download Models action
        self.actionDownloadModels = QAction("Download Models...", self)
        self.actionDownloadModels.setToolTip(
            "Download pre-configured models from HuggingFace"
        )
        self.actionDownloadModels.triggered.connect(self._show_download_models_dialog)
        self.ui.menuTools.addAction(self.actionDownloadModels)
        
        # Privacy Settings action
        self.actionPrivacySettings = QAction("Privacy Settings...", self)
        self.actionPrivacySettings.setToolTip(
            "Manage external service connections and privacy options"
        )
        self.actionPrivacySettings.triggered.connect(self._show_privacy_settings)
        self.ui.menuTools.addAction(self.actionPrivacySettings)

    
    def _show_privacy_settings(self):
        """Show the Privacy Settings dialog."""
        from airunner.components.application.gui.dialogs.privacy_consent_dialog import (
            PrivacyConsentDialog,
        )
        dialog = PrivacyConsentDialog(self)
        dialog.exec()

    def _show_download_models_dialog(self):
        """Show the Download Models dialog."""
        from airunner.components.application.gui.dialogs.download_models_dialog import (
            show_download_models_dialog,
        )
        show_download_models_dialog(self)
    
    def _show_age_agreement(self):
        """Show Age Agreement dialog."""
        from airunner.components.application.gui.dialogs.legal_document_dialog import (
            LegalDocumentDialog,
        )
        dialog = LegalDocumentDialog(
            self,
            title="Age Restriction Policy",
            document_type="age"
        )
        dialog.exec()
    
    def _show_terms_of_service(self):
        """Show Terms of Service dialog."""
        from airunner.components.application.gui.dialogs.legal_document_dialog import (
            LegalDocumentDialog,
        )
        dialog = LegalDocumentDialog(
            self,
            title="Terms of Service",
            document_type="terms"
        )
        dialog.exec()
    
    def _show_privacy_policy(self):
        """Show Privacy Policy dialog."""
        from airunner.components.application.gui.dialogs.legal_document_dialog import (
            LegalDocumentDialog,
        )
        dialog = LegalDocumentDialog(
            self,
            title="Privacy Policy",
            document_type="privacy"
        )
        dialog.exec()

    @Slot()
    def on_actionAbout_triggered(self):
        AboutWindow()

    @Slot()
    def on_actionNew_Conversation_triggered(self):
        if not self.api or not hasattr(self.api, "llm"):
            self.logger.warning(
                "MainWindow: self.api.llm is missing. Cannot clear LLM history."
            )
            return
        self.api.llm.clear_history()

    @Slot()
    def on_actionDelete_conversation_triggered(self):
        if not self.api or not hasattr(self.api, "llm"):
            self.logger.warning(
                "MainWindow: self.api.llm is missing. Cannot delete conversation."
            )
            return
        current_conversation = self.llm_generator_settings.current_conversation
        self.api.llm.converation_deleted(current_conversation.id)

    def _set_tab_index(self, tab_widget):
        """Legacy compatibility stub for removed center-tab navigation."""
        del tab_widget

    def _attach_lazy_widget(
        self,
        parent_attr,
        widget_attr,
        object_name,
        factory,
        placeholder_attr=None,
    ):
        widget = getattr(self.ui, widget_attr, None)
        if widget is not None:
            return widget

        parent = getattr(self.ui, parent_attr)
        layout = parent.layout()
        if layout is None:
            layout = QGridLayout(parent)
            layout.setContentsMargins(0, 0, 0, 0)

        widget = factory(parent)
        widget.setObjectName(object_name)

        if placeholder_attr is not None:
            placeholder = getattr(self.ui, placeholder_attr, None)
        else:
            placeholder = None
        if placeholder is not None:
            layout.removeWidget(placeholder)
            placeholder.deleteLater()
            if placeholder_attr is not None:
                setattr(self.ui, placeholder_attr, None)

        layout.addWidget(widget, 0, 0, 1, 1)
        setattr(self.ui, widget_attr, widget)
        return widget

    def _ensure_canvas_loaded(self) -> None:
        """Create the main canvas once after the window is shown."""
        from airunner.components.art.gui.widgets.canvas.canvas_widget import (
            CanvasWidget,
        )

        self.canvas = self._attach_lazy_widget(
            "center_tab_container",
            "canvas",
            "canvas",
            CanvasWidget,
            placeholder_attr="canvas_placeholder",
        )

    def _ensure_knowledgebase_loaded(self) -> None:
        """Create the documents sidebar page only when it is shown."""
        from airunner.components.documents.gui.widgets.documents import (
            DocumentsWidget,
        )

        self._ensure_left_panel_host()
        self._attach_lazy_widget(
            "left_documents_page",
            "documents",
            "documents",
            DocumentsWidget,
            placeholder_attr="left_documents_placeholder",
        )

    def _ensure_left_history_loaded(self) -> None:
        """Create the history left-panel page only when it is shown."""
        from airunner.components.llm.gui.widgets.llm_history_widget import (
            LLMHistoryWidget,
        )

        self._ensure_left_panel_host()
        self._attach_lazy_widget(
            "left_history_page",
            "left_history_widget",
            "left_history_widget",
            LLMHistoryWidget,
            placeholder_attr="left_history_placeholder",
        )

    def _ensure_left_llm_settings_loaded(self) -> None:
        """Create the LLM settings left-panel page only when it is shown."""
        from airunner.components.llm.gui.widgets.llm_settings_widget import (
            LLMSettingsWidget,
        )

        self._ensure_left_panel_host()
        widget = self._attach_lazy_widget(
            "left_llm_settings_page",
            "left_llm_settings_widget",
            "left_llm_settings_widget",
            LLMSettingsWidget,
            placeholder_attr="left_llm_settings_placeholder",
        )
        handle_loaded = getattr(widget, "handle_main_window_loaded", None)
        if callable(handle_loaded):
            handle_loaded()

    def _create_left_sidebar_buttons(self) -> None:
        """Ensure left-rail history/settings buttons exist and are wired."""
        history_button = getattr(self.ui, "history_sidebar_button", None)
        if history_button is None:
            history_button = QPushButton(self.ui.actionsidebar)
            history_button.setObjectName("history_sidebar_button")
            history_button.setMinimumSize(35, 35)
            history_button.setMaximumSize(35, 35)
            history_button.setCursor(
                QCursor(Qt.CursorShape.PointingHandCursor)
            )
            history_button.setCheckable(True)
            history_button.setFlat(True)
            history_button.setToolTip("Chat history")
            self.ui.action_sidebar.insertWidget(2, history_button)
            self.ui.history_sidebar_button = history_button

        llm_settings_button = getattr(
            self.ui,
            "llm_settings_sidebar_button",
            None,
        )
        if llm_settings_button is None:
            llm_settings_button = QPushButton(self.ui.actionsidebar)
            llm_settings_button.setObjectName("llm_settings_sidebar_button")
            llm_settings_button.setMinimumSize(35, 35)
            llm_settings_button.setMaximumSize(35, 35)
            llm_settings_button.setCursor(
                QCursor(Qt.CursorShape.PointingHandCursor)
            )
            llm_settings_button.setCheckable(True)
            llm_settings_button.setFlat(True)
            llm_settings_button.setToolTip("LLM generator settings")
            self.ui.action_sidebar.insertWidget(3, llm_settings_button)
            self.ui.llm_settings_sidebar_button = llm_settings_button

        if getattr(self, "_left_sidebar_buttons_connected", False):
            return

        history_button.toggled.connect(
            self.on_history_sidebar_button_toggled
        )
        llm_settings_button.toggled.connect(
            self.on_llm_settings_sidebar_button_toggled
        )
        self._left_sidebar_buttons_connected = True

    def _ensure_left_panel_host(self) -> None:
        """Replace the single documents placeholder with a hidden tab host."""
        existing_tab_widget = getattr(self.ui, "left_panel_tab", None)
        if existing_tab_widget is not None:
            existing_tab_widget.tabBar().hide()
            if not getattr(self, "_left_panel_host_connected", False):
                existing_tab_widget.currentChanged.connect(
                    self.on_left_panel_tab_current_changed
                )
                self._left_panel_host_connected = True
            return

        container = self.ui.documents_sidebar
        layout = container.layout()
        if layout is None:
            layout = QGridLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)

        tab_widget = QTabWidget(container)
        tab_widget.setObjectName("left_panel_tab")
        tab_widget.tabBar().hide()

        def add_page(page_name: str, placeholder_name: str) -> None:
            page = QWidget(tab_widget)
            page.setObjectName(page_name)
            page_layout = QGridLayout(page)
            page_layout.setContentsMargins(0, 0, 0, 0)
            placeholder = QWidget(page)
            placeholder.setObjectName(placeholder_name)
            page_layout.addWidget(placeholder, 0, 0, 1, 1)
            tab_widget.addTab(page, "")
            setattr(self.ui, page_name, page)
            setattr(self.ui, placeholder_name, placeholder)

        add_page("left_documents_page", "left_documents_placeholder")
        add_page("left_history_page", "left_history_placeholder")
        add_page(
            "left_llm_settings_page",
            "left_llm_settings_placeholder",
        )

        placeholder = getattr(self.ui, "documents_placeholder", None)
        if placeholder is not None:
            layout.removeWidget(placeholder)
            placeholder.deleteLater()
            setattr(self.ui, "documents_placeholder", None)

        if isinstance(layout, QGridLayout):
            layout.addWidget(tab_widget, 0, 0, 1, 1)
        else:
            layout.addWidget(tab_widget)
        self.ui.left_panel_tab = tab_widget
        self.ui.left_panel_tab.currentChanged.connect(
            self.on_left_panel_tab_current_changed
        )
        self._left_panel_host_connected = True
    
    def _ensure_stats_loaded(self) -> None:
        """Create the stats sidebar page only when it is shown."""
        self._attach_lazy_widget(
            "stats_page",
            "model_status_widget",
            "model_status_widget",
            ModelStatusWidget,
            placeholder_attr="stats_placeholder",
        )

    def _ensure_art_prompt_loaded(self) -> None:
        """Create the art prompt page only when it is shown."""
        from airunner.components.art.gui.widgets.stablediffusion.stablediffusion_generator_form import (
            StableDiffusionGeneratorForm,
        )

        self._attach_lazy_widget(
            "prompt_sidebar",
            "art_prompt_widget",
            "art_prompt_widget",
            StableDiffusionGeneratorForm,
            placeholder_attr="art_prompt_placeholder",
        )

    def _ensure_art_tools_loaded(self) -> None:
        """Create the art settings page only when it is shown."""
        from airunner.components.art.gui.widgets.stablediffusion.stablediffusion_tool_tab_widget import (
            StablediffusionToolTabWidget,
        )

        widget = self._attach_lazy_widget(
            "art_tools_page",
            "art_tools_widget",
            "art_tools_widget",
            StablediffusionToolTabWidget,
            placeholder_attr="art_tools_placeholder",
        )
        show_tool_page = getattr(widget, "show_tool_page", None)
        if callable(show_tool_page):
            show_tool_page(self._saved_art_tools_tab_index())
        return widget

    @property
    def buttons(self) -> Dict:
        return {}

    def _restore_tab(self):
        """Center-tab restoration was removed with the home/art split."""

    def _set_current_button_and_tab(self, button_name: str):
        """Center-tab switching was removed with the home/art split."""
        del button_name

    @Slot(bool)
    def on_settings_button_clicked(self, val: bool):
        del val
        self._show_settings_window()

    def _show_settings_window(self):
        if self.settings_window is None:
            self.settings_window = SettingsWindow(
                prevent_always_on_top=False, exec=False
            )
            self.settings_window.show()
        elif not self.settings_window.isVisible():
            self.settings_window.show()
        self.settings_window.raise_()

    def _action_reset_settings(self):
        reply = QMessageBox.question(
            self,
            "Reset Settings",
            "Are you sure you want to reset all settings to their default values?",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.reset_settings()
            self.restart()

    """
    End slot functions
    """

    def on_reset_paths_signal(self):
        self.reset_path_settings()

    def restart(self):
        # Save the current state
        self.save_state()

        # Close the main window
        self.close()

        # Start a new instance of the application
        QProcess.startDetached(sys.executable, sys.argv)

    def toggle_window_visibility(self):
        """Toggle window visibility and update the menu text."""
        toggle_visibility_action = getattr(
            self,
            "toggle_visibility_action",
            None,
        )
        tray_icon = getattr(self, "tray_icon", None)
        tray_menu = getattr(self, "tray_menu", None)
        if self.isVisible():
            self.hide()
            if toggle_visibility_action is not None:
                toggle_visibility_action.setText("Show Window")
        else:
            self.showNormal()
            self.activateWindow()  # Ensure window gets focus when showing
            if toggle_visibility_action is not None:
                toggle_visibility_action.setText("Hide Window")

        # Update the tray menu so it reflects the current state immediately
        if tray_icon is not None and tray_menu is not None:
            tray_icon.setContextMenu(tray_menu)

    def handle_single_click(self):
        """Handle single-click on the tray icon."""
        # Create a dropdown menu
        menu = QMenu()

        # Dynamically set the text based on current window visibility
        show_hide_text = "Hide Window" if self.isVisible() else "Show Window"
        show_action = QAction(show_hide_text, self)
        quit_action = QAction("Quit", self)

        # Connect actions to their respective slots
        show_action.triggered.connect(self.toggle_window_visibility)
        quit_action.triggered.connect(QApplication.quit)

        # Add actions to the menu
        menu.addAction(show_action)
        menu.addAction(quit_action)

        # Display the menu under the tray icon
        menu.exec(QCursor.pos())

    def handle_double_click(self):
        """Handle double-click on the tray icon."""
        self.toggle_window_visibility()  # Use toggle instead of just showing

    @staticmethod
    def on_write_file_signal(data: Dict):
        """
        Writes data to a file.
        :param data: Dict
        :return: None
        """
        args = data["args"]
        if len(args) == 1:
            message = args[0]
        else:
            message = args[1]
        with open("output.txt", "w") as f:
            f.write(message)

    def on_theme_changed_signal(self, data: Dict):
        template = data.get("template")
        self.set_stylesheet(
            template=template,
        )

    def initialize_ui(self):
        total_started_at = time.perf_counter()
        self.logger.debug("Loading UI")

        phase_started_at = time.perf_counter()
        self.ui.setupUi(self)
        self._create_left_sidebar_buttons()
        self._ensure_left_panel_host()
        self.logger.info(
            "MainWindow startup phase setup_ui completed in %.2fs",
            time.perf_counter() - phase_started_at,
        )

        phase_started_at = time.perf_counter()
        # Add legal document menu items to Help menu
        self._add_legal_menu_items()

        # Add Download Models menu item to Tools menu
        self._add_download_models_menu_item()

        self.icon_manager = IconManager(self.icons, self.ui)

        if not AIRUNNER_ART_ENABLED:
            self._disable_aiart_gui_elements()

        left_panel_page_index = self._saved_left_panel_tab_index()
        self.ui.left_panel_tab.blockSignals(True)
        self.ui.left_panel_tab.setCurrentIndex(left_panel_page_index)
        self.ui.left_panel_tab.blockSignals(False)
        sidebar_page_index = self._saved_sidebar_tab_index()
        self.ui.sidebar_tab.tabBar().hide()
        self.ui.sidebar_tab.blockSignals(True)
        self.ui.sidebar_tab.setCurrentIndex(sidebar_page_index)
        self.ui.sidebar_tab.blockSignals(False)
        self.ui.sidebar_tab.currentChanged.connect(
            self.on_sidebar_tab_current_changed
        )
        self.logger.info(
            "MainWindow startup phase startup_state_prep completed in %.2fs",
            time.perf_counter() - phase_started_at,
        )

        phase_started_at = time.perf_counter()
        self.set_stylesheet()
        self.icon_manager.set_icons()
        self.logger.info(
            "MainWindow startup phase styles_and_icons completed in %.2fs",
            time.perf_counter() - phase_started_at,
        )

        phase_started_at = time.perf_counter()
        self.restore_state()
        self.logger.info(
            "MainWindow startup phase restore_state completed in %.2fs",
            time.perf_counter() - phase_started_at,
        )

        phase_started_at = time.perf_counter()
        # Configure default splitter sizes to maximize the canvas area (index 1)
        default_splitter_config = {
            "main_window_splitter": {
                "index_to_maximize": self._center_splitter_index,
                "min_other_size": 50,
            },
            "center_splitter": {
                "index_to_maximize": self._canvas_panel_index,
                "min_other_size": 0,
            }
        }
        load_splitter_settings(
            self.ui,
            ["main_window_splitter", "center_splitter"],
            default_maximize_config=default_splitter_config,
            namespace="MainWindow",
        )

        if self._sidebar_is_visible():
            self._restore_sidebar_page_after_startup = sidebar_page_index
        if self._prompt_panel_is_visible():
            self._ensure_art_prompt_loaded()
        if self._left_panel_is_visible():
            self._restore_left_panel_page_after_startup = (
                left_panel_page_index
            )

        self.status_widget = StatusWidget()
        self.statusBar().addPermanentWidget(self.status_widget)
        if not self.api:
            self.logger.warning(
                "MainWindow: self.api is missing. Cannot clear status message."
            )
            return
        self.api.clear_status_message()
        self.logger.info(
            "MainWindow startup phase splitter_and_status completed in %.2fs",
            time.perf_counter() - phase_started_at,
        )

        phase_started_at = time.perf_counter()
        self.initialize_widget_elements()
        self.logger.info(
            "MainWindow startup phase initialize_widget_elements completed in %.2fs",
            time.perf_counter() - phase_started_at,
        )
        self.last_tray_click_time = 0
        self.settings_window = None
        self.hide_center_tab_header()

        self.ui.main_window_splitter.splitterMoved.connect(
            self.on_splitter_changed_sizes
        )
        self.ui.center_splitter.splitterMoved.connect(
            self.on_splitter_changed_sizes
        )
        self.set_chat_button_checked()
        self._sync_left_panel_button_states()
        self._sync_sidebar_button_states()

        # Keyboard shortcut: Ctrl+N -> placeholder handler using QAction
        try:
            action_new_shortcut = QAction(self)
            action_new_shortcut.setShortcut(QKeySequence("Ctrl+N"))
            action_new_shortcut.triggered.connect(self._on_ctrl_n_pressed)
            # add to window so the shortcut is active
            self.addAction(action_new_shortcut)
            self._action_new_shortcut = action_new_shortcut
        except Exception:
            # Fail silently if QAction creation fails
            try:
                self.logger.debug("Could not create Ctrl+N QAction shortcut")
            except Exception:
                pass

        self.logger.info(
            "MainWindow initialize_ui completed in %.2fs",
            time.perf_counter() - total_started_at,
        )

    def _disable_aiart_gui_elements(self):
        for attr in (
            "center_widget",
            "menuFilters",
            "menuStable_Diffusion",
            "menuArt",
        ):
            widget = getattr(self.ui, attr, None)
            if widget is None:
                continue
            widget.hide()
            widget.deleteLater()

        for attr in (
            "actionBrowse_AI_Runner_Path",
            "actionBrowse_Images_Path_2",
            "actionCut",
            "actionCopy",
            "actionPaste",
            "actionPrompt_Browser",
        ):
            action = getattr(self.ui, attr, None)
            if action is not None:
                action.deleteLater()

    def initialize_widget_elements(self):
        for element, enabled in (
            (
                getattr(self.ui, "text_to_speech_button", None),
                self.application_settings.tts_enabled,
            ),
            (
                getattr(self.ui, "speech_to_text_button", None),
                self.application_settings.stt_enabled,
            ),
        ):
            if element is None:
                continue
            element.blockSignals(True)
            element.setChecked(enabled or False)
            element.blockSignals(False)

        # Initialize safety checker action if it exists
        if hasattr(self.ui, "actionSafety_Checker"):
            self.ui.actionSafety_Checker.blockSignals(True)
            self.ui.actionSafety_Checker.setChecked(
                self.application_settings.nsfw_filter
            )
            self.ui.actionSafety_Checker.blockSignals(False)
            self.set_nsfw_filter_tooltip()
        self.initialized = True

    @staticmethod
    def _set_action_checked_state(action, checked: bool) -> None:
        """Update one toggle without re-triggering its signal."""
        action.blockSignals(True)
        action.setChecked(checked)
        action.blockSignals(False)

    @staticmethod
    def _allows_loading_toggle(model_type: ModelType) -> bool:
        """Return True when a loading toggle may still change preference."""
        return model_type in (ModelType.TTS, ModelType.STT)

    @staticmethod
    def _modifier_value(modifiers: object) -> int:
        """Return a stable integer value for Qt keyboard modifiers."""
        if modifiers is None:
            return 0
        value = getattr(modifiers, "value", modifiers)
        if isinstance(value, int):
            return value
        return 0

    def keyPressEvent(self, event):
        super().keyPressEvent(event)
        try:
            event_modifiers = self._modifier_value(event.modifiers())
            for v in self.shortcut_keys:
                shortcut_modifiers = int(getattr(v, "modifiers", 0) or 0)
                if v.key != event.key():
                    continue
                if shortcut_modifiers != event_modifiers:
                    continue
                for signal in SignalCode:
                    if signal.value == v.signal:
                        self.emit_signal(signal)
                        return
        except Exception:
            self.logger.exception("Failed to process keyboard shortcut")

    def key_text(self, key_name):
        for shortcutkey in self.shortcut_keys:
            if shortcutkey.name == key_name:
                return shortcutkey.text
        return ""

    @Slot()
    def _on_ctrl_n_pressed(self):
        """Create a new art document for the always-visible canvas."""
        if not self.api or not hasattr(self.api, "art"):
            return
        canvas = getattr(self.api.art, "canvas", None)
        if canvas is None:
            self._ensure_canvas_loaded()
            canvas = getattr(self.api.art, "canvas", None)
        if canvas is not None:
            canvas.new_document()

    def on_save_stablediffusion_prompt_signal(self, data: Dict):
        self.create_saved_prompt(
            {
                "prompt": data["prompt"],
                "negative_prompt": data["negative_prompt"],
                "secondary_prompt": data["secondary_prompt"],
                "secondary_negative_prompt": data["secondary_negative_prompt"],
            }
        )

    def create_saved_prompt(self, data: Dict):
        """Persist a Stable Diffusion prompt in the SavedPrompt table.

        This is invoked by SD_SAVE_PROMPT_SIGNAL. Previously this method was
        referenced but not implemented, causing an AttributeError.
        """

        try:
            from airunner.components.art.data.saved_prompt import SavedPrompt
        except Exception as e:
            self.logger.error(f"Failed to import SavedPrompt: {e}")
            return

        saved_prompt = SavedPrompt(
            prompt=data.get("prompt"),
            negative_prompt=data.get("negative_prompt"),
            secondary_prompt=data.get("secondary_prompt"),
            secondary_negative_prompt=data.get("secondary_negative_prompt"),
        )

        saved_prompt.save()
        # NOTE: SavedPrompt instances are session-scoped and may be detached
        # after save(); avoid touching ORM attributes here (e.g. saved_prompt.id)
        # to prevent DetachedInstanceError.
        self.logger.info("Saved Stable Diffusion prompt")

    def set_path_settings(self, key, val):
        self.update_path_settings(**{key: val})

    def closeEvent(self, event):
        event.ignore()
        self.handle_close()

    def handle_close(self):
        """Override close to minimize to tray instead of exiting."""
        self.quit()

    def quit(self):
        if self.quitting:
            return
        self.logger.debug("Quitting")
        if self._daemon_status_timer.isActive():
            self._daemon_status_timer.stop()
        self.save_state()
        self.quitting = True
        if not self.api:
            self.logger.warning(
                "MainWindow: self.api is missing. Cannot quit application."
            )
            return
        self.emit_signal(SignalCode.SAVE_STATE, {})
        self.emit_signal(SignalCode.QUIT_APPLICATION, {})

    def handle_quit_application_signal(self):
        self.hide()
        QTimer.singleShot(0, QApplication.quit)

    def show_settings_path(self, name, default_path=None):
        # Note: show_path functionality removed with old agent system
        # path = getattr(self.path_settings, name)
        # TODO: Implement file browser opening if needed
        del name, default_path
        pass

    def on_toggle_fullscreen_signal(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def on_toggle_llm(
        self,
        data: Optional[Dict] = None,
        val: Optional[bool] = None,
    ):
        data = data or {}
        if val is None:
            val = bool(
                data.get(
                    "enabled", not self.application_settings.llm_enabled
                )
            )
        if bool(data.get("sync_only", False)):
            if bool(self.application_settings.llm_enabled) != bool(val):
                self.update_application_settings(llm_enabled=bool(val))
            return
        self._update_action_button(
            ModelType.LLM,
            None,
            bool(val),
            SignalCode.LLM_LOAD_SIGNAL,
            SignalCode.LLM_UNLOAD_SIGNAL,
            "llm_enabled",
            data,
        )

    def on_toggle_tts(
        self,
        data: Optional[Dict] = None,
        val: Optional[bool] = None,
    ):
        data = data or {}
        if val is None:
            val = bool(
                data.get(
                    "enabled", not self.application_settings.tts_enabled
                )
            )
        self._update_action_button(
            ModelType.TTS,
            getattr(self.ui, "text_to_speech_button", None),
            bool(val),
            SignalCode.TTS_ENABLE_SIGNAL,
            SignalCode.TTS_DISABLE_SIGNAL,
            "tts_enabled",
            data,
        )

    def _update_action_button(
        self,
        model_type,
        element,
        val: bool,
        load_signal: SignalCode,
        unload_signal: SignalCode,
        application_setting: Optional[str] = None,
        data: Optional[Dict] = None,
    ):
        is_loading = self._model_status[model_type] is ModelStatus.LOADING
        if is_loading and not self._allows_loading_toggle(model_type):
            if element is not None:
                self._set_action_checked_state(element, not val)
            return
        if element is not None:
            self._set_action_checked_state(element, val)
        if application_setting:
            settings_data = {}
            settings_data[application_setting] = val
            self.update_application_settings(**settings_data)
        if is_loading:
            return
        if val:
            self.emit_signal(load_signal, data)
        else:
            self.emit_signal(unload_signal, data)

    def save_state(self):
        self.logger.debug("Saving window state")

        self.qsettings.beginGroup("window_settings")
        is_maximized = self.isMaximized()
        is_fullscreen = self.isFullScreen()
        self.logger.debug(
            f"Saving state - maximized: {is_maximized}, fullscreen: {is_fullscreen}"
        )
        self.qsettings.setValue("is_maximized", is_maximized)
        self.qsettings.setValue("is_fullscreen", is_fullscreen)

        # Always save current geometry and position
        width = self.width()
        height = self.height()
        x_pos = self.pos().x()
        y_pos = self.pos().y()
        self.logger.debug(
            f"Saving geometry - width: {width}, height: {height}, x: {x_pos}, y: {y_pos}"
        )
        self.qsettings.setValue("width", width)
        self.qsettings.setValue("height", height)
        self.qsettings.setValue("x_pos", x_pos)
        self.qsettings.setValue("y_pos", y_pos)

        # Save which screen the window is on
        try:
            screen = self.screen()
            if screen:
                screen_name = screen.name()
                self.qsettings.setValue("screen_name", screen_name)
                self.logger.debug(f"Saving screen: {screen_name}")
        except Exception:
            self.logger.exception("Failed to save screen information")

        self.qsettings.setValue(
            "active_main_tab_index",
            0,
        )
        self.qsettings.setValue(
            "active_left_panel_tab_index",
            self.ui.left_panel_tab.currentIndex(),
        )
        self.qsettings.setValue(
            "active_sidebar_tab_index",
            self.ui.sidebar_tab.currentIndex(),
        )
        self.qsettings.endGroup()
        
        # Ensure settings are written to disk before exit
        self.qsettings.sync()
        
        save_splitter_settings(
            self.ui,
            ["main_window_splitter", "center_splitter"],
            "MainWindow",
        )

        # Save canvas offset for all canvas views
        try:
            image_canvas = getattr(self.ui, "image_canvas", None)
            if image_canvas is not None:
                image_canvas.save_canvas_offset()
            brush_canvas = getattr(self.ui, "brush_canvas", None)
            if brush_canvas is not None:
                brush_canvas.save_canvas_offset()
        except Exception:
            self.logger.exception("Failed to save canvas offset")

    def restore_state(self):
        """
        Restore the window based on the previous state using QSettings.
        """
        self.qsettings.beginGroup("window_settings")
        is_maximized = self.qsettings.value("is_maximized", False, type=bool)
        is_fullscreen = self.qsettings.value("is_fullscreen", False, type=bool)
        width_value = self.qsettings.value("width", 1024, type=int)
        height_value = self.qsettings.value("height", 768, type=int)
        x_pos_value = self.qsettings.value("x_pos", 100, type=int)
        y_pos_value = self.qsettings.value("y_pos", 100, type=int)
        width = width_value if isinstance(width_value, int) else 1024
        height = height_value if isinstance(height_value, int) else 768
        x_pos = x_pos_value if isinstance(x_pos_value, int) else 100
        y_pos = y_pos_value if isinstance(y_pos_value, int) else 100
        screen_name = self.qsettings.value("screen_name", None, type=str)
        self.qsettings.endGroup()

        self.logger.debug(
            f"Restoring state - maximized: {is_maximized}, fullscreen: {is_fullscreen}, "
            f"geometry: {width}x{height} at ({x_pos}, {y_pos}), screen: {screen_name}"
        )

        # Try to restore to the same screen
        target_screen = None
        if screen_name:
            try:
                from PySide6.QtGui import QGuiApplication

                for screen in QGuiApplication.screens():
                    if screen.name() == screen_name:
                        target_screen = screen
                        self.logger.debug(
                            f"Found target screen: {screen_name}"
                        )
                        break
                if not target_screen:
                    self.logger.warning(
                        f"Could not find screen: {screen_name}, using primary"
                    )
            except Exception:
                self.logger.exception("Error finding target screen")

        # If we found a target screen, set it BEFORE positioning/showing the window
        if target_screen:
            try:
                self.create()  # Ensure native window is created
                if self.windowHandle():
                    self.windowHandle().setScreen(target_screen)

                    # Calculate position relative to the target screen
                    screen_geometry = target_screen.geometry()
                    if is_maximized or is_fullscreen:
                        # For maximized/fullscreen, move to screen's top-left
                        self.move(screen_geometry.x(), screen_geometry.y())
                    else:
                        # For normal windows, ensure saved position is on the target screen
                        # If saved position is outside target screen, center it
                        if not screen_geometry.contains(x_pos, y_pos):
                            centered_x = (
                                screen_geometry.x()
                                + (screen_geometry.width() - width) // 2
                            )
                            centered_y = (
                                screen_geometry.y()
                                + (screen_geometry.height() - height) // 2
                            )
                            self.move(centered_x, centered_y)
                        else:
                            self.move(x_pos, y_pos)
            except Exception:
                self.logger.exception("Error setting window screen")
        else:
            # No target screen found, use saved position
            self.move(x_pos, y_pos)

        # Set size
        self.resize(width, height)
        self.setMinimumSize(512, 512)

        # Force the screen again right before showing (Qt sometimes resets it)
        if target_screen:
            try:
                if self.windowHandle():
                    self.windowHandle().setScreen(target_screen)
            except Exception:
                self.logger.exception(
                    "Error re-setting window screen before show"
                )

        # Mark that state has been restored BEFORE showing to prevent _initialize_window from overriding
        self._state_restored = True

        # Now apply special states if needed
        if is_maximized:
            self.logger.info("Applying maximized state")
            # Move to screen one more time right before maximizing
            if target_screen:
                screen_geometry = target_screen.geometry()
                self.move(screen_geometry.x(), screen_geometry.y())
            self.showMaximized()
        elif is_fullscreen:
            self.logger.info("Applying fullscreen state")
            if target_screen:
                screen_geometry = target_screen.geometry()
                self.move(screen_geometry.x(), screen_geometry.y())
            self.showFullScreen()
        else:
            self.logger.info("Window restored to normal state")
            self.showNormal()

        # Raise the window to the top of the stack
        self.raise_()

    ##### End window properties #####
    #################################

    ###### Window handlers ######
    def on_toggle_tool_signal(self, data: Dict):
        toggle_tool = getattr(self, "toggle_tool", None)
        if callable(toggle_tool):
            toggle_tool(data["tool"], data["active"])

    def on_retranslate_ui_signal(self):
        self.ui.retranslateUi(self)

    ###### End window handlers ######

    def show_update_message(self):
        if not self.api:
            self.logger.warning(
                "MainWindow: self.api is missing. Cannot display update message."
            )
            return
        self.api.application_status(
            f"New version available: {self.latest_version}"
        )

    def show_update_popup(self):
        self.update_popup = UpdateWindow()

    @staticmethod
    def show_setup_wizard():
        AppInstaller(close_on_cancel=False)

    def _complete_launcher_splash_handoff(self) -> None:
        """Dismiss the launcher splash after the first show event."""
        api = self.refresh_api_reference() or getattr(self, "api", None)
        app = QApplication.instance()
        splash = getattr(api, "splash", None)
        if not api or not splash or not isinstance(app, QApplication):
            return

        from airunner.app_mixins.ui_runtime_mixin import UIRuntimeMixin

        UIRuntimeMixin._dismiss_splash_screen(api, self, app)
        self.raise_()
        self.activateWindow()
        self.logger.debug("Dismissed launcher splash after showEvent")

    def _handoff_launcher_splash(self) -> None:
        """Queue splash dismissal after the first show event returns."""
        if self._launcher_splash_dismissed:
            return
        api = getattr(self, "api", None)
        if not api or not getattr(api, "splash", None):
            return

        self._launcher_splash_dismissed = True
        QTimer.singleShot(0, self._complete_launcher_splash_handoff)
        self.logger.debug("Queued launcher splash dismissal from showEvent")

    def showEvent(self, event):
        """Override to update the tray menu text when window is shown."""
        super().showEvent(event)
        self._handoff_launcher_splash()
        # Make sure we update the menu text whenever the window is shown
        toggle_visibility_action = getattr(
            self,
            "toggle_visibility_action",
            None,
        )
        tray_icon = getattr(self, "tray_icon", None)
        tray_menu = getattr(self, "tray_menu", None)
        if toggle_visibility_action is not None:
            toggle_visibility_action.setText("Hide Window")
            # Update the tray menu so it reflects the current state immediately
            if tray_icon is not None and tray_menu is not None:
                tray_icon.setContextMenu(tray_menu)

        self.logger.debug("showEvent called, initializing window")
        self._initialize_window()
        self._initialize_filter_actions()

        self.initialized = True
        self.logger.debug("Showing window")
        self._set_keyboard_shortcuts()
        self._schedule_main_window_loaded_signal()

        # Show donation dialog after window is fully displayed (only on first show)
        if not hasattr(self, "_donation_dialog_shown"):
            self._donation_dialog_shown = True
            from PySide6.QtCore import QTimer
            # Show privacy consent first, then donation dialog
            QTimer.singleShot(300, self._show_privacy_consent_dialog)
            QTimer.singleShot(500, self._show_donation_dialog)

    def _show_privacy_consent_dialog(self):
        """Show the privacy consent dialog on first launch."""
        from airunner.components.application.gui.dialogs.privacy_consent_dialog import (
            PrivacyConsentDialog,
        )
        PrivacyConsentDialog.show_if_needed(self)

    def _show_donation_dialog(self):
        """Show the donation dialog if appropriate."""
        from airunner.components.application.gui.dialogs.donation_dialog import (
            DonationDialog,
        )
        DonationDialog.show_if_appropriate(self)

    def move_to_second_screen(self):
        screens = QGuiApplication.screens()
        if len(screens) > 1:
            screen = screens[1]
            screen_geometry = screen.availableGeometry()
            self.move(screen_geometry.topLeft())
            self.resize(screen_geometry.size())
            self.setMinimumSize(512, 512)
            max_width = max(screen_geometry.width(), self.minimumWidth())
            max_height = max(screen_geometry.height(), self.minimumHeight())
            self.setMaximumSize(max_width, max_height)

    def on_keyboard_shortcuts_updated(self):
        self._set_keyboard_shortcuts()

    def _set_keyboard_shortcuts(self):
        quit_key = ShortcutKeys.objects.filter_by_first(display_name="Quit")
        if quit_key is not None:
            key_sequence = QKeySequence(quit_key.key | quit_key.modifiers)
            self.ui.actionQuit.setShortcut(key_sequence)
            self.ui.actionQuit.setToolTip(
                f"{quit_key.display_name} ({quit_key.text})"
            )

    def _initialize_filter_actions(self):
        self.ui.menuFilters.clear()
        image_filters = ImageFilter.objects.all()
        try:
            for image_filter in image_filters:
                action = self.ui.menuFilters.addAction(
                    image_filter.display_name
                )
                action.triggered.connect(
                    partial(self.display_filter_window, image_filter)
                )
        except RuntimeError as e:
            if AIRUNNER_ART_ENABLED:
                self.logger.warning(f"Error setting SD status text: {e}")

    @staticmethod
    def display_filter_window(image_filter):
        FilterWindow(image_filter.id)

    def _initialize_window(self):
        # Don't override window geometry if it's already been restored
        if hasattr(self, "_state_restored") and self._state_restored:
            self.logger.debug(
                "Skipping window initialization - state already restored"
            )
            self.setWindowIcon(
                QIcon(
                    os.path.join(
                        self.path_settings.base_path, "images/icon.png"
                    )
                )
            )
            self.set_window_title()
            return

        # self.center()
        screen = QGuiApplication.primaryScreen()  # Use primaryScreen

        if not screen:
            self.logger.warning(
                "Could not get primary screen. Falling back to default size."
            )
            # Fallback to a default size if screen info is unavailable
            default_width, default_height = 1024, 768
            self.resize(default_width, default_height)
            self.setMinimumSize(512, 512)
            # Set maximum size to something reasonable if screen info is missing
            self.setMaximumSize(
                default_width, default_height
            )  # Or a larger sensible max
        else:
            screen_geometry = screen.availableGeometry()
            self.logger.info(
                f"Available screen geometry: "
                f"x={screen_geometry.x()}, y={screen_geometry.y()}, "
                f"width={screen_geometry.width()}, height={screen_geometry.height()}"
            )

            # Set geometry using explicit move and resize
            self.move(screen_geometry.topLeft())
            self.resize(screen_geometry.size())

            self.setMinimumSize(512, 512)
            # Ensure maximum size is at least the minimum size and not smaller than the available geometry
            max_width = max(screen_geometry.width(), self.minimumWidth())
            max_height = max(screen_geometry.height(), self.minimumHeight())
            self.setMaximumSize(max_width, max_height)

        self.setWindowIcon(
            QIcon(
                os.path.join(self.path_settings.base_path, "images/icon.png")
            )
        )
        self.set_window_title()

    def center(self):
        available_geometry = (
            QGuiApplication.primaryScreen().availableGeometry()
        )
        frame_geometry = self.frameGeometry()
        frame_geometry.moveCenter(available_geometry.center())
        self.move(frame_geometry.topLeft())

    def set_window_title(self):
        """
        Overrides base method to set the window title
        :return:
        """
        self.setWindowTitle(self._window_title)

    def handle_unknown(self, message):
        self.logger.error(
            "Unknown message code payload (%s)",
            summarize_mapping_keys(message, label="message"),
        )

    def clear_all_prompts(self):
        self.prompt = ""
        self.negative_prompt = ""
        if not self.api:
            self.logger.warning(
                "MainWindow: self.api is missing. Cannot clear prompts."
            )
            return
        self.api.clear_prompts()

    def new_batch(self, index, image, data):
        new_batch = getattr(self.generator_tab_widget, "new_batch", None)
        if callable(new_batch):
            new_batch(index, image, data)

    def _refresh_model_status_from_daemon(self) -> None:
        """Refresh GUI model status from daemon lifecycle state."""
        if self.api is None or self._daemon_status_refresh_inflight:
            return
        client = getattr(self.api, "daemon_client", None)
        if client is None:
            return
        self._daemon_status_refresh_inflight = True
        threading.Thread(
            target=self._fetch_daemon_runtime_status,
            args=(client,),
            daemon=True,
        ).start()

    def _fetch_daemon_runtime_status(self, client) -> None:
        """Fetch one daemon runtime snapshot without blocking the UI."""
        status = None
        try:
            status = client.daemon_runtime_status(
                auto_start=False,
                timeout_seconds=self._daemon_status_request_timeout_seconds,
            )
        except RuntimeError:
            pass
        self.daemon_runtime_status_ready.emit(status)

    def _on_daemon_runtime_status_ready(self, status: object) -> None:
        """Apply one daemon runtime snapshot on the GUI thread."""
        self._daemon_status_refresh_inflight = False
        if not isinstance(status, dict):
            return
        runtime_statuses = self._runtime_statuses_from_daemon_status(status)
        if runtime_statuses:
            runtime_statuses[ModelType.LLM] = self._effective_llm_status(
                runtime_statuses.get(ModelType.LLM, ModelStatus.UNLOADED)
            )
            for model_type in (
                ModelType.LLM,
                ModelType.TTS,
                ModelType.STT,
                ModelType.SD,
            ):
                self._sync_model_status_value(
                    model_type,
                    runtime_statuses.get(model_type, ModelStatus.UNLOADED),
                )
        else:
            loaded_models = self._loaded_model_names_from_runtime_status(status)
            llm_status = self._effective_llm_status(
                ModelStatus.LOADED
                if "LLM" in loaded_models
                else ModelStatus.UNLOADED
            )
            self._sync_model_status_value(ModelType.LLM, llm_status)
            self._sync_model_status(ModelType.TTS, "TTS", loaded_models)
            self._sync_model_status(ModelType.STT, "STT", loaded_models)
            self._sync_model_status(ModelType.SD, "SD", loaded_models)
        MainWindow._sync_model_resource_manager_from_daemon(self, status)
        loaded_models = self._loaded_model_names_from_runtime_status(status)
        self._reconcile_optional_runtime_preferences(loaded_models)

    def _sync_model_resource_manager_from_daemon(self, status: dict) -> None:
        """Mirror daemon runtime state into the shared resource manager."""
        runtimes = status.get("runtimes")
        if not isinstance(runtimes, list):
            return

        manager = ModelResourceManager()
        for runtime in runtimes:
            model_type = MainWindow._resource_model_type_from_runtime(runtime)
            if model_type is None:
                continue
            model_status = MainWindow._model_status_from_runtime_summary(
                runtime
            )
            model_id = MainWindow._resource_model_id_from_runtime(
                runtime,
                manager,
                model_type,
            )
            MainWindow._apply_runtime_resource_state(
                manager,
                model_type,
                model_id,
                model_status,
            )

    @staticmethod
    def _resource_model_type_from_runtime(runtime: dict) -> Optional[str]:
        """Return the resource-manager type for one daemon runtime."""
        runtime_name = str(runtime.get("runtime", "")).strip().lower()
        return {
            "art": "text_to_image",
            "llm": "llm",
            "stt": "stt",
            "tts": "tts",
        }.get(runtime_name)

    @staticmethod
    def _active_resource_model_ids(
        manager: ModelResourceManager,
        model_type: str,
    ) -> list[str]:
        """Return active model IDs tracked for one resource-manager type."""
        return [
            model.model_id
            for model in manager.get_active_models()
            if getattr(model, "model_type", "") == model_type
        ]

    @staticmethod
    def _resource_model_id_from_runtime(
        runtime: dict,
        manager: ModelResourceManager,
        model_type: str,
    ) -> Optional[str]:
        """Resolve one daemon runtime summary to a stable model ID."""
        metadata = runtime.get("metadata") or {}
        for key in ("model_path", "model_id", "model_version", "model_type"):
            value = str(metadata.get(key, "")).strip()
            if value:
                return value

        active_ids = MainWindow._active_resource_model_ids(manager, model_type)
        if active_ids:
            return active_ids[0]

        runtime_name = str(runtime.get("runtime", "")).strip().lower()
        if runtime_name in {"llm", "stt", "tts"}:
            return runtime_name.upper()
        return None

    @staticmethod
    def _resource_model_type_from_status_signal(
        model_type: ModelType,
    ) -> Optional[str]:
        """Return the resource-manager type for one direct status signal."""
        return {
            ModelType.LLM: "llm",
            ModelType.TTS: "tts",
            ModelType.STT: "stt",
            ModelType.SAFETY_CHECKER: "safety_checker",
        }.get(model_type)

    def _configured_resource_model_id(self, model_type: ModelType) -> str:
        """Return the configured model identifier for one runtime."""
        if model_type is ModelType.LLM:
            settings = getattr(self, "llm_generator_settings", None)
            for key in ("model_path", "model_id", "model_version"):
                value = str(getattr(settings, key, "") or "").strip()
                if value:
                    return value
            return "LLM"
        if model_type is ModelType.TTS:
            return MainWindow._configured_tts_resource_model_id(self)
        if model_type is ModelType.STT:
            return MainWindow._configured_stt_resource_model_id(self)
        if model_type is ModelType.SAFETY_CHECKER:
            return "Safety Checker"
        return ""

    def _configured_tts_resource_model_id(self) -> str:
        """Return the label used for one TTS runtime row."""
        voice_settings = getattr(self, "chatbot_voice_settings", None)
        model_type = str(getattr(voice_settings, "model_type", "") or "")
        if model_type.strip():
            return model_type.strip()

        settings = getattr(self, "path_settings", None)
        value = str(getattr(settings, "tts_model_path", "") or "")
        return value.strip() or "TTS"

    def _configured_stt_resource_model_id(self) -> str:
        """Return the label used for one STT runtime row."""
        from airunner.settings import AIRUNNER_DEFAULT_STT_HF_PATH

        settings = getattr(self, "path_settings", None)
        base_path = str(getattr(settings, "stt_model_path", "") or "")
        if base_path.strip():
            return os.path.join(
                base_path.strip(),
                AIRUNNER_DEFAULT_STT_HF_PATH,
            )
        return AIRUNNER_DEFAULT_STT_HF_PATH

    def _resource_model_id_from_status_signal(
        self,
        data: dict,
        manager: ModelResourceManager,
        model_type: ModelType,
        resource_model_type: str,
        status: ModelStatus,
    ) -> Optional[str]:
        """Resolve one stable model ID from a direct status signal."""
        for key in ("model_path", "path", "model_id"):
            value = str(data.get(key, "") or "").strip()
            if value:
                return value
        active_ids = MainWindow._active_resource_model_ids(
            manager,
            resource_model_type,
        )
        if status in (ModelStatus.UNLOADED, ModelStatus.FAILED) and active_ids:
            return active_ids[0]
        configured = MainWindow._configured_resource_model_id(
            self,
            model_type,
        )
        if configured:
            return configured
        if active_ids:
            return active_ids[0]
        return None

    def _sync_model_resource_manager_from_status_signal(
        self,
        data: dict,
        model_type: ModelType,
        status: ModelStatus,
    ) -> None:
        """Mirror a direct status signal into the shared resource widget."""
        resource_model_type = MainWindow._resource_model_type_from_status_signal(
            model_type
        )
        if resource_model_type is None:
            return
        manager = ModelResourceManager()
        model_id = MainWindow._resource_model_id_from_status_signal(
            self,
            data,
            manager,
            model_type,
            resource_model_type,
            status,
        )
        current_state = None
        if model_id is not None:
            current_state = manager.get_model_state(model_id)
        if status is ModelStatus.READY:
            status = ModelStatus.LOADED
        if (
            status is ModelStatus.LOADING
            and current_state in (ModelState.LOADED, ModelState.BUSY)
        ):
            return
        MainWindow._apply_runtime_resource_state(
            manager,
            resource_model_type,
            model_id,
            status,
        )

    @staticmethod
    def _apply_runtime_resource_state(
        manager: ModelResourceManager,
        model_type: str,
        model_id: Optional[str],
        model_status: ModelStatus,
    ) -> None:
        """Apply one daemon runtime summary to the shared resource state."""
        active_ids = MainWindow._active_resource_model_ids(manager, model_type)
        if model_status not in (ModelStatus.LOADING, ModelStatus.LOADED):
            for active_id in active_ids:
                manager.cleanup_model(active_id, model_type)
            return

        if not model_id:
            return

        for active_id in active_ids:
            if active_id != model_id:
                manager.cleanup_model(active_id, model_type)

        if model_status is ModelStatus.LOADING:
            manager.set_model_state(
                model_id,
                ModelState.LOADING,
                model_type,
            )
            return

        manager.model_loaded(model_id, model_type)

    def _effective_llm_status(
        self,
        daemon_status: ModelStatus,
    ) -> ModelStatus:
        """Prefer live local worker state over non-ready daemon summaries."""
        if daemon_status in (ModelStatus.LOADED, ModelStatus.LOADING):
            return daemon_status
        worker_manager = getattr(self, "worker_manager", None)
        worker = getattr(worker_manager, "_llm_generate_worker", None)
        if worker is None:
            return daemon_status
        status_getter = getattr(worker, "current_model_status", None)
        if not callable(status_getter):
            return daemon_status
        local_status = status_getter()
        if local_status in (
            ModelStatus.LOADED,
            ModelStatus.LOADING,
            ModelStatus.FAILED,
        ):
            return local_status
        if daemon_status == ModelStatus.FAILED:
            return ModelStatus.UNLOADED
        return daemon_status

    def _normalize_direct_llm_status(
        self,
        status: ModelStatus,
    ) -> ModelStatus:
        """Ignore stale failed events while a local load is still healthy."""
        if status is not ModelStatus.FAILED:
            return status
        worker_manager = getattr(self, "worker_manager", None)
        worker = getattr(worker_manager, "_llm_generate_worker", None)
        if worker is None:
            return status
        status_getter = getattr(worker, "current_model_status", None)
        if not callable(status_getter):
            return status
        local_status = status_getter()
        if local_status in (ModelStatus.LOADING, ModelStatus.LOADED):
            return local_status
        if local_status in (None, ModelStatus.UNLOADED) and (
            self._model_status.get(ModelType.LLM)
            in (ModelStatus.LOADING, ModelStatus.LOADED)
        ):
            return self._model_status[ModelType.LLM]
        return status

    @staticmethod
    def _model_status_from_runtime_summary(summary: dict) -> ModelStatus:
        """Translate one daemon runtime summary into GUI model status."""
        runtime_status = str(summary.get("status", "")).strip().lower()
        if runtime_status == "starting":
            return ModelStatus.LOADING
        if runtime_status == "failed":
            return ModelStatus.FAILED
        if runtime_status == "ready":
            return ModelStatus.LOADED
        if bool(summary.get("loaded")):
            return ModelStatus.LOADED
        return ModelStatus.UNLOADED

    @staticmethod
    def _runtime_statuses_from_daemon_status(
        status: dict,
    ) -> dict[ModelType, ModelStatus]:
        """Return GUI model statuses derived from daemon runtime summaries."""
        runtime_map = {
            "llm": ModelType.LLM,
            "tts": ModelType.TTS,
            "stt": ModelType.STT,
            "art": ModelType.SD,
        }
        runtimes = status.get("runtimes")
        if not isinstance(runtimes, list):
            return {}
        statuses: dict[ModelType, ModelStatus] = {}
        for runtime in runtimes:
            model_type = runtime_map.get(str(runtime.get("runtime", "")).lower())
            if model_type is None:
                continue
            statuses[model_type] = MainWindow._model_status_from_runtime_summary(
                runtime
            )
        return statuses

    @staticmethod
    def _optional_runtime_preference_specs():
        """Return daemon-backed runtime preference sync definitions."""
        return (
            (
                ModelType.TTS,
                "TTS",
                "tts_enabled",
                SignalCode.TTS_ENABLE_SIGNAL,
                SignalCode.TTS_DISABLE_SIGNAL,
            ),
            (
                ModelType.STT,
                "STT",
                "stt_enabled",
                SignalCode.STT_LOAD_SIGNAL,
                SignalCode.STT_UNLOAD_SIGNAL,
            ),
        )

    def _reconcile_optional_runtime_preferences(
        self,
        loaded_models: set[str],
    ) -> None:
        """Align daemon-backed TTS/STT state with persisted preferences."""
        now = time.monotonic()
        for spec in self._optional_runtime_preference_specs():
            MainWindow._reconcile_optional_runtime_preference(
                self,
                spec,
                loaded_models,
                now,
            )

    def _reconcile_optional_runtime_preference(
        self,
        spec,
        loaded_models: set[str],
        now: float,
    ) -> None:
        """Emit one load or unload signal when a preference is out of sync."""
        model_type, loaded_name, setting_name, load_signal, unload_signal = spec
        desired_enabled = bool(
            getattr(self.application_settings, setting_name, False)
        )
        is_loaded = loaded_name in loaded_models
        if desired_enabled == is_loaded:
            self._runtime_preference_retry_after.pop(model_type, None)
            return
        if (
            desired_enabled
            and self._model_status[model_type] is ModelStatus.LOADING
        ):
            return
        if now < self._runtime_preference_retry_after.get(model_type, 0.0):
            return
        self._runtime_preference_retry_after[model_type] = (
            now + self._runtime_preference_retry_seconds
        )
        signal = load_signal if desired_enabled else unload_signal
        self.emit_signal(signal, {"source": "runtime_preference_sync"})

    @staticmethod
    def _loaded_model_names_from_runtime_status(status: dict) -> set[str]:
        """Return loaded model names using runtime summaries when present."""
        runtimes = status.get("runtimes")
        if isinstance(runtimes, list):
            loaded_models = set()
            for runtime in runtimes:
                if not runtime.get("loaded"):
                    continue
                runtime_name = str(runtime.get("runtime", "")).upper()
                if runtime_name == "ART":
                    runtime_name = "SD"
                loaded_models.add(runtime_name)
            return loaded_models
        lifecycle = status.get("lifecycle") or {}
        return set(lifecycle.get("loaded_models") or [])

    def _sync_model_status(
        self,
        model_type: ModelType,
        loaded_name: str,
        loaded_models: set[str],
    ) -> None:
        """Emit one model-status update when daemon truth changed."""
        status = ModelStatus.LOADED
        if loaded_name not in loaded_models:
            status = ModelStatus.UNLOADED
        self._sync_model_status_value(model_type, status)

    def _sync_model_status_value(
        self,
        model_type: ModelType,
        status: ModelStatus,
    ) -> None:
        """Emit one model-status update when the status changed."""
        if self._model_status[model_type] is status:
            return
        self.emit_signal(
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
            {"model": model_type, "status": status},
        )

    def on_model_status_changed_signal(self, data):
        if not isinstance(data, dict):
            return
        model = data.get("model")
        status = data.get("status")
        if model is None or status is None:
            return
        if model is ModelType.LLM:
            status = self._normalize_direct_llm_status(status)
        MainWindow._sync_model_resource_manager_from_status_signal(
            self,
            data,
            model,
            status,
        )
        if self._model_status.get(model) is status:
            return
        self._model_status[model] = status
        if model is ModelType.SD:
            if status is ModelStatus.LOADED:
                self.update_application_settings(sd_enabled=True)
            elif status is ModelStatus.UNLOADED:
                self.update_application_settings(sd_enabled=False)
        elif model is ModelType.LLM:
            if status is ModelStatus.LOADED:
                self.update_application_settings(llm_enabled=True)
            elif status is ModelStatus.FAILED:
                self.logger.warning("LLM failed to load")
            elif status is ModelStatus.UNLOADED:
                self.update_application_settings(llm_enabled=False)
        elif model is ModelType.TTS:
            button = getattr(self.ui, "text_to_speech_button", None)
            if button is not None:
                button.setDisabled(False)
        elif model is ModelType.STT:
            button = getattr(self.ui, "speech_to_text_button", None)
            if button is not None:
                button.setDisabled(False)
        QApplication.processEvents()

    def _generate_drawingpad_mask(self):
        width = self.application_settings.working_width
        height = self.application_settings.working_height
        img = Image.new("RGB", (width, height), (0, 0, 0))
        base64_image = convert_image_to_binary(img)

        self.update_drawing_pad_settings(mask=base64_image)

    def display_missing_models_error(self, data):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle(data.get("title", "Error: Missing models"))
        msg_box.setText(data.get("message", "Something went wrong"))
        msg_box.exec()

    def on_status_error_signal(self, data):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle(data.get("title", "Error"))
        msg_box.setText(data.get("message", "Something went wrong"))
        msg_box.exec()

    def hide_center_tab_header(self):
        """Hide the right-sidebar tab bar so it behaves like VS Code."""
        tab_widget = getattr(self.ui, "sidebar_tab", None)
        if tab_widget is not None:
            tab_bar = tab_widget.tabBar()
            tab_bar.hide()
