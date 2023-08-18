from functools import partial

from PIL import Image
from PyQt6.QtWidgets import QComboBox, QWidget, QHBoxLayout

from airunner.utils import image_to_pixmap
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.slider_widget import SliderWidget


class ControlNetSettingsData:
    input_image: Image = None
    controlnet_image: Image = None
    use_active_grid_area: bool = False
    controlnet_scale_slider: float = 1.0


class ControlNetSettingsWidget(BaseWidget):
    name = "controlnet_settings/controlnet_settings"
    _active_grid_area_image = None
    data: ControlNetSettingsData = None
    icons = {
        "import_image_button": "046-import",
        "clear_image_button": "006-trash",
        "export_generated_button": "export",
        "import_control_image_button": "046-import",
        "clear_control_image_button": "006-trash",
    }

    @property
    def active_grid_area_image(self):
        if self.app.canvas.current_layer.image_data.image:
            self._active_grid_area_image = self.app.canvas.current_layer.image_data.image.copy()
        return self._active_grid_area_image

    @property
    def current_image(self):
        if not self.data.use_active_grid_area:
            return self.data.input_image
        else:
            return self.active_grid_area_image

    @property
    def current_controlnet_image(self):
        return self.data.controlnet_image

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data = ControlNetSettingsData()
        
        self.template.controlnet_groupbox.setChecked(self.app.enable_controlnet)
        self.template.controlnet_groupbox.toggled.connect(
            partial(self.app.handle_value_change, "enable_controlnet"))
        self.add_controlnet_widgets()
        self.template.use_active_grid_area.toggled.connect(
            partial(self.toggle_use_active_grid_area))
        self.template.use_imported_image.toggled.connect(
            partial(self.toggle_use_imported_image))
        self.template.import_image_button.clicked.connect(
            self.import_input_image)
        self.template.import_control_image_button.clicked.connect(
            self.import_controlnet_image)
        self.template.clear_image_button.clicked.connect(
            self.clear_input_image)
        self.template.clear_control_image_button.clicked.connect(
            self.clear_controlnet_input_image)
        self.app.image_generated.connect(self.handle_image_generated)
        self.app.controlnet_image_generated.connect(self.handle_controlnet_image_generated)
        self.template.export_generated_button.clicked.connect(self.export_generated_controlnet_image)

        self.toggle_import_image_button()
        self.set_stylesheet()

    def export_generated_controlnet_image(self):
        file_path, _ = self.app.display_file_export_dialog()
        if file_path == "":
            return
        self.data.controlnet_image.save(file_path)

    def handle_controlnet_image_generated(self):
        self.data.controlnet_image = self.app.controlnet_image
        self.set_controlnet_thumbnail(self.data.controlnet_image)

    def toggle_import_image_button(self):
        self.template.import_image_button.setEnabled(not self.data.use_active_grid_area)
        self.template.clear_image_button.setEnabled(not self.data.use_active_grid_area)

    def toggle_use_imported_image(self, value):
        self.data.use_active_grid_area = not value
        self.set_thumbnail(self.data.input_image)
        self.toggle_import_image_button()

    def toggle_use_active_grid_area(self, value):
        self.data.use_active_grid_area = value
        self.set_thumbnail(self.active_grid_area_image)
        self.toggle_import_image_button()

    def clear_input_image(self):
        self.data.input_image = None
        self.set_thumbnail(None)

    def clear_controlnet_input_image(self):
        self.data.controlnet_image = None
        self.set_controlnet_thumbnail(None)

    def import_input_image(self):
        """
        Allow user to browse for a controlnet image on disk and import
        it into the application for use with controlnet during image generation.
        :return:
        """
        file_path, _ = self.app.display_import_image_dialog()
        if file_path == "":
            return
        self.data.input_image = Image.open(file_path)
        self.set_thumbnail(self.data.input_image)

    def import_controlnet_image(self):
        """
        Allow user to browse for a controlnet image on disk and import
        it into the application for use with controlnet during image generation.
        :return:
        """
        file_path, _ = self.app.display_import_image_dialog()
        if file_path == "":
            return
        self.data.controlnet_image = Image.open(file_path)
        self.set_controlnet_thumbnail(self.data.controlnet_image)

    def handle_image_generated(self):
        if self.data.use_active_grid_area:
            self.set_thumbnail(self.active_grid_area_image)

    def set_thumbnail(self, image):
        if image:
            self.template.image_thumbnail.setPixmap(image_to_pixmap(image, size=128))
        else:
            # clear the image
            self.template.image_thumbnail.clear()

    def set_controlnet_thumbnail(self, image):
        if image:
            self.template.controlnet_image_thumbnail.setPixmap(image_to_pixmap(image, size=128))
        else:
            # clear the image
            self.template.controlnet_image_thumbnail.clear()

    # model_frame
    def add_controlnet_widgets(self):
        # if self.tab not in ["txt2img", "img2img", "outpaint", "txt2vid"] \
        #         or self.tab_section == "kandinsky" or self.tab_section == "shapegif":
        #     return
        controlnet_options = [
            "Canny",
            "MLSD",
            "Depth Leres",
            "Depth Leres++",
            "Depth Midas",
            # "Depth Zoe",
            "Normal Bae",
            # "Normal Midas",
            # "Segmentation",
            "Lineart Anime",
            "Lineart Coarse",
            "Lineart Realistic",
            "Openpose",
            "Openpose Face",
            "Openpose Faceonly",
            "Openpose Full",
            "Openpose Hand",
            "Scribble Hed",
            "Scribble Pidinet",
            "Softedge Hed",
            "Softedge Hedsafe",
            "Softedge Pidinet",
            "Softedge Pidsafe",
            # "Pixel2Pixel",
            # "Inpaint",
            "Shuffle",
        ]
        controlnet_widget = QComboBox(self)
        controlnet_widget.setObjectName("controlnet_dropdown")
        controlnet_widget.addItems(controlnet_options)
        current_index = 0
        for index, controlnet_name in enumerate(controlnet_options):
            if controlnet_name.lower() == self.app.controlnet:
                current_index = index
                break
        controlnet_widget.setCurrentIndex(current_index)
        # set fontsize of controlnet_widget to 9
        font = controlnet_widget.font()
        font.setPointSize(9)
        controlnet_widget.setFont(font)
        controlnet_widget.currentTextChanged.connect(
            partial(self.app.handle_value_change, "controlnet", widget=controlnet_widget))
        controlnet_scale_slider = SliderWidget(
            app=self.app,
            label_text="Controlnet Scale",
            slider_callback=partial(self.app.handle_value_change, "controlnet_scale"),
            current_value=self.app.controlnet_guidance_scale,
            slider_minimum=0,
            slider_maximum=1000,
            spinbox_minimum=0.0,
            spinbox_maximum=1.0
        )
        # self.data[self.tab_section][self.tab]["controlnet_scale_slider"] = controlnet_scale_slider
        self.data.controlnet_scale_slider = controlnet_scale_slider
        grid_layout = QHBoxLayout(self.template.model_frame)
        widget = QWidget()
        grid_layout.addWidget(widget)
        grid_layout.addWidget(controlnet_widget)
        grid_layout.addWidget(controlnet_scale_slider)
