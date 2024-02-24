import base64
import io

from PIL import Image
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QHBoxLayout, QWidget

from airunner.enums import SignalCode, ServiceCode
from airunner.utils import image_to_pixmap
from airunner.widgets.input_image.templates.input_image_ui import Ui_input_image
from airunner.widgets.base_widget import BaseWidget


class InputImageSettingsWidget(BaseWidget):
    widget_class_ = Ui_input_image

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.input_image = None
        self.keep_refreshed = False
        self._active_grid_area_image = None

    @property
    def generator_settings(self):
        if "input_image_settings" in self.settings["generator_settings"]:
            return self.settings["generator_settings"]["input_image_settings"]
        return {}

    @generator_settings.setter
    def generator_settings(self, value):
        settings = self.settings
        settings["generator_settings"]["input_image_settings"] = value
        self.settings = settings

    @property
    def generator_section(self):
        return self.property("generator_section")

    @property
    def generator_name(self):
        return self.property("generator_name")

    @property
    def get_current_input_image(self):
        try:
            if not self.generator_settings:
                return None
            if self.generator_settings["use_imported_image"]:
                return self.input_image
            elif self.generator_settings["use_grid_image"]:
                return self.grid_image()
        except AttributeError:
            return None

    def active_grid_area_image(self):
        if not self.generator_settings["recycle_grid_image"] or not self._active_grid_area_image:
            image = self.grid_image()
            if image:
                self._active_grid_area_image = image.copy()
        return self._active_grid_area_image

    def grid_image(self):
        return self.get_service(ServiceCode.CURRENT_ACTIVE_IMAGE)()

    def showEvent(self, event):
        super().showEvent(event)
        self.update_buttons()
        self.ui.groupBox.setTitle(self.property("checkbox_label"))
        self.ui.scale_slider_widget.initialize()
        self.initialize_groupbox()
    
    def initialize_combobox(self):
        pass

    def initialize_groupbox(self):
        self.ui.groupBox.blockSignals(True)
        self.ui.groupBox.setChecked(self.generator_settings["enable_input_image"])
        self.ui.groupBox.blockSignals(False)

    def action_toggled_use_input_image(self, val):
        generator_settings = self.generator_settings
        generator_settings["enable_input_image"] = val
        self.generator_settings = generator_settings
        self.toggle_use_active_grid_area(not val)
        self.set_thumbnail()
        self.update_buttons()

    def action_toggled_button_use_imported_image(self, val):
        self.toggle_use_imported_image(val)
        self.toggle_use_active_grid_area(not val)
        self.update_buttons()

    def action_toggled_button_use_grid_image(self, val):
        self.toggle_use_imported_image(not val)
        self.toggle_use_active_grid_area(val)
        self.update_buttons()

    def toggle_use_imported_image(self, value):
        generator_settings = self.generator_settings
        generator_settings["use_imported_image"] = value
        self.generator_settings = generator_settings
        self.set_thumbnail(self.input_image)

    def action_toggled_button_lock_grid_image(self, val):
        self.toggle_keep_refreshed(val)

    def action_toggled_button_refresh_input_image(self, val):
        self.toggle_keep_refreshed(val)

    def toggle_keep_refreshed(self, value):
        if self.generator_settings["use_grid_image"]:
            generator_settings = self.generator_settings
            generator_settings["recycle_grid_image"] = value
            self.generator_settings = generator_settings
        self.set_thumbnail()

    def action_clicked_button_refresh_grid_image(self):
        self.set_thumbnail(self.toggle_use_active_grid_area(True))

    def action_clicked_button_import_image(self):
        self.import_input_image()

    def action_clicked_button_thumbnail(self):
        self.send_active_image_to_canvas()

    def action_clicked_button_clear_input_image(self):
        self.clear_input_image()

    def handle_image_strength_changed(self, val):
        generator_settings = self.generator_settings
        generator_settings["strength"] = val
        self.generator_settings = generator_settings

    def handle_image_scale_changed(self, val):
        generator_settings = self.generator_settings
        generator_settings["image_scale"] = val
        self.generator_settings = generator_settings

    def import_input_image(self):
        file_path, _ = self.get_service(ServiceCode.DISPLAY_IMPORT_IMAGE_DIALOG)(
            directory=self.settings["path_settings"]["image_path"],
        )
        if file_path == "":
            return
        image = Image.open(file_path)
        image = image.convert("RGBA")
        self.input_image = image
        self.set_thumbnail(image)
        # convert image to base64_image
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()
        image_base64 = base64.encodebytes(img_byte_arr).decode('ascii')
        generator_settings = self.generator_settings
        generator_settings["imported_image_base64"] = image_base64
        self.generator_settings = generator_settings

    def clear_input_image(self):
        if self.generator_settings["use_grid_image"]:
            self._active_grid_area_image = None
        elif self.generator_settings["use_imported_image"]:
            self.input_image = None
        self.set_thumbnail()

    def toggle_use_active_grid_area(self, value):
        generator_settings = self.generator_settings
        generator_settings["use_grid_image"] = value
        self.generator_settings = generator_settings
        self.set_thumbnail(self.get_current_input_image)

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

    def export_input_image_mask(self):
        print("export input image mask")

    def clear_input_image_mask(self):
        print("clear input image mask")

    def handle_new_image(self, data):
        if not self.generator_settings["recycle_grid_image"] or not self._active_grid_area_image:
            self._active_grid_area_image = data["processed_image"].copy()
        self.set_thumbnail()

    def set_thumbnail(self, image=None):
        try:
            image = self.get_current_input_image if not image else image
        except AttributeError:
            return
        if image:
            # self.ui.image_thumbnail is a QPushButton
            self.ui.image_thumbnail.setIcon(QIcon(image_to_pixmap(image, size=72)))
        else:
            self.ui.image_thumbnail.setIcon(QIcon())

    def send_active_image_to_canvas(self):
        # send the current input image to the canvas
        if not self.current_input_image:
            return
        self.emit(SignalCode.CANVAS_UPDATE_SIGNAL)
