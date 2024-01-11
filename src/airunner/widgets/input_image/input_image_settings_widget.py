from PIL import Image
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QHBoxLayout, QWidget

from airunner.utils import image_to_pixmap
from airunner.widgets.input_image.templates.input_image_ui import Ui_input_image
from airunner.widgets.base_widget import BaseWidget


class InputImageSettingsWidget(BaseWidget):
    widget_class_ = Ui_input_image
    input_image = None
    keep_refreshed = False
    _active_grid_area_image = None

    @property
    def generator_section(self):
        return self.property("generator_section")

    @property
    def generator_name(self):
        return self.property("generator_name")

    def active_grid_area_image(self):
        if not self.app.settings_manager.generator_settings.input_image_recycle_grid_image or not self._active_grid_area_image:
            layer_image = self.app.canvas.current_layer.image
            if layer_image.image:
                self._active_grid_area_image = layer_image.image.copy()
        return self._active_grid_area_image

    @property
    def current_input_image(self):
        try:
            if not self.app.settings_manager.generator_settings:
                return None
            if self.app.settings_manager.generator_settings.input_image_use_imported_image:
                return self.input_image
            elif self.app.settings_manager.generator_settings.input_image_use_grid_image:
                return self.active_grid_area_image()
        except AttributeError:
            return None

    def initialize(self):
        self.update_buttons()
        self.ui.groupBox.setTitle(self.property("checkbox_label"))
        self.ui.scale_slider_widget.initialize()
        self.initialize_groupbox()
    
    def initialize_combobox(self):
        pass

    def initialize_groupbox(self):
        self.ui.groupBox.blockSignals(True)
        self.ui.groupBox.setChecked(self.app.settings_manager.generator_settings.enable_input_image)
        self.ui.groupBox.blockSignals(False)

    def action_toggled_use_input_image(self, val):
        self.app.settings_manager.set_value("generator.enable_input_image", val)

    def action_toggled_button_use_imported_image(self, val):
        self.toggle_use_imported_image(val)
        self.toggle_use_active_grid_area(not val)
        self.update_buttons()

    def action_toggled_button_use_grid_image(self, val):
        self.toggle_use_imported_image(not val)
        self.toggle_use_active_grid_area(val)
        self.update_buttons()

    def toggle_use_imported_image(self, value):
        self.app.settings_manager.set_value("generator.input_image_use_imported_image", value)
        self.set_thumbnail(self.input_image)

    def action_toggled_button_lock_grid_image(self, val):
        self.toggle_keep_refreshed(val)

    def action_toggled_button_refresh_input_image(self, val):
        self.toggle_keep_refreshed(val)

    def toggle_keep_refreshed(self, value):
        if self.app.settings_manager.generator_settings.input_image_use_grid_image:
            self.app.settings_manager.set_value("generator.input_image_recycle_grid_image", value)
        self.set_thumbnail()

    def action_clicked_button_refresh_grid_image(self):
        self.set_thumbnail(self.active_grid_area_image())

    def action_clicked_button_import_image(self):
        self.import_input_image()

    def action_clicked_button_thumbnail(self):
        self.send_active_image_to_canvas()

    def action_clicked_button_clear_input_image(self):
        self.clear_input_image()
        grid_layout = QHBoxLayout(self.ui.scale_frame)
        grid_layout.setSpacing(0)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        widget = QWidget()
        grid_layout.addWidget(widget)
        grid_layout.addWidget(slider)

    def handle_image_strength_changed(self, val):
        self.app.settings_manager.set_value("generator.strength", val)

    def handle_image_scale_changed(self, val):
        self.app.settings_manager.set_value("generator.image_scale", val)

    def import_input_image(self):
        file_path, _ = self.app.display_import_image_dialog(
            directory=self.app.image_path,
        )
        if file_path == "":
            return
        image = Image.open(file_path)
        image = image.convert("RGBA")
        self.input_image = image
        self.set_thumbnail(image)

    def clear_input_image(self):
        if self.app.settings_manager.generator_settings.input_image_use_grid_image:
            self._active_grid_area_image = None
        elif self.app.settings_manager.generator_settings.input_image_use_imported_image:
            self.input_image = None
        self.set_thumbnail()

    def toggle_use_active_grid_area(self, value):
        self.app.settings_manager.set_value("generator.input_image_use_grid_image", value)
        self.set_thumbnail(self.current_input_image)

    def update_buttons(self):
        if not self.app.settings_manager.generator_settings:
            return
    
        self.ui.use_imported_image_button.blockSignals(True)
        self.ui.use_grid_image_button.blockSignals(True)
        self.ui.recycle_grid_image_button.blockSignals(True)

        if self.app.settings_manager.generator_settings.input_image_use_grid_image:
            self.ui.import_image_button.setEnabled(False)
            self.ui.recycle_grid_image_button.setEnabled(True)
            # hide the self.ui.refresh_input_image_button button widget
            self.ui.clear_image_button.hide()
            self.ui.refresh_input_image_button.show()
            self.ui.use_imported_image_button.setChecked(False)
            self.ui.use_grid_image_button.setChecked(self.app.settings_manager.generator_settings.input_image_use_grid_image)
            self.ui.recycle_grid_image_button.setChecked(self.app.settings_manager.generator_settings.input_image_recycle_grid_image)
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
        if not self.app.settings_manager.generator_settings.input_image_recycle_grid_image or not self._active_grid_area_image:
            self._active_grid_area_image = data["processed_image"].copy()
        self.set_thumbnail()

    def set_thumbnail(self, image=None):
        try:
            image = self.current_input_image if not image else image
        except AttributeError:
            return
        if image:
            # self.ui.image_thumbnail is a QPushButton
            self.ui.image_thumbnail.setIcon(QIcon(image_to_pixmap(image, size=72)))
        else:
            self.ui.image_thumbnail.setIcon(QIcon())

        # self.app.update_controlnet_thumbnail()

    def send_active_image_to_canvas(self):
        # send the current input image to the canvas
        if not self.current_input_image:
            return
        self.app.canvas.update_image_canvas(
            self.app.current_section,
            {
                "action": self.app.current_section,
                "options": {
                    "outpaint_box_rect": self.app.canvas.active_grid_area_rect,
                    "generator_section": self.generator_section,
                }
            },
            self.current_input_image
        )
        self.app.canvas.update()
