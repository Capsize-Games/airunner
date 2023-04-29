import os
import pickle
import sys
from PyQt6 import uic, QtCore
from PyQt6.QtWidgets import QApplication, QFileDialog
from PyQt6.QtCore import pyqtSlot
from PyQt6.QtGui import QGuiApplication
from aihandler.qtvar import TQDMVar, ImageVar, MessageHandlerVar, ErrorHandlerVar
from aihandler.settings import LOG_LEVEL
from airunner.mixins.canvas_mixin import CanvasMixin
from airunner.mixins.comic_mixin import ComicMixin
from airunner.mixins.embedding_mixin import EmbeddingMixin
from airunner.mixins.extension_mixin import ExtensionMixin
from airunner.mixins.generator_mixin import GeneratorMixin
from airunner.mixins.history_mixin import HistoryMixin
from airunner.mixins.layer_mixin import LayerMixin
from airunner.mixins.menubar_mixin import MenubarMixin
from airunner.mixins.model_mixin import ModelMixin
from airunner.mixins.toolbar_mixin import ToolbarMixin
from airunner.windows.video import VideoPopup
from aihandler.settings_manager import SettingsManager
from airunner.runai_client import OfflineClient
import qdarktheme


class MainWindow(
    QApplication,
    ExtensionMixin,
    EmbeddingMixin,
    LayerMixin,
    ToolbarMixin,
    HistoryMixin,
    MenubarMixin,
    ModelMixin,
    CanvasMixin,
    GeneratorMixin,
    ComicMixin,
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
        # "superresolution",
        "controlnet",
        "txt2vid",
    ]
    models = None
    client = None

    @property
    def grid_size(self):
        return self.settings_manager.settings.size.get()

    @property
    def current_index(self):
        return self.window.tabWidget.currentIndex()

    @property
    def current_section(self):
        return self.sections[self.current_index]

    @property
    def use_pixels(self):
        # get name of current tab
        return self.current_section in ("txt2img", "img2img", "pix2pix", "depth2img", "outpaint", "controlnet")

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
    def document_name(self):
        return f"{self._document_name}{'*' if self.is_dirty else ''}"

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
        super().__init__(*args, **kwargs)
        self.initialize()
        self.display()
        self.settings_manager.enable_save()
        self.exec()

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

    def initialize_settings_manager(self):
        self.settings_manager = SettingsManager()
        self.settings_manager.disable_save()
        self.get_extensions_from_path()
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

    def display(self):
        self.window.show()
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
