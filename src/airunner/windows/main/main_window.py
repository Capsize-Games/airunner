import os
import re
import sys
import urllib
import webbrowser
from functools import partial

import requests
from PySide6 import QtGui
from PySide6.QtCore import (
    Slot,
    Signal, QProcess
)
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QMessageBox,
    QCheckBox, QInputDialog
)
from bs4 import BeautifulSoup

from airunner.aihandler.llm.agent.actions.bash_execute import bash_execute
from airunner.aihandler.llm.agent.actions.show_path import show_path
from airunner.aihandler.logger import Logger
from airunner.settings import (
    STATUS_ERROR_COLOR,
    STATUS_NORMAL_COLOR_LIGHT,
    STATUS_NORMAL_COLOR_DARK,
    NSFW_CONTENT_DETECTED_MESSAGE, DEFAULT_PATH_SETTINGS
)
from airunner.enums import (
    SignalCode,
    CanvasToolName,
    GeneratorSection, StatusColors, ModelStatus, ModelType, LLMAction
)
from airunner.mediator_mixin import MediatorMixin
from airunner.resources_dark_rc import *
from airunner.settings import (
    BASE_PATH,
    BUG_REPORT_LINK,
    VULNERABILITY_REPORT_LINK
)
from airunner.utils.file_system.operations import FileSystemOperations
from airunner.utils.get_current_chatbot import get_current_chatbot, set_current_chatbot

from airunner.utils.get_version import get_version
from airunner.utils.set_widget_state import set_widget_state
from airunner.windows.main.ai_model_mixin import AIModelMixin
from airunner.windows.main.controlnet_model_mixin import ControlnetModelMixin
from airunner.windows.main.pipeline_mixin import PipelineMixin
from airunner.windows.main.settings_mixin import SettingsMixin
from airunner.windows.main.templates.main_window_ui import Ui_MainWindow


class MainWindow(
    QMainWindow,
    MediatorMixin,
    SettingsMixin,
    PipelineMixin,
    ControlnetModelMixin,
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
    tab_section_changed_signal = Signal()
    load_image = Signal(str)
    load_image_object = Signal(object)
    loaded = Signal()
    window_opened = Signal()
    ui_class_ = Ui_MainWindow
    _window_title = f"AI Runner"
    icons = [
        ("pencil-icon", "toggle_brush_button"),
        ("eraser-icon", "toggle_eraser_button"),
        ("frame-grid-icon", "toggle_grid_button"),
        ("circle-center-icon", "focus_button"),
        ("artificial-intelligence-ai-chip-icon", "ai_button"),
        ("setting-line-icon", "settings_button"),
        ("object-selected-icon", "toggle_active_grid_area_button"),
        ("select-svgrepo-com", "toggle_select_button"),
    ]

    def __init__(
        self,
        *args,
        disable_sd: bool = False,
        disable_llm: bool = False,
        disable_tts: bool = False,
        disable_stt: bool = False,
        use_cuda: bool = True,
        tts_enabled: bool = False,
        stt_enabled: bool = False,
        ai_mode: bool = True,
        restrict_os_access=None,
        defendatron=None,
        **kwargs
    ):
        self.ui = self.ui_class_()
        self.disable_sd = disable_sd
        self.disable_llm = disable_llm
        self.disable_tts = disable_tts
        self.disable_stt = disable_stt

        self.restrict_os_access = restrict_os_access
        self.defendatron = defendatron
        self.quitting = False
        self._override_system_theme = None
        self._dark_mode_enabled = None
        self.update_popup = None
        self._document_path = None
        self.prompt = None
        self.negative_prompt = None
        self.image_path = None
        self.token_signal = Signal(str)
        self.api = None
        self.input_event_manager = None
        self.current_filter = None
        self.tqdm_callback_triggered = False
        self.is_saved = False
        self.action = GeneratorSection.TXT2IMG.value
        self.progress_bar_started = False
        self.window = None
        self.canvas = None
        self.models = None
        self.client = None
        self._version = None
        self._latest_version = None
        self.data = None  # this is set in the generator_mixin image_handler function and used for deterministic generation
        self.status_error_color = STATUS_ERROR_COLOR
        self.status_normal_color_light = STATUS_NORMAL_COLOR_LIGHT
        self.status_normal_color_dark = STATUS_NORMAL_COLOR_DARK
        self.is_started = False
        self._themes = None
        self.button_clicked_signal = Signal(dict)
        self.status_widget = None
        self.header_widget_spacer = None
        self.deterministic_window = None
        self.generator = None
        self._generator = None
        self._generator_settings = None
        self.listening = False
        self.initialized = False

        self.logger = Logger(prefix=self.__class__.__name__)
        self.logger.debug("Starting AI Runnner")
        MediatorMixin.__init__(self)
        SettingsMixin.__init__(self)

        self.do_load_llm_on_init = self.settings["llm_enabled"]

        self.update_settings()

        super().__init__(*args, **kwargs)

        self._updating_settings = True
        self.update_settings()

        PipelineMixin.__init__(self)
        ControlnetModelMixin.__init__(self)
        AIModelMixin.__init__(self)
        self._updating_settings = False

        self.register_signals()
        self.register(
            SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL,
            self.on_application_settings_changed_signal
        )

        self.initialize_ui()
        self.worker_manager = None
        self.is_started = True
        self.image_window = None

        for item in (
            (SignalCode.AI_MODELS_SAVE_OR_UPDATE_SIGNAL, self.on_ai_models_save_or_update_signal),
            (SignalCode.NAVIGATE_TO_URL, self.on_navigate_to_url),
        ):
            self.register(item[0], item[1])

        self.emit_signal(SignalCode.APPLICATION_MAIN_WINDOW_LOADED_SIGNAL, { "main_window": self })

    def download_url(self, url, save_path):
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

    def download_pdf(self, url, save_path):
        response = requests.get(url)
        filename = url.split('/')[-1]  # Get the filename from the URL
        save_path = os.path.join(save_path, filename)
        with open(save_path, 'wb') as file:
            file.write(response.content)
        return filename

    def on_navigate_to_url(self, data: dict = None):
        url, ok = QInputDialog.getText(self, 'Browse Web', 'Enter your URL:')
        if ok:
            settings = self.settings

            try:
                result = urllib.parse.urlparse(url)
                is_url = all([result.scheme, result.netloc])
            except ValueError:
                is_url = False

            # If the input is a URL, download it
            if is_url:
                if url.lower().endswith('.pdf'):
                    # Handle PDF file
                    filepath = os.path.expanduser(settings["path_settings"]["pdf_path"])
                    filename = self.download_pdf(url, filepath)
                else:
                    # Handle URL
                    filepath = os.path.expanduser(settings["path_settings"]["webpages_path"])
                    filename = self.download_url(url, filepath)
            elif os.path.isfile(url):
                filepath = os.path.dirname(url)
                filename = os.path.basename(url)
            else:
                self.logger.error(f"Invalid URL or file path")
                return

            # Update target files to use only the file that was downloaded or navigated to
            # and update the index.
            chatbot = get_current_chatbot(settings)
            chatbot["target_files"] = [os.path.join(filepath, filename)]
            settings = set_current_chatbot(settings, chatbot)
            self.settings = settings
            self.emit_signal(SignalCode.RAG_RELOAD_INDEX_SIGNAL, {
                "target_files": chatbot["target_files"]
            })
            self.emit_signal(
                SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL,
                {
                    "llm_request": True,
                    "request_data": {
                        "action": LLMAction.RAG,
                        "prompt": "Summarize the text and provide a synopsis of the content. Be concise and informative.",
                    }
                }
            )

    def keyPressEvent(self, event):
        super().keyPressEvent(event)
        self.handle_key_press(event.key)

    def handle_key_press(self, key):
        shortcut_key_settings = self.settings["shortcut_key_settings"]
        for k, v in shortcut_key_settings.items():
            if v["key"] == key():
                for signal in SignalCode:
                    if signal.value == v["signal"]:
                        self.emit_signal(signal)
                        break

    def key_matches(self, key_name, keyboard_key):
        settings = self.settings
        if not key_name in settings["shortcut_key_settings"]:
            return False
        return settings["shortcut_key_settings"][key_name]["key"] == keyboard_key.value

    def key_text(self, key_name):
        settings = self.settings
        if not key_name in settings["shortcut_key_settings"]:
            return ""
        return settings["shortcut_key_settings"][key_name]["text"]

    def on_update_saved_stablediffusion_prompt_signal(self, options: dict):
        index, prompt, negative_prompt = options
        settings = self.settings
        try:
            settings["saved_prompts"][index] = {
                'prompt': prompt,
                'negative_prompt': negative_prompt,
            }
        except KeyError:
            self.logger.error(f"Unable to update prompt at index {index}")
        self.settings = settings

    def on_save_stablediffusion_prompt_signal(self):
        settings = self.settings
        settings["saved_prompts"].append({
            'prompt': settings["generator_settings"]["prompt"],
            'negative_prompt': settings["generator_settings"]["negative_prompt"],
        })
        self.settings = settings

    def set_path_settings(self, key, val):
        settings = self.settings
        settings["path_settings"][key] = val
        self.settings = settings

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

    def on_describe_image_signal(self, data):
        image = data["image"]
        callback = data["callback"]
        self.generator_tab_widget.ui.ai_tab_widget.describe_image(
            image=image,
            callback=callback
        )

    def show_layers(self):
        self.emit_signal(SignalCode.LAYERS_SHOW_SIGNAL)

    def register_signals(self):
        self.logger.debug("Connecting signals")
        self.register(SignalCode.SD_SAVE_PROMPT_SIGNAL, self.on_save_stablediffusion_prompt_signal)
        self.register(SignalCode.SD_UPDATE_SAVED_PROMPT_SIGNAL, self.on_update_saved_stablediffusion_prompt_signal)
        self.register(SignalCode.QUIT_APPLICATION, self.action_quit_triggered)
        self.register(SignalCode.SD_NSFW_CONTENT_DETECTED_SIGNAL, self.on_nsfw_content_detected_signal)
        self.register(SignalCode.ENABLE_BRUSH_TOOL_SIGNAL, lambda _message: self.action_toggle_brush(True))
        self.register(SignalCode.ENABLE_ERASER_TOOL_SIGNAL, lambda _message: self.action_toggle_eraser(True))
        self.register(SignalCode.ENABLE_SELECTION_TOOL_SIGNAL, lambda _message: self.action_toggle_select(True))
        self.register(SignalCode.ENABLE_MOVE_TOOL_SIGNAL, lambda _message: self.action_toggle_active_grid_area(True))
        self.register(SignalCode.BASH_EXECUTE_SIGNAL, self.on_bash_execute_signal)
        self.register(SignalCode.WRITE_FILE, self.on_write_file_signal)
        self.register(SignalCode.TOGGLE_FULLSCREEN_SIGNAL, self.on_toggle_fullscreen_signal)
        self.register(SignalCode.TOGGLE_TTS_SIGNAL, self.on_toggle_tts)
        self.register(SignalCode.APPLICATION_RESET_SETTINGS_SIGNAL, self.action_reset_settings)
        self.register(SignalCode.APPLICATION_RESET_PATHS_SIGNAL, self.on_reset_paths_signal)
        self.register(SignalCode.REFRESH_STYLESHEET_SIGNAL, self.refresh_stylesheet)
        self.register(SignalCode.MODEL_STATUS_CHANGED_SIGNAL, self.on_model_status_changed_signal)

    def on_reset_paths_signal(self):
        settings = self.settings
        settings["path_settings"] = DEFAULT_PATH_SETTINGS
        self.settings = settings

    def restart(self):
        # Save the current state
        self.save_state()

        # Close the main window
        self.close()

        # Start a new instance of the application
        QProcess.startDetached(sys.executable, sys.argv)

    def on_write_file_signal(self, data: dict):
        """
        Writes data to a file.
        :param data: dict
        :return: None
        """
        args = data["args"]
        if len(args) == 1:
            message = args[0]
        else:
            message = args[1]
        with open("output.txt", "w") as f:
            f.write(message)

    def on_bash_execute_signal(self, data: dict) -> str:
        """
        Takes a message from the LLM and strips bash commands from it.
        Passes bash command to the bash_execute function.
        :param message:
        :return:
        """
        args = data["args"]
        return bash_execute(args[0])

    def on_application_settings_changed_signal(self):
        if not self._updating_settings:
            self.set_stylesheet()

    def initialize_ui(self):
        self.logger.debug("Loading UI")
        self.ui.setupUi(self)

        self.logger.debug("Restoring state")
        self.restore_state()
        settings = self.settings

        from airunner.widgets.status.status_widget import StatusWidget
        self.status_widget = StatusWidget()
        self.statusBar().addPermanentWidget(self.status_widget)
        self.emit_signal(SignalCode.APPLICATION_CLEAR_STATUS_MESSAGE_SIGNAL)

        self.set_stylesheet()
        self.initialize_widget_elements()

    def initialize_widget_elements(self):
        settings = self.settings
        for item in (
            (self.ui.actionToggle_LLM, settings["llm_enabled"]),
            (self.ui.actionToggle_Text_to_Speech, settings["tts_enabled"]),
            (self.ui.actionToggle_Speech_to_Text, settings["stt_enabled"]),
            (self.ui.actionToggle_Stable_Diffusion, settings["sd_enabled"]),
            (self.ui.actionToggle_Controlnet, settings["controlnet_enabled"]),
        ):
            item[0].blockSignals(True)
            item[0].setChecked(item[1])
            item[0].blockSignals(False)
        self.initialized = True

    def layer_opacity_changed(self, attr_name, value=None, widget=None):
        self.emit_signal(SignalCode.LAYER_OPACITY_CHANGED_SIGNAL, value)

    """
    Slot functions
    
    The following functions are defined in and connected to the appropriate
    signals in the corresponding ui file.
    """
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
        # super().closeEvent(event)

    @Slot()
    def action_new_document_triggered(self):
        self.new_document()
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
        self.show_prompt_browser()

    @Slot()
    def action_clear_all_prompts_triggered(self):
        self.clear_all_prompts()

    @Slot()
    def action_show_model_manager(self):
        from airunner.widgets.model_manager.model_manager_widget import ModelManagerWidget
        ModelManagerWidget()

    @Slot()
    def action_show_stablediffusion(self):
        self.activate_image_generation_section()

    @Slot()
    def action_triggered_browse_ai_runner_path(self):
        path = self.settings["path_settings"]["base_path"]
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

    def show_settings_path(self, name, default_path=None):
        path = self.settings["path_settings"][name]
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

    @Slot()
    def action_show_about_window(self):
        from airunner.windows.about.about import AboutWindow
        AboutWindow()

    @Slot()
    def action_show_settings(self):
        from airunner.windows.settings.airunner_settings import SettingsWindow
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

    """
    End slot functions
    """

    def toggle_nsfw_filter(self):
        self.set_nsfw_filter_tooltip()

    def set_nsfw_filter_tooltip(self):
        self.ui.actionSafety_Checker.setToolTip(
            f"Click to {'enable' if not self.settings['nsfw_filter'] else 'disable'} NSFW filter"
        )

    def on_toggle_fullscreen_signal(self, message: dict = None):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def on_toggle_tts(self, message: dict = None):
        self.tts_button_toggled(not self.settings["tts_enabled"])

    @Slot(bool)
    def tts_button_toggled(self, val):
        new_settings = self.settings
        new_settings["tts_enabled"] = val
        self.settings = new_settings
        self.emit_signal(SignalCode.TTS_ENABLE_SIGNAL if val else SignalCode.TTS_DISABLE_SIGNAL)

    @Slot(bool)
    def v2t_button_toggled(self, val):
        new_settings = self.settings
        new_settings["stt_enabled"] = val
        self.settings = new_settings
        if not val:
            self.emit_signal(SignalCode.STT_STOP_CAPTURE_SIGNAL)
        else:
            self.emit_signal(SignalCode.STT_START_CAPTURE_SIGNAL)

    def save_state(self):
        if self.quitting:
            return
        self.quitting = True
        self.logger.debug("Saving window state")
        settings = self.settings
        window_settings = settings["window_settings"]
        window_settings.update(dict(
            is_maximized=self.isMaximized(),
            is_fullscreen=self.isFullScreen(),
            llm_splitter=self.ui.tool_tab_widget.ui.llm_splitter.saveState(),
            content_splitter=self.ui.content_splitter.saveState(),
            canvas_splitter=self.ui.canvas_widget_2.ui.canvas_splitter.saveState(),
            generator_form_splitter=self.ui.generator_widget.ui.generator_form_splitter.saveState(),
            tool_tab_widget_index=self.ui.tool_tab_widget.ui.tool_tab_widget_container.currentIndex(),
            grid_settings_splitter=self.ui.tool_tab_widget.ui.grid_settings_splitter.saveState(),
            width=self.width(),
            height=self.height(),
            x_pos=self.pos().x(),
            y_pos=self.pos().y()
        ))
        settings["window_settings"] = window_settings
        self.settings = settings
        self.save_settings()

    def restore_state(self):
        self.logger.debug("Restoring state")
        settings = self.settings

        window_settings = settings["window_settings"]

        if window_settings["is_maximized"]:
            self.showMaximized()
        elif window_settings["is_fullscreen"]:
            self.showFullScreen()
        else:
            self.showNormal()

        self.ui.ai_button.setChecked(settings["ai_mode"])
        self.set_button_checked("toggle_grid", settings["grid_settings"]["show_grid"], False)

        splitters = [
            ("content_splitter", self.ui.content_splitter),
            ("llm_splitter", self.ui.tool_tab_widget.ui.llm_splitter),
            ("canvas_splitter", self.ui.canvas_widget_2.ui.canvas_splitter),
            ("generator_form_splitter", self.ui.generator_widget.ui.generator_form_splitter),
            ("grid_settings_splitter", self.ui.tool_tab_widget.ui.grid_settings_splitter),
        ]
        for splitter_name, splitter in splitters:
            if window_settings[splitter_name] is not None:
                splitter.blockSignals(True)
                splitter.restoreState(window_settings[splitter_name])
                splitter.blockSignals(False)

        self.setMinimumSize(100, 100)  # Set a reasonable minimum size
        width = window_settings["width"] if "width" in window_settings else 800
        height = window_settings["height"] if "height" in window_settings else 600
        self.resize(width, height)

        x_pos = window_settings["x_pos"] if "x_pos" in window_settings else 0
        y_pos = window_settings["y_pos"] if "y_pos" in window_settings else 0
        self.move(x_pos, y_pos)
    ##### End window properties #####
    #################################
        
    ###### Window handlers ######
    def cell_size_changed(self, val):
        settings = self.settings
        settings["grid_settings"]["cell_size"] = val
        self.settings = settings

    def line_width_changed(self, val):
        settings = self.settings
        settings["grid_settings"]["line_width"] = val
        self.settings = settings
    
    def line_color_changed(self, val):
        settings = self.settings
        settings["grid_settings"]["line_color"] = val
        self.settings = settings
    
    def snap_to_grid_changed(self, val):
        settings = self.settings
        settings["grid_settings"]["snap_to_grid"] = val
        self.settings = settings
    
    def canvas_color_changed(self, val):
        settings = self.settings
        settings["grid_settings"]["canvas_color"] = val
        self.settings = settings

    def action_ai_toggled(self, val):
        settings = self.settings
        settings["ai_mode"] = val
        self.settings = settings
    
    def action_toggle_grid(self, val):
        settings = self.settings
        settings["grid_settings"]["show_grid"] = val
        self.settings = settings

    @Slot(bool)
    def action_toggle_brush(self, active: bool):
        if active:
            self.ui.toggle_select_button.setChecked(False)
            self.ui.toggle_active_grid_area_button.setChecked(False)
            self.ui.toggle_eraser_button.setChecked(False)
            self.ui.toggle_brush_button.blockSignals(True)
            self.ui.toggle_brush_button.setChecked(True)
            self.ui.toggle_brush_button.blockSignals(False)
        self.toggle_tool(CanvasToolName.BRUSH, active)

    @Slot(bool)
    def action_toggle_eraser(self, active: bool):
        if active:
            self.ui.toggle_select_button.setChecked(False)
            self.ui.toggle_active_grid_area_button.setChecked(False)
            self.ui.toggle_brush_button.setChecked(False)
            self.ui.toggle_eraser_button.blockSignals(True)
            self.ui.toggle_eraser_button.setChecked(True)
            self.ui.toggle_eraser_button.blockSignals(False)
        self.toggle_tool(CanvasToolName.ERASER, active)

    @Slot(bool)
    def action_toggle_select(self, active: bool):
        if active:
            self.ui.toggle_active_grid_area_button.setChecked(False)
            self.ui.toggle_brush_button.setChecked(False)
            self.ui.toggle_eraser_button.setChecked(False)
        self.toggle_tool(CanvasToolName.SELECTION, active)

    @Slot(bool)
    def action_toggle_active_grid_area(self, active: bool):
        if active:
            self.ui.toggle_select_button.setChecked(False)
            self.ui.toggle_brush_button.setChecked(False)
            self.ui.toggle_eraser_button.setChecked(False)
        self.toggle_tool(CanvasToolName.ACTIVE_GRID_AREA, active)

    @Slot(bool)
    def action_toggle_nsfw_filter_triggered(self, val: bool):
        if val is False:
            self.show_nsfw_warning_popup()
        else:
            settings = self.settings
            settings["nsfw_filter"] = val
            self.settings = settings
            self.toggle_nsfw_filter()
            self.emit_signal(SignalCode.SAFETY_CHECKER_LOAD_SIGNAL)

    def show_nsfw_warning_popup(self):
        settings = self.settings

        if settings["show_nsfw_warning"]:
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
                    "Only disable it if you are sure the Image model you are using is not capable of generating harmful content.\n"
                    "Disabling the safety checker is intended as a last resort for continual false positives and as a research feature.\n"
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
            self.ui.actionSafety_Checker.setChecked(settings["nsfw_filter"])
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
        settings = self.settings
        settings["nsfw_filter"] = False
        # Update the show_nsfw_warning setting based on the checkbox state
        if show_nsfw_warning is not None:
            settings["show_nsfw_warning"] = show_nsfw_warning
        self.settings = settings
        self.toggle_nsfw_filter()
        self.emit_signal(SignalCode.SAFETY_CHECKER_UNLOAD_SIGNAL)

    def action_toggle_darkmode(self):
        self.set_stylesheet()
    ###### End window handlers ######

    def show_update_message(self):
        self.emit_signal(
            SignalCode.APPLICATION_STATUS_INFO_SIGNAL,
            f"New version available: {self.latest_version}"
        )

    def show_update_popup(self):
        from airunner.windows.update.update_window import UpdateWindow
        self.update_popup = UpdateWindow()

    def refresh_stylesheet(self):
        self.set_stylesheet(force=True)

    def set_stylesheet(self, ui=None, force=False):
        """
        Sets the stylesheet for the application based on the current theme
        """
        settings = self.settings
        if (
            self._override_system_theme is not settings["override_system_theme"] or
            self._dark_mode_enabled is not settings["dark_mode_enabled"] or
            force
        ):
            ui = ui or self
            self._override_system_theme = settings["override_system_theme"]
            self._dark_mode_enabled = settings["dark_mode_enabled"]

            if self._override_system_theme:
                self.logger.debug("Setting stylesheet")

                stylesheet = FileSystemOperations().read_stylesheet()
                ui.setStyleSheet(stylesheet)
            else:
                self.logger.debug("Using system theme")
                ui.setStyleSheet("")

    def show_setup_wizard(self):
        from airunner.windows.setup_wizard.setup_wizard_window import SetupWizard
        wizard = SetupWizard()
        wizard.exec()

    def showEvent(self, event):
        super().showEvent(event)
        self.logger.debug("showEvent called, initializing window")
        settings = self.settings
        self._initialize_window()
        self._initialize_default_buttons(settings)
        self._initialize_filter_actions(settings)
        self.initialized = True
        for icon_data in self.icons:
            self.set_icons(
                icon_data[0],
                icon_data[1],
                "dark" if settings["dark_mode_enabled"] else "light"
            )
        self._initialize_worker_manager()
        self.logger.debug("Showing window")

    def _initialize_worker_manager(self):
        self.logger.debug("Initializing worker manager")
        from airunner.worker_manager import WorkerManager
        self.worker_manager = WorkerManager(
            disable_sd=self.disable_sd,
            disable_llm=self.disable_llm,
            disable_tts=self.disable_tts,
            disable_stt=self.disable_stt,
            do_load_llm_on_init=self.do_load_llm_on_init
        )

    def _initialize_filter_actions(self, settings):
        # add more filters:
        for filter_name, filter_data in settings["image_filters"].items():

            action = self.ui.menuFilters.addAction(filter_data["display_name"])
            action.triggered.connect(partial(self.display_filter_window, filter_data["name"]))

    def display_filter_window(self, filter_name):
        from airunner.windows.filter_window import FilterWindow
        FilterWindow(filter_name)

    def _initialize_default_buttons(self, settings):
        show_grid = settings["grid_settings"]["show_grid"]
        current_tool = settings["current_tool"]
        ai_mode = settings["ai_mode"]

        set_widget_state(self.ui.toggle_active_grid_area_button, current_tool is CanvasToolName.ACTIVE_GRID_AREA)
        set_widget_state(self.ui.toggle_brush_button, current_tool is CanvasToolName.BRUSH)
        set_widget_state(self.ui.toggle_eraser_button, current_tool is CanvasToolName.ERASER)
        set_widget_state(self.ui.toggle_grid_button, show_grid is True)
        set_widget_state(self.ui.ai_button, ai_mode)

        self.ui.actionSafety_Checker.blockSignals(True)
        self.ui.actionSafety_Checker.setChecked(settings["nsfw_filter"])
        self.ui.actionSafety_Checker.blockSignals(False)

    def toggle_tool(self, tool: CanvasToolName, active: bool):
        if not active:
            tool = CanvasToolName.NONE
        settings = self.settings
        settings["current_tool"] = tool
        self.settings = settings
        self.emit_signal(SignalCode.APPLICATION_TOOL_CHANGED_SIGNAL, {
            "tool": tool
        })

    def plain_text_widget_value(self, widget):
        try:
            return widget.toPlainText()
        except AttributeError:
            return None

    def current_text_widget_value(self, widget):
        try:
            return widget.currentText()
        except AttributeError:
            return None

    def value_widget_value(self, widget):
        try:
            return widget.value()
        except AttributeError:
            return None

    def _initialize_window(self):
        self.center()
        self.set_window_title()

    def display(self):
        self.logger.debug("Displaying window")
        self.set_stylesheet()
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowType.Window)
        self.show()

    def center(self):
        availableGeometry = QGuiApplication.primaryScreen().availableGeometry()
        frameGeometry = self.frameGeometry()
        frameGeometry.moveCenter(availableGeometry.center())
        self.move(frameGeometry.topLeft())

    def set_window_title(self):
        """
        Overrides base method to set the window title
        :return:
        """
        self.setWindowTitle(self._window_title)

    def new_document(self):
        self.is_saved = False
        self.set_window_title()
        self.current_filter = None

    def post_process_images(self, images):
        #return self.automatic_filter_manager.apply_filters(images)
        return images

    def handle_unknown(self, message):
        self.logger.error(f"Unknown message code: {message}")

    def clear_all_prompts(self):
        self.prompt = ""
        self.negative_prompt = ""
        self.generator_tab_widget.clear_prompts()

    def show_prompt_browser(self):
        from airunner.windows.prompt_browser.prompt_browser import PromptBrowser
        PromptBrowser()

    def new_batch(self, index, image, data):
        self.generator_tab_widget.new_batch(index, image, data)

    def set_button_checked(self, name, val=True, block_signals=True):
        widget = getattr(self.ui, f"{name}_button")
        if block_signals:
            widget.blockSignals(True)
        widget.setChecked(val)
        if block_signals:
            widget.blockSignals(False)

    def action_center_clicked(self):
        print("center clicked")

    def action_reset_settings(self):
        reply = QMessageBox.question(
            self,
            'Reset Settings',
            'Are you sure you want to reset all settings to their default values?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.settings = self.default_settings
            self.restart()

    def import_controlnet_image(self):
        self.emit_signal(SignalCode.CONTROLNET_IMPORT_IMAGE_SIGNAL)

    def export_controlnet_image(self):
        self.emit_signal(SignalCode.CONTROLNET_EXPORT_IMAGE_SIGNAL)

    def import_drawingpad_image(self):
        self.emit_signal(SignalCode.DRAWINGPAD_IMPORT_IMAGE_SIGNAL)

    def export_drawingpad_image(self):
        self.emit_signal(SignalCode.DRAWINGPAD_EXPORT_IMAGE_SIGNAL)

    def action_export_image_triggered(self):
        self.emit_signal(SignalCode.CANVAS_EXPORT_IMAGE_SIGNAL)

    def action_import_image_triggered(self):
        self.emit_signal(SignalCode.CANVAS_IMPORT_IMAGE_SIGNAL)

    @Slot()
    def action_clear_memory(self):
        from airunner.utils.clear_memory import clear_memory
        clear_memory()

    @Slot(bool)
    def action_outpaint_toggled(self, val: bool):
        settings = self.settings
        settings["outpaint_settings"]["enabled"] = val
        self.settings = settings

    @Slot()
    def action_outpaint_export(self):
        self.emit_signal(SignalCode.OUTPAINT_EXPORT_SIGNAL)

    @Slot()
    def action_outpaint_import(self):
        self.emit_signal(SignalCode.OUTPAINT_IMPORT_SIGNAL)

    @Slot()
    def action_run_setup_wizard_clicked(self):
        self.show_setup_wizard()

    @Slot(bool)
    def action_toggle_llm(self, val):
        settings = self.settings
        settings["llm_enabled"] = val
        self.settings = settings
        if val:
            self.emit_signal(SignalCode.LLM_LOAD_SIGNAL)
        else:
            self.emit_signal(SignalCode.LLM_UNLOAD_SIGNAL)

    @Slot(bool)
    def action_image_generator_toggled(self, val: bool):
        settings = self.settings
        settings["sd_enabled"] = val
        self.settings = settings
        if val:
            self.emit_signal(SignalCode.SD_LOAD_SIGNAL)
        else:
            self.update()
            self.emit_signal(SignalCode.SD_UNLOAD_SIGNAL)

    @Slot(bool)
    def action_controlnet_toggled(self, val: bool):
        settings = self.settings
        settings["controlnet_enabled"] = val
        self.settings = settings

        for widget in [self.ui.controlnet_toggle_button, self.ui.enable_controlnet]:
            widget.blockSignals(True)
            widget.setChecked(val)
            widget.blockSignals(False)

        signal = SignalCode.CONTROLNET_LOAD_SIGNAL if val else SignalCode.CONTROLNET_UNLOAD_SIGNAL
        self.emit_signal(signal)

    @Slot()
    def action_stats_triggered(self):
        from airunner.widgets.stats.stats_widget import StatsWidget
        widget = StatsWidget()
        # display in a window
        widget.show()

    def on_model_status_changed_signal(self, data):
        model = data["model"]
        status = data["status"]
        if model is ModelType.SD:
            self.__set_button_state(self.ui.sd_toggle_button, status)
        elif model is ModelType.CONTROLNET:
            self.__set_button_state(self.ui.controlnet_toggle_button, status)
        elif model is ModelType.LLM:
            self.__set_button_state(self.ui.llm_button, status)

    def __set_button_state(self, button, status):
        # button.blockSignals(True)
        # button.setChecked(status not in (
        #     ModelStatus.FAILED,
        #     ModelStatus.UNLOADED
        # ))
        button.setEnabled(status is not ModelStatus.LOADING)
        # button.blockSignals(False)
        button.repaint()
