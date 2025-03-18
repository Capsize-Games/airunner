import os
import re
import sys
import urllib
import webbrowser
from functools import partial
from typing import Dict

import requests
from PIL import Image
from PySide6 import QtGui
from PySide6.QtCore import (
    Slot,
    Signal,
    QProcess
)
from PySide6.QtGui import QGuiApplication, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QMessageBox,
    QCheckBox, QInputDialog
)
from bs4 import BeautifulSoup

from airunner.handlers.llm.agent.actions.bash_execute import bash_execute
from airunner.handlers.llm.agent.actions.show_path import show_path
from airunner.data.models import ShortcutKeys, ImageFilter, DrawingPadSettings
from airunner.app_installer import AppInstaller
from airunner.settings import (
    STATUS_ERROR_COLOR,
    STATUS_NORMAL_COLOR_LIGHT,
    STATUS_NORMAL_COLOR_DARK,
    NSFW_CONTENT_DETECTED_MESSAGE,
)
from airunner.enums import (
    SignalCode,
    CanvasToolName,
    GeneratorSection,
    LLMActionType, 
    ModelType, 
    ModelStatus
)
from airunner.mediator_mixin import MediatorMixin
from airunner.settings import (
    BASE_PATH,
    BUG_REPORT_LINK,
    VULNERABILITY_REPORT_LINK
)
from airunner.styles_mixin import StylesMixin
from airunner.utils.image.convert_image_to_binary import convert_image_to_binary
from airunner.utils.create_worker import create_worker
from airunner.workers.audio_capture_worker import AudioCaptureWorker
from airunner.workers.audio_processor_worker import AudioProcessorWorker
from airunner.workers.llm_generate_worker import LLMGenerateWorker
from airunner.workers.mask_generator_worker import MaskGeneratorWorker
from airunner.workers.sd_worker import SDWorker
from airunner.workers.tts_generator_worker import TTSGeneratorWorker
from airunner.workers.tts_vocalizer_worker import TTSVocalizerWorker

from airunner.utils.get_version import get_version
from airunner.widgets.stats.stats_widget import StatsWidget
from airunner.widgets.status.status_widget import StatusWidget
from airunner.windows.about.about import AboutWindow
from airunner.windows.filter_window import FilterWindow
from airunner.windows.main.ai_model_mixin import AIModelMixin
from airunner.windows.main.pipeline_mixin import PipelineMixin
from airunner.windows.main.settings_mixin import SettingsMixin
from airunner.windows.main.templates.main_window_ui import Ui_MainWindow
from airunner.windows.prompt_browser.prompt_browser import PromptBrowser
from airunner.windows.settings.airunner_settings import SettingsWindow
from airunner.windows.update.update_window import UpdateWindow
from airunner.handlers.llm.llm_request import LLMRequest
from airunner.data.models import SplitterSetting, Tab
from airunner.plugin_loader import PluginLoader


class MainWindow(
    QMainWindow,
    MediatorMixin,
    SettingsMixin,
    StylesMixin,
    PipelineMixin,
    AIModelMixin
):
    show_grid_toggled = Signal(bool)
    cell_size_changed_signal = Signal(int)
    line_width_changed_signal = Signal(int)
    line_color_changed_signal = Signal(str)
    canvas_color_changed_signal = Signal(str)
    snap_to_grid_changed_signal = Signal(bool)
    image_generated = Signal(bool)
    generator_tab_changed_signal = Signal()
    load_image = Signal(str)
    load_image_object = Signal(object)
    loaded = Signal()
    window_opened = Signal()
    ui_class_ = Ui_MainWindow
    _window_title = f"AI Runner"
    icons = [
        ("pencil-icon", "actionToggle_Brush"),
        ("eraser-icon", "actionToggle_Eraser"),
        ("frame-grid-icon", "actionToggle_Grid"),
        ("circle-center-icon", "actionRecenter"),
        ("setting-line-icon", "actionSettings"),
        ("object-selected-icon", "actionToggle_Active_Grid_Area"),
        ("select-svgrepo-com", "actionToggle_Selection"),
        ("layer-icon", "actionMask_toggle"),
    ]

    def __init__(
        self,
        *args,
        **kwargs
    ):
        self.ui = self.ui_class_()
        self.quitting = False
        self.update_popup = None
        self._document_path = None
        self.prompt = None
        self.negative_prompt = None
        self.image_path = None
        self.token_signal = Signal(str)
        self.api = None
        self.input_event_manager = None
        self.tqdm_callback_triggered = False
        self.action = GeneratorSection.TXT2IMG.value
        self.progress_bar_started = False
        self.window = None
        self.canvas = None
        self.models = None
        self.client = None
        self._version = None
        self._latest_version = None
        self.status_error_color = STATUS_ERROR_COLOR
        self.status_normal_color_light = STATUS_NORMAL_COLOR_LIGHT
        self.status_normal_color_dark = STATUS_NORMAL_COLOR_DARK
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
        self._model_status = {model_type: ModelStatus.UNLOADED for model_type in ModelType}
        MediatorMixin.__init__(self)
        
        self.logger.debug("Starting AI Runnner")
        super().__init__(*args, **kwargs)
        
        # Add plugins directory to Python path
        plugins_path = os.path.join(self.path_settings.base_path, "plugins")
        if plugins_path not in sys.path:
            sys.path.append(plugins_path)

        self._updating_settings = True
        PipelineMixin.__init__(self)
        AIModelMixin.__init__(self)
        self._updating_settings = False
        self._worker_manager = None
        self.register_signals()
        self.initialize_ui()
        self._initialize_workers()

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
    def action_toggle_brush(self, active: bool):
        self.toggle_tool(CanvasToolName.BRUSH, active)

    @Slot(bool)
    def action_toggle_eraser(self, active: bool):
        self.toggle_tool(CanvasToolName.ERASER, active)

    @Slot(bool)
    def action_toggle_select(self, active: bool):
        self.toggle_tool(CanvasToolName.SELECTION, active)

    @Slot(bool)
    def action_toggle_active_grid_area(self, active: bool):
        self.toggle_tool(CanvasToolName.ACTIVE_GRID_AREA, active)

    @Slot(bool)
    def action_toggle_nsfw_filter_triggered(self, val: bool):
        if val is False:
            self.show_nsfw_warning_popup()
        else:
            self.update_application_settings("nsfw_filter", val)
            self.toggle_nsfw_filter()
            self.emit_signal(SignalCode.SAFETY_CHECKER_LOAD_SIGNAL)

    @Slot()
    def action_center_clicked(self):
        print("center clicked")

    @Slot()
    def action_reset_settings(self):
        reply = QMessageBox.question(
            self,
            'Reset Settings',
            'Are you sure you want to reset all settings to their default values?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.reset_settings()
            self.restart()

    @Slot()
    def import_controlnet_image(self):
        pass

    @Slot()
    def export_controlnet_image(self):
        pass

    @Slot()
    def import_drawingpad_image(self):
        pass

    @Slot()
    def export_drawingpad_image(self):
        pass

    @Slot()
    def action_export_image_triggered(self):
        self.emit_signal(SignalCode.CANVAS_EXPORT_IMAGE_SIGNAL)

    @Slot()
    def action_import_image_triggered(self):
        self.emit_signal(SignalCode.CANVAS_IMPORT_IMAGE_SIGNAL)

    @Slot()
    def action_new_document_triggered(self):
        self.emit_signal(SignalCode.CANVAS_CLEAR)

    @Slot()
    def action_undo_triggered(self):
        self.emit_signal(SignalCode.UNDO_SIGNAL)

    @Slot()
    def action_redo_triggered(self):
        self.emit_signal(SignalCode.REDO_SIGNAL)

    @Slot()
    def action_paste_image_triggered(self):
        self.emit_signal(SignalCode.CANVAS_PASTE_IMAGE_SIGNAL)

    @Slot()
    def action_copy_image_triggered(self):
        self.emit_signal(SignalCode.CANVAS_COPY_IMAGE_SIGNAL)

    @Slot()
    def action_cut_image_triggered(self):
        self.emit_signal(SignalCode.CANVAS_CUT_IMAGE_SIGNAL)

    @Slot()
    def action_rotate_90_clockwise_triggered(self):
        self.emit_signal(SignalCode.CANVAS_ROTATE_90_CLOCKWISE_SIGNAL)

    @Slot()
    def action_rotate_90_counterclockwise_triggered(self):
        self.emit_signal(SignalCode.CANVAS_ROTATE_90_COUNTER_CLOCKWISE_SIGNAL)

    @Slot()
    def action_show_prompt_browser_triggered(self):
        PromptBrowser()

    @Slot()
    def action_clear_all_prompts_triggered(self):
        self.clear_all_prompts()

    @Slot()
    def action_triggered_browse_ai_runner_path(self):
        path = self.path_settings.base_path
        if path == "":
            path = BASE_PATH
        show_path(path)

    @Slot()
    def action_show_images_path(self):
        self.show_settings_path("image_path")

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
    def action_show_about_window(self):
        AboutWindow()

    @Slot()
    def action_show_settings(self):
        SettingsWindow()

    @Slot()
    def action_open_vulnerability_report(self):
        webbrowser.open(VULNERABILITY_REPORT_LINK)

    @Slot()
    def action_open_bug_report(self):
        webbrowser.open(BUG_REPORT_LINK)

    @Slot()
    def action_open_discord(self):
        pass

    @Slot(bool)
    def action_toggle_mask_layer(self, val: bool):
        if val is True and self.drawing_pad_mask is None:
            self._generate_drawingpad_mask()

        self.update_drawing_pad_settings("mask_layer_enabled", val)
        self.emit_signal(SignalCode.MASK_LAYER_TOGGLED)

    @Slot(bool)
    def action_outpaint_toggled(self, val: bool):
        self.update_outpaint_settings("enabled", val)

    @Slot()
    def action_outpaint_export(self):
        pass

    @Slot()
    def action_outpaint_import(self):
        pass

    @Slot()
    def action_run_setup_wizard_clicked(self):
        self.show_setup_wizard()

    @Slot(bool)
    def action_toggle_llm(self, val: bool):
        self.on_toggle_llm(val=val)

    @Slot(bool)
    def action_image_generator_toggled(self, val: bool):
        self.on_toggle_sd(val=val)

    @Slot(bool)
    def tts_button_toggled(self, val: bool):
        self.on_toggle_tts(val=val)

    @Slot(bool)
    def action_controlnet_toggled(self, val: bool):
        self._update_action_button(
            ModelType.CONTROLNET,
            self.ui.actionToggle_Controlnet,
            val,
            SignalCode.CONTROLNET_LOAD_SIGNAL,
            SignalCode.CONTROLNET_UNLOAD_SIGNAL,
            "controlnet_enabled"
        )

    @Slot(bool)
    def v2t_button_toggled(self, val):
        if self._model_status[ModelType.STT] is ModelStatus.LOADING:
            val = not val
        self._update_action_button(
            ModelType.STT,
            self.ui.actionToggle_Speech_to_Text,
            val,
            SignalCode.STT_LOAD_SIGNAL,
            SignalCode.STT_UNLOAD_SIGNAL,
            "stt_enabled"
        )
        QApplication.processEvents()
        self.update_application_settings("stt_enabled", val)
        if not val:
            self.emit_signal(SignalCode.STT_UNLOAD_SIGNAL)
        else:
            self.emit_signal(SignalCode.STT_LOAD_SIGNAL)

    @Slot()
    def action_stats_triggered(self):
        widget = StatsWidget()
        # display in a window
        widget.show()

    """
    End slot functions
    """
    @staticmethod
    def download_url(url, save_path):
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        title = soup.title.string if soup.title else url
        # Truncate title to 10 words
        title_words = title.split()[:10]
        filename = "_".join(title_words) + '.html'
        # Replace any characters in filename that are not alphanumerics, underscores, or hyphens
        filename = re.sub(r'[^\w\-_]', '_', filename)
        save_path = os.path.join(save_path, filename)
        with open(save_path, 'wb') as file:
            file.write(response.content)
        return filename

    @staticmethod
    def download_pdf(url, save_path):
        response = requests.get(url)
        filename = url.split('/')[-1]  # Get the filename from the URL
        save_path = os.path.join(save_path, filename)
        with open(save_path, 'wb') as file:
            file.write(response.content)
        return filename

    def on_navigate_to_url(self, _data: Dict = None):
        url, ok = QInputDialog.getText(self, 'Browse Web', 'Enter your URL:')
        if ok:
            try:
                result = urllib.parse.urlparse(url)
                is_url = all([result.scheme, result.netloc])
            except ValueError:
                is_url = False

            # If the input is a URL, download it
            if is_url:
                if url.lower().endswith('.pdf'):
                    # Handle PDF file
                    filepath = os.path.expanduser(self.path_settings.pdf_path)
                    filename = self.download_pdf(url, filepath)
                else:
                    # Handle URL
                    filepath = os.path.expanduser(self.path_settings.webpages_path)
                    filename = self.download_url(url, filepath)
            elif os.path.isfile(url):
                filepath = os.path.dirname(url)
                filename = os.path.basename(url)
            else:
                self.logger.error(f"Invalid URL or file path")
                return

            # Update target files to use only the file that was downloaded or navigated to
            # and update the index.
            self.update_chatbot("target_files", [os.path.join(filepath, filename)])
            self.emit_signal(SignalCode.RAG_RELOAD_INDEX_SIGNAL, {
                "target_files": self.chatbot.target_files
            })
            self.emit_signal(
                SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL,
                {
                    "llm_request": True,
                    "request_data": {
                        "action": LLMActionType.RAG,
                        "prompt": "Summarize the text and provide a synopsis of the content. "
                                  "Be concise and informative.",
                        "llm_request": LLMRequest.from_default()
                    }
                }
            )

    def show_layers(self):
        self.emit_signal(SignalCode.LAYERS_SHOW_SIGNAL)

    def register_signals(self):
        self.logger.debug("Connecting signals")
        for item in (
            (SignalCode.SD_SAVE_PROMPT_SIGNAL, self.on_save_stablediffusion_prompt_signal),
            (SignalCode.QUIT_APPLICATION, self.action_quit_triggered),
            (SignalCode.SD_NSFW_CONTENT_DETECTED_SIGNAL, self.on_nsfw_content_detected_signal),
            (SignalCode.BASH_EXECUTE_SIGNAL, self.on_bash_execute_signal),
            (SignalCode.WRITE_FILE, self.on_write_file_signal),
            (SignalCode.TOGGLE_FULLSCREEN_SIGNAL, self.on_toggle_fullscreen_signal),
            (SignalCode.TOGGLE_TTS_SIGNAL, self.on_toggle_tts),
            (SignalCode.TOGGLE_SD_SIGNAL, self.on_toggle_sd),
            (SignalCode.TOGGLE_LLM_SIGNAL, self.on_toggle_llm),
            (SignalCode.UNLOAD_NON_SD_MODELS, self.on_unload_non_sd_models),
            (SignalCode.LOAD_NON_SD_MODELS, self.on_load_non_sd_models),
            (SignalCode.APPLICATION_RESET_SETTINGS_SIGNAL, self.action_reset_settings),
            (SignalCode.APPLICATION_RESET_PATHS_SIGNAL, self.on_reset_paths_signal),
            (SignalCode.MODEL_STATUS_CHANGED_SIGNAL, self.on_model_status_changed_signal),
            (SignalCode.KEYBOARD_SHORTCUTS_UPDATED, self.on_keyboard_shortcuts_updated),
            (SignalCode.HISTORY_UPDATED, self.on_history_updated),
            (SignalCode.REFRESH_STYLESHEET_SIGNAL, self.on_theme_changed_signal),
            (SignalCode.AI_MODELS_SAVE_OR_UPDATE_SIGNAL, self.on_ai_models_save_or_update_signal),
            (SignalCode.NAVIGATE_TO_URL, self.on_navigate_to_url),
            (SignalCode.MISSING_REQUIRED_MODELS, self.display_missing_models_error),
            (SignalCode.TOGGLE_TOOL, self.on_toggle_tool_signal)
        ):
            self.register(item[0], item[1])

    def on_reset_paths_signal(self):
        self.reset_path_settings()

    def restart(self):
        # Save the current state
        self.save_state()

        # Close the main window
        self.close()

        # Start a new instance of the application
        QProcess.startDetached(sys.executable, sys.argv)

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

    @staticmethod
    def on_bash_execute_signal(data: Dict) -> str:
        """
        Takes a message from the LLM and strips bash commands from it.
        Passes bash command to the bash_execute function.
        :param data: Dict
        :return:
        """
        args = data["args"]
        return bash_execute(args[0])

    def on_theme_changed_signal(self):
        self.set_stylesheet()

    def initialize_ui(self):
        self.logger.debug("Loading UI")
        self.ui.setupUi(self)
        active_index = 0
        tabs = Tab.objects.filter_by(section="center")
        for tab in tabs:
            if (tab.active):
                active_index = tab.index
                break
        self.ui.center_tab_container.setCurrentIndex(active_index)

        self.set_stylesheet()
        self.restore_state()
        
        settings = SplitterSetting.objects.filter_by_first(name="main_window_splitter")
        if settings:
            self.ui.main_window_splitter.restoreState(settings.splitter_settings)
        self.ui.center_tab_container.currentChanged.connect(self.on_tab_section_changed)

        self.status_widget = StatusWidget()
        self.statusBar().addPermanentWidget(self.status_widget)
        self.emit_signal(SignalCode.APPLICATION_CLEAR_STATUS_MESSAGE_SIGNAL)
        self.initialize_widget_elements()

        self.ui.actionUndo.setEnabled(False)
        self.ui.actionRedo.setEnabled(False)
        self._load_plugins()
        self.emit_signal(
            SignalCode.APPLICATION_MAIN_WINDOW_LOADED_SIGNAL, 
            {"main_window": self}
        )

    def _load_plugins(self):
        base_path = self.path_settings.base_path
        path = os.path.join(base_path, "plugins")
        plugin_loader = PluginLoader(plugin_dir=path)
        plugins = plugin_loader.load_plugins()

        if len(plugins) == 0:
            self.logger.info("No plugins found at " + path)
        else:
            self.logger.info("Loading plugins from " + path)
            for plugin in plugins:
                if hasattr(plugin, "get_widget"):
                    widget = plugin.get_widget()
                    self.ui.center_tab_container.addTab(widget, plugin.name)

    @Slot(int)
    def on_tab_section_changed(self, index: int):
        Tab.update_tabs("center", self.ui.center_tab_container, index)
        self.emit_signal(SignalCode.SECTION_CHANGED)

    def initialize_widget_elements(self):
        for item in (
            (self.ui.actionToggle_LLM, self.application_settings.llm_enabled),
            (self.ui.actionToggle_Text_to_Speech, self.application_settings.tts_enabled),
            (self.ui.actionToggle_Speech_to_Text, self.application_settings.stt_enabled),
            (self.ui.actionToggle_Stable_Diffusion, self.application_settings.sd_enabled),
            (self.ui.actionToggle_Controlnet, self.application_settings.controlnet_enabled),
        ):
            item[0].blockSignals(True)
            item[0].setChecked(item[1] or False)
            item[0].blockSignals(False)
        self.initialized = True

    def layer_opacity_changed(self, _attr_name, value=None, _widget=None):
        self.emit_signal(SignalCode.LAYER_OPACITY_CHANGED_SIGNAL, value)

    def keyPressEvent(self, event):
        super().keyPressEvent(event)
        for v in self.shortcut_keys:
            if v.key == event.key():
                for signal in SignalCode:
                    if signal.value == v.signal:
                        self.emit_signal(signal)
                        break

    def key_text(self, key_name):
        for shortcutkey in self.shortcut_keys:
            if shortcutkey.name == key_name:
                return shortcutkey.text
        return ""

    def on_save_stablediffusion_prompt_signal(self, data: Dict):
        self.create_saved_prompt({
            'prompt': data["prompt"],
            'negative_prompt': data["negative_prompt"],
            'secondary_prompt': data["secondary_prompt"],
            'secondary_negative_prompt': data["secondary_negative_prompt"],
        })

    def set_path_settings(self, key, val):
        self.update_path_settings(key, val)

    def action_quit_triggered(self):
        QApplication.quit()
        self.close()

    def on_nsfw_content_detected_signal(self):
        # display message in status
        self.emit_signal(
            SignalCode.APPLICATION_STATUS_ERROR_SIGNAL,
            NSFW_CONTENT_DETECTED_MESSAGE
        )

    def closeEvent(self, event) -> None:
        self.logger.debug("Quitting")
        self.save_state()
        self.emit_signal(SignalCode.QUIT_APPLICATION)

    def show_settings_path(self, name, default_path=None):
        path = getattr(self.path_settings, name)
        show_path(default_path if default_path and path == "" else path)

    def set_icons(self, icon_name, widget_name, theme):
        if not self.initialized:
            return

        icon = QtGui.QIcon()
        icon.addPixmap(
            QtGui.QPixmap(f":/icons/{theme}/{icon_name}.svg"),
            QtGui.QIcon.Mode.Normal,
            QtGui.QIcon.State.Off)
        getattr(self.ui, widget_name).setIcon(icon)
        self.update()

    def toggle_nsfw_filter(self):
        self.set_nsfw_filter_tooltip()

    def set_nsfw_filter_tooltip(self):
        self.ui.actionSafety_Checker.setToolTip(
            f"Click to {'enable' if not self.application_settings.nsfw_filter else 'disable'} NSFW filter"
        )

    def on_toggle_fullscreen_signal(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def on_unload_non_sd_models(self, data: Dict = None):
        self._llm_generate_worker.on_llm_on_unload_signal()
        self._tts_generator_worker.unload()
        self._stt_audio_processor_worker.unload()
        callback = data.get("callback", None)
        if callback:
            callback(data)

    def on_load_non_sd_models(self, data: Dict = None):
        if self.application_settings.llm_enabled:
            self._llm_generate_worker.load()
        if self.application_settings.tts_enabled:
            self._tts_generator_worker.load()
        if self.application_settings.stt_enabled:
            self._stt_audio_processor_worker.load()
        callback = data.get("callback", None)
        if callback:
            callback(data)

    def on_toggle_llm(self, data: Dict = None, val=None):
        if val is None:
            val = not self.application_settings.llm_enabled
        self._update_action_button(
            ModelType.LLM,
            self.ui.actionToggle_LLM,
            val,
            SignalCode.LLM_LOAD_SIGNAL,
            SignalCode.LLM_UNLOAD_SIGNAL,
            "llm_enabled",
            data
        )

    def on_toggle_sd(self, data: Dict = None, val=None):
        if val is None:
            val = not self.application_settings.sd_enabled
        self._update_action_button(
            ModelType.SD,
            self.ui.actionToggle_Stable_Diffusion,
            val,
            SignalCode.SD_LOAD_SIGNAL,
            SignalCode.SD_UNLOAD_SIGNAL,
            "sd_enabled",
            data
        )

    def on_toggle_tts(self, data: Dict = None, val=None):
        if val is None:
            val = not self.application_settings.sd_enabled
        self._update_action_button(
            ModelType.TTS,
            self.ui.actionToggle_Text_to_Speech,
            val,
            SignalCode.TTS_ENABLE_SIGNAL,
            SignalCode.TTS_DISABLE_SIGNAL,
            "tts_enabled",
            data
        )

    def _update_action_button(
        self,
        model_type,
        element,
        val: bool,
        load_signal: SignalCode,
        unload_signal: SignalCode,
        application_setting: str = None,
        data: Dict = None
    ):
        if self._model_status[model_type] is ModelStatus.LOADING:
            val = not val
        element.blockSignals(True)
        element.setChecked(val)
        element.blockSignals(False)
        QApplication.processEvents()
        if application_setting:
            self.update_application_settings(application_setting, val)
        if self._model_status[model_type] is not ModelStatus.LOADING:
            if val:
                self.emit_signal(load_signal, data)
            else:
                self.emit_signal(unload_signal, data)

    def save_state(self):
        if self.quitting:
            return
        self.quitting = True
        self.logger.debug("Saving window state")

        self.save_window_settings("is_maximized", self.isMaximized())
        self.save_window_settings("is_fullscreen", self.isFullScreen())
        self.save_window_settings("llm_splitter", self.ui.tool_tab_widget.ui.llm_splitter.saveState())
        self.save_window_settings("width", self.width())
        self.save_window_settings("height", self.height())
        self.save_window_settings("x_pos", self.pos().x())
        self.save_window_settings("y_pos", self.pos().y())
        self.save_window_settings(
            "mode_tab_widget_index",
            self.ui.generator_widget.ui.generator_form_tabs.currentIndex()
        )

        settings = SplitterSetting.objects.filter_by_first(name="main_window_splitter")
        if not settings:
            SplitterSetting.objects.create(
                name="main_window_splitter",
                splitter_settings=self.ui.main_window_splitter.saveState()
            )
        else:
            SplitterSetting.objects.update(
                settings.id,
                splitter_settings=self.ui.main_window_splitter.saveState()
            )

    def restore_state(self):
        self.logger.debug("Restoring state")
        if self.window_settings is not None and self.window_settings.is_maximized:
            self.showMaximized()
        elif self.window_settings is not None and self.window_settings.is_fullscreen:
            self.showFullScreen()
        else:
            self.showNormal()

        first_run = False   

        self.setMinimumSize(100, 100)  # Set a reasonable minimum size

        width = int(self.window_settings.width)
        height = int(self.window_settings.height)
        if first_run:
            screen_geometry = QGuiApplication.primaryScreen().geometry()
            x_pos = (screen_geometry.width() - width) // 2
            y_pos = (screen_geometry.height() - height) // 2
        else:
            x_pos = int(self.window_settings.x_pos)
            y_pos = int(self.window_settings.y_pos)

        self.resize(width, height)
        self.move(x_pos, y_pos)
        self.raise_()

        # settings = SplitterSetting.objects.filter_by_first(
        #     name="main_window_splitter"
        # )
        # if settings:
        #     self.ui.main_window_splitter.restoreState(
        #         settings.splitter_settings
        #     )

    ##### End window properties #####
    #################################

    ###### Window handlers ######
    def cell_size_changed(self, val):
        self.update_grid_settings("cell_size", val)

    def line_width_changed(self, val):
        self.update_grid_settings("line_width", val)

    def line_color_changed(self, val):
        self.update_grid_settings("line_color", val)

    def snap_to_grid_changed(self, val):
        self.update_grid_settings("snap_to_grid", val)

    def canvas_color_changed(self, val):
        self.update_grid_settings("canvas_color", val)

    def action_ai_toggled(self, val):
        self.update_application_settings("ai_mode", val)

    @Slot(bool)
    def action_toggle_grid(self, val):
        self.update_grid_settings("show_grid", val)
        self.emit_signal(SignalCode.TOGGLE_GRID, {
            "show_grid": val
        })
    
    def on_toggle_tool_signal(self, data: Dict):
        self.toggle_tool(data["tool"], data["active"])

    def show_nsfw_warning_popup(self):
        if self.application_settings.show_nsfw_warning:
            """
            Display a popup window which asks the user if they are sure they want to disable the NSFW filter
            along with a checkbox that allows the user to disable the warning in the future.
            """
            msg_box = QMessageBox()
            msg_box.setWindowTitle("Disable Safety Checker Warning")
            msg_box.setText(
                (
                    "WARNING\n\n"
                    "You are attempting to disable the safety checker (NSFW filter).\n"
                    "It is strongly recommended that you keep this enabled at all times.\n"
                    "The Safety Checker prevents potentially harmful content from being displayed.\n"
                    "Only disable it if you are sure the Image model you are using is not capable of generating "
                    "harmful content.\n"
                    "Disabling the safety checker is intended as a last resort for continual false positives and as a "
                    "research feature.\n"
                    "\n\n"
                    "Are you sure you want to disable the filter?"
                )
            )
            msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            msg_box.setDefaultButton(QMessageBox.StandardButton.No)

            # Create a QCheckBox
            checkbox = QCheckBox("Do not show this warning again")
            # Add the checkbox to the message box
            msg_box.setCheckBox(checkbox)

            result = msg_box.exec()

            if result == QMessageBox.StandardButton.Yes:
                self._disable_nsfw_filter(not checkbox.isChecked())

            self.ui.actionSafety_Checker.blockSignals(True)
            self.ui.actionSafety_Checker.setChecked(self.application_settings.nsfw_filter)
            self.ui.actionSafety_Checker.blockSignals(False)
        else:
            self._disable_nsfw_filter()

    def _disable_nsfw_filter(self, show_nsfw_warning=None):
        """
        Do not call this function directly.
        :return:
        """
        # User confirmed to disable the NSFW filter
        # Update the settings accordingly
        self.update_application_settings("nsfw_filter", False)
        # Update the show_nsfw_warning setting based on the checkbox state
        if show_nsfw_warning is not None:
            self.update_application_settings("show_nsfw_warning", show_nsfw_warning)
        self.toggle_nsfw_filter()
        self.emit_signal(SignalCode.SAFETY_CHECKER_UNLOAD_SIGNAL)

    ###### End window handlers ######

    def show_update_message(self):
        self.emit_signal(
            SignalCode.APPLICATION_STATUS_INFO_SIGNAL,
            f"New version available: {self.latest_version}"
        )

    def show_update_popup(self):
        self.update_popup = UpdateWindow()

    @staticmethod
    def show_setup_wizard():
        AppInstaller(close_on_cancel=False)

    def showEvent(self, event):
        super().showEvent(event)
        self.logger.debug("showEvent called, initializing window")
        self._initialize_window()
        self._initialize_default_buttons()
        self._initialize_filter_actions()
        self.initialized = True
        for icon_data in self.icons:
            self.set_icons(
                icon_data[0],
                icon_data[1],
                "dark" if self.application_settings.dark_mode_enabled else "light"
            )
        self.logger.debug("Showing window")
        self._set_keyboard_shortcuts()

    def on_keyboard_shortcuts_updated(self):
        self._set_keyboard_shortcuts()

    def on_history_updated(self, data):
        self.ui.actionUndo.setEnabled(data["undo"] != 0)
        self.ui.actionRedo.setEnabled(data["redo"] != 0)

    def _set_keyboard_shortcuts(self):
        
        quit_key = ShortcutKeys.objects.filter_by_first(display_name="Quit")
        brush_key = ShortcutKeys.objects.filter_by_first(display_name="Brush")
        eraser_key = ShortcutKeys.objects.filter_by_first(display_name="Eraser")
        move_tool_key = ShortcutKeys.objects.filter_by_first(display_name="Move Tool")
        select_tool_key = ShortcutKeys.objects.filter_by_first(display_name="Select Tool")

        if quit_key is not None:
            key_sequence = QKeySequence(quit_key.key | quit_key.modifiers)
            self.ui.actionQuit.setShortcut(key_sequence)
            self.ui.actionQuit.setToolTip(f"{quit_key.display_name} ({quit_key.text})")

        if brush_key is not None:
            key_sequence = QKeySequence(brush_key.key | brush_key.modifiers)
            self.ui.actionToggle_Brush.setShortcut(key_sequence)
            self.ui.actionToggle_Brush.setToolTip(f"{brush_key.display_name} ({brush_key.text})")

        if eraser_key is not None:
            key_sequence = QKeySequence(eraser_key.key | eraser_key.modifiers)
            self.ui.actionToggle_Eraser.setShortcut(key_sequence)
            self.ui.actionToggle_Eraser.setToolTip(f"{eraser_key.display_name} ({eraser_key.text})")

        if move_tool_key is not None:
            key_sequence = QKeySequence(move_tool_key.key | move_tool_key.modifiers)
            self.ui.actionToggle_Active_Grid_Area.setShortcut(key_sequence)
            self.ui.actionToggle_Active_Grid_Area.setToolTip(f"{move_tool_key.display_name} ({move_tool_key.text})")

        if select_tool_key is not None:
            key_sequence = QKeySequence(select_tool_key.key | select_tool_key.modifiers)
            self.ui.actionToggle_Selection.setShortcut(key_sequence)
            self.ui.actionToggle_Selection.setToolTip(f"{select_tool_key.display_name} ({select_tool_key.text})")

    def _initialize_workers(self):
        self.logger.debug("Initializing worker manager")
        self._mask_generator_worker = create_worker(MaskGeneratorWorker)
        self._sd_worker = create_worker(SDWorker)
        self._stt_audio_capture_worker = create_worker(AudioCaptureWorker)
        self._stt_audio_processor_worker = create_worker(AudioProcessorWorker)
        self._tts_generator_worker = create_worker(TTSGeneratorWorker)
        self._tts_vocalizer_worker = create_worker(TTSVocalizerWorker)
        self._llm_generate_worker = create_worker(LLMGenerateWorker)

    def _initialize_filter_actions(self):
        image_filters = ImageFilter.objects.all()
        for image_filter in image_filters:
            action = self.ui.menuFilters.addAction(image_filter.display_name)
            action.triggered.connect(partial(self.display_filter_window, image_filter))

    @staticmethod
    def display_filter_window(image_filter):
        FilterWindow(image_filter.id)

    def _initialize_default_buttons(self):
        self.ui.actionSafety_Checker.blockSignals(True)
        self.ui.actionSafety_Checker.setChecked(self.application_settings.nsfw_filter)
        self.ui.actionSafety_Checker.blockSignals(False)

    def toggle_tool(self, tool: CanvasToolName, active: bool):
        self.update_application_settings("current_tool", tool.value)
        self.emit_signal(SignalCode.APPLICATION_TOOL_CHANGED_SIGNAL, {
            "tool": tool,
            "active": active
        })

    def _initialize_window(self):
        self.center()
        self.set_window_title()

    def center(self):
        available_geometry = QGuiApplication.primaryScreen().availableGeometry()
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
        self.logger.error(f"Unknown message code: {message}")

    def clear_all_prompts(self):
        self.prompt = ""
        self.negative_prompt = ""
        self.emit_signal(SignalCode.CLEAR_PROMPTS)

    def new_batch(self, index, image, data):
        self.generator_tab_widget.new_batch(index, image, data)

    def on_model_status_changed_signal(self, data):
        model = data["model"]
        status = data["status"]
        if self._model_status[model] is status:
            return
        self._model_status[model] = status
        if model is ModelType.SD:
            self.ui.actionToggle_Stable_Diffusion.setDisabled(status is ModelStatus.LOADING)
            if status is ModelStatus.FAILED:
                self.ui.actionToggle_Stable_Diffusion.setChecked(False)
        elif model is ModelType.CONTROLNET:
            self.ui.actionToggle_Controlnet.setDisabled(status is ModelStatus.LOADING)
            if status is ModelStatus.FAILED:
                self.ui.actionToggle_Controlnet.setChecked(False)
        elif model is ModelType.LLM:
            self.ui.actionToggle_LLM.setDisabled(status is ModelStatus.LOADING)
            if status is ModelStatus.FAILED:
                self.logger.warning("LLM failed to load")
                self.ui.actionToggle_LLM.setChecked(False)
        elif model is ModelType.TTS:
            self.ui.actionToggle_Text_to_Speech.setDisabled(status is ModelStatus.LOADING)
            if status is ModelStatus.FAILED:
                self.ui.actionToggle_Text_to_Speech.setChecked(False)
        elif model is ModelType.STT:
            self.ui.actionToggle_Speech_to_Text.setDisabled(status is ModelStatus.LOADING)
            if status is ModelStatus.FAILED:
                self.ui.actionToggle_Speech_to_Text.setChecked(False)
        self.initialize_widget_elements()
        QApplication.processEvents()

    def _generate_drawingpad_mask(self):
        width = self.active_grid_settings.width
        height = self.active_grid_settings.height
        img = Image.new("RGB", (width, height), (0, 0, 0))
        base64_image = convert_image_to_binary(img)
        
        drawing_pad_settings = DrawingPadSettings.objects.first()
        drawing_pad_settings.mask = base64_image
        drawing_pad_settings.save()
        
    def display_missing_models_error(self):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle("Error: Missing models")
        msg_box.setText("You are missing some required models.")
        
        download_missing_models = msg_box.addButton("Download missing models", QMessageBox.AcceptRole)
        
        msg_box.exec()
        
        if msg_box.clickedButton() == download_missing_models:
            self.show_setup_wizard()
