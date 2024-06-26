import os
import re
import urllib
import webbrowser
from functools import partial

import requests
from PySide6 import QtGui
from PySide6.QtCore import (
    Slot,
    Signal, QTimer
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
from airunner.aihandler.llm.agent.base_agent import BaseAgent
from airunner.aihandler.logger import Logger
from airunner.settings import (
    STATUS_ERROR_COLOR,
    STATUS_NORMAL_COLOR_LIGHT,
    STATUS_NORMAL_COLOR_DARK,
    NSFW_CONTENT_DETECTED_MESSAGE
)
from airunner.enums import (
    Mode,
    SignalCode,
    CanvasToolName,
    WindowSection,
    GeneratorSection, StatusColors, ModelStatus, ModelType, LLMAction
)
from airunner.mediator_mixin import MediatorMixin
from airunner.resources_dark_rc import *
from airunner.settings import (
    BASE_PATH,
    BUG_REPORT_LINK,
    VULNERABILITY_REPORT_LINK
)
from airunner.utils.agents.current_chatbot import current_chatbot, update_chatbot
from airunner.utils.file_system.operations import FileSystemOperations

from airunner.utils.get_version import get_version
from airunner.utils.set_widget_state import set_widget_state
from airunner.widgets.model_manager.model_manager_widget import ModelManagerWidget
from airunner.widgets.status.status_widget import StatusWidget
from airunner.windows.about.about import AboutWindow
from airunner.windows.filter_window import FilterWindow
from airunner.windows.image_window import ImageWindow
from airunner.windows.main.ai_model_mixin import AIModelMixin
from airunner.windows.main.controlnet_model_mixin import ControlnetModelMixin
from airunner.windows.main.embedding_mixin import EmbeddingMixin
from airunner.windows.main.lora_mixin import LoraMixin
from airunner.windows.main.pipeline_mixin import PipelineMixin
from airunner.windows.main.settings_mixin import SettingsMixin
from airunner.windows.main.templates.main_window_ui import Ui_MainWindow
from airunner.windows.model_merger import ModelMerger
from airunner.windows.prompt_browser.prompt_browser import PromptBrowser
from airunner.windows.settings.airunner_settings import SettingsWindow
from airunner.windows.setup_wizard.setup_wizard_window import SetupWizard
from airunner.windows.update.update_window import UpdateWindow
from airunner.windows.video import VideoPopup


class History:
    def add_event(self, *args, **kwargs):
        print("TODO")


class MainWindow(
    QMainWindow,
    MediatorMixin,
    SettingsMixin,
    LoraMixin,
    EmbeddingMixin,
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
        disable_vision_capture: bool = False,
        use_cuda: bool = True,
        ocr_enabled: bool = False,
        tts_enabled: bool = False,
        stt_enabled: bool = False,
        ai_mode: bool = True,
        tts_handler_class=None,
        restrict_os_access=None,
        defendatron=None,
        **kwargs
    ):
        self.ui = self.ui_class_()

        self.disable_sd = disable_sd
        self.disable_llm = disable_llm
        self.disable_tts = disable_tts
        self.disable_stt = disable_stt
        self.disable_vision_capture = disable_vision_capture
        self.tts_handler_class = tts_handler_class

        self.restrict_os_access = restrict_os_access
        self.defendatron = defendatron
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
        self.history = None
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
        self.intialized = False
        self.history = History()

        self.splitter_names = [
            "content_splitter",
            "splitter",
        ]
        self.logger = Logger(prefix=self.__class__.__name__)
        self.logger.debug("Starting AI Runnner")
        MediatorMixin.__init__(self)
        SettingsMixin.__init__(
            self,
            use_cuda=use_cuda,
            ocr_enabled=ocr_enabled,
            tts_enabled=tts_enabled,
            stt_enabled=stt_enabled,
            ai_mode=ai_mode,
        )
        self.do_load_llm_on_init = self.settings["llm_enabled"]

        self.update_settings()

        super().__init__(*args, **kwargs)

        self._updating_settings = True
        self.update_settings()

        LoraMixin.__init__(self)
        EmbeddingMixin.__init__(self)
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

        self.emit_signal(SignalCode.APPLICATION_MAIN_WINDOW_LOADED_SIGNAL, {
            "main_window": self
        })
        self.register(
            SignalCode.AI_MODELS_SAVE_OR_UPDATE_SIGNAL,
            self.on_ai_models_save_or_update_signal
        )
        self.register(
            SignalCode.NAVIGATE_TO_URL,
            self.on_navigate_to_url
        )

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
            try:
                result = urllib.parse.urlparse(url)
                is_url = all([result.scheme, result.netloc])
            except ValueError:
                is_url = False

            # If the input is a URL, download it
            if is_url:
                if url.lower().endswith('.pdf'):
                    # Handle PDF file
                    filepath = os.path.expanduser(self.settings["path_settings"]["pdf_path"])
                    filename = self.download_pdf(url, filepath)
                else:
                    # Handle URL
                    filepath = os.path.expanduser(self.settings["path_settings"]["webpages_path"])
                    filename = self.download_url(url, filepath)
            elif os.path.isfile(url):
                filepath = os.path.dirname(url)
                filename = os.path.basename(url)
            else:
                self.logger.error(f"Invalid URL or file path")
                return

            # Update target files to use only the file that was downloaded or navigated to
            # and update the index.
            settings = self.settings
            chatbot = current_chatbot(settings)
            chatbot["target_files"] = [os.path.join(filepath, filename)]
            settings = update_chatbot(settings, chatbot)
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
        if not key_name in self.settings["shortcut_key_settings"]:
            return False
        return self.settings["shortcut_key_settings"][key_name]["key"] == keyboard_key.value

    def key_text(self, key_name):
        if not key_name in self.settings["shortcut_key_settings"]:
            return ""
        return self.settings["shortcut_key_settings"][key_name]["text"]

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

    def on_save_stablediffusion_prompt_signal(self, _message):
        settings = self.settings
        settings["saved_prompts"].append({
            'prompt': self.settings["generator_settings"]["prompt"],
            'negative_prompt': self.settings["generator_settings"]["negative_prompt"],
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
        self.register(SignalCode.VISION_DESCRIBE_IMAGE_SIGNAL, self.on_describe_image_signal)
        self.register(SignalCode.SD_SAVE_PROMPT_SIGNAL, self.on_save_stablediffusion_prompt_signal)
        self.register(SignalCode.SD_UPDATE_SAVED_PROMPT_SIGNAL, self.on_update_saved_stablediffusion_prompt_signal)
        self.register(SignalCode.QUIT_APPLICATION, self.action_quit_triggered)
        self.register(SignalCode.SD_NSFW_CONTENT_DETECTED_SIGNAL, self.on_nsfw_content_detected_signal)
        self.register(SignalCode.VISION_CAPTURED_SIGNAL, self.on_vision_captured_signal)
        self.register(SignalCode.ENABLE_BRUSH_TOOL_SIGNAL, lambda _message: self.action_toggle_brush(True))
        self.register(SignalCode.ENABLE_ERASER_TOOL_SIGNAL, lambda _message: self.action_toggle_eraser(True))
        self.register(SignalCode.ENABLE_SELECTION_TOOL_SIGNAL, lambda _message: self.action_toggle_select(True))
        self.register(SignalCode.ENABLE_MOVE_TOOL_SIGNAL, lambda _message: self.action_toggle_active_grid_area(True))
        self.register(SignalCode.BASH_EXECUTE_SIGNAL, self.on_bash_execute_signal)
        self.register(SignalCode.WRITE_FILE, self.on_write_file_signal)
        self.register(SignalCode.APPLICATION_RESET_PATHS_SIGNAL, self.reset_paths)
        self.register(SignalCode.MODEL_STATUS_CHANGED_SIGNAL, self.on_model_status_changed_signal)
        self.register(SignalCode.TOGGLE_FULLSCREEN_SIGNAL, self.on_toggle_fullscreen_signal)
        self.register(SignalCode.TOGGLE_TTS_SIGNAL, self.on_toggle_tts)

    def on_model_status_changed_signal(self, data: dict):
        if data["status"] == ModelStatus.LOADING:
            color = StatusColors.LOADING
        elif data["status"] == ModelStatus.LOADED:
            color = StatusColors.LOADED
        elif data["status"] == ModelStatus.FAILED:
            color = StatusColors.FAILED
        else:
            color = StatusColors.UNLOADED

        styles = "QLabel { color: " + color.value + "; }"
        element_name = ""
        tool_tip = ""
        if data["model"] == ModelType.SD:
            element_name = "sd_status"
            tool_tip = "Stable Diffusion"
        elif data["model"] == ModelType.CONTROLNET:
            element_name = "controlnet_status"
            tool_tip = "Controlnet"
        elif data["model"] == ModelType.LLM:
            element_name = "llm_status"
            tool_tip = "LLM"
        elif data["model"] == ModelType.TTS:
            element_name = "tts_status"
            tool_tip = "TTS"
        elif data["model"] == ModelType.STT:
            element_name = "stt_status"
            tool_tip = "STT"
        # elif data["model"] == ModelType.OCR:
        #     element_name = "ocr_status"

        tool_tip += " model status: " + data["status"].value

        if element_name != "":
            getattr(self.ui, element_name).setStyleSheet(styles)
            getattr(self.ui, element_name).setToolTip(tool_tip)



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

    def on_application_settings_changed_signal(self, _message: dict):
        if not self._updating_settings:
            self.set_stylesheet()

    def on_vision_captured_signal(self, data: dict):
        # Create the window if it doesn't exist
        if self.image_window is None:
            self.image_window = ImageWindow()

        image = data.get("image", None)

        if image:
            # Update the image in the window
            self.image_window.update_image(image)
        else:
            self.logger.error("on_vision_captured_signal failed - no image")

    def initialize_ui(self):
        self.logger.debug("Loading ui")
        self.ui.setupUi(self)
        self.restore_state()

        self.status_widget = StatusWidget()
        self.statusBar().addPermanentWidget(self.status_widget)
        self.emit_signal(SignalCode.APPLICATION_CLEAR_STATUS_MESSAGE_SIGNAL)

        self.set_stylesheet()
        self.initialize_widget_elements()

    def initialize_widget_elements(self):
        self.ui.mode_tab_widget.tabBar().hide()
        self.ui.center_tab.tabBar().hide()
        self.ui.ocr_button.blockSignals(True)
        self.ui.tts_button.blockSignals(True)
        self.ui.v2t_button.blockSignals(True)
        self.ui.llm_button.blockSignals(True)
        self.ui.sd_toggle_button.blockSignals(True)
        self.ui.sd_toggle_button.blockSignals(True)
        self.ui.enable_controlnet.blockSignals(True)
        self.ui.controlnet_toggle_button.blockSignals(True)
        self.ui.ocr_button.setChecked(self.settings["ocr_enabled"])
        self.ui.llm_button.setChecked(self.settings["llm_enabled"])
        self.ui.tts_button.setChecked(self.settings["tts_enabled"])
        self.ui.v2t_button.setChecked(self.settings["stt_enabled"])
        self.ui.sd_toggle_button.setChecked(self.settings["sd_enabled"])
        self.ui.enable_controlnet.setChecked(self.settings["controlnet_enabled"])
        self.ui.controlnet_toggle_button.setChecked(self.settings["controlnet_enabled"])
        self.ui.ocr_button.blockSignals(False)
        self.ui.llm_button.blockSignals(False)
        self.ui.tts_button.blockSignals(False)
        self.ui.v2t_button.blockSignals(False)
        self.ui.sd_toggle_button.blockSignals(False)
        self.ui.enable_controlnet.blockSignals(False)
        self.ui.sd_toggle_button.blockSignals(False)
        self.ui.controlnet_toggle_button.blockSignals(False)
        self.initialize_tool_section_buttons()
        self.intialized = True

    def mode_tab_index_changed(self, index):
        settings = self.settings
        settings["mode"] = self.ui.mode_tab_widget.tabText(index)
        self.settings = settings

    def layer_opacity_changed(self, attr_name, value=None, widget=None):
        self.emit_signal(SignalCode.LAYER_OPACITY_CHANGED_SIGNAL, value)

    """
    Slot functions
    
    The following functions are defined in and connected to the appropriate
    signals in the corresponding ui file.
    """
    def action_quit_triggered(self, _message: dict):
        QApplication.quit()
        self.close()

    def on_nsfw_content_detected_signal(self, _message: dict):
        # display message in status
        self.emit_signal(
            SignalCode.APPLICATION_STATUS_ERROR_SIGNAL,
            NSFW_CONTENT_DETECTED_MESSAGE
        )

    def closeEvent(self, event) -> None:
        self.logger.debug("Quitting")
        self.save_state()
        self.save_state()
        super().closeEvent(event)

    @Slot()
    def action_new_document_triggered(self):
        self.new_document()
        self.emit_signal(SignalCode.CANVAS_CLEAR)

    @Slot()
    def action_undo_triggered(self):
        self.undo()

    @Slot()
    def action_redo_triggered(self):
        self.redo()

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
        ModelManagerWidget()

    @Slot()
    def action_show_controlnet(self):
        self.show_section(WindowSection.CONTROLNET)

    @Slot()
    def action_show_embeddings(self):
        self.show_section(WindowSection.EMBEDDINGS)

    @Slot()
    def action_show_lora(self):
        self.show_section(WindowSection.LORA)

    @Slot()
    def action_show_pen(self):
        self.show_section(WindowSection.PEN)

    @Slot()
    def action_show_active_grid(self):
        self.show_section(WindowSection.ACTIVE_GRID)

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
    def action_show_videos_path(self):
        self.show_settings_path("video_path")

    @Slot()
    def action_show_model_path_txt2img(self):
        self.show_settings_path("txt2img_model_path")

    @Slot()
    def action_show_model_path_depth2img(self):
        self.show_settings_path("depth2img_model_path")

    @Slot()
    def action_show_model_path_pix2pix(self):
        self.show_settings_path("pix2pix_model_path")

    @Slot()
    def action_show_model_path_inpaint(self):
        self.show_settings_path("inpaint_model_path")

    @Slot()
    def action_show_model_path_upscale(self):
        self.show_settings_path("upscale_model_path")

    @Slot()
    def action_show_model_path_txt2vid(self):
        self.show_settings_path("txt2vid_model_path")

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
        if not self.intialized:
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
        AboutWindow()

    @Slot()
    def action_show_model_merger_window(self):
        ModelMerger()

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
    def ocr_button_toggled(self, val):
        new_settings = self.settings
        new_settings["ocr_enabled"] = val
        self.settings = new_settings

    @Slot(bool)
    def v2t_button_toggled(self, val):
        new_settings = self.settings
        new_settings["stt_enabled"] = val
        self.settings = new_settings
        if not val:
            self.emit_signal(SignalCode.STT_STOP_CAPTURE_SIGNAL)
        else:
            self.emit_signal(SignalCode.STT_START_CAPTURE_SIGNAL)

    quitting = False

    def save_state(self):
        if self.quitting:
            return
        self.quitting = True
        self.logger.debug("Saving window state")
        settings = self.settings
        settings["window_settings"] = {
            'mode_tab_widget_index': self.ui.mode_tab_widget.currentIndex(),
            'tool_tab_widget_index': self.ui.tool_tab_widget.currentIndex(),
            'center_tab_index': self.ui.center_tab.currentIndex(),
            'is_maximized': self.isMaximized(),
            'is_fullscreen': self.isFullScreen(),
        }

        # Store splitter settings in application settings
        for splitter in self.splitter_names:
            settings["window_settings"][splitter] = getattr(self.ui, splitter).saveState()

        settings["window_settings"]["chat_prompt_splitter"] = self.ui.generator_widget.ui.chat_prompt_widget.ui.chat_prompt_splitter.saveState()
        settings["window_settings"]["canvas_splitter"] = self.ui.canvas_widget_2.ui.canvas_splitter.saveState()
        settings["window_settings"]["canvas_side_splitter"] = self.ui.canvas_widget_2.ui.canvas_side_splitter.saveState()
        settings["window_settings"][
            "canvas_side_splitter_2"] = self.ui.canvas_widget_2.ui.canvas_side_splitter_2.saveState()

        self.settings = settings
        self.save_settings()

    def restore_state(self):
        self.logger.debug("Restoring state")
        window_settings = self.settings["window_settings"]

        if window_settings["is_maximized"]:
            self.showMaximized()
        elif window_settings["is_fullscreen"]:
            self.showFullScreen()
        else:
            self.showNormal()

        self.ui.mode_tab_widget.setCurrentIndex(window_settings["mode_tab_widget_index"])
        self.ui.tool_tab_widget.setCurrentIndex(window_settings["tool_tab_widget_index"])
        self.ui.center_tab.setCurrentIndex(window_settings["center_tab_index"])
        self.ui.ai_button.setChecked(self.settings["ai_mode"])
        self.set_button_checked("toggle_grid", self.settings["grid_settings"]["show_grid"], False)

        # Restore splitters
        for splitter in self.splitter_names:
            try:
                getattr(self.ui, splitter).restoreState(window_settings[splitter])
            except TypeError:
                self.logger.warning(f"failed to restore {splitter} splitter")
            except KeyError:
                self.logger.warning(f"{splitter} missing in window_settings")

        if "chat_prompt_splitter" in window_settings:
            self.ui.generator_widget.ui.chat_prompt_widget.ui.chat_prompt_splitter.restoreState(
                window_settings["chat_prompt_splitter"]
            )

        if window_settings["canvas_splitter"] is not None:
            self.ui.canvas_widget_2.ui.canvas_splitter.restoreState(window_settings["canvas_splitter"])

        if window_settings["canvas_side_splitter"] is not None:
            self.ui.canvas_widget_2.ui.canvas_side_splitter.restoreState(window_settings["canvas_side_splitter"])

        if window_settings["canvas_side_splitter_2"] is not None:
            self.ui.canvas_widget_2.ui.canvas_side_splitter_2.restoreState(window_settings["canvas_side_splitter"])

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
        if self.settings["show_nsfw_warning"]:
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
            self.ui.actionSafety_Checker.setChecked(self.settings["nsfw_filter"])
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
    
    def image_generation_toggled(self):
        settings = self.settings
        settings["mode"] = Mode.IMAGE.value
        self.settings = settings
        self.activate_image_generation_section()

    def language_processing_toggled(self):
        settings = self.settings
        settings["mode"] = Mode.LANGUAGE_PROCESSOR.value
        self.settings = settings
        self.activate_language_processing_section()
    ###### End window handlers ######

    def show_update_message(self):
        self.emit_signal(
            SignalCode.APPLICATION_STATUS_INFO_SIGNAL,
            f"New version available: {self.latest_version}"
        )

    def show_update_popup(self):
        self.update_popup = UpdateWindow()

    def refresh_styles(self):
        self.set_stylesheet()

    def set_stylesheet(self, ui=None):
        """
        Sets the stylesheet for the application based on the current theme
        """
        if (
            self._override_system_theme is not self.settings["override_system_theme"] or
            self._dark_mode_enabled is not self.settings["dark_mode_enabled"]
        ):
            ui = ui or self
            self._override_system_theme = self.settings["override_system_theme"]
            self._dark_mode_enabled = self.settings["dark_mode_enabled"]

            if self._override_system_theme:
                self.logger.debug("Setting stylesheet")

                stylesheet = FileSystemOperations().read_stylesheet()
                ui.setStyleSheet(stylesheet)
            else:
                self.logger.debug("Using system theme")
                ui.setStyleSheet("")

    def show_setup_wizard(self):
        wizard = SetupWizard()
        wizard.exec()

    def showEvent(self, event):
        super().showEvent(event)
        # self.automatic_filter_manager = AutomaticFilterManager()
        # self.automatic_filter_manager.register_filter(PixelFilter, base_size=256)

        # print("*"*1000)
        # for filename, modules in self.restrict_os_access.logging_importer.imported_files.items():
        #     print(filename)
        #     for module, submodules in modules.items():
        #         print(f"    {module}")
        #         for submodule in submodules:
        #             print(f"        {submodule}")

        self.initialize_window()
        self.initialize_default_buttons()
        self.initialize_filter_actions()
        self.intialized = True
        for icon_data in self.icons:
            self.set_icons(
                icon_data[0],
                icon_data[1],
                "dark" if self.settings["dark_mode_enabled"] else "light"
            )

        # call initialize_worker_manager after 100ms
        QTimer.singleShot(100, self.initialize_worker_manager)

    def initialize_worker_manager(self):
        from airunner.worker_manager import WorkerManager
        if self.tts_handler_class is None:
            from airunner.aihandler.tts.espeak_tts_handler import EspeakTTSHandler
            self.tts_handler_class = EspeakTTSHandler
        self.worker_manager = WorkerManager(
            disable_sd=self.disable_sd,
            disable_llm=self.disable_llm,
            disable_tts=self.disable_tts,
            disable_stt=self.disable_stt,
            disable_vision_capture=self.disable_vision_capture,
            do_load_llm_on_init=self.do_load_llm_on_init,
            tts_handler_class=self.tts_handler_class,
            agent_class=BaseAgent
        )

    def initialize_filter_actions(self):
        # add more filters:
        for filter_name, filter_data in self.settings["image_filters"].items():

            action = self.ui.menuFilters.addAction(filter_data["display_name"])
            action.triggered.connect(partial(self.display_filter_window, filter_data["name"]))

    def display_filter_window(self, filter_name):
        FilterWindow(filter_name)

    def initialize_default_buttons(self):
        show_grid = self.settings["grid_settings"]["show_grid"]
        current_tool = self.settings["current_tool"]
        ai_mode = self.settings["ai_mode"]

        set_widget_state(self.ui.toggle_active_grid_area_button, current_tool is CanvasToolName.ACTIVE_GRID_AREA)
        set_widget_state(self.ui.toggle_brush_button, current_tool is CanvasToolName.BRUSH)
        set_widget_state(self.ui.toggle_eraser_button, current_tool is CanvasToolName.ERASER)
        set_widget_state(self.ui.toggle_grid_button, show_grid is True)
        set_widget_state(self.ui.ai_button, ai_mode)

        self.ui.actionSafety_Checker.blockSignals(True)
        self.ui.actionSafety_Checker.setChecked(self.settings["nsfw_filter"])
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

    def show_section(self, section: WindowSection):
        section_lists = {
            "right": [
                self.ui.tool_tab_widget.tabText(i) for i in range(self.ui.tool_tab_widget.count())
            ]
        }
        for k, v in section_lists.items():
            if section.value in v:
                self.ui.tool_tab_widget.setCurrentIndex(v.index(section.value))
                break

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

    def initialize_window(self):
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

    def video_handler(self, data):
        filename = data["video_filename"]
        VideoPopup(file_path=filename)

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
    
    def activate_image_generation_section(self):
        self.ui.mode_tab_widget.setCurrentIndex(0)

    def activate_language_processing_section(self):
        self.ui.mode_tab_widget.setCurrentIndex(1)

    def initialize_tool_section_buttons(self):
        pass
    
    def redraw(self):
        self.set_stylesheet()

        # Update the window
        self.update()

    def action_center_clicked(self):
        print("center clicked")

    def action_reset_settings(self):
        self.emit_signal(SignalCode.APPLICATION_RESET_SETTINGS_SIGNAL)

    def action_toggle_controlnet(self, val):
        settings = self.settings
        settings["controlnet_enabled"] = val
        self.settings = settings

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
    def action_unload_llm(self):
        self.emit_signal(SignalCode.LLM_UNLOAD_SIGNAL)

    @Slot()
    def action_unload_sd(self):
        self.emit_signal(SignalCode.SD_UNLOAD_SIGNAL)

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
            self.emit_signal(SignalCode.SD_UNLOAD_SIGNAL)

    @Slot(bool)
    def action_controlnet_toggled(self, val: bool):
        settings = self.settings
        settings["controlnet_enabled"] = val
        self.settings = settings
        if val:
            self.emit_signal(SignalCode.CONTROLNET_LOAD_SIGNAL)
        else:
            self.emit_signal(SignalCode.CONTROLNET_UNLOAD_SIGNAL)
