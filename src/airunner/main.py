import os
import pickle
import sys
from functools import partial
import psutil
import torch
from PyQt6 import uic, QtCore
from PyQt6.QtWidgets import QApplication, QFileDialog, QSplashScreen, QMainWindow, QLabel, QVBoxLayout, QDialog, \
    QSplitter
from PyQt6.QtCore import pyqtSlot, Qt, QThread, pyqtSignal, QObject, QTimer, QEvent
from PyQt6.QtGui import QGuiApplication, QPixmap, QShortcut, QKeySequence, QKeyEvent
from aihandler.qtvar import TQDMVar, ImageVar, MessageHandlerVar, ErrorHandlerVar
from aihandler.logger import logger
from aihandler.settings import LOG_LEVEL
from airunner.mixins.canvas_mixin import CanvasMixin
from airunner.mixins.comic_mixin import ComicMixin
from airunner.mixins.embedding_mixin import EmbeddingMixin
from airunner.mixins.extension_mixin import ExtensionMixin
from airunner.mixins.generator_mixin import GeneratorMixin
from airunner.mixins.history_mixin import HistoryMixin
from airunner.mixins.menubar_mixin import MenubarMixin
from airunner.mixins.toolbar_mixin import ToolbarMixin
from airunner.themes import Themes
from airunner.widgets.canvas_widget import CanvasWidget
from airunner.widgets.footer_widget import FooterWidget
from airunner.widgets.generator_tab_widget import GeneratorTabWidget
from airunner.widgets.tool_bar_widget import ToolBarWidget
from airunner.widgets.tool_menu_widget import ToolMenuWidget
from airunner.widgets.header_widget import HeaderWidget
from airunner.windows.update_window import UpdateWindow
from airunner.utils import get_version, get_latest_version
from aihandler.settings_manager import SettingsManager, PromptManager
from airunner.runai_client import OfflineClient
import qdarktheme
from PyQt6.QtGui import QIcon


class MainWindow(
    QMainWindow,
    EmbeddingMixin,
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
    tqdm_var = None
    message_var = None
    error_var = None
    image_var = None
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
            "txt2vid": None,
        },
        "kandinsky": {
            "txt2img": None,
            "img2img": None,
            "outpaint": None,
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
        else:
            return self.generator_tab_widget.kandinskyTabWidget

    @property
    def generator_type(self):
        """
        Returns either stablediffusion or kandinsky
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

    @pyqtSlot(int, int, str, object, object)
    def tqdm_callback(self, step, total, action, image=None, data=None):
        if step == 0 and total == 0:
            current = 0
        else:
            if self.progress_bar_started and not self.tqdm_callback_triggered:
                self.tqdm_callback_triggered = True
                self.tabs[action].progressBar.setRange(0, 100)
            try:
                current = (step / total)
            except ZeroDivisionError:
                current = 0
        self.tabs[action].progressBar.setValue(int(current * 100))

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
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseDesktopOpenGL)
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
        GeneratorMixin.reset_settings(self)
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
        self.instantiate_widgets()
        self.initialize_saved_prompts()
        self.initialize_settings_manager()
        self.initialize_tqdm()
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
        EmbeddingMixin.initialize(self)

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

        splitter = QSplitter()
        splitter.addWidget(self.generator_tab_widget)
        splitter.addWidget(self.canvas_widget)
        splitter.addWidget(self.tool_menu_widget)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([self.generator_tab_widget.minimumWidth(), 520, self.tool_menu_widget.minimumWidth()])
        self.gridLayout.addWidget(splitter, 1, 0, 1, 3)
        self.gridLayout.addWidget(self.toolbar_widget, 1, 3, 1, 1)
        self.gridLayout.addWidget(self.footer_widget, 2, 0, 1, 4)

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

    def initialize_tqdm(self):
        self.tqdm_var = TQDMVar()
        self.tqdm_var.my_signal.connect(self.tqdm_callback)

    def initialize_handlers(self):
        self.message_var = MessageHandlerVar()
        self.message_var.my_signal.connect(self.message_handler)
        self.error_var = ErrorHandlerVar()
        self.error_var.my_signal.connect(self.error_handler)
        self.image_var = ImageVar()
        self.image_var.my_signal.connect(self.image_handler)

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
            tqdm_var=self.tqdm_var,
            image_var=self.image_var,
            error_var=self.error_var,
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
            print("is_maximized")
            self.showMaximized()
        else:
            print("is_normal")
            self.showNormal()

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
        CanvasMixin.initialize(self)
        self.is_saved = False
        self.canvas.is_dirty = False
        self._document_name = "Untitled"
        self.set_window_title()
        # clear the layers list widget
        #self.tool_menu_widget.layers.setWidget(None)
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

    def message_handler(self, msg):
        if isinstance(msg, dict):
            msg = msg["response"]
        self.set_status_label(msg)

    def error_handler(self, msg):
        if isinstance(msg, dict):
            msg = msg["response"]
        self.set_status_label(msg, error=True)

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
        data = {
            "layers": self.canvas.layers,
            "image_pivot_point": self.canvas.image_pivot_point,
            "image_root_point": self.canvas.image_root_point,
        }
        with open(document_name, "wb") as f:
            pickle.dump(data, f)
        # get the document name stripping .airunner from the end
        self._document_name = document_name.split("/")[-1].split(".")[0]
        self.set_window_title()
        self.is_saved = True
        self.canvas.is_dirty = False

    def save_document(self):
        if not self.is_saved:
            return self.saveas_document()
        document_name = f"{self._document_name}.airunner"
        self.do_save(document_name)

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


if __name__ == "__main__":
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
        splash.showMessage("Loading AI Runner v2.0.0", QtCore.Qt.AlignmentFlag.AlignBottom | QtCore.Qt.AlignmentFlag.AlignCenter, QtCore.Qt.GlobalColor.white)
        app.processEvents()
        return splash

    splash = display_splash_screen(app)

    def show_main_application(splash):
        window = MainWindow()
        splash.finish(window)
        window.raise_()

    QTimer.singleShot(50, partial(show_main_application, splash))

    sys.exit(app.exec())
