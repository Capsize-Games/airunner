import os
import pickle
import platform
import subprocess
import sys
import webbrowser
from functools import partial

from PyQt6 import uic, QtCore
from PyQt6.QtCore import pyqtSlot, Qt, QThread, pyqtSignal, QObject, QTimer
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QApplication, QFileDialog, QMainWindow

from airunner.aihandler.enums import MessageCode
from airunner.aihandler.logger import Logger as logger
from airunner.aihandler.pyqt_client import OfflineClient
from airunner.aihandler.qtvar import MessageHandlerVar
from airunner.aihandler.settings import LOG_LEVEL
from airunner.aihandler.settings_manager import SettingsManager
from airunner.airunner_api import AIRunnerAPI
from airunner.data.db import session
from airunner.data.models import SplitterSection, Prompt, TabSection
from airunner.filters.windows.filter_base import FilterBase
from airunner.input_event_manager import InputEventManager
from airunner.mixins.history_mixin import HistoryMixin
from airunner.resources_rc import *
from airunner.settings import BASE_PATH
from airunner.utils import get_version, get_latest_version, auto_export_image, save_session, \
    create_airunner_paths, default_hf_cache_dir
from airunner.widgets.status.status_widget import StatusWidget
from airunner.windows.about.about import AboutWindow
from airunner.windows.deterministic_generation.deterministic_generation_window import DeterministicGenerationWindow
from airunner.windows.interpolation.image_interpolation import ImageInterpolation
from airunner.windows.main.templates.main_window_ui import Ui_MainWindow
from airunner.windows.model_merger import ModelMerger
from airunner.windows.prompt_browser.prompt_browser import PromptBrowser
from airunner.windows.settings.airunner_settings import SettingsWindow
from airunner.windows.update.update_window import UpdateWindow
from airunner.windows.video import VideoPopup


class MainWindow(
    QMainWindow,
    HistoryMixin
):
    api = None
    input_event_manager = None
    current_filter = None
    tqdm_callback_triggered = False
    _document_name = "Untitled"
    is_saved = False
    action = "txt2img"
    message_var = MessageHandlerVar()
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
    image_generated = pyqtSignal(bool)
    controlnet_image_generated = pyqtSignal(bool)
    generator_tab_changed_signal = pyqtSignal()
    tab_section_changed_signal = pyqtSignal()
    image_data = pyqtSignal(dict)

    @property
    def generate_signal(self):
        return self.generator_tab_widget.generate_signal

    @property
    def settings_manager(self):
        if self._settings_manager is None:
            self._settings_manager = SettingsManager(app=self)
        return self._settings_manager

    # @property
    # def current_prompt_generator_settings(self):
    #     """
    #     Convenience property to get the current prompt generator settings
    #     :return:
    #     """
    #     return self.settings_manager.prompt_generator_settings

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
    def generator_type(self):
        """
        Returns either stablediffusion, shapegif, kandinsky
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
        name = f"{self._document_name}{'*' if self.canvas and self.canvas.is_dirty else ''}"
        return f"{name} - {self.version}"

    @property
    def is_windows(self):
        return sys.platform.startswith("win") or sys.platform.startswith("cygwin") or sys.platform.startswith("msys")

    @property
    def image_path(self):
        return self.settings_manager.path_settings.image_path

    @property
    def is_maximized(self):
        return self.settings_manager.is_maximized

    @is_maximized.setter
    def is_maximized(self, val):
        self.settings_manager.set_value("is_maximized", val)

    @property
    def current_layer(self):
        return self.ui.layer_widget.current_layer

    @property
    def current_layer_image_data(self):
        return self.ui.layer_widget.current_layer.image_data

    def send_message(self, code, message):
        self.message_var.emit({
            "code": code,
            "message": message,
        })

    def available_model_names_by_section(self, section):
        for model in self.settings_manager.available_models_by_category(section):
            yield model["name"]
    loaded = pyqtSignal()
    def __init__(self, *args, **kwargs):
        logger.info("Starting AI Runnner")
        # qdarktheme.enable_hi_dpi()

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

        self.register_keypress()

        if not self.testing:
            logger.info("Executing window")
            self.display()
        self.set_window_state()
        self.is_started = True

        # change the color of tooltips
        #self.setStyleSheet("QToolTip { color: #000000; background-color: #ffffff; border: 1px solid black; }")

        self.status_widget = StatusWidget()
        self.statusBar().addPermanentWidget(self.status_widget)
        self.clear_status_message()

        # create paths if they do not exist
        create_airunner_paths()

        #self.ui.layer_widget.initialize()

        self.ui.toggle_grid_button.setChecked(self.settings_manager.grid_settings.show_grid)
        self.ui.safety_checker_button.setChecked(self.settings_manager.nsfw_filter)

        self.ui.layer_widget.initialize()

        # call a function after the window has finished loading:
        QTimer.singleShot(500, self.on_show)

        self.ui.mode_tab_widget.tabBar().hide()

        self.ui.image_generation_button.blockSignals(True)
        self.ui.language_processing_button.blockSignals(True)

        print(self.settings_manager.mode)
        self.ui.image_generation_button.setChecked(
            self.settings_manager.mode == "Image Generation"
        )
        self.ui.language_processing_button.setChecked(
            self.settings_manager.mode == "Language Processing"
        )
        
        self.ui.image_generation_button.blockSignals(False)
        self.ui.language_processing_button.blockSignals(False)

        self.initialize_panel_tabs()
        self.loaded.emit()

    def initialize_panel_tabs(self):
        """
        Iterate over each TabSection entry from database and set the active tab
        for each panel section.
        :return:
        """
        self.ui.mode_tab_widget.currentChanged.connect(self.mode_tab_index_changed)
        tabsections = session.query(TabSection).filter(
            TabSection.panel != "generator_tabs"
        ).all()
        for ts in tabsections:
            widget = getattr(self.ui, ts.panel)
            for i in range(widget.count()):
                if widget.tabText(i) == ts.active_tab:
                    widget.setCurrentIndex(i)
                    break

        for i in range(self.ui.mode_tab_widget.count()):
            if self.ui.mode_tab_widget.tabText(i) == self.settings_manager.mode:
                self.ui.mode_tab_widget.setCurrentIndex(i)
                break

    def mode_tab_index_changed(self, index):
        self.settings_manager.set_value("mode", self.ui.mode_tab_widget.tabText(index))

    def on_show(self):
        self.ui.canvas_plus_widget.do_draw()

    def action_slider_changed(self, value_name, value):
        self.settings_manager.set_value(value_name, value)

    def quick_export(self):
        if os.path.isdir(self.image_path) is False:
            self.choose_image_export_path()
        if os.path.isdir(self.image_path) is False:
            return
        path = auto_export_image(self.ui.layer_widget.current_layer.image_data.image, seed=self.seed)
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
        self.canvas.paste_image_from_clipboard()

    def action_copy_image_triggered(self):
        if self.settings_manager.mode == "Image Generation":
            self.canvas.copy_image()

    def action_cut_image_triggered(self):
        self.canvas.cut_image()

    def action_rotate_90_clockwise_triggered(self):
        self.canvas.rotate_90_clockwise()

    def action_rotate_90_counterclockwise_triggered(self):
        self.canvas.rotate_90_counterclockwise()

    def action_show_prompt_browser_triggered(self):
        self.show_prompt_browser()

    def action_show_image_interpolation_triggered(self):
        self.show_image_interpolation()

    def action_clear_all_prompts_triggered(self):
        self.clear_all_prompts()

    def action_show_deterministic_batches(self):
        self.show_section("Deterministic Batches")

    def action_show_standard_batches(self):
        self.show_section("Standard Batches")

    def action_show_model_manager(self):
        self.show_section("Model Manager")

    def action_show_prompt_builder(self):
        self.show_section("Prompt Builder")

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
        self.show_section("Stable Diffusion")

    def action_show_kandinsky(self):
        self.show_section("Kandinsky")

    def action_show_shape(self):
        self.show_section("Shap-e")

    def action_triggered_browse_ai_runner_path(self):
        path = self.settings_manager.path_settings.base_path
        if path == "":
            path = BASE_PATH
        self.show_path(path)

    def action_show_hf_cache_manager(self):
        self.show_settings_path("hf_cache_path", default_hf_cache_dir())

    def action_show_images_path(self):
        self.show_settings_path("image_path")
    
    def action_show_videos_path(self):
        self.show_settings_path("video_path")
    
    def action_show_gifs_path(self):
        self.show_settings_path("gif_path")
    
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

    def refresh_available_models(self):
        self.generator_tab_widget.refresh_models()

    def show_settings_path(self, name, default_path=None):
        path = getattr(self.settings_manager.path_settings, name)
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
        self.ui.canvas_plus_widget.update()
        # self.canvas.update()

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
        tab_section = session.query(TabSection).filter_by(
            panel="tool_tab_widget"
        ).first()
        tab_section.active_tab = self.ui.tool_tab_widget.tabText(index)
        session.commit()

    def center_panel_tab_index_changed(self, int):
        tab_section = session.query(TabSection).filter_by(
            panel="center_tab"
        ).first()
        tab_section.active_tab = self.ui.center_tab.tabText(int)
        session.commit()

    def batches_panel_tab_index_changed(self, index):
        tab_section = session.query(TabSection).filter_by(
            panel="batches_tab"
        ).first()
        tab_section.active_tab = self.ui.batches_tab.tabText(index)
        session.commit()

    def bottom_panel_tab_index_changed(self, index):
        tab_section = session.query(TabSection).filter_by(
            panel="bottom_panel_tab_widget"
        ).first()
        tab_section.active_tab = self.ui.bottom_panel_tab_widget.tabText(index)
        session.commit()

    def right_splitter_moved(self, size, index):
        print("right_splitter_moved")

    def main_splitter_moved(self, size, index):
        print("main_splitter_moved")

    def content_splitter_moved(self, size, index):
        print("content_splitter_moved")

    """
    End slot functions
    """

    def set_size_increment_levels(self):
        size = self.grid_size
        self.ui.width_slider_widget.slider_single_step = size
        self.ui.width_slider_widget.slider_tick_interval = size

        self.ui.height_slider_widget.slider_single_step = size
        self.ui.height_slider_widget.slider_tick_interval = size

        self.canvas.update()

    def toggle_nsfw_filter(self):
        # self.canvas.update()
        self.set_nsfw_filter_tooltip()

    def set_nsfw_filter_tooltip(self):
        nsfw_filter = self.settings_manager.nsfw_filter
        self.ui.safety_checker_button.setToolTip(
            f"Click to {'enable' if not nsfw_filter else 'disable'} NSFW filter"
        )

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
        # self.canvas.is_canvas_drag_mode = True
        pass

    def dragmode_released(self):
        # self.canvas.is_canvas_drag_mode = False
        pass

    def shift_pressed(self):
        # self.canvas.shift_is_pressed = True
        pass

    def shift_released(self):
        # self.canvas.shift_is_pressed = False
        pass

    def register_keypress(self):
        self.input_event_manager.register_keypress("fullscreen", self.toggle_fullscreen)
        self.input_event_manager.register_keypress("control_pressed", self.dragmode_pressed, self.dragmode_released)
        self.input_event_manager.register_keypress("shift_pressed", self.shift_pressed, self.shift_released)
        #self.input_event_manager.register_keypress("delete_outside_active_grid_area", self.canvas.delete_outside_active_grid_area)

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
        # self.canvas.timerEvent(event)
        self.status_widget.update_system_stats(queue_size=self.client.queue.qsize())

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
        self.canvas.reset_settings()

    def on_state_changed(self, state):
        if state == Qt.ApplicationState.ApplicationActive:
            self.canvas.pos_x = int(self.x() / 4)
            self.canvas.pos_y = int(self.y() / 2)
            self.canvas.update()

    def set_stylesheet(self):
        """
        Sets the stylesheet for the application based on the current theme
        """
        logger.info("Setting stylesheets")
        theme_name = "dark_theme"
        here = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(here, "..", "..", "styles", theme_name, "styles.qss"), "r") as f:
            stylesheet = f.read()
        self.setStyleSheet(stylesheet)

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
        try:
            self.prompt_builder.process_prompt()
        except AttributeError:
            pass
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
        #self.prompt_builder.inject_prompt()
        pass

    def initialize_default_buttons(self):
        pass

    @pyqtSlot(dict)
    def handle_button_clicked(self, kwargs):
        action = kwargs.get("action", "")
        if action == "toggle_tool":
            self.toggle_tool(kwargs["tool"])

    def toggle_tool(self, tool):
        self.settings_manager.set_value("current_tool", tool)
        self.ui.canvas_plus_widget.update_cursor()

    def initialize_mixins(self):
        HistoryMixin.initialize(self)
        #self.canvas = Canvas()

    def connect_signals(self):
        logger.info("Connecting signals")
        #self.canvas._is_dirty.connect(self.set_window_title)

        for signal, handler in self.registered_settings_handlers:
            getattr(self.settings_manager, signal).connect(handler)

        self.button_clicked_signal.connect(self.handle_button_clicked)

    def connect_splitter_handlers(self):
        self.ui.content_splitter.splitterMoved.connect(self.handle_main_splitter_moved)
        self.ui.main_splitter.splitterMoved.connect(self.handle_bottom_splitter_moved)

    def show_section(self, section):
        section_lists = {
            "left": [self.ui.generator_widget.ui.generator_tabs.tabText(i) for i in range(self.ui.generator_widget.ui.generator_tabs.count())],
            "center": [self.ui.center_tab.tabText(i) for i in range(self.ui.center_tab.count())],
            "right": [self.ui.tool_tab_widget.tabText(i) for i in range(self.ui.tool_tab_widget.count())],
            "right_center": [self.ui.batches_tab.tabText(i) for i in range(self.ui.batches_tab.count())],
            "bottom": [self.ui.bottom_panel_tab_widget.tabText(i) for i in range(self.ui.bottom_panel_tab_widget.count())]
        }
        for k, v in section_lists.items():
            if section in v:
                if k == "left":
                    self.ui.generator_widget.ui.generator_tabs.setCurrentIndex(v.index(section))
                elif k == "right":
                    self.ui.tool_tab_widget.setCurrentIndex(v.index(section))
                elif k == "right_center":
                    self.ui.batches_tab.setCurrentIndex(v.index(section))
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
            Canvas is in the center panel..
            Tool menus are in the right panel.
        center_splitter
            Vertical
            Allows multiple grids or additional panels in the center area.
        right_panel_splitter divides the right panel into sections
            Vertical
            Currently used for tool menus (embeddings, layers etc.).
        :return:
        """
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
        elif key == "generator.seed":
            self.prompt_builder.process_prompt()
        elif key == "use_prompt_builder_checkbox":
            self.generator_tab_widget.toggle_all_prompt_builder_checkboxes(value)
        elif key == "models":
            self.model_manager.models_changed(key, value)

    def initialize_shortcuts(self):
        event_callbacks = {
            "wheelEvent": self.handle_wheel_event,
        }

        for event, callback in event_callbacks.items():
            self.input_event_manager.register_event(event, callback)

    def initialize_handlers(self):
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
        self.set_stylesheet()
        if not self.testing:
            self.show()
        else:
            # do not show the window when testing, otherwise it will block the tests
            # self.hide()
            # the above solution doesn't work, gives this error:
            # QBasicTimer::start: QBasicTimer can only be used with threads started with QThread
            # so instead we do this in order to run without showing the window:
            self.showMinimized()

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

    def handle_wheel_event(self, event):
        grid_size = self.grid_size

        # if the shift key is pressed
        try:
            if QtCore.Qt.KeyboardModifier.ShiftModifier in event.modifiers():
                delta = event.angleDelta().y()
                increment = grid_size if delta > 0 else -grid_size
                val = self.settings_manager.working_width + increment
                self.settings_manager.set_value("working_width", val)
        except TypeError:
            pass

        # if the control key is pressed
        try:
            if QtCore.Qt.KeyboardModifier.ControlModifier in event.modifiers():
                delta = event.angleDelta().y()
                increment = grid_size if delta > 0 else -grid_size
                val = self.settings_manager.working_height + increment
                self.settings_manager.set_value("working_height", val)
        except TypeError:
            pass

    # def toggle_stylesheet(self, path):
    #     # use fopen to open the file
    #     # read the file
    #     # set the stylesheet
    #     with open(path, "r") as stream:
    #         self.setStyleSheet(stream.read())

    def set_window_title(self):
        """
        Overrides base method to set the window title
        :return:
        """
        self.setWindowTitle(f"AI Runner {self.document_name}")

    def new_document(self):
        self.ui.layer_widget.clear_layers()
        self.clear_history()
        self.is_saved = False
        self._document_name = "Untitled"
        self.set_window_title()
        self.current_filter = None
        #self.canvas.update()
        self.ui.layer_widget.show_layers()

    def set_status_label(self, txt, error=False):
        # color = self.status_normal_color_dark if self.is_dark else \
        #     self.status_normal_color_light
        # self.footer_widget.ui.status_label.setText(txt)
        # self.footer_widget.ui.status_label.setStyleSheet(
        #     f"color: {self.status_error_color if error else color};"
        # )
        if self.status_widget:
            self.status_widget.set_system_status(txt, error)

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
        }.get(code, lambda *args: None)(message)
    
    def handle_controlnet_image_generated(self, message):
        self.controlnet_image = message["image"]
        self.controlnet_image_generated.emit(True)
        self.generator_tab_widget.controlnet_settings_widget.handle_controlnet_image_generated()

    def video_handler(self, data):
        filename = data["video_filename"]
        VideoPopup(settings_manager=self.settings_manager, file_path=filename)

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
                "action"] != "outpaint" and self.settings_manager.image_to_new_layer and self.ui.layer_widget.current_layer.image_data.image is not None:
                self.ui.layer_widget.add_layer()
            # print width and height of image
            # self.canvas.image_handler(images[0], data)
            self.image_data.emit({
                "image": images[0],
                "data": data
            })
            self.message_handler("")
            self.ui.layer_widget.show_layers()

        self.image_generated.emit(True)

    def post_process_images(self, images):
        #return self.automatic_filter_manager.apply_filters(images)
        return images

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
        # save self.ui.layer_widget.layers as pickle
        layers = []
        # we need to save self.ui.layer_widget.layers but it contains a QWdget
        # so we will remove the QWidget from each layer, add the layer to a new
        # list and then restore the QWidget
        layer_widgets = []
        for layer in self.ui.layer_widget.layers:
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
        self.ui.layer_widget.layers = layers
        self.canvas.image_pivot_point = image_pivot_point
        self.canvas.image_root_point = image_root_point
        self.canvas.update()
        self.is_saved = True
        self.set_window_title()
        self.ui.layer_widget.show_layers()

    def update(self):
        self.generator_tab_widget.update_thumbnails()

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
        self.update()
        self.generator_tab_changed_signal.emit()

    def handle_tab_section_changed(self):
        self.update()
        self.tab_section_changed_signal.emit()

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

    def import_image(self):
        file_path, _ = self.display_import_image_dialog(
            directory=self.settings_manager.path_settings.image_path)
        if file_path == "":
            return
        self.ui.canvas_plus_widget.load_image(file_path)

    def export_image(self):
        file_path, _ = self.display_file_export_dialog()
        if file_path == "":
            return
        self.ui.canvas_plus_widget.save_image(file_path)

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

    def load_prompt(self, prompt: Prompt):
        """
        Loads prompt values from a Prompt model instance.
        :param prompt: PromptModel
        :return:
        """
        self.update_prompt(prompt.prompt)
        self.update_negative_prompt(prompt.negative_prompt)

    def update_prompt(self, prompt_value):
        self.generator_tab_widget.update_prompt(prompt_value)

    def update_negative_prompt(self, prompt_value):
        self.generator_tab_widget.update_negative_prompt(prompt_value)

    def new_batch(self, index, image, data):
        self.generator_tab_widget.current_generator.new_batch(index, image, data)

    def image_generation_toggled(self, val):
        self.ui.mode_tab_widget.setCurrentIndex(0 if val else 1)
        self.ui.language_processing_button.setChecked(not val)

    def language_processing_toggled(self, val):
        self.ui.mode_tab_widget.setCurrentIndex(1 if val else 0)
        self.ui.image_generation_button.setChecked(not val)