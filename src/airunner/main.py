import os
import pickle
import sys
from PyQt6 import uic, QtCore
from PyQt6.QtWidgets import QApplication, QFileDialog
from PyQt6.QtCore import pyqtSlot, Qt, QThread, pyqtSignal, QObject
from PyQt6.QtGui import QGuiApplication
from aihandler.qtvar import TQDMVar, ImageVar, MessageHandlerVar, ErrorHandlerVar
from aihandler.settings import LOG_LEVEL
from airunner.mixins.brushes_mixin import BrushesMixin
from airunner.mixins.canvas_mixin import CanvasMixin
from airunner.mixins.comic_mixin import ComicMixin
from airunner.mixins.embedding_mixin import EmbeddingMixin
from airunner.mixins.extension_mixin import ExtensionMixin
from airunner.mixins.generator_mixin import GeneratorMixin
from airunner.mixins.history_mixin import HistoryMixin
from airunner.mixins.layer_mixin import LayerMixin
from airunner.mixins.menubar_mixin import MenubarMixin
from airunner.mixins.toolbar_mixin import ToolbarMixin
from airunner.windows.update_window import UpdateWindow
from airunner.windows.video import VideoPopup
from airunner.utils import get_version, get_latest_version
from aihandler.settings_manager import SettingsManager
from airunner.runai_client import OfflineClient
import qdarktheme


class MainWindow(
    QApplication,
    EmbeddingMixin,
    LayerMixin,
    ToolbarMixin,
    HistoryMixin,
    MenubarMixin,
    CanvasMixin,
    GeneratorMixin,
    ComicMixin,
    ExtensionMixin,
    BrushesMixin,
):
    current_filter = None
    tabs = {}
    tqdm_callback_triggered = False
    _document_name = "Untitled"
    _is_dirty = False
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
    sections = [
        "txt2img",
        "img2img",
        "depth2img",
        "pix2pix",
        "outpaint",
        "controlnet",
        "upscale",
        "superresolution",
        "txt2vid",
    ]
    models = None
    client = None
    _override_section = None
    _version = None
    _latest_version = None

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
    def current_index(self):
        return self.window.tabWidget.currentIndex()

    @property
    def current_section(self):
        if self.override_section:
            return self.override_section
        return self.sections[self.current_index]

    @property
    def use_pixels(self):
        # get name of current tab
        return self.current_section in ("txt2img", "img2img", "pix2pix", "depth2img", "outpaint", "controlnet", "superresolution", "upscale")

    @property
    def settings(self):
        settings = self.settings_manager.settings
        settings.set_namespace(self.current_section)
        return settings

    @property
    def is_dirty(self):
        return self._is_dirty

    @is_dirty.setter
    def is_dirty(self, val):
        self._is_dirty = val
        self.set_window_title()

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
        name = f"{self._document_name}{'*' if self.is_dirty else ''}"
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

    def __init__(self, *args, **kwargs):
        self.set_log_levels()
        self.testing = kwargs.pop("testing", False)
        super().__init__(*args, **kwargs)
        self.initialize()
        self.display()
        self.settings_manager.enable_save()
        # on window resize:
        # self.applicationStateChanged.connect(self.on_state_changed)
        self.window.wordballoon_button.hide()  # hide word balloon

        if self.settings_manager.settings.latest_version_check.get():
            self.check_for_latest_version()

        if not self.testing:
            self.exec()

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
        latest_major, latest_minor, latest_patch = self.latest_version[1:].split(".")
        current_major, current_minor, current_patch = self.version[1:].split(".")

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
        self.window.debug_label.setText(f"New version available: {self.latest_version}")

    def show_update_popup(self):
        self.update_popup = UpdateWindow(self.settings_manager, app=self)

    def reset_settings(self):
        GeneratorMixin.reset_settings(self)
        BrushesMixin.reset_settings(self)
        self.canvas.reset_settings()
        ToolbarMixin.set_stylesheet(self)

    def on_state_changed(self, state):
        if state == Qt.ApplicationState.ApplicationActive:
            self.canvas.pos_x = int(self.window.x() / 4)
            self.canvas.pos_y = int(self.window.y() / 2)
            self.canvas.update()

    def initialize(self):
        self.initialize_settings_manager()
        self.initialize_tqdm()
        self.initialize_handlers()
        self.initialize_window()
        HistoryMixin.initialize(self)
        CanvasMixin.initialize(self)
        GeneratorMixin.initialize(self)
        self.initialize_size_sliders()
        LayerMixin.initialize(self)
        MenubarMixin.initialize(self)
        self.initialize_shortcuts()
        ToolbarMixin.initialize(self)
        self.initialize_stable_diffusion()
        # ExtensionMixin.initialize(self)  TODO: Extensions
        BrushesMixin.initialize(self)
        EmbeddingMixin.initialize(self)
        if self.settings_manager.settings.force_reset.get():
            self.reset_settings()
            self.settings_manager.settings.force_reset.set(False)

    def initialize_settings_manager(self):
        self.settings_manager = SettingsManager()
        self.settings_manager.disable_save()
        # self.get_extensions_from_path()  TODO: Extensions
        self.settings_manager.settings.canvas_color.my_signal.connect(self.update_canvas_color)
        self.settings_manager.settings.size.my_signal.connect(self.set_size_form_element_step_values)
        self.settings_manager.settings.line_width.my_signal.connect(self.set_size_form_element_step_values)

    def initialize_shortcuts(self):
        # on shift + mouse scroll change working width
        self.window.wheelEvent = self.change_width

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
        self.window = uic.loadUi(os.path.join(HERE, "pyqt/main_window.ui"))
        self.center()
        self.set_window_title()

    def initialize_stable_diffusion(self):
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
        if not self.testing:
            self.window.show()
        else:
            # do not show the window when testing, otherwise it will block the tests
            # self.window.hide()
            # the above solution doesn't work, gives this error:
            # QBasicTimer::start: QBasicTimer can only be used with threads started with QThread
            # so instead we do this in order to run without showing the window:
            self.window.showMinimized()
        self.show_layers()
        self.set_stylesheet()
        self.window.move_button.hide()

    def set_log_levels(self):
        uic.properties.logger.setLevel(LOG_LEVEL)
        uic.uiparser.logger.setLevel(LOG_LEVEL)

    def center(self):
        availableGeometry = QGuiApplication.primaryScreen().availableGeometry()
        frameGeometry = self.window.frameGeometry()
        frameGeometry.moveCenter(availableGeometry.center())
        self.window.move(frameGeometry.topLeft())

    def change_width(self, event):
        grid_size = self.grid_size

        # if the shift key is pressed
        if QtCore.Qt.KeyboardModifier.ShiftModifier in event.modifiers():
            delta = event.angleDelta().y()

            if delta < 0:
                delta = delta / 2

            size = int(self.settings_manager.settings.working_height.get() + delta)
            size = int(size / grid_size) * grid_size

            if size < grid_size:
                size = grid_size

            self.settings_manager.settings.working_height.set(size)
            self.canvas.update()
            self.window.height_slider.setValue(size)
            self.window.height_spinbox.setValue(size)

        # if the control key is pressed
        if QtCore.Qt.KeyboardModifier.ControlModifier in event.modifiers():
            delta = event.angleDelta().y()

            if delta < 0:
                delta = delta / 2

            size = int(self.settings_manager.settings.working_width.get() + delta)
            size = int(size / grid_size) * grid_size

            if size < grid_size:
                size = grid_size

            self.settings_manager.settings.working_width.set(size)
            self.canvas.update()
            self.window.width_slider.setValue(size)
            self.window.width_spinbox.setValue(size)

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
        self.window.setWindowTitle(f"AI Runner {self.document_name}")

    def new_document(self):
        CanvasMixin.initialize(self)
        self.is_saved = False
        self.is_dirty = False
        self._document_name = "Untitled"
        self.set_window_title()
        # clear the layers list widget
        self.window.layers.setWidget(None)
        self.current_filter = None
        self.canvas.update()
        self.show_layers()

    def message_handler(self, msg, error=False):
        try:
            self.window.status_label.setStyleSheet("color: black;")
        except Exception as e:
            print("something went wrong while setting label")
            print(e)

        try:
            self.window.status_label.setText(msg["response"])
        except TypeError:
            self.window.status_label.setText("")

    def error_handler(self, msg):
        try:
            self.window.status_label.setStyleSheet("color: red;")
        except Exception as e:
            print("something went wrong while setting label")
            print(e)

        self.window.status_label.setText(msg)

    def set_size_form_element_step_values(self):
        """
        This function is called when grid_size is changed in the settings.

        :return:
        """
        size = self.grid_size
        self.window.width_slider.singleStep = size
        self.window.height_slider.singleStep = size
        self.window.width_spinbox.singleStep = size
        self.window.height_spinbox.singleStep = size
        self.window.width_slider.pageStep = size
        self.window.height_slider.pageStep = size
        self.window.width_slider.minimum = size
        self.window.height_slider.minimum = size
        self.window.width_spinbox.minimum = size
        self.window.height_spinbox.minimum = size
        self.canvas.update()

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
        self.is_dirty = False

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
        self.show_layers()


if __name__ == "__main__":
    qdarktheme.enable_hi_dpi()
    MainWindow([])
