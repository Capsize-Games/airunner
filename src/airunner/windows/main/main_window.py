import os
import pickle
import sys
import webbrowser
from functools import partial
from airunner.resources_rc import *

import psutil
import torch

from PyQt6 import uic, QtCore
from PyQt6.QtWidgets import QApplication, QFileDialog, QMainWindow, QTabWidget, QWidget, \
    QVBoxLayout, QLabel, QHBoxLayout
from PyQt6.QtCore import pyqtSlot, Qt, QThread, pyqtSignal, QObject, QTimer
from PyQt6.QtGui import QGuiApplication

from airunner.aihandler.qtvar import MessageHandlerVar
from airunner.aihandler.logger import Logger as logger
from airunner.aihandler.pyqt_client import OfflineClient
from airunner.aihandler.settings import LOG_LEVEL
from airunner.aihandler.enums import MessageCode
from airunner.airunner_api import AIRunnerAPI
from airunner.data.db import session
from airunner.data.models import SplitterSection
from airunner.filters.windows.filter_base import FilterBase
from airunner.input_event_manager import InputEventManager
from airunner.mixins.canvas_mixin import CanvasMixin
from airunner.mixins.generator_mixin import GeneratorMixin
from airunner.mixins.history_mixin import HistoryMixin
from airunner.settings import BASE_PATH
from airunner.windows.main.templates.main_window_new_ui import Ui_MainWindow
from airunner.widgets.embeddings.embedding_widget import EmbeddingWidget
from airunner.themes import Themes
from airunner.windows.about.about import AboutWindow
from airunner.windows.settings.airunner_settings import SettingsWindow
from airunner.windows.deterministic_generation.deterministic_generation_window import DeterministicGenerationWindow
from airunner.windows.interpolation.image_interpolation import ImageInterpolation
from airunner.windows.model_merger import ModelMerger
from airunner.windows.prompt_browser.prompt_browser import PromptBrowser
from airunner.windows.update.update_window import UpdateWindow
from airunner.utils import get_version, get_latest_version, auto_export_image, get_session, save_session, \
    create_airunner_paths
from airunner.aihandler.settings_manager import SettingsManager

import qdarktheme


class MainWindow(
    QMainWindow,
    HistoryMixin,
    CanvasMixin,
    GeneratorMixin
):
    api = None
    input_event_manager = None
    current_filter = None
    tqdm_callback_triggered = False
    _document_name = "Untitled"
    is_saved = False
    action = "txt2img"
    message_var = None
    progress_bar_started = False
    window = None
    history = None
    canvas = None
    _settings_manager = None
    models = None
    client = None
    override_current_generator = None
    override_section = None
    _version = None
    _latest_version = None
    use_interpolation = None
    add_image_to_canvas_signal = pyqtSignal(dict)
    data = None  # this is set in the generator_mixin image_handler function and used for deterministic generation
    status_error_color = "#ff0000"
    status_normal_color_light = "#000000"
    status_normal_color_dark = "#ffffff"
    is_started = False
    _themes = None
    button_clicked_signal = pyqtSignal(dict)

    image_interpolation_window = None
    deterministic_window = None

    _embedding_names = None
    embedding_widgets = {}
    bad_model_embedding_map = {}
    _tabs = {
        "stablediffusion": {
            "txt2img": None,
            "outpaint": None,
            "depth2img": None,
            "pix2pix": None,
            "upscale": None,
            "superresolution": None,
            "txt2vid": None
        },
        "kandinsky": {
            "txt2img": None,
            "outpaint": None,
        },
        "shapegif": {
            "txt2img": None
        }
    }
    registered_settings_handlers = []
    tab_sections = {
        "left": {
            "stable_diffusion": {
                "widget": None,
                "index": 0
            },
            "kandinsky": {
                "widget": None,
                "index": 1
            },
            "shapegif": {
                "widget": None,
                "index": 2
            },
        },
        "center": {},
        "right": {}
    }
    image_generated = pyqtSignal(bool)
    controlnet_image_generated = pyqtSignal(bool)

    @property
    def settings_manager(self):
        if self._settings_manager is None:
            self._settings_manager = SettingsManager(app=self)
        return self._settings_manager

    @settings_manager.setter
    def settings_manager(self, val):
        self._settings_manager = val

    @property
    def current_prompt_generator_settings(self):
        """
        Convenience property to get the current prompt generator settings
        :return:
        """
        return self.settings_manager.prompt_generator_settings

    @property
    def embedding_names(self):
        if self._embedding_names is None:
            self._embedding_names = self.get_list_of_available_embedding_names()
        return self._embedding_names

    @property
    def is_dark(self):
        return self.settings_manager.dark_mode_enabled

    @property
    def grid_size(self):
        return self.settings_manager.grid_settings.size

    @property
    def canvas_widget(self):
        return self.ui.canvas_widget.ui

    @property
    def generator_tab_widget(self):
        return self.ui.generator_widget

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
    def canvas_position(self):
        return self.canvas_widget.canvas_position

    @canvas_position.setter
    def canvas_position(self, val):
        self.canvas_widget.canvas_position.setText(val)

    @property
    def current_generator(self):
        """
        Returns the current generator (stablediffusion, kandinksy, etc) as
        determined by the selected generator tab in the
        generator_tab_widget. This value can be override by setting
        the override_current_generator property.
        :return: string
        """
        if self.override_current_generator:
            return self.override_current_generator
        return self.generator_tab_widget.current_generator

    @property
    def current_section(self):
        """
        Returns the current section (txt2img, outpaint, etc) as
        determined by the selected sub-tab in the generator tab widget.
        This value can be override by setting the override_section property.
        :return: string
        """
        if self.override_section:
            return self.override_section
        return self.generator_tab_widget.current_section

    @property
    def tabs(self):
        return self._tabs[self.current_generator]

    @tabs.setter
    def tabs(self, val):
        self._tabs[self.current_generator] = val

    @property
    def is_txt2img(self):
        return self.current_section == "txt2img"

    @property
    def is_outpaint(self):
        return self.current_section == "outpaint"

    @property
    def is_depth2img(self):
        return self.current_section == "depth2img"

    @property
    def is_pix2pix(self):
        return self.current_section == "pix2pix"

    @property
    def is_upscale(self):
        return self.current_section == "upscale"

    @property
    def is_superresolution(self):
        return self.current_section == "superresolution"

    @property
    def is_txt2vid(self):
        return self.current_section == "txt2vid"

    @property
    def generator_type(self):
        """
        Returns either stablediffusion, shapegif, kandinsky
        :return: string
        """
        return self._generator_type

    @property
    def use_pixels(self):
        # get name of current tab
        if self.current_section == "txt2img" and self.enable_controlnet and self.controlnet is not None:
            use_pixels = True
        else:
            use_pixels = self.current_section in (
                "txt2img",
                "pix2pix",
                "depth2img",
                "outpaint",
                "controlnet",
                "superresolution",
                "upscale"
            )
        return use_pixels

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
        name = f"{self._document_name}{'*' if self.canvas and self.canvas.is_dirty else ''}"
        return f"{name} - {self.version}"

    @property
    def is_windows(self):
        return sys.platform.startswith("win") or sys.platform.startswith("cygwin") or sys.platform.startswith("msys")

    @property
    def is_maximized(self):
        return self.settings_manager.is_maximized

    @property
    def css(self):
        if self._themes is None:
            self._themes = Themes()
        return self._themes.css

    @property
    def image_path(self):
        return self.settings_manager.path_settings.image_path

    @is_maximized.setter
    def is_maximized(self, val):
        self.settings_manager.set_value("is_maximized", val)

    @property
    def enable_input_image(self):
        return self.settings_manager.generator.enable_input_image

    @enable_input_image.setter
    def enable_input_image(self, val):
        self.settings_manager.set_value("generator.enable_input_image", val)

    @property
    def input_image_use_imported_image(self):
        return self.settings_manager.generator.input_image_use_imported_image

    @input_image_use_imported_image.setter
    def input_image_use_imported_image(self, val):
        self.settings_manager.set_value("generator.input_image_use_imported_image", val)

    @property
    def input_image_use_grid_image(self):
        return self.settings_manager.generator.input_image_use_grid_image

    @input_image_use_grid_image.setter
    def input_image_use_grid_image(self, val):
        self.settings_manager.set_value("generator.input_image_use_grid_image", val)

    @property
    def input_image_recycle_grid_image(self):
        return self.settings_manager.generator.input_image_recycle_grid_image

    @input_image_recycle_grid_image.setter
    def input_image_recycle_grid_image(self, val):
        self.settings_manager.set_value("generator.input_image_recycle_grid_image", val)

    @property
    def input_image_mask_use_input_image(self):
        return self.settings_manager.generator.input_image_mask_use_input_image

    @input_image_mask_use_input_image.setter
    def input_image_mask_use_input_image(self, val):
        self.settings_manager.set_value("generator.input_image_mask_use_input_image", val)

    @property
    def input_image_mask_use_imported_image(self):
        return self.settings_manager.generator.input_image_mask_use_imported_image

    @input_image_mask_use_imported_image.setter
    def input_image_mask_use_imported_image(self, val):
        self.settings_manager.set_value("generator.input_image_mask_use_imported_image", val)

    @property
    def controlnet_input_image_link_to_input_image(self):
        return self.settings_manager.generator.controlnet_input_image_link_to_input_image

    @controlnet_input_image_link_to_input_image.setter
    def controlnet_input_image_link_to_input_image(self, val):
        self.settings_manager.set_value("generator.controlnet_input_image_link_to_input_image", val)

    @property
    def controlnet_input_image_use_imported_image(self):
        return self.settings_manager.generator.controlnet_input_image_use_imported_image

    @controlnet_input_image_use_imported_image.setter
    def controlnet_input_image_use_imported_image(self, val):
        self.settings_manager.set_value("generator.controlnet_input_image_use_imported_image", val)

    @property
    def controlnet_use_grid_image(self):
        return self.settings_manager.generator.controlnet_use_grid_image

    @controlnet_use_grid_image.setter
    def controlnet_use_grid_image(self, val):
        self.settings_manager.set_value("generator.controlnet_use_grid_image", val)

    @property
    def controlnet_recycle_grid_image(self):
        return self.settings_manager.generator.controlnet_recycle_grid_image

    @controlnet_recycle_grid_image.setter
    def controlnet_recycle_grid_image(self, val):
        self.settings_manager.set_value("generator.controlnet_recycle_grid_image", val)

    @property
    def controlnet_mask_link_input_image(self):
        return self.settings_manager.generator.controlnet_mask_link_input_image

    @controlnet_mask_link_input_image.setter
    def controlnet_mask_link_input_image(self, val):
        self.settings_manager.set_value("generator.controlnet_mask_link_input_image", val)

    @property
    def controlnet_mask_use_imported_image(self):
        return self.settings_manager.generator.controlnet_mask_use_imported_image

    @controlnet_mask_use_imported_image.setter
    def controlnet_mask_use_imported_image(self, val):
        self.settings_manager.set_value("generator.controlnet_mask_use_imported_image", val)

    def available_model_names_by_section(self, section):
        for model in self.settings_manager.available_models_by_category(section):
            yield model["name"]

    def __init__(self, *args, **kwargs):
        logger.info("Starting AI Runnner")
        qdarktheme.enable_hi_dpi()

        # set the api
        self.api = AIRunnerAPI(window=self)

        self.set_log_levels()
        self.testing = kwargs.pop("testing", False)

        # initialize the document
        from airunner.data.db import session
        from airunner.data.models import Document
        self.document = session.query(Document).first()

        super().__init__(*args, **kwargs)


        self.initialize()


        # on window resize:
        # self.applicationStateChanged.connect(self.on_state_changed)

        if self.settings_manager.latest_version_check:
            logger.info("Checking for latest version")
            self.check_for_latest_version()

        # check for self.current_layer.lines every 100ms
        self.timer = self.startTimer(100)

        # self.header_widget.set_size_increment_levels()
        self.clear_status_message()

        self.register_keypress()

        if not self.testing:
            logger.info("Executing window")
            self.display()
        self.set_window_state()
        self.is_started = True

        # change the color of tooltips
        self.setStyleSheet("QToolTip { color: #000000; background-color: #ffffff; border: 1px solid black; }")

        widget = QWidget()
        hbox = QHBoxLayout()
        widget.setLayout(hbox)
        self.system_stats_label = QLabel("", widget)
        widget.layout().addWidget(self.system_stats_label)
        self.statusBar().addPermanentWidget(widget)

        # create paths if they do not exist
        create_airunner_paths()

        self.ui.layer_widget.initialize()

        self.ui.toggle_grid_button.setChecked(self.settings_manager.grid_settings.show_grid)
        self.ui.safety_checker_button.setChecked(self.settings_manager.nsfw_filter)

    def quick_export(self):
        if os.path.isdir(self.image_path) is False:
            self.choose_image_export_path()
        if os.path.isdir(self.image_path) is False:
            return
        path = auto_export_image(self.canvas.current_layer.image_data.image, seed=self.seed)
        if path is not None:
            self.set_status_label(f"Image exported to {path}")

    """
    Slot functions
    
    The following functions are defined in and connected to the appropriate
    signals in the corresponding ui file.
    """
    def action_new_document_triggered(self):
        self.new_document()

    def action_save_document_triggered(self):
        self.save_document()

    def action_quick_export_image_triggered(self):
        self.quick_export()

    def action_export_image_triggered(self):
        self.export_image()

    def action_load_document_triggered(self):
        self.load_document()

    def action_import_image_triggered(self):
        self.import_image()

    def action_quit_triggered(self):
        self.quit()

    def action_undo_triggered(self):
        self.undo()

    def action_redo_triggered(self):
        self.redo()

    def action_paste_image_triggered(self):
        self.paste_image()

    def action_copy_image_triggered(self):
        self.copy_image()

    def action_cut_image_triggered(self):
        self.cut_image()

    def action_rotate_90_clockwise_triggered(self):
        self.canvas.rotate_90_clockwise()

    def action_rotate_90_counterclockwise_triggered(self):
        self.canvas.rotate_90_counterclockwise()

    def action_save_prompt_triggered(self):
        self.save_prompt()

    def action_show_prompt_browser_triggered(self):
        self.show_prompt_browser()

    def action_show_image_interpolation_triggered(self):
        self.show_image_interpolation()

    def action_clear_all_prompts_triggered(self):
        self.clear_all_prompts()

    def action_show_model_manager(self):
        self.show_section("model_manager")

    def action_show_prompt_builder(self):
        self.show_section("prompt_builder")

    def action_show_controlnet(self):
        self.show_section("controlnet")

    def action_show_embeddings(self):
        self.show_section("embeddings")

    def action_show_lora(self):
        self.show_section("lora")

    def action_show_pen(self):
        self.show_section("pen")

    def action_show_stablediffusion(self):
        self.show_section("stable_diffusion")

    def action_show_kandinsky(self):
        self.show_section("kandinsky")

    def action_show_shape(self):
        self.show_section("shapegif")

    def action_triggered_browse_ai_runner_path(self):
        path = self.settings_manager.path_settings.base_path
        if path == "":
            path = BASE_PATH
        self.show_path(path)

    def action_show_hf_cache_manager(self):
        path = self.settings_manager.path_settings.hf_cache_path
        if path == "":
            from airunner.utils import default_hf_cache_dir
            path = default_hf_cache_dir()
        self.show_path(path)

    def show_path(self, path):
        import subprocess
        import platform
        import os
        if platform.system() == "Windows":
            subprocess.Popen(["explorer", os.path.realpath(path)])
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", os.path.realpath(path)])
        else:
            subprocess.Popen(["xdg-open", os.path.realpath(path)])

    def action_focus_button_triggered(self):
        self.canvas.recenter()

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

    def action_toggle_nsfw_filter_triggered(self, bool):
        self.settings_manager.set_value("nsfw_filter", bool)
        self.toggle_nsfw_filter()

    def action_toggle_grid(self, active):
        self.settings_manager.set_value("grid_settings.show_grid", active)
        self.canvas.update()

    def action_toggle_darkmode(self):
        self.set_stylesheet()

    def action_show_about_window(self):
        AboutWindow(app=self)

    def action_show_model_merger_window(self):
        ModelMerger(app=self)

    def action_show_settings(self):
        SettingsWindow(app=self)

    def action_open_bug_report(self):
        webbrowser.open("https://github.com/Capsize-Games/airunner/issues/new?assignees=&labels=&template=bug_report.md&title=")

    def action_open_discord(self):
        webbrowser.open("https://github.com/Capsize-Games/airunner/security/advisories/new")

    def tool_tab_index_changed(self, index):
        print(index)

    def bottom_panel_tab_index_changed(self, index):
        print(index)

    def right_splitter_moved(self, size, index):
        print("right_splitter_moved")

    def main_splitter_moved(self, size, index):
        print("main_splitter_moved")

    def content_splitter_moved(self, size, index):
        print("content_splitter_moved")

    def brush_size_slider_callback(self, val):
        self.settings_manager.set_value("mask_brush_size", val)

    def width_slider_callback(self, val):
        self.settings_manager.set_value("working_width", val)

    def height_slider_callback(self, val):
        self.settings_manager.set_value("working_height", val)
    """
    End slot functions
    """

    def set_size_increment_levels(self):
        size = self.grid_size
        self.width_slider_widget.slider_single_step = size
        self.width_slider_widget.slider_tick_interval = size

        self.height_slider_widget.slider_single_step = size
        self.height_slider_widget.slider_tick_interval = size

        self.app.canvas.update()

    def toggle_nsfw_filter(self):
        self.canvas.update()
        self.set_nsfw_filter_tooltip()

    def set_nsfw_filter_tooltip(self):
        nsfw_filter = self.settings_manager.nsfw_filter
        self.ui.safety_checker_button.setToolTip(
            f"Click to {'enable' if not nsfw_filter else 'disable'} NSFW filter"
        )

    def update_system_stats(self, queue_size):
        system_memory_percentage = psutil.virtual_memory().percent
        has_cuda = torch.cuda.is_available()
        queue_items = f"Queued items: {queue_size}"
        cuda_memory = f"Using {'GPU' if has_cuda else 'CPU'}, VRAM allocated {torch.cuda.memory_allocated() / 1024 ** 3:.1f}GB cached {torch.cuda.memory_cached() / 1024 ** 3:.1f}GB"
        system_memory = f"RAM {system_memory_percentage:.1f}%"
        self.system_stats_label.setText(
            f"{queue_items}, {system_memory}, {cuda_memory}")

    def update_controlnet_thumbnail(self):
        self.generator_tab_widget.update_controlnet_thumbnail()

    def resizeEvent(self, event):
        if not self.is_started:
            return
        state = self.windowState()
        if state == Qt.WindowState.WindowMaximized:
            timer = QTimer(self)
            timer.setSingleShot(True)
            timer.timeout.connect(self.checkWindowState)
            timer.start(100)
        else:
            self.checkWindowState()

    def checkWindowState(self):
        state = self.windowState()
        self.is_maximized = state == Qt.WindowState.WindowMaximized

    def dragmode_pressed(self):
        self.canvas.is_canvas_drag_mode = True

    def dragmode_released(self):
        self.canvas.is_canvas_drag_mode = False

    def shift_pressed(self):
        self.canvas.shift_is_pressed = True

    def shift_released(self):
        self.canvas.shift_is_pressed = False

    def register_keypress(self):
        self.input_event_manager.register_keypress("fullscreen", self.toggle_fullscreen)
        self.input_event_manager.register_keypress("control_pressed", self.dragmode_pressed, self.dragmode_released)
        self.input_event_manager.register_keypress("shift_pressed", self.shift_pressed, self.shift_released)
        self.input_event_manager.register_keypress("delete_outside_active_grid_area", self.canvas.delete_outside_active_grid_area)

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def quit(self):
        self.close()

    def closeEvent(self, event):
        logger.info("Quitting")
        QApplication.quit()

    def timerEvent(self, event):
        self.canvas.timerEvent(event)
        # self.footer_widget.update_system_stats(
        #     queue_size=self.client.queue.qsize()
        # )
        self.update_system_stats(queue_size=self.client.queue.qsize())

    def check_for_latest_version(self):
        self.version_thread = QThread()
        class VersionCheckWorker(QObject):
            version = None
            finished = pyqtSignal()
            def get_latest_version(self):
                self.version = f"v{get_latest_version()}"
                self.finished.emit()
        self.version_worker = VersionCheckWorker()
        self.version_worker.moveToThread(self.version_thread)
        self.version_thread.started.connect(self.version_worker.get_latest_version)
        self.version_worker.finished.connect(self.handle_latest_version)
        self.version_thread.start()

    def handle_latest_version(self):
        self.latest_version = self.version_worker.version
        # call get_latest_version() in a separate thread
        # to avoid blocking the UI, show a popup if version doesn't match self.version
        # check if latest_version is greater than version using major, minor, patch
        current_major, current_minor, current_patch = self.version[1:].split(".")
        try:
            latest_major, latest_minor, latest_patch = self.latest_version[1:].split(".")
        except ValueError:
            latest_major, latest_minor, latest_patch = 0, 0, 0

        latest_major = int(latest_major)
        latest_minor = int(latest_minor)
        latest_patch = int(latest_patch)
        current_major = int(current_major)
        current_minor = int(current_minor)
        current_patch = int(current_patch)

        if current_major == latest_major and current_minor == latest_minor and current_patch < latest_patch:
            self.show_update_message()
        elif current_major == latest_major and current_minor < latest_minor:
            self.show_update_message()
        elif current_major < latest_major:
            self.show_update_message()

    def show_update_message(self):
        self.set_status_label(f"New version available: {self.latest_version}")

    def show_update_popup(self):
        self.update_popup = UpdateWindow(self.settings_manager, app=self)

    def reset_settings(self):
        logger.info("Resetting settings")
        # GeneratorMixin.reset_settings(self)
        self.canvas.reset_settings()

    def on_state_changed(self, state):
        if state == Qt.ApplicationState.ApplicationActive:
            self.canvas.pos_x = int(self.x() / 4)
            self.canvas.pos_y = int(self.y() / 2)
            self.canvas.update()

    def set_stylesheet(self):
        logger.info("Setting stylesheets")
        try:
            qdarktheme.setup_theme("dark" if self.settings_manager.dark_mode_enabled else "light")
        except PermissionError:
            pass
        self.generator_tab_widget.set_stylesheet()
        # self.header_widget.set_stylesheet()
        self.canvas_widget.set_stylesheet()
        # self.tool_menu_widget.set_stylesheet()
        self.toolbar_widget.set_stylesheet()
        self.footer_widget.set_stylesheet()

    def initialize(self):
        # self.automatic_filter_manager = AutomaticFilterManager(app=self)
        # self.automatic_filter_manager.register_filter(PixelFilter, base_size=256)

        self.input_event_manager = InputEventManager(app=self)
        self.initialize_settings_manager()
        self.initialize_window()
        self.initialize_handlers()
        self.connect_splitter_handlers()
        self.initialize_mixins()
        self.generate_signal.connect(self.handle_generate)
        # self.header_widget.initialize()
        # self.header_widget.set_size_increment_levels()
        self.initialize_shortcuts()
        self.initialize_stable_diffusion()
        if self.settings_manager.force_reset:
            self.reset_settings()
            self.settings_manager.set_value("force_reset", False)
        # self.actionShow_Active_Image_Area.setChecked(
        #     self.settings_manager.show_active_image_area == True
        # )
        self.initialize_default_buttons()
        self.generator_tab_widget.initialize()
        self.prompt_builder.process_prompt()
        self.connect_signals()
        self.initialize_filter_actions()

    def initialize_filter_actions(self):
        # add more filters:
        for filter in self.settings_manager.get_image_filters():
            action = self.ui.menuFilters.addAction(filter.display_name)
            action.triggered.connect(partial(self.display_filter_window, filter))

    def display_filter_window(self, filter):
        FilterBase(self, filter.name).show()

    def handle_generate(self):
        self.prompt_builder.inject_prompt()

    def initialize_default_buttons(self):
        pass

    @pyqtSlot(dict)
    def handle_button_clicked(self, kwargs):
        action = kwargs.get("action", "")
        if action == "toggle_tool":
            self.toggle_tool(kwargs["tool"])

    def toggle_tool(self, tool):
        self.settings_manager.set_value("current_tool", tool)
        self.canvas.update_cursor()

    def initialize_mixins(self):
        HistoryMixin.initialize(self)
        CanvasMixin.initialize(self)
        GeneratorMixin.initialize(self)

    def connect_signals(self):
        logger.info("Connecting signals")
        self.canvas._is_dirty.connect(self.set_window_title)

        for signal, handler in self.registered_settings_handlers:
            getattr(self.settings_manager, signal).connect(handler)

        self.button_clicked_signal.connect(self.handle_button_clicked)

    def connect_splitter_handlers(self):
        self.ui.content_splitter.splitterMoved.connect(self.handle_main_splitter_moved)
        self.ui.main_splitter.splitterMoved.connect(self.handle_bottom_splitter_moved)

    def track_tab_section(
        self,
        location: str,
        section: str,
        display_name: str,
        widget: QWidget,
        tab_widget: QTabWidget
    ):
        index = tab_widget.addTab(widget, display_name)
        self.tab_sections[location][section] = {
            "widget": widget,
            "index": index
        }

    def show_section(self, section):
        left_sections = self.tab_sections["left"].keys()
        center_sections = self.tab_sections["center"].keys()
        right_sections = self.tab_sections["right"].keys()

        if section in left_sections:
            if self.splitter.widget(0).width() <= self.default_splitter_sizes[0]:
                main_sizes = self.settings_manager.main_splitter_sizes
                main_sizes[0] = self.default_splitter_sizes[0] + 1
                self.splitter.setSizes(main_sizes)
            self.generator_tab_widget.sectionTabWidget.setCurrentIndex(self.tab_sections["left"][section]["index"])

        if section in right_sections:
            # right splitter is self.splitter.widget(2)
            if self.splitter.widget(2).width() <= self.default_splitter_sizes[2]:
                # set the width to 500
                main_sizes = self.settings_manager.main_splitter_sizes
                main_sizes[2] = self.default_splitter_sizes[2] + 1
                self.splitter.setSizes(main_sizes)
            self.tab_widget.setCurrentIndex(self.tab_sections["right"][section]["index"])

        if section in center_sections:
            # check if self.center_panel is collapsed and expand it if so
            if self.center_splitter.sizes()[1] == 0:
                self.center_splitter.setSizes([self.center_splitter.sizes()[0], 520])
            self.center_panel.setCurrentIndex(self.tab_sections["center"][section]["index"])

    def handle_value_change(self, attr_name, value=None, widget=None):
        if attr_name == "generator.controlnet":
            value = value.lower()

        if value is None:
            try:
                value = widget.toPlainText()
            except AttributeError:
                try:
                    value = widget.currentText()
                except AttributeError:
                    try:
                        value = widget.value()
                    except AttributeError:
                        print("something went wrong while setting the value 123")

        self.settings_manager.set_value(attr_name, value)

    def set_splitter_sizes(self):
        """
        Splitters are used to divide the window into sections. This function
        intializes the sizes of each splitter section. The sizes are stored
        in the database and are loaded when the application starts.

        The SplitterSection model is used to store the sizes.
        The name field for each SplitterSection is set to the name of its
        corresponding widget.

        main_splitter divides the top and bottom sections
            Horizontal
            Top section is the generator tab widget, canvas and tool menus.
            Bottom section is a tool tab menu (model manager, prompt builder, etc).
        content_splitter divides the left, center and right sections
            Horizontal
            Generator tab widgets are in the left panel.
            Canvas is in the center panel.
            Tool menus are in the right panel.
        center_splitter
            Vertical
            Allows multiple grids or additional panels in the center area.
        right_panel_splitter divides the right panel into sections
            Vertical
            Currently used for tool menus (embeddings, layers etc.).
        :return:
        """
        session = get_session()

        main_splitter_sections = session.query(SplitterSection.size).filter(
            SplitterSection.name == "main_splitter"
        ).order_by(
            SplitterSection.order
        ).all()

        content_splitter_sections = session.query(SplitterSection.size).filter(
            SplitterSection.name == "content_splitter"
        ).order_by(
            SplitterSection.order
        ).all()

        main_splitter_sizes = [size[0] for size in main_splitter_sections]
        content_splitter_sizes = [size[0] for size in content_splitter_sections]

        self.ui.main_splitter.setSizes(main_splitter_sizes)
        self.ui.content_splitter.setSizes(content_splitter_sizes)

    def handle_main_splitter_moved(self, pos, index):
        sizes = {
            "left": session.query(SplitterSection).filter_by(
                name="content_splitter",
                order=0
            ).first(),
            "right": session.query(SplitterSection).filter_by(
                name="content_splitter",
                order=2
            ).first()
        }
        col_a_width = self.ui.content_splitter.widget(0).width()
        col_b_width = self.ui.content_splitter.widget(1).width()
        col_c_width = self.ui.content_splitter.widget(2).width()
        col_d_width = self.ui.content_splitter.widget(3).width()
        window_width = self.width()

        if index == 2 and window_width - pos == 60:
            col_c_width = 0
        if index == 1 and pos == 1:
            col_a_width = 0
        if index == 1:
            col_c_width = sizes["right"].size
        if index == 2:
            col_a_width = sizes["left"].size

        updated_sizes = [col_a_width, col_b_width, col_c_width, col_d_width]
        for n, size in enumerate(updated_sizes):
            obj = session.query(SplitterSection).filter_by(
                name="content_splitter",
                order=n
            ).first()
            obj.size = size
            save_session()

    def handle_bottom_splitter_moved(self, pos, index):
        top_height = self.ui.main_splitter.widget(0).height()
        bottom_height = self.ui.main_splitter.widget(1).height()
        obj = session.query(SplitterSection).filter_by(
            name="main_splitter",
            order=0
        ).first()
        obj.size = top_height
        obj_b = session.query(SplitterSection).filter_by(
            name="main_splitter",
            order=1
        ).first()
        obj_b.size = bottom_height
        save_session()

    def initialize_settings_manager(self):
        self.settings_manager.changed_signal.connect(self.handle_changed_signal)

    def handle_changed_signal(self, key, value):
        if key == "size":
            self.set_size_form_element_step_values()
            self.header_widget.update_widget_values()
        elif key == "line_width":
            self.set_size_form_element_step_values()
        elif key == "show_grid":
            self.canvas.update()
        elif key == "snap_to_grid":
            self.canvas.update()
        elif key == "line_color":
            self.canvas.update_grid_pen()
        elif key == "lora_path":
            self.refresh_lora()
        elif key == "model_base_path":
            self.generator_tab_widget.refresh_model_list()
        elif key == "working_width":
            self.header_widget.update_widget_values()
        elif key == "working_height":
            self.header_widget.update_widget_values()
        elif key == "embeddings_path":
            self.update_embedding_names()
        elif key == "generator.seed":
            self.prompt_builder.process_prompt()
        elif key == "use_prompt_builder_checkbox":
            self.generator_tab_widget.toggle_all_prompt_builder_checkboxes(value)
        elif key == "generator.model":
            self.enable_embeddings()
        elif key == "models":
            self.model_manager.models_changed(key, value)

    def initialize_shortcuts(self):
        event_callbacks = {
            "wheelEvent": self.change_width,
        }

        for event, callback in event_callbacks.items():
            self.input_event_manager.register_event(event, callback)

    def initialize_handlers(self):
        self.message_var = MessageHandlerVar()
        self.message_var.my_signal.connect(self.message_handler)

    def initialize_window(self):
        self.window = Ui_MainWindow()
        self.window.setupUi(self)
        self.ui = self.window
        self.center()
        self.set_window_title()

    def initialize_stable_diffusion(self):
        logger.info("Initializing stable diffusion")
        self.client = OfflineClient(
            app=self,
            message_var=self.message_var,
            settings_manager=self.settings_manager,
        )

    def save_settings(self):
        self.settings_manager.save_settings()

    def display(self):
        logger.info("Displaying window")
        # self.set_stylesheet()
        if not self.testing:
            self.show()
        else:
            # do not show the window when testing, otherwise it will block the tests
            # self.hide()
            # the above solution doesn't work, gives this error:
            # QBasicTimer::start: QBasicTimer can only be used with threads started with QThread
            # so instead we do this in order to run without showing the window:
            self.showMinimized()
        self.canvas.show_layers()

    def set_window_state(self):
        if self.is_maximized:
            self.showMaximized()
        else:
            self.showNormal()
        self.set_splitter_sizes()

    def set_log_levels(self):
        uic.properties.logger.setLevel(LOG_LEVEL)
        uic.uiparser.logger.setLevel(LOG_LEVEL)

    def center(self):
        availableGeometry = QGuiApplication.primaryScreen().availableGeometry()
        frameGeometry = self.frameGeometry()
        frameGeometry.moveCenter(availableGeometry.center())
        self.move(frameGeometry.topLeft())

    def change_width(self, event):
        grid_size = self.grid_size

        # if the shift key is pressed
        if QtCore.Qt.KeyboardModifier.ShiftModifier in event.modifiers():
            delta = event.angleDelta().y()
            increment = grid_size if delta > 0 else -grid_size
            self.working_width = int(self.working_width + increment)

        # if the control key is pressed
        if QtCore.Qt.KeyboardModifier.ControlModifier in event.modifiers():
            delta = event.angleDelta().y()
            increment = grid_size if delta > 0 else -grid_size
            self.working_height = int(self.working_height + increment)

    def toggle_stylesheet(self, path):
        # use fopen to open the file
        # read the file
        # set the stylesheet
        with open(path, "r") as stream:
            self.setStyleSheet(stream.read())

    def set_window_title(self):
        """
        Overrides base method to set the window title
        :return:
        """
        self.setWindowTitle(f"AI Runner {self.document_name}")

    def new_document(self):
        self.canvas.clear_layers()
        self.clear_history()
        #CanvasMixin.initialize(self)
        self.is_saved = False
        self.canvas.is_dirty = False
        self._document_name = "Untitled"
        self.set_window_title()
        self.current_filter = None
        self.canvas.update()
        self.canvas.show_layers()

    def set_status_label(self, txt, error=False):
        # color = self.status_normal_color_dark if self.is_dark else \
        #     self.status_normal_color_light
        # self.footer_widget.ui.status_label.setText(txt)
        # self.footer_widget.ui.status_label.setStyleSheet(
        #     f"color: {self.status_error_color if error else color};"
        # )
        print(txt)

    @pyqtSlot(dict)
    def message_handler(self, response: dict):
        try:
            code = response["code"]
        except TypeError:
            # logger.error(f"Invalid response message: {response}")
            # traceback.print_exc()
            return
        message = response["message"]
        {
            MessageCode.STATUS: self.handle_status,
            MessageCode.ERROR: self.handle_error,
            MessageCode.PROGRESS: self.handle_progress,
            MessageCode.IMAGE_GENERATED: self.handle_image_generated,
            MessageCode.CONTROLNET_IMAGE_GENERATED: self.handle_controlnet_image_generated,
            MessageCode.EMBEDDING_LOAD_FAILED: self.handle_embedding_load_failed,
        }.get(code, self.handle_unknown)(message)

    def handle_controlnet_image_generated(self, message):
        self.controlnet_image = message["image"]
        self.controlnet_image_generated.emit(True)
        self.generator_tab_widget.controlnet_settings_widget.handle_controlnet_image_generated()

    def handle_image_generated(self, message):
        images = message["images"]
        data = message["data"]
        nsfw_content_detected = message["nsfw_content_detected"]
        self.clear_status_message()
        self.data = data
        if data["action"] == "txt2vid":
            return self.video_handler(data)

        self.generator_tab_widget.stop_progress_bar(
            data["tab_section"], data["action"]
        )

        if self.settings_manager.auto_export_images:
            path = auto_export_image(images[0], data, self.seed)
            if path is not None:
                self.set_status_label(f"Image exported to {path}")

        self.generator_tab_widget.stop_progress_bar(
            data["tab_section"], data["action"]
        )
        # get max progressbar value
        if nsfw_content_detected and self.settings_manager.nsfw_filter:
            self.message_handler({
                "message": "NSFW content detected, try again.",
                "code": MessageCode.ERROR
            })

        images = self.post_process_images(images)

        if data["options"][f"deterministic_generation"]:
            self.deterministic_images = images
            DeterministicGenerationWindow(
                self.settings_manager,
                app=self,
                images=images,
                data=data)
        else:
            if data[
                "action"] != "outpaint" and self.settings_manager.image_to_new_layer and self.canvas.current_layer.image_data.image is not None:
                self.canvas.add_layer()
            # print width and height of image
            self.canvas.image_handler(images[0], data)
            self.message_handler("")
            self.canvas.show_layers()

        self.image_generated.emit(True)

    def post_process_images(self, images):
        return self.automatic_filter_manager.apply_filters(images)

    def handle_status(self, message):
        self.set_status_label(message)

    def handle_error(self, message):
        self.set_status_label(message, error=True)

    def handle_progress(self, message):
        step = message.get("step")
        total = message.get("total")
        action = message.get("action")
        tab_section = message.get("tab_section")

        if step == 0 and total == 0:
            current = 0
        else:
            try:
                current = (step / total)
            except ZeroDivisionError:
                current = 0
        self.generator_tab_widget.set_progress_bar_value(tab_section, action, int(current * 100))

    def handle_embedding_load_failed(self, message):
        # TODO:
        #  on model change, re-enable the buttons
        embedding_name = message["embedding_name"]
        model_name = message["model_name"]
        self.disable_embedding(embedding_name, model_name)

    def handle_unknown(self, message):
        logger.error(f"Unknown message code: {message}")

    def clear_status_message(self):
        self.set_status_label("")

    def set_size_form_element_step_values(self):
        """
        This function is called when grid_size is changed in the settings.

        :return:
        """
        self.set_size_increment_levels()

    def saveas_document(self):
        # get file path
        file_path, _ = QFileDialog.getSaveFileName(
            self.window, "Save Document", "", "AI Runner Document (*.airunner)"
        )
        if file_path == "":
            return

        # ensure file_path ends with .airunner
        if not file_path.endswith(".airunner"):
            file_path += ".airunner"

        self.do_save(file_path)

    def do_save(self, document_name):
        # save self.canvas.layers as pickle
        layers = []
        # we need to save self.canvas.layers but it contains a QWdget
        # so we will remove the QWidget from each layer, add the layer to a new
        # list and then restore the QWidget
        layer_widgets = []
        for layer in self.canvas.layers:
            layer_widgets.append(layer.layer_widget)
            layer.layer_widget = None
            layers.append(layer)
        data = {
            "layers": layers,
            "image_pivot_point": self.canvas.image_pivot_point,
            "image_root_point": self.canvas.image_root_point,
        }
        with open(document_name, "wb") as f:
            pickle.dump(data, f)
        # restore the QWidget
        for i, layer in enumerate(layers):
            layer.layer_widget = layer_widgets[i]
        # get the document name stripping .airunner from the end
        self._document_path = document_name
        self._document_name = document_name.split("/")[-1].split(".")[0]
        self.set_window_title()
        self.is_saved = True
        self.canvas.is_dirty = False

    def save_document(self):
        if not self.is_saved:
            return self.saveas_document()
        self.do_save(self._document_path)

    def load_document(self):
        self.new_document()
        # load all settings and layer data from a file called "<document_name>.airunner"

        # get file path
        file_path, _ = QFileDialog.getOpenFileName(
            self.window, "Load Document", "", "AI Runner Document (*.airunner)"
        )
        if file_path == "":
            return

        # get document data
        image_pivot_point = self.canvas.image_pivot_point
        image_root_point = self.canvas.image_root_point
        with open(file_path, "rb") as f:
            try:
                data = pickle.load(f)
                layers = data["layers"]
                image_pivot_point = data["image_pivot_point"]
                image_root_point = data["image_root_point"]
            except Exception as e:
                layers = data

        # get the document name stripping .airunner from the end
        self._document_path = file_path
        self._document_name = file_path.split("/")[-1].split(".")[0]

        # load document data
        self.canvas.layers = layers
        self.canvas.image_pivot_point = image_pivot_point
        self.canvas.image_root_point = image_root_point
        self.canvas.update()
        self.is_saved = True
        self.set_window_title()
        self.canvas.show_layers()

    def update_embedding_names(self):
        self._embedding_names = None
        for tab_name in self.tabs.keys():
            tab = self.tabs[tab_name]
            # clear embeddings
            try:
                tab.embeddings.widget().deleteLater()
            except AttributeError:
                pass
            self.load_embeddings(tab)

    def update(self):
        self.generator_tab_widget.update_thumbnails()

    def register_embedding_widget(self, name, widget):
        self.embedding_widgets[name] = widget

    def disable_embedding(self, name, model_name):
        self.embedding_widgets[name].setEnabled(False)
        if name not in self.bad_model_embedding_map:
            self.bad_model_embedding_map[name] = []
        if model_name not in self.bad_model_embedding_map[name]:
            self.bad_model_embedding_map[name].append(model_name)

    def enable_embeddings(self):
        for name in self.embedding_widgets.keys():
            enable = True
            if name in self.bad_model_embedding_map:
                if self.model in self.bad_model_embedding_map[name]:
                    enable = False
            self.embedding_widgets[name].setEnabled(enable)

    def load_embeddings(self, tab):
        container = QWidget()
        container.setLayout(QVBoxLayout())
        for embedding_name in self.embedding_names:
            embedding_widget = EmbeddingWidget(
                app=self,
                name=embedding_name
            )
            self.register_embedding_widget(embedding_name, embedding_widget)
            container.layout().addWidget(embedding_widget)
        container.layout().addStretch()
        # self.tool_menu_widget.embeddings_container_widget.embeddings.setWidget(container)

    def get_list_of_available_embedding_names(self):
        embeddings_path = self.settings_manager.path_settings.embeddings_path or "embeddings"
        if embeddings_path == "embeddings":
            embeddings_path = os.path.join(self.settings_manager.path_settings.model_base_path, embeddings_path)
        return self.find_embeddings_in_path(embeddings_path)

    def find_embeddings_in_path(self, embeddings_path, tokens=None):
        if tokens is None:
            tokens = []
        if not os.path.exists(embeddings_path):
            return tokens
        if os.path.exists(embeddings_path):
            for f in os.listdir(embeddings_path):
                # check if f is directory
                if os.path.isdir(os.path.join(embeddings_path, f)):
                    return self.find_embeddings_in_path(os.path.join(embeddings_path, f), tokens)
                words = f.split(".")
                if words[-1] in ["pt", "ckpt", "pth", "safetensors"]:
                    words = words[:-1]
                words = ".".join(words).lower()
                tokens.append(words)
        return tokens

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

    def handle_generator_tab_changed(self):
        self.enable_embeddings()
        self.update()

    def handle_tab_section_changed(self):
        self.enable_embeddings()
        self.update()

    def release_tab_overrides(self):
        self.override_current_generator = None
        self.override_section = None

    def clear_all_prompts(self):
        for tab_section in self._tabs.keys():
            self.override_current_generator = tab_section
            for tab in self.tabs.keys():
                self.override_section = tab
                self.prompt = ""
                self.negative_prompt = ""
                self.generator_tab_widget.clear_prompts(tab_section, tab)
        self.override_current_generator = None
        self.override_section = None

    def show_prompt_browser(self):
        PromptBrowser(settings_manager=self.settings_manager, app=self)

    def save_prompt(self):
        self.settings_manager.create_saved_prompt(self.prompt, self.negative_prompt)

    def import_image(self):
        file_path, _ = self.display_import_image_dialog(
            directory=self.settings_manager.path_settings.image_path)
        if file_path == "":
            return
        self.canvas.load_image(file_path)
        self.canvas.update()

    def export_image(self):
        file_path, _ = self.display_file_export_dialog()
        if file_path == "":
            return
        self.canvas.save_image(file_path)

    def choose_image_export_path(self):
        # display a dialog to choose the export path
        path = QFileDialog.getExistingDirectory(None, "Select Directory")
        if path == "":
            return
        self.settings_manager.set_value("image_path", path)

    def display_file_export_dialog(self):
        return QFileDialog.getSaveFileName(
            self,
            "Export Image",
            "",
            "Image Files (*.png *.jpg *.jpeg *.gif)"
        )

    def display_import_image_dialog(self, label="Import Image", directory=""):
        return QFileDialog.getOpenFileName(
            self,
            label,
            directory,
            "Image Files (*.png *.jpg *.jpeg)"
        )

    def paste_image(self):
        self.canvas.paste_image_from_clipboard()
        self.canvas.current_layer.layer_widget.set_thumbnail()

    def copy_image(self):
        self.canvas.copy_image()

    def cut_image(self):
        self.canvas.cut_image()

    def show_image_interpolation(self):
        self.image_interpolation_window = ImageInterpolation(app=self, exec=False)
        self.image_interpolation_window.show()
        self.image_interpolation_window = None

    def show_deterministic_generation(self):
        if not self.deterministic_window:
            self.deterministic_window = DeterministicGenerationWindow(app=self, exec=False, images=self.deterministic_images, data=self.data)
            self.deterministic_window.show()
            self.deterministic_window = None
        else:
            self.deterministic_window.update_images(self.deterministic_images)

    def close_deterministic_generation_window(self):
        self.deterministic_window = None
        self.deterministic_data = None
        self.deterministic_images = None