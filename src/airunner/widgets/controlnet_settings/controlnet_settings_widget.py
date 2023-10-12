import os
from functools import partial

from PIL import Image
from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QComboBox, QWidget, QHBoxLayout

from airunner.utils import image_to_pixmap, auto_export_image, open_file_path
from airunner.widgets.controlnet_settings.templates.controlnet_settings_ui import Ui_controlnet_settings
from airunner.widgets.input_image.input_image_settings_widget import InputImageSettingsWidget
from airunner.widgets.slider.slider_widget import SliderWidget


class ControlNetSettingsWidget(InputImageSettingsWidget):
    widget_class_ = Ui_controlnet_settings
    controlnet_image = None
    imported_controlnet_image = None
    controlnet_scale_slider = 0
    _current_input_image = None
    _current_imported_image = None
    _current_active_grid_area_image = None

    @property
    def current_controlnet_image(self):
        if self.settings_manager.generator.controlnet_mask_link_input_image:
            return self.controlnet_image
        elif self.settings_manager.generator.controlnet_mask_use_imported_image:
            return self.imported_controlnet_image

    @current_controlnet_image.setter
    def current_controlnet_image(self, value):
        if self.settings_manager.generator.controlnet_mask_link_input_image:
            self.controlnet_image = value
        elif self.settings_manager.generator.controlnet_mask_use_imported_image:
            self.imported_controlnet_image = value
        self.toggle_mask_export_button(value is not None)
        self.set_mask_thumbnail()

    def toggle_mask_export_button(self, enabled):
        self.ui.mask_export_image_button.setEnabled(enabled)

    @property
    def active_grid_area_image(self):
        if self.app.canvas.current_layer.image_data.image:
            self._active_grid_area_image = self.app.canvas.current_layer.image_data.image.copy()
        return self._active_grid_area_image

    @property
    def current_image(self):
        if not self.settings_manager.generator.enable_controlnet:
            return None

        if self.settings_manager.generator.controlnet_input_image_link_to_input_image:
            return self.app.generator_tab_widget.current_input_image
        elif self.settings_manager.generator.controlnet_input_image_use_imported_image:
            return self.input_image
        elif self.settings_manager.generator.controlnet_use_grid_image:
            return self.active_grid_area_image
        else:
            return None

    @property
    def cached_image(self):
        if self.settings_manager.generator.controlnet_input_image_link_to_input_image:
            return self._current_input_image
        elif self.settings_manager.generator.controlnet_input_image_use_imported_image:
            return self._current_imported_image
        elif self.settings_manager.generator.controlnet_use_grid_image:
            return self._current_active_grid_area_image
        else:
            return None

    @cached_image.setter
    def cached_image(self, value):
        if self.settings_manager.generator.controlnet_input_image_link_to_input_image:
            self._current_input_image = value
        elif self.settings_manager.generator.controlnet_input_image_use_imported_image:
            self._current_imported_image = value
        elif self.settings_manager.generator.controlnet_use_grid_image:
            self._current_active_grid_area_image = value

    def initialize_groupbox(self):
        if self.settings_manager.generator:
            self.ui.groupBox.setChecked(self.settings_manager.generator.enable_controlnet)

    def handle_toggle_controlnet(self, value):
        if self.settings_manager.current_tab != "stablediffusion":
            value = False
        self.settings_manager.set_value("generator.enable_controlnet", value)
        self.set_thumbnail()
        # self.set_stylesheet()

    def action_toggled_use_controlnet(self, val):
        self.handle_toggle_controlnet(val)

    def action_toggled_button_link_input_image(self, val):
        self.handle_link_settings_clicked(val)

    def action_toggled_button_import_image_mask(self, val):
        self.import_controlnet_image()

    def action_toggled_button_link_input_image_mask(self, val):
        self.toggle_mask_link(val)

    def action_toggled_button_use_input_image_mask(self, val):
        self.toggle_mask_use_imported_image(val)

    def action_clicked_button_thumbnail_mask(self):
        self.send_active_mask_to_canvas()

    def action_clicked_button_export_mask(self):
        self.export_generated_controlnet_image()

    def action_clicked_button_clear_input_image_mask(self):
        self.clear_controlnet_input_image()

    def action_clicked_button_import_image_mask(self):
        self.import_controlnet_image()

    def send_active_mask_to_canvas(self):
        if not self.current_controlnet_image:
            return

        self.app.canvas.update_image_canvas(
            self.settings_manager.current_tab,
            {
                "action": self.settings_manager.current_tab,
                "options": {
                    "outpaint_box_rect": self.app.canvas.active_grid_area_rect,
                    "generator_section": self.settings_manager.current_generator_section
                }
            },
            self.current_controlnet_image
        )
        self.app.canvas.update()

    def toggle_mask_link(self, value):
        self.settings_manager.generator.controlnet_mask_use_imported_image = not value
        self.settings_manager.generator.controlnet_mask_link_input_image = value
        self.set_mask_thumbnail()
        self.toggle_buttons()

    def toggle_mask_use_imported_image(self, value):
        self.settings_manager.generator.controlnet_mask_use_imported_image = value
        self.settings_manager.generator.controlnet_mask_link_input_image = not value
        self.set_mask_thumbnail()
        self.toggle_buttons()

    def handle_link_settings_clicked(self, value):
        """
        Use the same setting as input image
        :return:
        """
        self.settings_manager.generator.controlnet_input_image_link_to_input_image = value
        if value:
            self.settings_manager.generator.controlnet_input_image_use_imported_image = False
            self.settings_manager.generator.controlnet_use_grid_image = False
        self.toggle_buttons()
        self.set_thumbnail()

    def export_generated_controlnet_image(self):
        path = auto_export_image(
            image=self.current_controlnet_image,
            type="controlnet",
            data={
                "controlnet": self.settings_manager.generator.controlnet
            },
            seed=self.settings_manager.generator.seed
        )
        if path is not None:
            self.app.set_status_label(f"Mask exported to {path}")

    @pyqtSlot(bool)
    def handle_controlnet_image_generated(self):
        self.current_controlnet_image = self.app.controlnet_image
        self.set_mask_thumbnail()

    def toggle_buttons(self):
        self.toggle_import_image_button()
        self.toggle_link_input_image_button()
        self.toggle_import_image_button()
        self.toggle_use_grid_image()
        self.toggle_mask_buttons()
        use_grid = self.settings_manager.generator.controlnet_use_grid_image
        if use_grid:
            self.ui.refresh_input_image_button.show()
            self.ui.clear_image_button.hide()
            self.ui.mask_clear_image_button.hide()
            self.ui.recycle_grid_image_button.setEnabled(True)
        else:
            self.ui.refresh_input_image_button.hide()
            self.ui.clear_image_button.show()
            self.ui.mask_clear_image_button.show()
            self.ui.recycle_grid_image_button.setEnabled(False)

    def toggle_mask_buttons(self):
        self.ui.mask_import_button.setEnabled(self.settings_manager.generator.controlnet_mask_use_imported_image)
        self.ui.mask_link_to_input_image_button.setChecked(self.settings_manager.generator.controlnet_mask_link_input_image)
        self.ui.mask_use_imported_image_button.setChecked(self.settings_manager.generator.controlnet_mask_use_imported_image)

    def toggle_link_input_image_button(self):
        use_input_image = self.settings_manager.generator.controlnet_input_image_link_to_input_image
        self.settings_manager.generator.controlnet_input_image_link_to_input_image = use_input_image
        self.ui.link_settings_button.setChecked(use_input_image)

    def toggle_import_image_button(self):
        use_import_image = self.settings_manager.generator.controlnet_input_image_use_imported_image
        self.ui.import_image_button.setEnabled(use_import_image)
        self.ui.use_imported_image_button.setChecked(use_import_image)

    def toggle_use_grid_image(self):
        use_grid_image = self.settings_manager.generator.controlnet_use_grid_image
        self.ui.recycle_grid_image_button.setEnabled(use_grid_image)
        self.ui.use_grid_image_button.setChecked(use_grid_image)
        self.ui.recycle_grid_image_button.setChecked(use_grid_image and self.settings_manager.generator.controlnet_recycle_grid_image)

    def clear_controlnet_input_image(self):
        self.current_controlnet_image = None

    def import_controlnet_image(self):
        """
        Allow user to browse for a controlnet image on disk and import
        it into the application for use with controlnet during image generation.
        :return:
        """
        controlnet_image_mask_path = os.path.join(self.settings_manager.path_settings.image_path, "controlnet_masks")
        file_path, _ = open_file_path(
            label="Import Mask",
            directory=controlnet_image_mask_path
        )
        if file_path == "":
            return
        self.imported_controlnet_image = Image.open(file_path)
        self.set_mask_thumbnail()

    def handle_image_generated(self):
        if self.settings_manager.generator.controlnet_use_grid_image:
            self.set_thumbnail()

    def set_mask_thumbnail(self):
        image = self.current_controlnet_image
        if image:
            self.ui.mask_thumbnail.setPixmap(image_to_pixmap(image, size=72))
        else:
            # clear the image
            self.ui.mask_thumbnail.clear()

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
            if controlnet_name.lower() == self.settings_manager.generator.controlnet:
                current_index = index
                break
        controlnet_widget.setCurrentIndex(current_index)
        # set fontsize of controlnet_widget to 9
        font = controlnet_widget.font()
        font.setPointSize(9)
        controlnet_widget.setFont(font)
        controlnet_widget.currentTextChanged.connect(
            partial(self.handle_controlnet_change, "controlnet", widget=controlnet_widget))
        controlnet_widget.setMaximumWidth(100)
        controlnet_scale_slider = SliderWidget(
            label_text="Scale",
            slider_callback=self.handle_controlnet_scale_slider_change,
            current_value=self.settings_manager.generator.controlnet_guidance_scale,
            slider_minimum=0,
            slider_maximum=1000,
            spinbox_minimum=0.0,
            spinbox_maximum=1.0
        )
        self.controlnet_scale_slider = controlnet_scale_slider
        grid_layout = QHBoxLayout(self.ui.model_frame)
        # remove spacing from grid layout
        grid_layout.setSpacing(5)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        widget = QWidget()
        grid_layout.addWidget(widget)
        grid_layout.addWidget(controlnet_widget)
        grid_layout.addWidget(controlnet_scale_slider)

    def handle_controlnet_scale_slider_change(self, value):
        self.settings_manager.set_value(
            "generator.controlnet_guidance_scale",
            value
        )

    def handle_controlnet_change(self, attr_name, value=None, widget=None):
        self.settings_manager.set_value(attr_name, value)
