import os
import pickle
import signal
import sys
import traceback
from functools import partial
import psutil
import torch
from PyQt6 import uic, QtCore
from PyQt6.QtWidgets import QApplication, QFileDialog, QSplashScreen, QMainWindow, QSplitter, QTabWidget, QWidget, \
    QVBoxLayout
from PyQt6.QtCore import pyqtSlot, Qt, QThread, pyqtSignal, QObject, QTimer
from PyQt6.QtGui import QGuiApplication, QPixmap, QShortcut, QKeySequence
from aihandler.qtvar import TQDMVar, ImageVar, MessageHandlerVar, ErrorHandlerVar
from aihandler.logger import logger
from aihandler.settings import LOG_LEVEL, MessageCode
from airunner.mixins.canvas_mixin import CanvasMixin
from airunner.mixins.comic_mixin import ComicMixin
from airunner.mixins.extension_mixin import ExtensionMixin
from airunner.mixins.generator_mixin import GeneratorMixin
from airunner.mixins.history_mixin import HistoryMixin
from airunner.mixins.menubar_mixin import MenubarMixin
from airunner.mixins.toolbar_mixin import ToolbarMixin
from airunner.themes import Themes
from airunner.widgets.canvas_widget import CanvasWidget
from airunner.widgets.embedding_widget import EmbeddingWidget
from airunner.widgets.footer_widget import FooterWidget
from airunner.widgets.generator_tab_widget import GeneratorTabWidget
from airunner.widgets.prompt_builder import PromptBuilderWidget
from airunner.widgets.tool_bar_widget import ToolBarWidget
from airunner.widgets.tool_menu_widget import ToolMenuWidget
from airunner.widgets.header_widget import HeaderWidget
from airunner.windows.deterministic_generation_window import DeterministicGenerationWindow
from airunner.windows.update_window import UpdateWindow
from airunner.utils import get_version, get_latest_version
from aihandler.settings_manager import SettingsManager, PromptManager
from airunner.runai_client import OfflineClient
import qdarktheme
from PyQt6.QtGui import QIcon


class MainWindow(
    QMainWindow,
    ToolbarMixin,
    HistoryMixin,
    MenubarMixin,
    CanvasMixin,
    GeneratorMixin,
    ComicMixin,
    ExtensionMixin
):
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
    settings_manager = None
    prompts_manager = None
    models = None
    client = None
    _override_section = None
    _override_tab_section = None
    _version = None
    _latest_version = None
    use_interpolation = None
    add_image_to_canvas_signal = pyqtSignal(dict)
    data = None  # this is set in the generator_mixin image_handler function and used for deterministic generation
    status_error_color = "#ff0000"
    status_normal_color_light = "#000000"
    status_normal_color_dark = "#ffffff"
    is_started = False

    _embedding_names = None
    embedding_widgets = {}
    bad_model_embedding_map = {}

    @property
    def embedding_names(self):
        if self._embedding_names is None:
            self._embedding_names = self.get_list_of_available_embedding_names()
        return self._embedding_names

    @property
    def is_dark(self):
        return self.settings_manager.settings.dark_mode_enabled.get()

    @property
    def grid_size(self):
        return self.settings_manager.settings.size.get()

    @property
    def override_section(self):
        return self._override_section

    @override_section.setter
    def override_section(self, val):
        self._override_section = val

    @property
    def override_tab_section(self):
        return self._override_tab_section

    @override_tab_section.setter
    def override_tab_section(self, val):
        self._override_tab_section = val

    @property
    def canvas_position(self):
        return self.canvas_widget.canvas_position

    @canvas_position.setter
    def canvas_position(self, val):
        self.canvas_widget.canvas_position.setText(val)

    _tabs = {
        "stablediffusion": {
            "txt2img": None,
            "img2img": None,
            "outpaint": None,
            "depth2img": None,
            "pix2pix": None,
            "upscale": None,
            "superresolution": None,
            "txt2vid": None
        },
        "kandinsky": {
            "txt2img": None,
            "img2img": None,
            "outpaint": None,
        },
        "shapegif": {
            "txt2img": None,
            "img2img": None,
        }
    }

    @property
    def currentTabSection(self):
        if self.override_tab_section:
            return self.override_tab_section
        return list(self._tabs.keys())[self.generator_tab_widget.sectionTabWidget.currentIndex()]

    @property
    def tabs(self):
        return self._tabs[self.currentTabSection]

    @tabs.setter
    def tabs(self, val):
        self._tabs[self.currentTabSection] = val

    @property
    def tabWidget(self):
        if self.currentTabSection == "stablediffusion":
            return self.generator_tab_widget.stableDiffusionTabWidget
        elif self.currentTabSection == "kandinsky":
            return self.generator_tab_widget.kandinskyTabWidget
        elif self.currentTabSection == "shapegif":
            return self.generator_tab_widget.shapegifTabWidget
        else:
            raise Exception("Invalid tab section")

    @property
    def generator_type(self):
        """
        Returns either stablediffusion, shapegif, kandinsky
        :return: string
        """
        return self._generator_type

    @property
    def current_index(self):
        return self.tabWidget.currentIndex()

    @property
    def current_section(self):
        if self.override_section:
            return self.override_section
        return list(self._tabs[self.currentTabSection].keys())[self.current_index]

    @property
    def use_pixels(self):
        # get name of current tab
        return self.current_section in (
            "txt2img",
            "img2img",
            "pix2pix",
            "depth2img",
            "outpaint",
            "controlnet",
            "superresolution",
            "upscale"
        )

    @property
    def settings(self):
        settings = self.settings_manager.settings
        settings.set_namespace(self.current_section, self.currentTabSection)
        return settings

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
        return self.settings_manager.settings.is_maximized.get()

    _themes = None
    @property
    def css(self):
        if self._themes is None:
            self._themes = Themes(self.settings_manager)
        return self._themes.css

    @is_maximized.setter
    def is_maximized(self, val):
        self.settings_manager.settings.is_maximized.set(val)

    def __init__(self, *args, **kwargs):
        logger.info("Starting AI Runnner...")
        # enable hardware acceleration
        qdarktheme.enable_hi_dpi()

        self.set_log_levels()
        self.testing = kwargs.pop("testing", False)
        super().__init__(*args, **kwargs)

        self.initialize()
        self.settings_manager.enable_save()
        # on window resize:
        # self.applicationStateChanged.connect(self.on_state_changed)

        if self.settings_manager.settings.latest_version_check.get():
            logger.info("Checking for latest version...")
            self.check_for_latest_version()

        # check for self.current_layer.lines every 100ms
        self.timer = self.startTimer(100)

        self.header_widget.set_size_increment_levels()
        self.clear_status_message()

        self.generate_shortcut = QShortcut(QKeySequence(Qt.Key.Key_F11), self)
        self.generate_shortcut.activated.connect(self.toggle_fullscreen)

        if not self.testing:
            logger.info("Executing window...")
            self.display()
        self.set_window_state()
        self.is_started = True

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

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Control:
            self.canvas.is_canvas_drag_mode = True

        if event.key() == Qt.Key.Key_Shift:
            self.canvas.shift_is_pressed = True

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key.Key_Control:
            self.canvas.is_canvas_drag_mode = False

        if event.key() == Qt.Key.Key_Shift:
            self.canvas.shift_is_pressed = False

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def quit(self):
        self.close()

    def closeEvent(self, event):
        logger.info("Quitting...")
        QApplication.quit()

    def timerEvent(self, event):
        self.canvas.timerEvent(event)
        self.update_system_stats()

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
        logger.info("Resetting settings...")
        # GeneratorMixin.reset_settings(self)
        self.canvas.reset_settings()

    def on_state_changed(self, state):
        if state == Qt.ApplicationState.ApplicationActive:
            self.canvas.pos_x = int(self.x() / 4)
            self.canvas.pos_y = int(self.y() / 2)
            self.canvas.update()

    def set_stylesheet(self):
        logger.info("Setting stylesheets...")
        try:
            qdarktheme.setup_theme("dark" if self.settings_manager.settings.dark_mode_enabled.get() else "light")
        except PermissionError:
            pass
        self.generator_tab_widget.set_stylesheet()
        self.header_widget.set_stylesheet()
        self.canvas_widget.set_stylesheet()
        self.tool_menu_widget.set_stylesheet()
        self.toolbar_widget.set_stylesheet()
        self.footer_widget.set_stylesheet()

    def initialize(self):
        self.initialize_settings_manager()
        self.instantiate_widgets()
        self.initialize_saved_prompts()
        self.initialize_handlers()
        self.initialize_window()
        self.initialize_widgets()
        self.initialize_mixins()
        self.header_widget.initialize()
        self.header_widget.set_size_increment_levels()
        self.initialize_shortcuts()
        self.initialize_stable_diffusion()
        if self.settings_manager.settings.force_reset.get():
            self.reset_settings()
            self.settings_manager.settings.force_reset.set(False)
        self.actionShow_Active_Image_Area.setChecked(
            self.settings_manager.settings.show_active_image_area.get() == True
        )
        self.connect_signals()

    def initialize_mixins(self):
        HistoryMixin.initialize(self)
        CanvasMixin.initialize(self)
        GeneratorMixin.initialize(self)
        MenubarMixin.initialize(self)
        ToolbarMixin.initialize(self)

    # a list of tuples that represents a signal name and its handler
    registered_settings_handlers = []

    def register_setting_handler(self, signal, handler):
        """
        Connect a signal to a handler. Signals must be part of settings_manager.settings
        in order to be registered later in the connect_signals() method.
        :param signal:
        :param handler:
        :return:
        """
        self.registered_settings_handlers.append((signal, handler))

    def connect_signals(self):
        logger.info("Connecting signals...")
        self.canvas._is_dirty.connect(self.set_window_title)

        for signal, handler in self.registered_settings_handlers:
            getattr(self.settings_manager.settings, signal).connect(handler)

        self.model_var.connect(self.enable_embeddings)
        self.settings_manager.settings.embeddings_path.my_signal.connect(self.update_embedding_names)
        self.seed_var.my_signal.connect(self.prompt_builder.process_prompt)
        self.settings_manager.settings.use_prompt_builder_checkbox.my_signal.connect(
            self.generator_tab_widget.toggle_all_prompt_builder_checkboxes
        )

    def instantiate_widgets(self):
        logger.info("Instantiating widgets...")
        self.generator_tab_widget = GeneratorTabWidget(app=self)
        self.header_widget = HeaderWidget(app=self)
        self.canvas_widget = CanvasWidget(app=self)
        self.tool_menu_widget = ToolMenuWidget(app=self)
        self.toolbar_widget = ToolBarWidget(app=self)
        self.footer_widget = FooterWidget(app=self)

    def initialize_widgets(self):
        logger.info("Initializing widgets...")
        self.gridLayout.setColumnStretch(1, 1)
        self.gridLayout.addWidget(self.header_widget, 0, 0, 1, 4)

        self.splitter = QSplitter()
        self.center_splitter = QSplitter(Qt.Orientation.Vertical)
        self.prompt_builder = PromptBuilderWidget(app=self)
        center_panel = QTabWidget()
        center_panel.setStyleSheet(self.css("center_panel"))
        center_panel.setTabPosition(QTabWidget.TabPosition.South)
        center_panel.addTab(self.prompt_builder, "Prompt Builder")
        # auto hide tabs
        center_panel.tabBar().hide()
        self.center_splitter.setStretchFactor(1, 1)
        self.center_splitter.setStretchFactor(2, 0)
        self.splitter.addWidget(self.generator_tab_widget)
        self.center_splitter.addWidget(self.canvas_widget)
        self.center_splitter.addWidget(center_panel)
        # listen to center_splitter size changes
        self.center_splitter.splitterMoved.connect(self.handle_bottom_splitter_moved)
        self.splitter.addWidget(self.center_splitter)
        self.splitter.addWidget(self.tool_menu_widget)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.splitterMoved.connect(self.handle_main_splitter_moved)
        self.gridLayout.addWidget(self.splitter, 1, 0, 1, 3)
        self.gridLayout.addWidget(self.toolbar_widget, 1, 3, 1, 1)
        self.gridLayout.addWidget(self.footer_widget, 2, 0, 1, 4)

    def set_splitter_sizes(self):
        bottom_sizes = self.settings_manager.settings.bottom_splitter_sizes.get()
        main_sizes = self.settings_manager.settings.main_splitter_sizes.get()
        if bottom_sizes[1] == -1:
            bottom_sizes[1] = 520
        if main_sizes[0] == -1:
            main_sizes[0] = self.generator_tab_widget.minimumWidth()
        if main_sizes[1] == -1:
            main_sizes[1] = 520
        if main_sizes[2] == -1:
            main_sizes[2] = self.tool_menu_widget.minimumWidth()
        self.center_splitter.setSizes(bottom_sizes)
        self.splitter.setSizes(main_sizes)

    def handle_main_splitter_moved(self, pos, index):
        left_width = self.splitter.widget(0).width()
        center_width = self.splitter.widget(1).width()
        right_width = self.splitter.widget(2).width()
        window_width = self.width()
        if index == 2 and window_width - pos == 60:
            right_width = 0
        if index == 1 and pos == 1:
            left_width = 0
        current_sizes = self.settings_manager.settings.main_splitter_sizes.get()
        if index == 1:
            right_width = current_sizes[2]
        if index == 2:
            left_width = current_sizes[0]
        self.settings_manager.settings.main_splitter_sizes.set([left_width, center_width, right_width])

    def handle_bottom_splitter_moved(self, pos, index):
        top_height = self.center_splitter.widget(0).height()
        bottom_height = self.center_splitter.widget(1).height()
        self.settings_manager.settings.bottom_splitter_sizes.set([top_height, bottom_height])

    def initialize_saved_prompts(self):
        self.prompts_manager = PromptManager()
        self.prompts_manager.enable_save()

    def initialize_settings_manager(self):
        self.settings_manager = SettingsManager()
        self.settings_manager.disable_save()
        # self.get_extensions_from_path()  TODO: Extensions
        self.settings_manager.settings.size.my_signal.connect(self.set_size_form_element_step_values)
        self.settings_manager.settings.line_width.my_signal.connect(self.set_size_form_element_step_values)

    def initialize_shortcuts(self):
        # on shift + mouse scroll change working width
        self.wheelEvent = self.change_width

    def initialize_handlers(self):
        self.message_var = MessageHandlerVar()
        self.message_var.my_signal.connect(self.message_handler)

    def initialize_window(self):
        HERE = os.path.dirname(os.path.abspath(__file__))
        self.window = uic.loadUi(os.path.join(HERE, "pyqt/main_window_new.ui"), self)
        self.center()
        self.set_window_title()
        self.set_window_icon()

    def initialize_stable_diffusion(self):
        logger.info("Initializing stable diffusion...")
        self.client = OfflineClient(
            app=self,
            message_var=self.message_var,
            settings_manager=self.settings_manager,
        )

    def save_settings(self):
        self.settings_manager.save_settings()

    def display(self):
        logger.info("Displaying window...")
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

    def set_window_icon(self):
        self.setWindowIcon(QIcon("src/icon_256.png"))

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
        color = self.status_normal_color_dark if self.is_dark else \
            self.status_normal_color_light
        self.footer_widget.status_label.setText(txt)
        self.footer_widget.status_label.setStyleSheet(
            f"color: {self.status_error_color if error else color};"
        )

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
            MessageCode.EMBEDDING_LOAD_FAILED: self.handle_embedding_load_failed,
        }.get(code, self.handle_unknown)(message)

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

        if self.settings_manager.settings.auto_export_images.get():
            self.auto_export_image(images[0], data)

        self.generator_tab_widget.stop_progress_bar(
            data["tab_section"], data["action"]
        )
        if nsfw_content_detected and self.settings_manager.settings.nsfw_filter.get():
            self.message_handler("NSFW content detected, try again.", error=True)
        elif data["options"][f"deterministic_generation"]:
            self.deterministic_images = images
            DeterministicGenerationWindow(
                self.settings_manager,
                app=self,
                images=self.deterministic_images,
                data=data)
        else:
            if data[
                "action"] != "outpaint" and self.image_to_new_layer and self.canvas.current_layer.image_data.image is not None:
                self.canvas.add_layer()
            # print width and height of image
            self.canvas.image_handler(images[0], data)
            self.message_handler("")
            self.canvas.show_layers()

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
        self.header_widget.set_size_increment_levels()

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

    def update_system_stats(self):
        system_memory_percentage = psutil.virtual_memory().percent
        cuda_memory = f"VRAM allocated {torch.cuda.memory_allocated() / 1024 ** 3:.1f}GB cached {torch.cuda.memory_cached() / 1024 ** 3:.1f}GB"
        system_memory = f"RAM {system_memory_percentage:.1f}%"
        self.footer_widget.system_status.setText(f"{system_memory}, {cuda_memory}")

    def update_embedding_names(self, _):
        self._embedding_names = None
        for tab_name in self.tabs.keys():
            tab = self.tabs[tab_name]
            # clear embeddings
            try:
                tab.embeddings.widget().deleteLater()
            except AttributeError:
                pass
            self.load_embeddings(tab)

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
        self.tool_menu_widget.embeddings_container_widget.embeddings.setWidget(container)

    def get_list_of_available_embedding_names(self):
        embeddings_path = self.settings_manager.settings.embeddings_path.get() or "embeddings"
        if embeddings_path == "embeddings":
            embeddings_path = os.path.join(self.settings_manager.settings.model_base_path.get(), embeddings_path)
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
        prompt_widget = self.generator_tab_widget.data[self.currentTabSection][self.current_section]["prompt_widget"]
        negative_prompt_widget = self.generator_tab_widget.data[self.currentTabSection][self.current_section]["negative_prompt_widget"]
        if negative_prompt:
            current_text = negative_prompt_widget.toPlainText()
            text = f"{current_text}, {text}" if current_text != "" else text
            negative_prompt_widget.setPlainText(text)
        else:
            current_text = prompt_widget.toPlainText()
            text = f"{current_text}, {text}" if current_text != "" else text
            prompt_widget.setPlainText(text)


if __name__ == "__main__":
    def signal_handler(signal, frame):
        print("\nExiting...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseDesktopOpenGL)
    app = QApplication([])

    def display_splash_screen(app):
        screens = QGuiApplication.screens()
        try:
            screen = screens.at(0)
        except AttributeError:
            screen = screens[0]
        pixmap = QPixmap("src/splashscreen.png")
        splash = QSplashScreen(screen, pixmap, QtCore.Qt.WindowType.WindowStaysOnTopHint)
        splash.show()
        # make message white
        splash.showMessage(f"Loading AI Runner v{get_version()}", QtCore.Qt.AlignmentFlag.AlignBottom | QtCore.Qt.AlignmentFlag.AlignCenter, QtCore.Qt.GlobalColor.white)
        app.processEvents()
        return splash

    splash = display_splash_screen(app)

    def show_main_application(splash):
        try:
            window = MainWindow()
        except Exception as e:
            # print a stacktrace to see where the original error occurred
            # we want to see the original error path using the traceback
            traceback.print_exc()

            print(e)
            splash.finish(None)
            sys.exit("""
                An error occurred while initializing the application. 
                Please report this issue on GitHub or Discord."
            """)
        splash.finish(window)
        window.raise_()

    QTimer.singleShot(50, partial(show_main_application, splash))

    sys.exit(app.exec())
