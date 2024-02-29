import base64
import io
import os

from PIL import Image
from PyQt6.QtCore import pyqtSlot
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QHBoxLayout, QWidget

from airunner.data.bootstrap.controlnet_bootstrap_data import controlnet_bootstrap_data
from airunner.enums import SignalCode, ServiceCode
from airunner.utils import image_to_pixmap, auto_export_image, open_file_path
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.controlnet_settings.templates.controlnet_settings_ui import Ui_controlnet_settings
from airunner.service_locator import ServiceLocator


class ControlNetSettingsWidget(BaseWidget):
    widget_class_ = Ui_controlnet_settings

    def __init__(self, *args, **kwrags):
        super().__init__(*args, **kwrags)
        self.controlnet_image = None
        self.imported_controlnet_image = None
        self.controlnet_scale_slider = 0
        self._current_input_image = None
        self._current_imported_image = None
        self._current_active_grid_area_image = None
        self.keep_refreshed = False
        self._active_grid_area_image = None
        self.signal_handlers = {
            SignalCode.CONTROLNET_IMAGE_GENERATED_SIGNAL: self.handle_controlnet_image_generated,
        }

    @property
    def current_controlnet_image(self):
        if self.generator_settings["mask_link_input_image"]:
            return self.controlnet_image
        elif self.generator_settings["mask_use_imported_image"]:
            return self.imported_controlnet_image

    @current_controlnet_image.setter
    def current_controlnet_image(self, value):
        if self.generator_settings["mask_link_input_image"]:
            self.controlnet_image = value
        elif self.generator_settings["mask_use_imported_image"]:
            self.imported_controlnet_image = value
        self.toggle_mask_export_button(value is not None)
        self.set_mask_thumbnail()

    @property
    def active_grid_area_image(self):
        return self._active_grid_area_image

    @property
    def generator_settings(self):
        if "controlnet_image_settings" in self.settings["generator_settings"]:
            return self.settings["generator_settings"]["controlnet_image_settings"]
        return {}

    @generator_settings.setter
    def generator_settings(self, value):
        settings = self.settings
        settings["generator_settings"]["controlnet_image_settings"] = value
        self.settings = settings

    def toggle_mask_export_button(self, enabled):
        self.ui.mask_export_image_button.setEnabled(enabled)

    def action_clicked_button_import_image(self):
        self.import_input_image()

    def action_toggled_use_input_image(self, val):
        generator_settings = self.generator_settings
        generator_settings["use_imported_image"] = val
        self.generator_settings = generator_settings
        self.toggle_use_active_grid_area(not val)
        self.set_thumbnail()
        self.update_buttons()

    def action_toggled_button_use_grid_image(self, val):
        self.toggle_use_imported_image(not val)
        self.toggle_use_active_grid_area(val)
        self.update_buttons()

    def action_toggled_button_lock_grid_image(self, val):
        self.toggle_keep_refreshed(val)

    def action_clicked_button_refresh_grid_image(self):
        self.toggle_use_active_grid_area(True)

    def action_clicked_button_clear_input_image(self):
        self.clear_input_image()
        widget = QWidget()
        grid_layout = QHBoxLayout()
        grid_layout.setSpacing(0)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.addWidget(widget)

    def clear_input_image(self):
        if self.generator_settings["use_grid_image"]:
            self._active_grid_area_image = None
        self.set_thumbnail()

    def toggle_keep_refreshed(self, value):
        if self.generator_settings["use_grid_image"]:
            generator_settings = self.generator_settings
            generator_settings["recycle_grid_image"] = value
            self.generator_settings = generator_settings
        self.set_thumbnail()

    def toggle_use_imported_image(self, value):
        generator_settings = self.generator_settings
        generator_settings["use_imported_image"] = value
        self.generator_settings = generator_settings
        self.set_thumbnail()

    def toggle_use_active_grid_area(self, value):
        generator_settings = self.generator_settings
        generator_settings["use_grid_image"] = value
        self.generator_settings = generator_settings
        self.set_thumbnail()

    def update_buttons(self):
        self.ui.use_imported_image_button.blockSignals(True)
        self.ui.use_grid_image_button.blockSignals(True)
        self.ui.recycle_grid_image_button.blockSignals(True)

        if self.generator_settings["use_grid_image"]:
            self.ui.import_image_button.setEnabled(False)
            self.ui.recycle_grid_image_button.setEnabled(True)
            # hide the self.ui.refresh_input_image_button button widget
            self.ui.clear_image_button.hide()
            self.ui.refresh_input_image_button.show()
            self.ui.use_imported_image_button.setChecked(False)
            self.ui.use_grid_image_button.setChecked(self.generator_settings["use_grid_image"])
            self.ui.recycle_grid_image_button.setChecked(self.generator_settings["recycle_grid_image"])
        else:
            self.ui.import_image_button.setEnabled(True)
            self.ui.recycle_grid_image_button.setEnabled(False)
            self.ui.refresh_input_image_button.hide()
            self.ui.clear_image_button.show()
            self.ui.use_imported_image_button.setChecked(True)
            self.ui.use_grid_image_button.setChecked(False)
            self.ui.recycle_grid_image_button.setChecked(False)

        self.ui.use_imported_image_button.blockSignals(False)
        self.ui.use_grid_image_button.blockSignals(False)
        self.ui.recycle_grid_image_button.blockSignals(False)

    def import_input_image(self):
        file_path, _ = self.get_service(ServiceCode.DISPLAY_IMPORT_IMAGE_DIALOG)(
            directory=self.settings["path_settings"]["image_path"],
        )
        if file_path == "":
            return
        image = Image.open(file_path)
        image = image.convert("RGBA")

        # convert image to base64_image
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()
        image_base64 = base64.encodebytes(img_byte_arr).decode('ascii')
        generator_settings = self.generator_settings
        generator_settings["imported_image_base64"] = image_base64
        self.generator_settings = generator_settings
        self.set_thumbnail()

    def get_current_input_image(self):
        if self.generator_settings["use_imported_image"]:
            if self.generator_settings["link_to_input_image"]:
                image_base64 = self.settings["generator_settings"]["input_image_settings"]["imported_image_base64"]
                if image_base64 is not None:
                    # Use the image from the input image settings
                    return Image.open(io.BytesIO(base64.b64decode(image_base64)))

            imported_image_base64 = self.generator_settings["imported_image_base64"]
            if imported_image_base64 is not None:
                return Image.open(io.BytesIO(base64.b64decode(imported_image_base64)))
        elif self.generator_settings["use_grid_image"]:
            return self.grid_image()

    def set_thumbnail(self):
        image = self.get_current_input_image()

        if image:
            # self.ui.image_thumbnail is a QPushButton
            self.ui.image_thumbnail.setIcon(QIcon(image_to_pixmap(image, size=72)))
        else:
            self.ui.image_thumbnail.setIcon(QIcon())

    def grid_image(self):
        return self.get_service(ServiceCode.CURRENT_ACTIVE_IMAGE)()

    def initialize_groupbox(self):
        self.ui.groupBox.setChecked(self.generator_settings["enable_controlnet"] is True)

    def handle_toggle_controlnet(self, value):
        generator_settings = self.generator_settings
        generator_settings["enable_controlnet"] = value
        self.generator_settings = generator_settings
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

    def action_clicked_button_clear_input_image_mask(self):self.clear_controlnet_input_image()

    def action_clicked_button_import_image_mask(self):
        self.import_controlnet_image()

    def send_active_mask_to_canvas(self):
        if not self.current_controlnet_image:
            return
        self.emit(SignalCode.CANVAS_UPDATE_SIGNAL)

    def toggle_mask_link(self, value):
        generator_settings = self.generator_settings
        generator_settings["mask_use_imported_image"] = not value
        generator_settings["mask_link_input_image"] = value
        self.generator_settings = generator_settings
        self.set_mask_thumbnail()
        self.toggle_buttons()

    def toggle_mask_use_imported_image(self, value):
        generator_settings = self.generator_settings
        generator_settings["mask_use_imported_image"] = value
        generator_settings["mask_link_input_image"] = not value
        self.generator_settings = generator_settings
        self.set_mask_thumbnail()
        self.toggle_buttons()

    def handle_link_settings_clicked(self, value):
        """
        Use the same setting as input image
        :return:
        """
        generator_settings = self.generator_settings
        generator_settings["link_to_input_image"] = value
        self.generator_settings = generator_settings
        self.toggle_buttons()
        self.set_thumbnail()

    def export_generated_controlnet_image(self):
        path, image = auto_export_image(
            base_path=self.settings["path_settings"]["base_path"],
            image_path=self.settings["path_settings"]["image_path"],
            image_export_type=self.settings["image_export_type"],
            image=self.current_controlnet_image,
            type="controlnet",
            data={
                "controlnet": self.generator_settings["controlnet"]
            },
            seed=self.generator_settings["seed"]
        )
        if path is not None:
            self.emit(
                SignalCode.APPLICATION_STATUS_INFO_SIGNAL,
                "Controlnet image exported to: {}".format(path)
            )

    def handle_controlnet_image_generated(self):
        self.current_controlnet_image = ServiceLocator.get("controlnet_image")()
        self.set_mask_thumbnail()

    def toggle_buttons(self):
        self.toggle_import_image_button()
        self.toggle_link_input_image_button()
        self.toggle_use_grid_image()
        self.toggle_mask_buttons()
        use_grid = self.generator_settings["use_grid_image"]
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

    def toggle_button(self, ui_element, value, setting_name):
        attr = getattr(self.ui, ui_element)
        attr.blockSignals(True)
        attr.setChecked(value)
        attr.blockSignals(False)
        generator_settings = self.generator_settings
        generator_settings[setting_name] = value
        self.generator_settings = generator_settings

    def toggle_mask_buttons(self):
        generator_settings = self.generator_settings
        self.toggle_button(
            "mask_import_button",
            generator_settings["mask_use_imported_image"],
            "mask_use_imported_image"
        )
        self.toggle_button(
            "mask_link_to_input_image_button",
            generator_settings["mask_link_input_image"],
            "mask_link_input_image"
        )
        self.toggle_button(
            "mask_use_imported_image_button",
            generator_settings["mask_use_imported_image"],
            "mask_use_imported_image"
        )

    def toggle_link_input_image_button(self):
        link_to_input_image = self.generator_settings["link_to_input_image"]
        self.toggle_button(
            "link_settings_button",
            link_to_input_image,
            "link_to_input_image"
        )

    def toggle_import_image_button(self):
        use_import_image = self.generator_settings["use_imported_image"]
        self.toggle_button(
            "import_image_button",
            use_import_image,
            "use_imported_image"
        )

    def toggle_use_grid_image(self):
        use_grid_image = self.generator_settings["use_grid_image"]
        self.ui.recycle_grid_image_button.setEnabled(use_grid_image)
        self.ui.use_grid_image_button.setChecked(use_grid_image)
        self.ui.recycle_grid_image_button.setChecked(use_grid_image and self.generator_settings["recycle_grid_image"])

    def clear_controlnet_input_image(self):
        self.current_controlnet_image = None

    def import_controlnet_image(self):
        """
        Allow user to browse for a controlnet image on disk and import
        it into the application for use with controlnet during image generation.
        :return:
        """
        controlnet_image_mask_path = os.path.join(self.settings["path_settings"]["image_path"], "controlnet_masks")
        file_path, _ = open_file_path(
            label="Import Mask",
            directory=controlnet_image_mask_path
        )
        if file_path == "":
            return
        self.imported_controlnet_image = Image.open(file_path)
        self.set_mask_thumbnail()

    def handle_image_generated(self):
        if self.generator_settings["use_grid_image"]:
            self.set_thumbnail()

    def set_mask_thumbnail(self):
        image = self.current_controlnet_image
        if image:
            self.ui.mask_thumbnail.setPixmap(image_to_pixmap(image, size=72))
        else:
            # clear the image
            self.ui.mask_thumbnail.clear()
    
    def showEvent(self, event):
        super().showEvent(event)
        super().initialize()
        self.initialize_combobox()
    
    def initialize_combobox(self):
        controlnet_options = [item["display_name"] for item in controlnet_bootstrap_data]
        self.ui.controlnet_dropdown.blockSignals(True)
        self.ui.controlnet_dropdown.clear()
        self.ui.controlnet_dropdown.addItems(controlnet_options)
        current_index = 0
        for index, controlnet_name in enumerate(controlnet_options):
            if controlnet_name.lower() == self.generator_settings["controlnet"]:
                current_index = index
                break
        self.ui.controlnet_dropdown.setCurrentIndex(current_index)
        self.ui.controlnet_dropdown.blockSignals(False)

    def handle_controlnet_scale_slider_change(self, value):
        generator_settings = self.generator_settings
        generator_settings["guidance_scale"] = value
        self.generator_settings = generator_settings

    def handle_controlnet_change(self, attr_name, value=None, widget=None):
        generator_settings = self.generator_settings
        generator_settings["controlnet"] = value
        self.generator_settings = generator_settings

    def action_controlnet_model_text_changed(self, model_value):
        generator_settings = self.generator_settings
        generator_settings["controlnet_model"] = model_value
        self.generator_settings = generator_settings
