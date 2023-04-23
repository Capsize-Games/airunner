import importlib
import io
import os
import pickle
import random
import sys
import webbrowser
import zipfile
import cv2
import numpy as np
import requests
import torch
from PIL import Image
from PyQt6 import uic, QtCore, QtGui
from PyQt6.QtWidgets import QApplication, QLabel, QWidget, QColorDialog, QFileDialog, QVBoxLayout, QDialog, QSpacerItem, \
    QSizePolicy
from PyQt6.QtCore import QPoint, pyqtSlot, QRect, QPointF
from PyQt6.QtGui import QPainter, QIcon, QColor, QGuiApplication
from aihandler.qtvar import TQDMVar, ImageVar, MessageHandlerVar, ErrorHandlerVar
from aihandler.settings import MAX_SEED, AVAILABLE_SCHEDULERS_BY_ACTION, MODELS, LOG_LEVEL
from aihandler.util import get_extensions_from_path, import_extension_class
from airunner.history import History
from airunner.windows.about import AboutWindow
from airunner.windows.advanced_settings import AdvancedSettings
from airunner.windows.extensions import ExtensionsWindow
from airunner.windows.grid_settings import GridSettings
from airunner.windows.preferences import PreferencesWindow
from airunner.windows.video import VideoPopup
from airunner.qtcanvas import Canvas
from airunner.settingsmanager import SettingsManager
from airunner.runai_client import OfflineClient
from airunner.filters import FilterGaussianBlur, FilterBoxBlur, FilterUnsharpMask, FilterSaturation, \
    FilterColorBalance, FilterPixelArt
from airunner.balloon import Balloon
import qdarktheme


class MainWindow(QApplication):
    progress_bar_started = False
    use_pixels = False
    action = "txt2img"
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
    current_filter = None
    tabs = {}
    tqdm_callback_triggered = False
    _document_name = "Untitled"
    _is_dirty = False
    is_saved = False
    _embedding_names = []

    @property
    def layer_highlight_style(self):
        return f"background-color: #c7f6fc; border: 1px solid #000000; color: #000000;"

    @property
    def layer_normal_style(self):
        return "background-color: #ffffff; border: 1px solid #333333; color: #333;"

    @property
    def current_index(self):
        return self.window.tabWidget.currentIndex()

    @property
    def current_section(self):
        return self.sections[self.current_index]

    @property
    def settings(self):
        settings = self.settings_manager.settings
        settings.set_namespace(self.current_section)
        return settings

    @property
    def steps(self):
        return self.settings.steps.get()

    @steps.setter
    def steps(self, val):
        self.settings.steps.set(val)

    @property
    def scale(self):
        return self.settings.scale.get()

    @scale.setter
    def scale(self, val):
        self.settings.scale.set(val)

    @property
    def image_scale(self):
        return self.settings.image_guidance_scale.get()

    @image_scale.setter
    def image_scale(self, val):
        self.settings.image_guidance_scale.set(val)

    @property
    def strength(self):
        return self.settings.strength.get()

    @strength.setter
    def strength(self, val):
        self.settings.strength.set(val)

    @property
    def seed(self):
        return self.settings.seed.get()

    @seed.setter
    def seed(self, val):
        self.settings.seed.set(val)

    @property
    def random_seed(self):
        return self.settings.random_seed.get()

    @random_seed.setter
    def random_seed(self, val):
        self.settings.random_seed.set(val)

    @property
    def samples(self):
        return self.settings.n_samples.get()

    @samples.setter
    def samples(self, val):
        self.settings.n_samples.set(val)

    @property
    def model(self):
        return self.settings.model_var.get()

    @model.setter
    def model(self, val):
        self.settings.model_var.set(val)

    @property
    def scheduler(self):
        return self.settings.scheduler_var.get()

    @scheduler.setter
    def scheduler(self, val):
        self.settings.scheduler_var.set(val)

    @property
    def width(self):
        return int(self.settings_manager.settings.working_width.get())

    @width.setter
    def width(self, val):
        self.settings_manager.settings.working_width.set(val)
        self.canvas.update()

    @property
    def height(self):
        return int(self.settings_manager.settings.working_height.get())

    @height.setter
    def height(self, val):
        self.settings_manager.settings.working_height.set(val)
        self.canvas.update()

    @property
    def is_dirty(self):
        return self._is_dirty

    @is_dirty.setter
    def is_dirty(self, val):
        self._is_dirty = val
        self.set_window_title()

    @property
    def use_pixels(self):
        # get name of current tab
        return self.current_section in ("txt2img", "img2img", "pix2pix", "depth2img", "outpaint", "controlnet")

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

    @property
    def grid_size(self):
        return self.settings_manager.settings.size.get()

    @property
    def embedding_names(self):
        if self._embedding_names is None:
            self._embedding_names = self.get_list_of_available_embedding_names()
        return self._embedding_names

    def __init__(self, *args, **kwargs):
        from PyQt6 import uic
        uic.properties.logger.setLevel(LOG_LEVEL)
        uic.uiparser.logger.setLevel(LOG_LEVEL)
        super().__init__(*args, **kwargs)
        self.tqdm_var = TQDMVar()
        self.tqdm_var.my_signal.connect(self.tqdm_callback)

        self.message_var = MessageHandlerVar()
        self.message_var.my_signal.connect(self.message_handler)
        self.error_var = ErrorHandlerVar()
        self.error_var.my_signal.connect(self.error_handler)

        self.image_var = ImageVar()
        self.image_var.my_signal.connect(self.image_handler)

        # initialize history
        self.history = History()

        # create settings manager
        self.settings_manager = SettingsManager()
        # self.get_extensions_from_path()

        # listen to signal on self.settings_manager.settings.canvas_color
        self.settings_manager.settings.canvas_color.my_signal.connect(self.update_canvas_color)

        # initialize window
        HERE = os.path.dirname(os.path.abspath(__file__))
        self.window = uic.loadUi(os.path.join(HERE, "pyqt/main_window.ui"))

        self.center()

        # add title to window
        self.set_window_title()

        self.show_initialize_buttons()

        self.initialize_tabs()

        # initialize filters
        self.filter_gaussian_blur = FilterGaussianBlur(parent=self)
        self.window.actionGaussian_Blur.triggered.connect(self.filter_gaussian_blur.show)

        self.filter_pixel_art = FilterPixelArt(parent=self)
        self.window.actionPixel_Art.triggered.connect(self.filter_pixel_art.show)

        self.filter_box_blur = FilterBoxBlur(parent=self)
        self.window.actionBox_Blur.triggered.connect(self.filter_box_blur.show)
        self.filter_unsharp_mask = FilterUnsharpMask(parent=self)
        self.window.actionUnsharp_Mask.triggered.connect(self.filter_unsharp_mask.show)
        self.filter_saturation = FilterSaturation(parent=self)
        self.window.actionSaturation.triggered.connect(self.filter_saturation.show)
        self.filter_color_balance = FilterColorBalance(parent=self)
        self.window.actionColor_Balance.triggered.connect(self.filter_color_balance.show)

        # initialize sizes
        self.window.width_slider.setValue(self.width)
        self.window.height_slider.setValue(self.height)
        self.window.width_spinbox.setValue(self.width)
        self.window.height_spinbox.setValue(self.height)
        grid_size = self.canvas.grid_size

        self.window.brush_size_slider.setValue(self.settings.mask_brush_size.get())

        self.show_layers()

        self.window.actionUndo.triggered.connect(self.undo)
        self.window.actionRedo.triggered.connect(self.redo)

        self.window.new_layer.clicked.connect(self.new_layer)
        self.window.layer_up_button.clicked.connect(self.layer_up_button)
        self.window.layer_down_button.clicked.connect(self.layer_down_button)
        self.window.delete_layer_button.clicked.connect(self.delete_layer_button)

        self.window.show()

        self.window.actionNew.triggered.connect(self.new_document)
        self.window.actionSave.triggered.connect(self.save_document)
        self.window.actionLoad.triggered.connect(self.load_document)
        self.window.actionImport.triggered.connect(self.import_image)
        self.window.actionExport.triggered.connect(self.export_image)
        self.window.actionQuit.triggered.connect(self.quit)

        self.window.actionPaste.triggered.connect(self.paste_image)
        self.window.actionCopy.triggered.connect(self.copy_image)

        self.window.brush_size_slider.valueChanged.connect(self.update_brush_size)
        self.window.brush_size_spinbox.valueChanged.connect(self.brush_spinbox_change)

        self.initialize_filters()

        self.initialize_shortcuts()

        # start stable diffusion
        self.initialize_stable_diffusion()

        self.window.actionResize_on_Paste.triggered.connect(self.toggle_resize_on_paste)

        # set tool button based on current tool
        if self.canvas.active_grid_area_selected:
            self.window.active_grid_area_button.setChecked(True)
        if self.canvas.eraser_selected:
            self.window.eraser_button.setChecked(True)
        if self.canvas.brush_selected:
            self.window.brush_button.setChecked(True)
        if self.canvas.move_selected:
            self.window.move_button.setChecked(True)
        if self.settings_manager.settings.snap_to_grid.get():
            self.window.grid_button.setChecked(True)
        if self.settings_manager.settings.nsfw_filter.get():
            self.window.nsfw_button.setChecked(True)

        self.window.darkmode_button.clicked.connect(self.toggle_darkmode)
        self.set_stylesheet()

        # hide self.window.move_button
        self.window.move_button.hide()

        # set the sliders of
        self.set_size_form_element_step_values()

        self.window.brush_size_slider.setValue(self.settings_manager.settings.mask_brush_size.get())
        self.window.brush_size_spinbox.setValue(self.settings_manager.settings.mask_brush_size.get())

        self.settings_manager.settings.size.my_signal.connect(self.set_size_form_element_step_values)
        self.settings_manager.settings.line_width.my_signal.connect(self.set_size_form_element_step_values)
        self.settings_manager.settings.show_grid.my_signal.connect(self.canvas.update)
        self.settings_manager.settings.snap_to_grid.my_signal.connect(self.canvas.update)
        self.settings_manager.settings.line_color.my_signal.connect(self.canvas.update_grid_pen)

        self.exec()

    ##############################################
    #  Begin extension functions
    ##############################################
    active_extensions = []

    def get_extensions_from_path(self):
        """
        Initialize extensions by loading them from the extensions_directory.
        These are extensions that have been activated by the user.
        Extensions can be activated by manually adding them to the extensions folder
        or by browsing for them in the extensions menu and activating them there.

        This method initializes active extensions.
        :return:
        """
        extensions = []
        base_path = self.settings_manager.settings.model_base_path.get()
        extension_path = os.path.join(base_path, "extensions")
        available_extensions = get_extensions_from_path(extension_path)
        if available_extensions:
            for extension in available_extensions:
                if extension.enabled:
                    repo = extension.repo.get()
                    name = repo.split("/")[-1]
                    print("REPO", repo)
                    path = os.path.join(extension_path, name)
                    if os.path.exists(path):
                        extension_files = [f for f in os.listdir(path) if
                                           os.path.isfile(os.path.join(path, f)) and f == 'main.py']
                        for file_name in extension_files:
                            module_name = file_name[:-3]
                            spec = importlib.util.spec_from_file_location(module_name,
                                                                          os.path.join(path, file_name))
                            module = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(module)

                            # initialize extension settings
                            ExtensionClass = getattr(module, 'Extension')
                            SettingsClass = getattr(module, 'Settings')
                            settings = SettingsClass(app=self)
                            for key, value in settings.__dict__.items():
                                self.settings_manager.settings.__dict__[key] = value

                            # initialize the extension
                            extensions.append(ExtensionClass(self.settings_manager))

        self.settings_manager.settings.available_extensions.set(extensions)
        print("*" * 100)
        print(f"EXTENSIONS LOADED ({len(extensions)}): ", extensions)
        print("*" * 100)

    def do_generator_tab_injection(self, tab_name, tab):
        """
        Ibjects extensions into the generator tab widget.
        :param tab_name:
        :param tab:
        :return:
        """
        for extension in self.settings_manager.settings.available_extensions.get():
            extension.generator_tab_injection(tab, tab_name)

    def do_generate_data_injection(self, data):
        for extension in self.settings_manager.settings.available_extensions.get():
            data = extension.generate_data_injection(data)
        return data

    ##############################################
    #  End extension functions
    ##############################################

    def set_size_form_element_step_values(self):
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

    def center(self):
        availableGeometry = QGuiApplication.primaryScreen().availableGeometry()
        frameGeometry = self.window.frameGeometry()
        frameGeometry.moveCenter(availableGeometry.center())
        self.window.move(frameGeometry.topLeft())

    def paste_image(self):
        self.canvas.paste_image_from_clipboard()

    def copy_image(self):
        self.canvas.copy_image()

    def toggle_darkmode(self):
        self.settings_manager.settings.dark_mode_enabled.set(not self.settings_manager.settings.dark_mode_enabled.get())
        self.set_stylesheet()

    def set_stylesheet(self):
        HERE = os.path.dirname(os.path.abspath(__file__))
        icons = {
            "darkmode_button": "weather-night",
            "move_button": "move",
            "active_grid_area_button": "stop",
            "eraser_button": "eraser",
            "brush_button": "pen",
            "grid_button": "grid",
            "nsfw_button": "underwear",
            "focus_button": "camera-focus",
            "undo_button": "undo",
            "redo_button": "redo",
            "new_layer": "file-add",
            "layer_up_button": "arrow-up",
            "layer_down_button": "arrow-down",
            "delete_layer_button": "delete"
        }
        if self.settings_manager.settings.dark_mode_enabled.get():
            qdarktheme.setup_theme("dark")
            icons["darkmode_button"] = "weather-sunny"
            for button, icon in icons.items():
                if icon != "weather-sunny":
                    icon = icon + "-light"
                getattr(self.window, button).setIcon(QtGui.QIcon(os.path.join(HERE, f"src/icons/{icon}.png")))
        else:
            for button, icon in icons.items():
                getattr(self.window, button).setIcon(QtGui.QIcon(os.path.join(HERE, f"src/icons/{icon}.png")))
            try:
                qdarktheme.setup_theme("light")
            except PermissionError:
                pass

    def layer_up_button(self):
        self.canvas.move_layer_up(self.canvas.current_layer)
        self.show_layers()

    def layer_down_button(self):
        self.canvas.move_layer_down(self.canvas.current_layer)
        self.show_layers()

    def delete_layer_button(self):
        self.canvas.delete_layer(self.canvas.current_layer_index)
        self.show_layers()

    def toggle_resize_on_paste(self):
        self.settings_manager.settings.resize_on_paste.set(self.window.actionResize_on_Paste.isChecked())

    def initialize_shortcuts(self):
        # on shift + mouse scroll change working width
        self.window.wheelEvent = self.change_width

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

    def load_embeddings(self, tab):
        # create a widget that can be added to scroll area
        container = QWidget()
        container.setLayout(QVBoxLayout())
        for embedding_name in self.embedding_names:
            label = QLabel(embedding_name)
            # add label to the contianer
            container.layout().addWidget(label)
            # on double click of label insert it into the prompt
            label.mouseDoubleClickEvent = lambda event, _label=label: self.insert_into_prompt(_label.text())
        tab.embeddings.setWidget(container)

    def get_list_of_available_embedding_names(self):
        embeddings_folder = os.path.join(self.settings_manager.settings.model_base_path.get(), "embeddings")
        tokens = []
        if os.path.exists(embeddings_folder):
            for f in os.listdir(embeddings_folder):
                loaded_learned_embeds = torch.load(os.path.join(embeddings_folder, f), map_location="cpu")
                trained_token = list(loaded_learned_embeds.keys())[0]
                if trained_token == "string_to_token":
                    trained_token = loaded_learned_embeds["name"]
                tokens.append(trained_token)
        return tokens

    def initialize_filters(self):
        pass

    def toggle_stylesheet(self, path):
        # use fopen to open the file
        # read the file
        # set the stylesheet
        with open(path, "r") as stream:
            self.setStyleSheet(stream.read())

    def set_window_title(self):
        self.window.setWindowTitle(f"AI Runner {self.document_name}")

    def update_brush_size(self, val):
        self.settings_manager.settings.mask_brush_size.set(val)
        self.window.brush_size_spinbox.setValue(val)

    def brush_spinbox_change(self, val):
        self.settings_manager.settings.mask_brush_size.set(val)
        self.window.brush_size_slider.setValue(val)

    def new_layer(self):
        self.canvas.add_layer()
        self.show_layers()

    def show_layers(self):
        # iterate over layers and add to self.window.layers list widget
        # each layer should be a layer.ui file item populated with the data from the layer object within
        # self.canvas.layers

        # create an object which can contain a layer_obj and then be added to layers.setWidget
        container = QWidget()
        container.setLayout(QVBoxLayout())

        index = 0
        for layer in self.canvas.layers:
            # add layer to self.window.layers list widget
            # each layer should be a layer.ui file item populated with the data from the layer object within
            # self.canvas.layers
            HERE = os.path.dirname(os.path.abspath(__file__))
            layer_obj = uic.loadUi(os.path.join(HERE, "pyqt/layer.ui"))
            layer_obj.layer_name.setText(layer.name)

            # onclick of layer_obj set as the current layer index on self.canvas
            layer_obj.mousePressEvent = lambda event, _layer=layer: self.set_current_layer(
                self.canvas.layers.index(_layer)
            )

            # show a border around layer_obj if it is the selected index
            if self.canvas.current_layer_index == index:
                layer_obj.frame.setStyleSheet(self.layer_highlight_style)
            else:
                layer_obj.frame.setStyleSheet(self.layer_normal_style)

            # enable delete button in layer_obj
            layer_obj.visible_button.setIcon(QIcon("src/icons/eye.png" if layer.visible else "src/icons/eye-off.png"))
            #layer_obj.delete_button.clicked.connect(lambda _, _index=index: self.canvas.delete_layer(_index))
            layer_obj.visible_button.clicked.connect(lambda _, _layer=layer, _layer_obj=layer_obj: self.toggle_layer_visibility(_layer, _layer_obj))
            # layer_obj.up_button.clicked.connect(lambda _, _layer=layer: self.canvas.move_layer_up(_layer))
            # layer_obj.down_button.clicked.connect(lambda _, _layer=layer: self.canvas.move_layer_down(_layer))

            container.layout().addWidget(layer_obj)
            index += 1
        # add a spacer to the bottom of the container
        container.layout().addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        self.window.layers.setWidget(container)
        self.container = container

    def toggle_layer_visibility(self, layer, layer_obj):
        # change the eye icon of the visible_button on the layer
        self.canvas.toggle_layer_visibility(layer)
        layer_obj.visible_button.setIcon(QIcon("src/icons/eye.png" if layer.visible else "src/icons/eye-off.png"))

    def set_current_layer(self, index):
        item = self.container.layout().itemAt(self.canvas.current_layer_index)
        if item:
            item.widget().frame.setStyleSheet(self.layer_normal_style)
        self.canvas.current_layer_index = index
        # green border should only be on the outter frame not all elements
        item = self.container.layout().itemAt(self.canvas.current_layer_index)
        if item:
            item.widget().frame.setStyleSheet(self.layer_highlight_style)

    def new_document(self):
        self.canvas = Canvas(self)
        self.is_saved = False
        self.is_dirty = False
        self._document_name = "Untitled"
        self.set_window_title()
        # clear the layers list widget
        self.window.layers.setWidget(None)
        self.current_filter = None
        self.canvas.update()
        self.show_layers()

    def save_document(self):
        if not self.is_saved:
            return self.saveas_document()
        document_name = f"{self._document_name}.airunner"
        self.do_save(document_name)

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

    def import_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self.window, "Import Image", "", "Image Files (*.png *.jpg *.jpeg)"
        )
        if file_path == "":
            return
        self.canvas.load_image(file_path)
        self.canvas.update()

    def export_image(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self.window,
            "Export Image",
            "",
            "Image Files (*.png *.jpg *.jpeg)"
        )
        if file_path == "":
            return
        self.canvas.save_image(file_path)

    def toggle_grid(self, event):
        self.settings_manager.settings.show_grid.set(
            event
        )
        self.canvas.update()

    def toggle_nsfw_filter(self, val):
        self.settings_manager.settings.nsfw_filter.set(val)
        self.canvas.update()

    def delete_layer(self):
        pass

    def resort_layers(self, event):
        # move layer back to original position
        layer_order = event["layer_order"]
        # rearrange the current layers to match the layer order before the move
        sorted_layers = []
        for uuid in layer_order:
            for layer in self.canvas.layers:
                if layer.uuid == uuid:
                    sorted_layers.append(layer)
                    break
        self.canvas.layers = sorted_layers

    def undo_draw(self, previous_event):
        index = previous_event["layer_index"]
        lines = previous_event["lines"]
        previous_event["lines"] = self.canvas.layers[index].lines.copy()
        self.canvas.layers[index].lines = lines
        return previous_event

    def undo_erase(self, previous_event):
        # add lines to layer
        lines = previous_event["lines"]
        images = previous_event["images"]
        index = previous_event["layer_index"]
        previous_event["lines"] = self.canvas.layers[index].lines
        previous_event["images"] = self.canvas.get_image_copy(index)
        self.canvas.layers[index].lines = lines
        self.canvas.layers[index].images = images
        return previous_event

    def undo_new_layer(self, previous_event):
        layers = self.canvas.get_layers_copy()
        self.canvas.layers = previous_event["layers"]
        self.canvas.current_layer_index = previous_event["layer_index"]
        previous_event["layers"] = layers
        return previous_event

    def undo_move_layer(self, previous_event):
        layer_order = []
        for layer in self.canvas.layers:
            layer_order.append(layer.uuid)
        self.resort_layers(previous_event)
        previous_event["layer_order"] = layer_order
        self.history.undone_history.append(previous_event)
        self.canvas.current_layer_index = previous_event["layer_index"]
        return previous_event

    def undo_delete_layer(self, previous_event):
        layers = self.canvas.get_layers_copy()
        self.canvas.layers = previous_event["layers"]
        self.canvas.current_layer_index = previous_event["layer_index"]
        previous_event["layers"] = layers
        return previous_event

    def undo_set_image(self, previous_event):
        # replace layer images with original images
        images = previous_event["images"]
        layer_index = previous_event["layer_index"]
        current_image_root_point = QPoint(self.canvas.image_root_point.x(), self.canvas.image_root_point.y())
        current_image_pivot_point = QPoint(self.canvas.image_pivot_point.x(), self.canvas.image_pivot_point.y())
        self.canvas.image_root_point = previous_event["previous_image_root_point"]
        self.canvas.image_pivot_point = previous_event["previous_image_pivot_point"]
        previous_event["images"] = self.canvas.get_image_copy(layer_index)
        previous_event["previous_image_root_point"] = current_image_root_point
        previous_event["previous_image_pivot_point"] = current_image_pivot_point
        self.canvas.layers[previous_event["layer_index"]].images = images
        return previous_event

    def undo_add_widget(self, previous_event):
        widets = previous_event["widgets"]
        previous_event["widgets"] = self.canvas.layers[previous_event["layer_index"]].widgets
        self.canvas.layers[previous_event["layer_index"]].widgets = widets
        return previous_event

    def undo(self):
        if len(self.history.event_history) == 0:
            return
        previous_event = self.history.event_history.pop()
        event_name = previous_event["event"]
        if event_name == "draw":
            previous_event = self.undo_draw(previous_event)
        elif event_name == "erase":
            previous_event = self.undo_erase(previous_event)
        elif event_name == "new_layer":
            if len(self.canvas.layers) == 1:
                self.history.event_history.append(previous_event)
                return
            previous_event = self.undo_new_layer(previous_event)
        elif event_name == "move_layer":
            self.undo_move_layer(previous_event)
        elif event_name == "delete_layer":
            self.undo_delete_layer(previous_event)
        elif event_name == "set_image":
            self.undo_set_image(previous_event)
        elif event_name == "add_widget":
            self.undo_add_widget(previous_event)
        self.history.undone_history.append(previous_event)
        self.show_layers()
        self.canvas.update()

    def redo_draw(self, undone_event):
        lines = undone_event["lines"]
        undone_event["lines"] = self.canvas.layers[undone_event["layer_index"]].lines
        self.canvas.layers[undone_event["layer_index"]].lines = lines
        return undone_event

    def redo_erase(self, undone_event):
        lines = undone_event["lines"]
        images = undone_event["images"]
        layer_index = undone_event["layer_index"]
        undone_event["lines"] = self.canvas.layers[layer_index].lines.copy()
        undone_event["images"] = self.canvas.get_image_copy(layer_index)
        self.canvas.layers[undone_event["layer_index"]].lines = lines
        self.canvas.layers[undone_event["layer_index"]].images = images
        return undone_event

    def redo_new_layer(self, undone_event):
        layers = self.canvas.get_layers_copy()
        self.canvas.layers = undone_event["layers"]
        self.canvas.current_layer_index = undone_event["layer_index"]
        undone_event["layers"] = layers
        return undone_event

    def redo_move_layer(self, undone_event):
        layer_order = []
        for layer in self.canvas.layers:
            layer_order.append(layer.uuid)
        self.resort_layers(undone_event)
        undone_event["layer_order"] = layer_order
        self.canvas.current_layer_index = undone_event["layer_index"]
        return undone_event

    def redo_delete_layer(self, undone_event):
        layers = self.canvas.get_layers_copy()
        self.canvas.layers = undone_event["layers"]
        self.canvas.current_layer_index = undone_event["layer_index"]
        undone_event["layers"] = layers
        return undone_event

    def redo_set_image(self, undone_event):
        layers = self.canvas.layers
        images = undone_event["images"]
        layer_index = undone_event["layer_index"]
        current_image_root_point = QPoint(self.canvas.image_root_point.x(), self.canvas.image_root_point.y())
        current_image_pivot_point = QPoint(self.canvas.image_pivot_point.x(), self.canvas.image_pivot_point.y())
        self.canvas.image_root_point = undone_event["previous_image_root_point"]
        self.canvas.image_pivot_point = undone_event["previous_image_pivot_point"]
        undone_event["images"] = self.canvas.get_image_copy(layer_index)
        undone_event["previous_image_root_point"] = current_image_root_point
        undone_event["previous_image_pivot_point"] = current_image_pivot_point
        self.canvas.layers[undone_event["layer_index"]].images = images
        return undone_event

    def redo_add_widget(self, undone_event):
        # add widget
        widgets = undone_event["widgets"]
        undone_event["widgets"] = self.canvas.layers[undone_event["layer_index"]].widgets
        self.canvas.layers[undone_event["layer_index"]].widgets = widgets
        return undone_event

    def redo(self):
        if len(self.history.undone_history) == 0:
            return
        undone_event = self.history.undone_history.pop()
        event_name = undone_event["event"]
        if event_name == "draw":
            undone_event = self.redo_draw(undone_event)
        elif event_name == "erase":
            undone_event = self.redo_erase(undone_event)
        elif event_name == "new_layer":
            undone_event = self.redo_new_layer(undone_event)
        elif event_name == "move_layer":
            undone_event = self.redo_move_layer(undone_event)
        elif event_name == "delete_layer":
            undone_event = self.redo_delete_layer(undone_event)
        elif event_name == "set_image":
            undone_event = self.redo_set_image(undone_event)
        elif event_name == "add_widget":
            undone_event = self.redo_add_widget(undone_event)
        self.history.event_history.append(undone_event)
        self.show_layers()
        self.canvas.update()

    def focus_button_clicked(self):
        self.canvas.recenter()

    def word_balloon_button_clicked(self):
        """
        Create and add a word balloon to the canvas.
        :return:
        """
        # create a word balloon
        word_balloon = Balloon()
        word_balloon.setGeometry(100, 100, 200, 100)
        word_balloon.set_tail_pos(QPointF(50, 100))
        # add the widget to the canvas
        self.history.add_event({
            "event": "add_widget",
            "layer_index": self.canvas.current_layer_index,
            "widgets": self.canvas.current_layer.widgets.copy(),
        })
        self.canvas.current_layer.widgets.append(word_balloon)
        self.show_layers()
        self.canvas.update()

    def show_initialize_buttons(self):
        self.window.eraser_button.clicked.connect(lambda: self.set_tool("eraser"))
        self.window.brush_button.clicked.connect(lambda: self.set_tool("brush"))
        self.window.active_grid_area_button.clicked.connect(lambda: self.set_tool("active_grid_area"))
        self.window.move_button.clicked.connect(lambda: self.set_tool("move"))
        #self.window.select_button.clicked.connect(lambda: self.set_tool("select"))
        self.window.primary_color_button.clicked.connect(self.set_primary_color)
        self.window.secondary_color_button.clicked.connect(self.set_secondary_color)
        self.window.grid_button.clicked.connect(self.toggle_grid)
        self.window.undo_button.clicked.connect(self.undo)
        self.window.redo_button.clicked.connect(self.redo)
        self.window.nsfw_button.clicked.connect(self.toggle_nsfw_filter)
        self.window.focus_button.clicked.connect(self.focus_button_clicked)
        self.window.wordballoon_button.clicked.connect(self.word_balloon_button_clicked)
        self.set_button_colors()
        self.window.grid_button.setChecked(
            self.settings_manager.settings.show_grid.get() == True
        )
        self.window.nsfw_button.setChecked(
            self.settings_manager.settings.nsfw_filter.get() == True
        )

    def set_button_colors(self):
        # set self.window.primaryColorButton color
        self.window.primary_color_button.setStyleSheet(
            f"background-color: {self.settings_manager.settings.primary_color.get()};"
        )
        self.window.secondary_color_button.setStyleSheet(
            f"background-color: {self.settings_manager.settings.secondary_color.get()};"
        )

    def set_primary_color(self):
        # display a color picker
        color = QColorDialog.getColor()
        if color.isValid():
            self.settings_manager.settings.primary_color.set(color.name())
            self.set_button_colors()

    def set_secondary_color(self):
        # display a color picker
        color = QColorDialog.getColor()
        if color.isValid():
            self.settings_manager.settings.secondary_color.set(color.name())
            self.set_button_colors()

    def set_tool(self, tool):
        # uncheck all buttons that are not this tool
        if tool != "brush":
            self.window.brush_button.setChecked(False)
        if tool != "eraser":
            self.window.eraser_button.setChecked(False)
        if tool != "active_grid_area":
            self.window.active_grid_area_button.setChecked(False)
        if tool != "move":
            self.window.move_button.setChecked(False)
        # if tool != "select":
        #     self.window.select_button.setChecked(False)

        if self.settings_manager.settings.current_tool.get() != tool:
            self.settings_manager.settings.current_tool.set(tool)
        else:
            self.settings_manager.settings.current_tool.set(None)

        self.canvas.update_cursor()

    def message_handler(self, msg):
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

    def initialize_stable_diffusion(self):
        self.client = OfflineClient(
            app=self,
            tqdm_var=self.tqdm_var,
            image_var=self.image_var,
            error_var=self.error_var,
            message_var=self.message_var,
        )

    def video_handler(self, data):
        filename = data["video_filename"]
        VideoPopup(settings_manager=self.settings_manager, file_path=filename)

    def image_handler(self, image, data, nsfw_content_detected):
        if data["action"] == "txt2vid":
            return self.video_handler(data)

        self.stop_progress_bar(data["action"])
        if nsfw_content_detected and self.settings_manager.settings.nsfw_filter.get():
            self.message_handler("NSFW content detected, try again.", error=True)
        else:
            if data["action"] != "outpaint":
                self.canvas.add_layer()
            self.canvas.image_handler(image, data)
            self.message_handler("")
            self.show_layers()

    def update_canvas_color(self, color):
        self.window.canvas_container.setStyleSheet(f"background-color: {color};")
        self.window.canvas_container.setAutoFillBackground(True)

    def initialize_tabs(self):
        # load all the forms
        sections = ["txt2img", "img2img", "depth2img", "pix2pix", "outpaint", "controlnet", "txt2vid"]
        HERE = os.path.dirname(os.path.abspath(__file__))
        self.tabs = {}
        for tab in sections:
            self.tabs[tab] = uic.loadUi(os.path.join(HERE, "pyqt/generate_form.ui"))

        for tab in self.tabs:
            if tab != "controlnet":
                self.tabs[tab].controlnet_label.deleteLater()
                self.tabs[tab].controlnet_dropdown.deleteLater()
            else:
                controlnet_options = [
                    "Canny",
                    "Depth",
                    "Hed",
                    "MLSD",
                    "Normal",
                    "Scribble",
                    "Segmentation",
                ]
                for option in controlnet_options:
                    self.tabs[tab].controlnet_dropdown.addItem(option)
            if tab in ["txt2img", "pix2pix", "outpaint", "super_resolution", "txt2vid"]:
                self.tabs[tab].strength.deleteLater()
            if tab in ["txt2img", "img2img", "depth2img", "outpaint", "controlnet", "super_resolution", "txt2vid"]:
                self.tabs[tab].image_scale_box.deleteLater()
            if tab in ["txt2vid"]:
                self.tabs[tab].scheduler_label.deleteLater()
                self.tabs[tab].scheduler_dropdown.deleteLater()


        # add all the tabs
        for tab in sections:
            self.window.tabWidget.addTab(self.tabs[tab], tab)

        # iterate over each tab and connect steps_slider with steps_spinbox
        for tab_name in self.tabs.keys():
            tab = self.tabs[tab_name]
            self.load_embeddings(tab)
            self.do_generator_tab_injection(tab_name, tab)

            tab.steps_slider.valueChanged.connect(lambda val, _tab=tab: self.handle_steps_slider_change(val, _tab))
            tab.steps_spinbox.valueChanged.connect(lambda val, _tab=tab: self.handle_steps_spinbox_change(val, _tab))

            # load models by section
            self.load_model_by_section(tab, tab_name)

            # on change of tab.model_dropdown set the model in self.settings_manager
            tab.model_dropdown.currentIndexChanged.connect(
                lambda val, _tab=tab, _section=tab_name: self.set_model(_tab, _section, val)
            )

            # set schedulers for each tab
            if tab_name not in ["txt2vid"]:
                tab.scheduler_dropdown.addItems(AVAILABLE_SCHEDULERS_BY_ACTION[tab_name])
                # on change of tab.scheduler_dropdown set the scheduler in self.settings_manager
                tab.scheduler_dropdown.currentIndexChanged.connect(
                    lambda val, _tab=tab, _section=tab_name: self.set_scheduler(_tab, _section, val)
                )

            # scale slider
            tab.scale_slider.valueChanged.connect(lambda val, _tab=tab: self.handle_scale_slider_change(val, _tab))
            tab.scale_spinbox.valueChanged.connect(lambda val, _tab=tab: self.handle_scale_spinbox_change(val, _tab))

            tab.image_scale_slider.valueChanged.connect(lambda val, _tab=tab: self.handle_image_scale_slider_change(val, _tab))
            tab.image_scale_spinbox.valueChanged.connect(lambda val, _tab=tab: self.handle_image_scale_spinbox_change(val, _tab))

            # strength slider
            section = tab_name
            if section in ["img2img", "depth2img", "controlnet"]:
                if section == "img2img":
                    strength = self.settings_manager.settings.img2img_strength.get()
                elif section == "depth2img":
                    strength = self.settings_manager.settings.depth2img_strength.get()
                elif section == "controlnet":
                    strength = self.settings_manager.settings.controlnet_strength.get()
                tab.strength_slider.setValue(int(strength * 100))
                tab.strength_spinbox.setValue(strength / 100)
                tab.strength_slider.valueChanged.connect(lambda val, _tab=tab: self.handle_strength_slider_change(val, _tab))
                tab.strength_spinbox.valueChanged.connect(lambda val, _tab=tab: self.handle_strength_spinbox_change(val, _tab))

            if section == "txt2vid":
                # change the label tab.samples_groupbox label to "Frames"
                tab.samples_groupbox.setTitle("Frames")

            # seed slider
            # seed is QTextEdit
            def text_changed(tab):
                try:
                    val = int(tab.seed.toPlainText())
                    self.seed = val
                except ValueError:
                    pass

            def handle_random_checkbox_change(val, _tab):
                if val == 2:
                    self.random_seed = True
                else:
                    self.random_seed = False
                _tab.seed.setEnabled(not self.random_seed)

            tab.seed.textChanged.connect(lambda _tab=tab: text_changed(_tab))
            tab.random_checkbox.stateChanged.connect(lambda val, _tab=tab: handle_random_checkbox_change(val, _tab))

            tab.random_checkbox.setChecked(self.random_seed == True)

            # samples slider
            tab.samples_slider.valueChanged.connect(lambda val, _tab=tab: self.handle_samples_slider_change(val, _tab))
            tab.samples_spinbox.valueChanged.connect(lambda val, _tab=tab: self.handle_samples_spinbox_change(val, _tab))

            # if samples is greater than 1 enable the interrupt_button
            if tab.samples_spinbox.value() > 1:
                tab.interrupt_button.setEnabled(tab.samples_spinbox.value() > 1)

            self.set_default_values(tab_name, tab)

        # assign callback to generate function on tab
        self.window.tabWidget.currentChanged.connect(self.tab_changed_callback)

        # add callbacks
        for tab in sections:
            self.tabs[tab].generate.clicked.connect(self.generate_callback)
        # super_resolution_form.generate.clicked.connect(self.generate_callback)

        self.canvas = Canvas(self)

        # set up all callbacks on window menu bar
        self.window.actionGrid.triggered.connect(self.show_grid_settings)
        self.window.actionPreferences.triggered.connect(self.show_preferences)
        self.window.actionAbout.triggered.connect(self.show_about)
        self.window.actionCanvas_color.triggered.connect(self.show_canvas_color)
        self.window.actionAdvanced.triggered.connect(self.show_advanced)
        self.window.actionBug_report.triggered.connect(lambda: webbrowser.open("https://github.com/Capsize-Games/airunner/issues/new?assignees=&labels=&template=bug_report.md&title="))
        self.window.actionReport_vulnerability.triggered.connect(lambda: webbrowser.open("https://github.com/Capsize-Games/airunner/security/advisories/new"))
        self.window.actionDiscord.triggered.connect(lambda: webbrowser.open("https://discord.gg/PUVDDCJ7gz"))
        self.window.actionExtensions.triggered.connect(self.show_extensions)

        # remove extensions menu item for now
        self.window.actionExtensions.deleteLater()

        self.window.actionInvert.triggered.connect(self.do_invert)

        self.initialize_size_form_elements()

    def show_extensions(self):
        self.extensions_window = ExtensionsWindow(self)

    def initialize_size_form_elements(self):
        # width form elements
        self.window.width_slider.valueChanged.connect(lambda val: self.handle_width_slider_change(val))
        self.window.width_spinbox.valueChanged.connect(lambda val: self.handle_width_spinbox_change(val))

        # height form elements
        self.window.height_slider.valueChanged.connect(lambda val: self.handle_height_slider_change(val))
        self.window.height_spinbox.valueChanged.connect(lambda val: self.handle_height_spinbox_change(val))

    def insert_into_prompt(self, text):
        # insert text into current tab prompt
        tab = self.window.tabWidget.currentWidget()
        tab.prompt.insertPlainText(text)

    def handle_width_slider_change(self, val):
        self.window.width_spinbox.setValue(val)
        self.width = val

    def handle_width_spinbox_change(self, val):
        self.window.width_slider.setValue(int(val))
        self.width = int(val)

    def handle_height_slider_change(self, val):
        self.window.height_spinbox.setValue(int(val))
        self.height = int(val)

    def handle_height_spinbox_change(self, val):
        self.window.height_slider.setValue(int(val))
        self.height = int(val)

    def handle_steps_slider_change(self, val, tab):
        tab.steps_spinbox.setValue(int(val))
        self.steps = int(val)

    def handle_steps_spinbox_change(self, val, tab):
        tab.steps_slider.setValue(int(val))
        self.steps = int(val)

    def handle_scale_slider_change(self, val, tab):
        tab.scale_spinbox.setValue(val / 100.0)
        self.scale = val

    def handle_image_scale_slider_change(self, val, tab):
        tab.image_scale_spinbox.setValue(val / 100.0)
        try:
            self.image_scale = val
        except:
            pass

    def handle_image_scale_spinbox_change(self, val, tab):
        tab.image_scale_slider.setValue(int(val * 100))
        try:
            self.image_scale = val * 100
        except:
            pass

    def handle_scale_spinbox_change(self, val, tab):
        tab.scale_slider.setValue(int(val * 100))
        self.scale = val * 100

    def handle_strength_slider_change(self, val, tab):
        tab.strength_spinbox.setValue(val / 100.0)
        self.strength = val

    def handle_strength_spinbox_change(self, val, tab):
        tab.strength_slider.setValue(int(val * 100))
        self.strength = val

    def handle_seed_spinbox_change(self, val, tab):
        tab.seed.setText(str(int(val)))
        self.seed = int(val)

    def handle_samples_slider_change(self, val, tab):
        tab.samples_spinbox.setValue(int(val))
        self.samples = int(val)
        tab.interrupt_button.setEnabled(tab.samples_spinbox.value() > 1)

    def handle_samples_spinbox_change(self, val, tab):
        tab.samples_slider.setValue(int(val))
        self.samples = int(val)
        tab.interrupt_button.setEnabled(tab.samples_spinbox.value() > 1)

    def set_model(self, tab, section, val):
        model = tab.model_dropdown.currentText()
        self.model = model

    def set_scheduler(self, tab, section, val):
        scheduler = tab.scheduler_dropdown.currentText()
        self.scheduler = scheduler

    def tab_changed_callback(self, index):
        self.canvas.update()

    def show_about(self):
        AboutWindow(self.settings_manager)

    def show_grid_settings(self):
        GridSettings(self.settings_manager)

    def do_invert(self):
        self.canvas.invert_image()
        self.canvas.update()

    def show_preferences(self):
        PreferencesWindow(self.settings_manager)

    def show_advanced(self):
        AdvancedSettings(self.settings_manager)

    def show_canvas_color(self):
        # show a color widget dialog and set the canvas color
        color = QColorDialog.getColor()
        if color.isValid():
            color = color.name()
            self.settings_manager.settings.canvas_color.set(color)
            self.canvas.set_canvas_color()

    def generate_callback(self):
        #self.new_layer()
        self.generate(True)

    def draw_something(self):
        painter = QPainter(self.window.canvas_container.pixmap())
        painter.drawLine(10, 10, 300, 200)
        painter.end()

    def prep_video(self):
        pass

    def set_default_values(self, section, tab):
        tab.steps_spinbox.setValue(self.steps)
        tab.scale_spinbox.setValue(self.scale / 100)
        if section == "pix2pix":
            val = self.settings_manager.settings.pix2pix_image_guidance_scale.get()
            tab.image_scale_spinbox.setValue(val / 100)
            tab.image_scale_slider.setValue(val)
        try:
            tab.strength_spinbox.setValue(self.strength / 100)
        except:
            pass
        tab.seed.setText(str(self.seed))
        tab.samples_spinbox.setValue(self.samples)
        tab.model_dropdown.setCurrentText(self.model)
        tab.scheduler_dropdown.setCurrentText(self.scheduler)

    def generate(
        self,
        do_generate=False,
        image=None,
        mask=None
    ):
        if self.use_pixels:
            self.requested_image = image
            self.start_progress_bar(self.current_section)
            try:
                image = self.canvas.current_layer.images[0].image
            except IndexError:
                image = None

            if image is None:
                # create a transparent image the size of self.canvas.active_grid_area_rect
                width = self.settings_manager.settings.working_width.get()
                height = self.settings_manager.settings.working_height.get()
                image = Image.new("RGBA", (int(width), int(height)), (0, 0, 0, 0))

            lines = self.canvas.current_layer.lines
            # combine lines with image
            for line in lines:
                # convert PIL.Image to numpy array
                image = np.array(image)
                start: QPoint = line.start_point
                end: QPoint = line.end_point
                color: QColor = line._pen["color"]
                image = cv2.line(image, (start.x(), start.y()), (end.x(), end.y()), (color.red(), color.green(), color.blue()), int(line._pen["width"]))
                # convert numpy array to PIL.Image
                image = Image.fromarray(image)

            img = image.copy().convert("RGBA")
            new_image = Image.new("RGBA", (self.settings.working_width.get(), self.settings.working_height.get()), (0, 0, 0))

            cropped_outpaint_box_rect = self.active_rect()
            crop_location = (
                cropped_outpaint_box_rect.x() - self.canvas.image_pivot_point.x(),
                cropped_outpaint_box_rect.y() - self.canvas.image_pivot_point.y(),
                cropped_outpaint_box_rect.width() - self.canvas.image_pivot_point.x(),
                cropped_outpaint_box_rect.height() - self.canvas.image_pivot_point.y()
            )
            new_image.paste(img.crop(crop_location), (0, 0))
            # save new_image to disc
            mask = Image.new("RGB", (new_image.width, new_image.height), (255, 255, 255))
            for x in range(new_image.width):
                for y in range(new_image.height):
                    try:
                        if new_image.getpixel((x, y))[3] != 0:
                            mask.putpixel((x, y), (0, 0, 0))
                    except IndexError:
                        pass

            # convert image to rgb
            image = new_image.convert("RGB")

            self.do_generate({
                "mask": mask,
                "image": image,
                "location": self.canvas.active_grid_area_rect
            })
        elif self.action == "vid2vid":
            images = self.prep_video()
            self.do_generate({
                "images": images
            })
        else:
            self.do_generate()

    def start_progress_bar(self, section):
        # progressBar: QProgressBar = self.tabs[section].progressBar
        # progressBar.setRange(0, 0)
        if self.progress_bar_started:
            return
        self.progress_bar_started = True
        self.tqdm_callback_triggered = False
        self.stop_progress_bar(section)
        self.tabs[section].progressBar.setRange(0, 0)
        self.tqdm_var.set({
            "step": 0,
            "total": 0,
            "action": section,
            "image": None,
            "data": None
        })

    def stop_progress_bar(self, section):
        self.tabs[section].progressBar.reset()
        self.tabs[section].progressBar.setRange(0, 100)

    def do_generate(self, extra_options=None):
        if not extra_options:
            extra_options = {}

        # self.start_progress_bar(self.current_section)

        action = self.current_section
        tab = self.tabs[action]
        # get the name of the model from the model_dropdown
        sm = self.settings_manager.settings
        sm.set_namespace(action)

        if sm.random_seed.get():
            # randomize seed
            seed = random.randint(0, MAX_SEED)
            sm.seed.set(seed)
            # set random_seed on current tab
            self.tabs[action].seed.setText(str(seed))
        if action in ("txt2img", "img2img", "pix2pix", "depth2img", "txt2vid"):
            samples = sm.n_samples.get()
        else:
            samples = 1

        prompt = self.tabs[action].prompt.toPlainText()
        negative_prompt = self.tabs[action].negative_prompt.toPlainText()
        if self.random_seed:
            seed = random.randint(0, MAX_SEED)
            self.settings.seed.set(seed)
        else:
            seed = sm.seed.get()
        # set model, model_path and model_branch
        # model = sm.model_var.get()

        # set the model data
        model = tab.model_dropdown.currentText()
        model_path = None
        model_branch = None
        section_name = action
        if section_name in ["txt2img", "img2img"]:
            section_name = "generate"
        if model in MODELS[section_name]:
            model_path = MODELS[section_name][model]["path"]
            model_branch = MODELS[section_name][model].get("branch", "main")
        elif model not in self.models:
            model_names = list(MODELS[section_name].keys())
            model = model_names[0]
            model_path = MODELS[section_name][model]["path"]
            model_branch = MODELS[section_name][model].get("branch", "main")
        else:
            model_path = model

        # get controlnet_dropdown from active tab
        use_controlnet = False
        controlnet = ""
        if action == "controlnet":
            controlnet_dropdown = self.tabs[action].controlnet_dropdown
            # get controlnet from controlnet_dropdown
            controlnet = controlnet_dropdown.currentText()
            controlnet = controlnet.lower()
            use_controlnet = controlnet != "none"

        options = {
            f"{action}_prompt": prompt,
            f"{action}_negative_prompt": negative_prompt,
            f"{action}_steps": sm.steps.get(),
            f"{action}_ddim_eta": sm.ddim_eta.get(),  # only applies to ddim scheduler
            f"{action}_n_iter": 1,
            f"{action}_width": sm.working_width.get(),
            f"{action}_height": sm.working_height.get(),
            f"{action}_n_samples": samples,
            f"{action}_scale": sm.scale.get() / 100,
            f"{action}_seed": seed,
            f"{action}_model": model,
            f"{action}_scheduler": sm.scheduler_var.get(),
            f"{action}_model_path": model_path,
            f"{action}_model_branch": model_branch,
            f"width": sm.working_width.get(),
            f"height": sm.working_height.get(),
            "do_nsfw_filter": self.settings_manager.settings.nsfw_filter.get(),
            "model_base_path": sm.model_base_path.get(),
            "pos_x": 0,
            "pos_y": 0,
            "outpaint_box_rect": self.active_rect(),
            "hf_token": self.settings_manager.settings.hf_api_key.get(),
            "enable_model_cpu_offload": sm.enable_model_cpu_offload.get(),
            "use_controlnet": use_controlnet,
            "controlnet": controlnet,
        }
        if action == "superresolution":
            options["original_image_width"] = self.canvas.current_active_image.width
            options["original_image_height"] = self.canvas.current_active_image.height

        if action in ["img2img", "depth2img", "pix2pix", "controlnet"]:
            options[f"{action}_strength"] = sm.strength.get() / 100.0

        if action == "pix2pix":
            options[f"pix2pix_image_guidance_scale"] = sm.pix2pix_image_guidance_scale.get()
        memory_options = {
            "use_last_channels": sm.use_last_channels.get(),
            "use_enable_sequential_cpu_offload": sm.use_enable_sequential_cpu_offload.get(),
            "use_attention_slicing": sm.use_attention_slicing.get(),
            "use_tf32": sm.use_tf32.get(),
            "use_cudnn_benchmark": sm.use_cudnn_benchmark.get(),
            "use_enable_vae_slicing": sm.use_enable_vae_slicing.get(),
            "use_xformers": sm.use_xformers.get(),
        }
        data = {
            "action": action,
            "options": {
                **options,
                **extra_options,
                **memory_options
            }
        }
        data = self.do_generate_data_injection(data)
        self.client.message = data

    def active_rect(self):
        rect = QRect(
            self.canvas.active_grid_area_rect.x(),
            self.canvas.active_grid_area_rect.y(),
            self.canvas.active_grid_area_rect.width(),
            self.canvas.active_grid_area_rect.height(),
        )
        rect.translate(-self.canvas.pos_x, -self.canvas.pos_y)

        return rect

    def refresh_model_list(self):
        for i in range(self.window.tabWidget.count()):
            self.load_model_by_section(self.window.tabWidget.widget(i), self.sections[i])

    def load_model_by_section(self, tab, section_name):
        if section_name in ["txt2img", "img2img"]:
            section_name = "generate"
        models = self.load_default_models(section_name)
        models += self.load_models_from_path()
        self.models = models
        tab.model_dropdown.addItems(models)

    def load_default_models(self, section_name):
        return [
            k for k in MODELS[section_name].keys()
        ]

    def load_models_from_path(self):
        path = os.path.join(self.settings_manager.settings.model_base_path.get())
        if os.path.exists(path):
            return [os.path.join(path, model) for model in os.listdir(path)]
        return []


if __name__ == "__main__":
    qdarktheme.enable_hi_dpi()
    MainWindow([])
