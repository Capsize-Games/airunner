import os
import platform
import subprocess
import sys
import webbrowser
from functools import partial

from PyQt6 import QtGui
from PyQt6 import uic, QtCore
from PyQt6.QtCore import pyqtSlot, Qt, pyqtSignal
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QApplication, QFileDialog, QMainWindow

from airunner.aihandler.logger import Logger
from airunner.aihandler.settings import LOG_LEVEL
from airunner.enums import Mode, SignalCode, ServiceCode
from airunner.filters.windows.filter_base import FilterBase
from airunner.mediator_mixin import MediatorMixin
from airunner.resources_dark_rc import *
from airunner.service_locator import ServiceLocator
from airunner.settings import BASE_PATH
from airunner.utils import get_version, auto_export_image, default_hf_cache_dir, open_file_path
from airunner.widgets.status.status_widget import StatusWidget
from airunner.windows.about.about import AboutWindow
from airunner.windows.main.ai_model_mixin import AIModelMixin
from airunner.windows.main.controlnet_model_mixin import ControlnetModelMixin
from airunner.windows.main.embedding_mixin import EmbeddingMixin
from airunner.windows.main.image_filter_mixin import ImageFilterMixin
from airunner.windows.main.layer_mixin import LayerMixin
from airunner.windows.main.lora_mixin import LoraMixin
from airunner.windows.main.pipeline_mixin import PipelineMixin
from airunner.windows.main.settings_mixin import SettingsMixin
from airunner.windows.main.templates.main_window_ui import Ui_MainWindow
from airunner.windows.model_merger import ModelMerger
from airunner.windows.prompt_browser.prompt_browser import PromptBrowser
from airunner.windows.settings.airunner_settings import SettingsWindow
from airunner.windows.update.update_window import UpdateWindow
from airunner.windows.video import VideoPopup
from airunner.worker_manager import WorkerManager


class MainWindow(
    QMainWindow,
    MediatorMixin,
    SettingsMixin,
    LayerMixin,
    LoraMixin,
    EmbeddingMixin,
    PipelineMixin,
    ControlnetModelMixin,
    AIModelMixin,
    ImageFilterMixin,
):
    # signals
    show_grid_toggled = pyqtSignal(bool)
    cell_size_changed_signal = pyqtSignal(int)
    line_width_changed_signal = pyqtSignal(int)
    line_color_changed_signal = pyqtSignal(str)
    canvas_color_changed_signal = pyqtSignal(str)
    snap_to_grid_changed_signal = pyqtSignal(bool)

    token_signal = pyqtSignal(str)
    api = None
    input_event_manager = None
    current_filter = None
    tqdm_callback_triggered = False
    _document_name = "Untitled"
    is_saved = False
    action = "txt2img"
    progress_bar_started = False
    window = None
    history = None
    canvas = None
    models = None
    client = None
    _version = None
    _latest_version = None
    data = None  # this is set in the generator_mixin image_handler function and used for deterministic generation
    status_error_color = "#ff0000"
    status_normal_color_light = "#000000"
    status_normal_color_dark = "#ffffff"
    is_started = False
    _themes = None
    button_clicked_signal = pyqtSignal(dict)
    status_widget = None
    header_widget_spacer = None
    deterministic_window = None

    class History:
        def add_event(self, *args, **kwargs):
            print("TODO")
    history = History()

    image_generated = pyqtSignal(bool)
    controlnet_image_generated = pyqtSignal(bool)
    generator_tab_changed_signal = pyqtSignal()
    tab_section_changed_signal = pyqtSignal()
    load_image = pyqtSignal(str)
    load_image_object = pyqtSignal(object)

    generator = None
    _generator = None
    _generator_settings = None
    listening = False
    loaded = pyqtSignal()
    window_opened = pyqtSignal()

    def handle_key_press(self, key):
        super().keyPressEvent(key)

        if self.key_matches("generate_image_key", key.key()):
            print("generate_image_key PRESSED")
    
    def key_matches(self, key_name, keyboard_key):
        if not key_name in self.settings["shortcut_key_settings"]:
            return False
        return self.settings["shortcut_key_settings"][key_name]["key"] == keyboard_key
    
    def key_text(self, key_name):
        if not key_name in self.settings["shortcut_key_settings"]:
            return ""
        return self.settings["shortcut_key_settings"][key_name]["text"]
    
    def add_preset(self, name, thumnail):
        settings = self.settings
        settings["presets"].append(dict(
            name=name,
            thumnail=thumnail,
        ))
        self.settings = settings
    
    def on_load_saved_stablediffuion_prompt_signal(self, index):
        try:
            saved_prompt = self.settings["saved_prompts"][index]
        except KeyError:
            self.logger.error(f"Unable to load prompt at index {index}")
            saved_prompt = None
        
        if saved_prompt:
            settings = self.settings
            settings["generator_settings"]["prompt"] = saved_prompt["prompt"]
            settings["generator_settings"]["negative_prompt"] = saved_prompt["negative_prompt"]
            self.settings = settings

    def on_update_saved_stablediffusion_prompt_signal(self, options):
        index, prompt, negative_prompt = options
        settings = self.settings
        try:
            settings["saved_prompts"][index] = dict(
                prompt=prompt,
                negative_prompt=negative_prompt,
            )
        except KeyError:
            self.logger.error(f"Unable to update prompt at index {index}")
        self.settings = settings

    def on_save_stablediffusion_prompt_signal(self):
        settings = self.settings
        settings["saved_prompts"].append(dict(
            prompt=self.settings["generator_settings"]["prompt"],
            negative_prompt=self.settings["generator_settings"]["negative_prompt"],
        ))
        self.settings = settings

    def set_path_settings(self, key, val):
        settings = self.settings
        settings["path_settings"][key] = val
        self.settings = settings
    #### END GENERATOR SETTINGS ####

    @property
    def standard_image_panel(self):
        return self.ui.standard_image_widget

    @property
    def generator_tab_widget(self):
        return self.ui.generator_widget
    
    @property
    def canvas_widget(self):
        return self.standard_image_panel.canvas_widget

    @property
    def toolbar_widget(self):
        return self.ui.toolbar_widget

    @property
    def prompt_builder(self):
        return self.ui.prompt_builder

    @property
    def footer_widget(self):
        return self.ui.footer_widget

    @property
    def generator_type(self):
        """
        Returns stablediffusion
        :return: string
        """
        return self._generator_type

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
        # name = f"{self._document_name}{'*' if self.canvas and self.canvas_widget.is_dirty else ''}"
        # return f"{name} - {self.version}"
        return "Untitled"

    @property
    def current_canvas(self):
        return self.standard_image_panel

    def on_describe_image_signal(self, data):
        image = data["image"]
        callback = data["callback"]
        self.generator_tab_widget.ui.ai_tab_widget.describe_image(
            image=image, 
            callback=callback
        )
    
    @pyqtSlot()
    def handle_generate(self):
        #self.prompt_builder.inject_prompt()
        pass

    @pyqtSlot(dict)
    def handle_button_clicked(self, kwargs):
        action = kwargs.get("action", "")
        if action == "toggle_tool":
            self.toggle_tool(kwargs["tool"])

    @pyqtSlot(str, object)
    def handle_changed_signal(self, key, value):
        print("main_window: handle_changed_signal", key, value)
        if key == "grid_settings.cell_size":
            self.set_size_form_element_step_values()
        elif key == "settings.line_color":
            self.canvas_widget.update_grid_pen()
        # elif key == "use_prompt_builder_checkbox":
        #     self.generator_tab_widget.toggle_all_prompt_builder_checkboxes(value)
        elif key == "models":
            self.model_manager.models_changed(key, value)

    def show_layers(self):
        self.emit(SignalCode.LAYERS_SHOW_SIGNAL)

    def on_controlnet_image_generated_signal(self, response: dict):
        self.handle_controlnet_image_generated(response)

    def __init__(self, *args, **kwargs):
        self.ui = Ui_MainWindow()
        self.update_popup = None
        self.controlnet_image = None
        self._document_path = None
        self.prompt = None
        self.negative_prompt = None
        self.image_path = None
        self.set_log_levels()
        self.logger = Logger(prefix=self.__class__.__name__)
        self.logger.info("Starting AI Runnner")
        MediatorMixin.__init__(self)
        SettingsMixin.__init__(self)
        super().__init__(*args, **kwargs)
        LoraMixin.__init__(self)
        LayerMixin.__init__(self)
        EmbeddingMixin.__init__(self)
        PipelineMixin.__init__(self)
        ControlnetModelMixin.__init__(self)
        AIModelMixin.__init__(self)
        ImageFilterMixin.__init__(self)
        self.register_services()
        self.update_settings()
        self.create_airunner_paths()
        self.register_signals()
        self.initialize_ui()
        self.worker_manager = WorkerManager()
        self.is_started = True
        self.emit(SignalCode.APPLICATION_MAIN_WINDOW_LOADED_SIGNAL)

    def register_services(self):
        self.logger.info("Registering services")
        ServiceLocator.register(ServiceCode.LAYER_WIDGET, lambda: self.ui.layer_widget)
        ServiceLocator.register(ServiceCode.GET_LLM_WIDGET, lambda: self.ui.llm_widget)
        ServiceLocator.register(ServiceCode.DISPLAY_IMPORT_IMAGE_DIALOG, self.display_import_image_dialog)
        ServiceLocator.register(ServiceCode.GET_SETTINGS_VALUE, self.get_settings_value)
        ServiceLocator.register(ServiceCode.GET_CALLBACK_FOR_SLIDER, self.get_callback_for_slider)

    def register_signals(self):
        # on window resize:
        # self.windowStateChanged.connect(self.on_state_changed)
        self.logger.info("Connecting signals")
        self.register(SignalCode.VISION_DESCRIBE_IMAGE_SIGNAL, self.on_describe_image_signal)
        self.register(SignalCode.SD_SAVE_PROMPT_SIGNAL, self.on_save_stablediffusion_prompt_signal)
        self.register(SignalCode.SD_LOAD_PROMPT_SIGNAL, self.on_load_saved_stablediffuion_prompt_signal)
        self.register(SignalCode.SD_UPDATE_SAVED_PROMPT_SIGNAL, self.on_update_saved_stablediffusion_prompt_signal)

    def initialize_ui(self):
        self.logger.info("Loading ui")
        self.ui.setupUi(self)

        # self.ui.layer_widget.initialize()

        self.status_widget = StatusWidget()
        self.statusBar().addPermanentWidget(self.status_widget)
        self.emit(SignalCode.APPLICATION_CLEAR_STATUS_MESSAGE_SIGNAL)

        self.set_stylesheet()

        self.ui.mode_tab_widget.tabBar().hide()
        self.ui.center_tab.tabBar().hide()
        self.ui.ocr_button.blockSignals(True)
        self.ui.tts_button.blockSignals(True)
        self.ui.v2t_button.blockSignals(True)
        self.ui.ocr_button.setChecked(self.settings["ocr_enabled"])
        self.ui.tts_button.setChecked(self.settings["tts_enabled"])
        self.ui.v2t_button.setChecked(self.settings["stt_enabled"])
        self.ui.ocr_button.blockSignals(False)
        self.ui.tts_button.blockSignals(False)
        self.ui.v2t_button.blockSignals(False)
        self.logger.info("Setting buttons")
        self.set_all_section_buttons()
        self.initialize_tool_section_buttons()

        self.restore_state()
    
    def do_listen(self):
        if not self.listening:
            self.listening = True
            self.worker_manager.do_listen()
    
    def create_airunner_paths(self):
        for k, path in self.settings["path_settings"].items():
            if not os.path.exists(path):
                print("cerating path", path)
                os.makedirs(path)
    
    def mode_tab_index_changed(self, index):
        settings = self.settings
        settings["mode"] = self.ui.mode_tab_widget.tabText(index)
        self.settings = settings

    def layer_opacity_changed(self, attr_name, value=None, widget=None):
        print("layer_opacity_changed", attr_name, value)
        self.ui.layer_widget.set_layer_opacity(value)

    def quick_export(self):
        if os.path.isdir(self.image_path) is False:
            self.choose_image_export_path()
        if os.path.isdir(self.image_path) is False:
            return
        path, image = auto_export_image(
            self.base_path, 
            self.settings["path_settings"]["image_path"],
            self.settings["image_export_type"],
            self.ui.layer_widget.current_layer.image_data.image, 
            seed=self.seed
        )
        if path is not None:
            self.emit(
                SignalCode.STATUS_INFO_SIGNAL,
                f"Image exported to {path}"
            )

    """
    Slot functions
    
    The following functions are defined in and connected to the appropriate
    signals in the corresponding ui file.
    """
    def action_new_document_triggered(self):
        self.new_document()
        self.emit(SignalCode.CANVAS_CLEAR)

    def action_quick_export_image_triggered(self):
        self.quick_export()

    def action_export_image_triggered(self):
        self.export_image()

    def action_import_image_triggered(self):
        self.import_image()

    def action_quit_triggered(self):
        QApplication.quit()
        self.close()

    def closeEvent(self, event) -> None:
        self.logger.info("Quitting")
        self.worker_manager.stop()
        self.save_state()
        self.worker_manager.stop()
        self.save_state()
        super().closeEvent(event)

    def action_undo_triggered(self):
        self.undo()

    def action_redo_triggered(self):
        self.redo()

    def action_paste_image_triggered(self):
        if self.settings["mode"] == Mode.IMAGE.value:
            self.canvas_widget.paste_image_from_clipboard()

    def action_copy_image_triggered(self):
        if self.settings["mode"] == Mode.IMAGE.value:
            self.canvas_widget.copy_image(ServiceLocator.get(ServiceCode.CURRENT_ACTIVE_IMAGE)())

    def action_cut_image_triggered(self):
        if self.settings["mode"] == Mode.IMAGE.value:
            self.canvas_widget.cut_image()

    def action_rotate_90_clockwise_triggered(self):
        if self.settings["mode"] == Mode.IMAGE.value:
            self.canvas_widget.rotate_90_clockwise()

    def action_rotate_90_counterclockwise_triggered(self):
        if self.settings["mode"] == Mode.IMAGE.value:
            self.canvas_widget.rotate_90_counterclockwise()

    def action_show_prompt_browser_triggered(self):
        self.show_prompt_browser()

    def action_clear_all_prompts_triggered(self):
        self.clear_all_prompts()

    def action_show_deterministic_batches(self):
        self.show_section("Deterministic Batches")

    def action_show_standard_batches(self):
        self.show_section("Standard Batches")

    def action_show_model_manager(self):
        self.activate_model_manager_section()

    def action_show_controlnet(self):
        self.show_section("controlnet")

    def action_show_embeddings(self):
        self.show_section("Embeddings")

    def action_show_lora(self):
        self.show_section("LoRA")

    def action_show_pen(self):
        self.show_section("Pen")

    def action_show_active_grid(self):
        self.show_section("Active Grid")

    def action_show_stablediffusion(self):
        self.activate_image_generation_section()

    def action_triggered_browse_ai_runner_path(self):
        path = self.base_path
        if path == "":
            path = BASE_PATH
        self.show_path(path)

    def action_show_hf_cache_manager(self):
        self.show_settings_path("hf_cache_path", default_hf_cache_dir())

    def action_show_images_path(self):
        self.show_settings_path("image_path")
    
    def action_show_videos_path(self):
        self.show_settings_path("video_path")
    
    def action_show_model_path_txt2img(self):
        self.show_settings_path("txt2img_model_path")
    
    def action_show_model_path_depth2img(self):
        self.show_settings_path("depth2img_model_path")
    
    def action_show_model_path_pix2pix(self):
        self.show_settings_path("pix2pix_model_path")
    
    def action_show_model_path_inpaint(self):
        self.show_settings_path("inpaint_model_path")
    
    def action_show_model_path_upscale(self):
        self.show_settings_path("upscale_model_path")
    
    def action_show_model_path_txt2vid(self):
        self.show_settings_path("txt2vid_model_path")
    
    def action_show_model_path_embeddings(self):
        self.show_settings_path("embeddings_model_path")
    
    def action_show_model_path_lora(self):
        self.show_settings_path("lora_model_path")

    def action_show_llm(self):
        pass

    def show_settings_path(self, name, default_path=None):
        path = self.settings["path_settings"][name]
        self.show_path(default_path if default_path and path == "" else path)

    def show_path(self, path):
        if not os.path.isdir(path):
            return
        if platform.system() == "Windows":
            subprocess.Popen(["explorer", os.path.realpath(path)])
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", os.path.realpath(path)])
        else:
            subprocess.Popen(["xdg-open", os.path.realpath(path)])

    def set_icons(self, icon_name, widget_name, theme):
        icon = QtGui.QIcon()
        icon.addPixmap(
            QtGui.QPixmap(f":/icons/{theme}/{icon_name}.svg"), 
            QtGui.QIcon.Mode.Normal, 
            QtGui.QIcon.State.Off)
        getattr(self.ui, widget_name).setIcon(icon)
        self.update()

    def action_show_about_window(self):
        AboutWindow()

    def action_show_model_merger_window(self):
        ModelMerger()

    def action_show_settings(self):
        SettingsWindow()

    def action_open_vulnerability_report(self):
        webbrowser.open("https://github.com/Capsize-Games/airunner/security/advisories/new")

    def action_open_bug_report(self):
        webbrowser.open("https://github.com/Capsize-Games/airunner/issues/new?assignees=&labels=&template=bug_report.md&title=")

    def action_open_discord(self):
        webbrowser.open("https://discord.gg/ukcgjEpc5f")

    """
    End slot functions
    """

    def set_size_increment_levels(self):
        size = self.settings["grid_settings"]["cell_size"]
        self.ui.width_slider_widget.slider_single_step = size
        self.ui.width_slider_widget.slider_tick_interval = size

        self.ui.height_slider_widget.slider_single_step = size
        self.ui.height_slider_widget.slider_tick_interval = size

        self.canvas_widget.update()

    def toggle_nsfw_filter(self):
        # self.canvas_widget.update()
        self.set_nsfw_filter_tooltip()

    def set_nsfw_filter_tooltip(self):
        self.ui.safety_checker_button.setToolTip(
            f"Click to {'enable' if not self.settings['nsfw_filter'] else 'disable'} NSFW filter"
        )

    def dragmode_pressed(self):
        # self.canvas_widget.is_canvas_drag_mode = True
        pass

    def dragmode_released(self):
        # self.canvas_widget.is_canvas_drag_mode = False
        pass

    def shift_pressed(self):
        # self.canvas_widget.shift_is_pressed = True
        pass

    def shift_released(self):
        # self.canvas_widget.shift_is_pressed = False
        pass

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    @pyqtSlot(bool)
    def tts_button_toggled(self, val):
        new_settings = self.settings
        new_settings["tts_enabled"] = val
        self.settings = new_settings

    @pyqtSlot(bool)
    def ocr_button_toggled(self, val):
        new_settings = self.settings
        new_settings["ocr_enabled"] = val
        self.settings = new_settings

    @pyqtSlot(bool)
    def v2t_button_toggled(self, val):
        new_settings = self.settings
        new_settings["stt_enabled"] = val
        self.settings = new_settings
    
    def save_state(self):
        self.logger.info("Saving window state")
        settings = self.settings
        settings["window_settings"] = dict(
            main_splitter=self.ui.main_splitter.saveState(),
            content_splitter=self.ui.content_splitter.saveState(),
            center_splitter=self.ui.center_splitter.saveState(),
            canvas_splitter=self.ui.canvas_splitter.saveState(),
            splitter=self.ui.splitter.saveState(),
            mode_tab_widget_index=self.ui.mode_tab_widget.currentIndex(),
            tool_tab_widget_index=self.ui.tool_tab_widget.currentIndex(),
            center_tab_index=self.ui.center_tab.currentIndex(),
            generator_tab_index=self.ui.standard_image_widget.ui.tabWidget.currentIndex(),
            is_maximized=self.isMaximized(),
            is_fullscreen=self.isFullScreen(),
        )
        self.settings = settings
    
    def restore_state(self):
        self.logger.info("Restoring state")
        window_settings = self.settings["window_settings"]

        if self.settings["is_maximized"]:
            self.showMaximized()
        elif window_settings["is_fullscreen"]:
            self.showFullScreen()
        else:
            self.showNormal()

        if window_settings["main_splitter"]:
            self.ui.main_splitter.restoreState(window_settings["main_splitter"])

        if window_settings["content_splitter"]:
            self.ui.content_splitter.restoreState(window_settings["content_splitter"])

        if window_settings["center_splitter"]:
            self.ui.center_splitter.restoreState(window_settings["center_splitter"])

        if window_settings["canvas_splitter"]:
            self.ui.canvas_splitter.restoreState(window_settings["canvas_splitter"])

        if window_settings["splitter"]:
            self.ui.splitter.restoreState(window_settings["splitter"])

        self.ui.mode_tab_widget.setCurrentIndex(window_settings["mode_tab_widget_index"])
        self.ui.tool_tab_widget.setCurrentIndex(window_settings["tool_tab_widget_index"])
        self.ui.center_tab.setCurrentIndex(window_settings["center_tab_index"])
        self.ui.standard_image_widget.ui.tabWidget.setCurrentIndex(window_settings["generator_tab_index"])
        self.ui.ai_button.setChecked(self.settings["ai_mode"])
        self.set_button_checked("toggle_grid", self.settings["grid_settings"]["show_grid"], False)

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
    
    def action_toggle_brush(self, active):
        if active:
            self.toggle_tool("brush")
            self.ui.toggle_active_grid_area_button.setChecked(False)
            self.ui.toggle_eraser_button.setChecked(False)

    def action_toggle_eraser(self, active):
        if active:
            self.toggle_tool("eraser")
            self.ui.toggle_active_grid_area_button.setChecked(False)
            self.ui.toggle_brush_button.setChecked(False)

    def action_toggle_active_grid_area(self, active):
        if active:
            self.toggle_tool("active_grid_area")
            self.ui.toggle_brush_button.setChecked(False)
            self.ui.toggle_eraser_button.setChecked(False)

    def action_toggle_nsfw_filter_triggered(self, val):
        settings = self.settings
        settings["nsfw_filter"] = val
        self.settings = settings
        self.toggle_nsfw_filter()

    def action_toggle_darkmode(self):
        self.set_stylesheet()
    
    def image_generation_toggled(self):
        settings = self.settings
        settings["mode"] = Mode.IMAGE.value
        self.settings = settings
        self.activate_image_generation_section()
        self.set_all_section_buttons()

    def language_processing_toggled(self):
        settings = self.settings
        settings["mode"] = Mode.LANGUAGE_PROCESSOR.value
        self.settings = settings
        self.activate_language_processing_section()
        self.set_all_section_buttons()
    
    def model_manager_toggled(self, val):
        if not val:
            self.image_generators_toggled()
        else:
            settings = self.settings
            settings["mode"] = Mode.MODEL_MANAGER.value
            self.settings = settings
            self.activate_model_manager_section()
            self.set_all_section_buttons()
    ###### End window handlers ######

    def show_update_message(self):
        self.emit(
            SignalCode.STATUS_INFO_SIGNAL,
            f"New version available: {self.latest_version}"
        )

    def show_update_popup(self):
        self.update_popup = UpdateWindow()

    def on_state_changed(self, state):
        if state == Qt.ApplicationState.ApplicationActive:
            self.canvas_widget.pos_x = int(self.x() / 4)
            self.canvas_widget.pos_y = int(self.y() / 2)
            self.canvas_widget.update()

    def refresh_styles(self):
        self.set_stylesheet()

    def set_stylesheet(self):
        """
        Sets the stylesheet for the application based on the current theme
        """
        self.logger.info("Setting stylesheet")
        theme_name = "dark_theme" if self.settings["dark_mode_enabled"] else "light_theme"
        here = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(here, "..", "..", "styles", theme_name, "styles.qss"), "r") as f:
            stylesheet = f.read()
        self.setStyleSheet(stylesheet)
        for icon_data in [
            ("tech-icon", "model_manager_button"),
            ("pencil-icon", "toggle_brush_button"),
            ("eraser-icon", "toggle_eraser_button"),
            ("frame-grid-icon", "toggle_grid_button"),
            ("circle-center-icon", "focus_button"),
            ("artificial-intelligence-ai-chip-icon", "ai_button"),
            ("setting-line-icon", "settings_button"),
            ("object-selected-icon", "toggle_active_grid_area_button"),
        ]:
            self.set_icons(icon_data[0], icon_data[1], "dark" if self.settings["dark_mode_enabled"] else "light")

    def showEvent(self, event):
        super().showEvent(event)
        # self.automatic_filter_manager = AutomaticFilterManager()
        # self.automatic_filter_manager.register_filter(PixelFilter, base_size=256)

        self.initialize_window()
        self.register(SignalCode.CONTROLNET_IMAGE_GENERATED_SIGNAL, self.on_controlnet_image_generated_signal)
        self.initialize_mixins()
        # self.header_widget.initialize()
        # self.header_widget.set_size_increment_levels()
        self.initialize_default_buttons()
        try:
            self.prompt_builder.process_prompt()
        except AttributeError:
            pass
        self.initialize_filter_actions()

    def initialize_filter_actions(self):
        # add more filters:
        for filter in self.image_filter_get_all():
            action = self.ui.menuFilters.addAction(filter["display_name"])
            action.triggered.connect(partial(self.display_filter_window, filter["name"]))

    def display_filter_window(self, filter_name):
        FilterBase(self, filter_name).show()

    def initialize_default_buttons(self):
        show_grid = self.settings["grid_settings"]["show_grid"]
        self.ui.toggle_active_grid_area_button.blockSignals(True)
        self.ui.toggle_brush_button.blockSignals(True)
        self.ui.toggle_eraser_button.blockSignals(True)
        self.ui.toggle_grid_button.blockSignals(True)
        self.ui.ai_button.blockSignals(True)
        self.ui.toggle_active_grid_area_button.setChecked(self.settings["current_tool"] == "active_grid_area")
        self.ui.toggle_brush_button.setChecked(self.settings["current_tool"] == "brush")
        self.ui.toggle_eraser_button.setChecked(self.settings["current_tool"] == "eraser")
        self.ui.toggle_grid_button.setChecked(show_grid is True)
        self.ui.toggle_active_grid_area_button.blockSignals(False)
        self.ui.toggle_brush_button.blockSignals(False)
        self.ui.toggle_eraser_button.blockSignals(False)
        self.ui.toggle_grid_button.blockSignals(False)
        self.ui.ai_button.blockSignals(False)

    def toggle_tool(self, tool):
        settings = self.settings
        settings["current_tool"] = tool
        self.settings = settings

    def initialize_mixins(self):
        #self.canvas = Canvas()
        pass

    def show_section(self, section):
        section_lists = {
            "center": [self.ui.center_tab.tabText(i) for i in range(self.ui.center_tab.count())],
            "right": [self.ui.tool_tab_widget.tabText(i) for i in range(self.ui.tool_tab_widget.count())]
        }
        for k, v in section_lists.items():
            if section in v:
                if k == "right":
                    self.ui.tool_tab_widget.setCurrentIndex(v.index(section))
                elif k == "bottom":
                    self.ui.bottom_panel_tab_widget.setCurrentIndex(v.index(section))
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

    def get_callback_for_slider(self, callback_name):
        return getattr(self, callback_name)

    def get_settings_value(self, settings_property):
        current_value = 0
        try:
            current_value = getattr(self, settings_property) or 0
        except AttributeError:
            keys = settings_property.split(".")
            if keys[0] == "settings":
                data = getattr(self, keys[0]) or None
            else:
                settings = self.settings
                if len(keys) > 1:
                    data = settings[keys[0]]
                else:
                    data = settings
            if data:
                if len(keys) > 1:
                    current_value = data[keys[1]]
                else:
                    current_value = data[keys[0]]
        return current_value

    def handle_value_change(self, attr_name, value=None, widget=None):
        """
        Slider widget callback - this is connected via dynamic properties in the
        qt widget. This function is then called when the value of a SliderWidget
        is changed.
        :param attr_name: the name of the attribute to change
        :param value: the value to set the attribute to
        :param widget: the widget that triggered the callback
        :return:
        """
        if attr_name is None:
            return
        
        keys = attr_name.split(".")
        if len(keys) > 0:
            settings = self.settings
            
            object_key = "settings"
            if len(keys) == 1:
                property_key = keys[0]
            if len(keys) == 2:
                object_key = keys[0]
                property_key = keys[1]

            if object_key != "settings":
                settings[object_key][property_key] = value
            else:
                settings[property_key] = value
            
            self.settings = settings
    
    def handle_similar_slider_change(self, attr_name, value=None, widget=None):
        self.standard_image_panel.handle_similar_slider_change(value)

    def initialize_window(self):
        self.center()
        self.set_window_title()

    def display(self):
        self.logger.info("Displaying window")
        self.set_stylesheet()
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowType.Window)
        self.show()

    def set_log_levels(self):
        uic.properties.logger.setLevel(LOG_LEVEL)
        uic.uiparser.logger.setLevel(LOG_LEVEL)

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
        self.setWindowTitle(f"AI Runner")

    def new_document(self):
        self.ui.layer_widget.clear_layers()
        self.is_saved = False
        self._document_name = "Untitled"
        self.set_window_title()
        self.current_filter = None
        #self.canvas_widget.update()
        self.ui.layer_widget.show_layers()

    def handle_controlnet_image_generated(self, message):
        self.controlnet_image = message["image"]
        self.controlnet_image_generated.emit(True)
        #self.generator_tab_widget.controlnet_settings_widget.handle_controlnet_image_generated()

    def video_handler(self, data):
        filename = data["video_filename"]
        VideoPopup(file_path=filename)

    def post_process_images(self, images):
        #return self.automatic_filter_manager.apply_filters(images)
        return images

    def handle_unknown(self, message):
        self.logger.error(f"Unknown message code: {message}")

    def set_size_form_element_step_values(self):
        """
        This function is called when grid_size is changed in the settings.

        :return:
        """
        self.set_size_increment_levels()

    def update(self):
        self.standard_image_panel.update_thumbnails()

    def insert_into_prompt(self, text, negative_prompt=False):
        prompt_widget = self.generator_tab_widget.data[self.current_generator][self.current_section]["prompt_widget"]
        negative_prompt_widget = self.generator_tab_widget.data[self.current_generator][self.current_section]["negative_prompt_widget"]
        if negative_prompt:
            current_text = negative_prompt_widget.toPlainText()
            text = f"{current_text}, {text}" if current_text != "" else text
            negative_prompt_widget.setPlainText(text)
        else:
            current_text = prompt_widget.toPlainText()
            text = f"{current_text}, {text}" if current_text != "" else text
            prompt_widget.setPlainText(text)

    def clear_all_prompts(self):
        self.prompt = ""
        self.negative_prompt = ""
        self.generator_tab_widget.clear_prompts()

    def show_prompt_browser(self):
        PromptBrowser()

    def import_image(self):
        file_path, _ = open_file_path(
            label="Import Image",
            directory=self.settings["path_settings"]["image_path"]
        )
        if file_path == "":
            return

    def export_image(self, image=None):
        file_path, _ = self.display_file_export_dialog()
        if file_path == "":
            return

    def choose_image_export_path(self):
        # display a dialog to choose the export path
        path = QFileDialog.getExistingDirectory(None, "Select Directory")
        if path == "":
            return
        self.image_path = path

    def display_file_export_dialog(self):
        return QFileDialog.getSaveFileName(
            self,
            "Export Image",
            "",
            "Image Files (*.png *.jpg *.jpeg)"
        )

    def display_import_image_dialog(self, label="Import Image", directory=""):
        return QFileDialog.getOpenFileName(
            self,
            label,
            directory,
            "Image Files (*.png *.jpg *.jpeg)"
        )

    def new_batch(self, index, image, data):
        self.generator_tab_widget.new_batch(index, image, data)

    def set_button_checked(self, name, val=True, block_signals=True):
        widget = getattr(self.ui, f"{name}_button")
        if block_signals:
            widget.blockSignals(True)
        widget.setChecked(val)
        if block_signals:
            widget.blockSignals(False)
    
    def set_all_section_buttons(self):
        self.set_button_checked("model_manager", self.settings["mode"] == Mode.MODEL_MANAGER.value)
    
    def activate_image_generation_section(self):
        self.ui.mode_tab_widget.setCurrentIndex(0)

    def activate_language_processing_section(self):
        self.ui.mode_tab_widget.setCurrentIndex(1)
    
    def activate_model_manager_section(self):
        self.ui.center_tab.setCurrentIndex(2)

    def initialize_tool_section_buttons(self):
        pass
    
    def redraw(self):
        self.set_stylesheet()

        # Update the window
        self.update()

    def action_center_clicked(self):
        print("center clicked")
    
    def action_slider_changed(self):
        print("action_slider_changed")

    def action_reset_settings(self):
        self.emit(SignalCode.APPLICATION_RESET_SETTINGS_SIGNAL)
