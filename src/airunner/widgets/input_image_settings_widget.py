from functools import partial

from PIL import Image
from PyQt6.QtWidgets import QHBoxLayout, QWidget

from airunner.utils import image_to_pixmap
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.slider_widget import SliderWidget


class InputImageSettingsWidget(BaseWidget):
    name = "input_image"
    input_image = None
    keep_refreshed = False
    _active_grid_area_image = None
    icons = {
        "use_imported_image_button": "046-import",
        "use_grid_image_button": "032-pixels",
        "recycle_grid_image_button": "047-recycle",
        "clear_image_button": "006-trash",
        "refresh_input_image_button": "050-refresh",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.initialize_input_image_buttons()
        self.app.add_image_to_canvas_signal.connect(self.handle_new_image)
        self.template.groupBox.setChecked(self.app.enable_input_image)
        self.template.groupBox.toggled.connect(self.handle_toggle_enable_input_image)
        self.template.refresh_input_image_button.clicked.connect(self.clear_input_image)
        self.add_input_image_strength_scale_widget()
        self.set_stylesheet()
        self.template.image_thumbnail.mousePressEvent = self.send_active_image_to_canvas
        self.update_buttons(use_grid=self.app.input_image_use_grid_image)

    def add_input_image_strength_scale_widget(self):
        slider = None
        if self.app.current_section in ["txt2img", "img2img", "depth2img"]:
            slider = SliderWidget(
                app=self.app,
                label_text="Input Image Scale",
                slider_callback=partial(self.handle_image_strength_changed),
                current_value=self.app.strength,
                slider_maximum=10000,
                spinbox_maximum=100.0,
                display_as_float=True,
                spinbox_single_step=0.01,
                spinbox_page_step=0.01
            )
        else:
            if self.app.current_section not in ["pix2pix"]:
                value = 10000
            else:
                value = int(self.app.image_scale)

            if self.app.current_section != "upscale":
                slider = SliderWidget(
                    app=self.app,
                    label_text="Input Image Scale",
                    slider_callback=partial(self.handle_image_scale_changed),
                    current_value=value,
                    slider_maximum=500,
                    spinbox_maximum=5.0,
                    display_as_float=True,
                    spinbox_single_step=0.01,
                    spinbox_page_step=0.01
                )
            if self.app.current_section not in ["pix2pix", "upscale"]:
                slider.setEnabled(False)
        if slider:
            self.add_slider_to_scale_frame(slider)

    def add_slider_to_scale_frame(self, slider):
        grid_layout = QHBoxLayout(self.template.scale_frame)
        grid_layout.setSpacing(0)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        widget = QWidget()
        grid_layout.addWidget(widget)
        grid_layout.addWidget(slider)

    def handle_image_strength_changed(self, value):
        self.app.strength_var.set(value)

    def handle_image_scale_changed(self, value):
        self.app.image_scale_var.set(value)

    @property
    def active_grid_area_image(self):
        if not self.app.input_image_recycle_grid_image or not self._active_grid_area_image:
            if self.app.canvas.current_layer.image_data.image:
                self._active_grid_area_image = self.app.canvas.current_layer.image_data.image.copy()
        return self._active_grid_area_image

    @property
    def current_input_image(self):
        if self.app.input_image_use_imported_image:
            return self.input_image
        elif self.app.input_image_use_grid_image:
            return self.active_grid_area_image

    def handle_toggle_enable_input_image(self, value):
        self.app.handle_value_change("enable_input_image", value, self)
        self.set_stylesheet()

    def initialize_input_image_buttons(self):
        self.update_buttons(use_grid=self.app.input_image_use_grid_image)

        # setup handlers for each button
        self.template.import_image_button.clicked.connect(self.import_input_image)
        self.template.use_imported_image_button.clicked.connect(self.toggle_use_imported_image)
        self.template.use_grid_image_button.clicked.connect(self.toggle_use_active_grid_area)
        self.template.clear_image_button.clicked.connect(self.clear_input_image)
        self.template.recycle_grid_image_button.clicked.connect(self.toggle_keep_refreshed)

    def set_stylesheet(self):
        super().set_stylesheet()
        self.template.groupBox.setStyleSheet(self.app.css("input_image_groupbox"))

        if self.app.enable_input_image:
            self.template.tabWidget.setStyleSheet(self.app.css("input_image_tab_widget"))
        else:
            self.template.tabWidget.setStyleSheet(self.app.css("input_image_tab_widget_disabled"))

    def import_input_image(self):
        file_path, _ = self.app.display_import_image_dialog(
            directory=self.app.settings_manager.settings.image_path.get(),
        )
        if file_path == "":
            return
        image = Image.open(file_path)
        image = image.convert("RGBA")
        self.input_image = image
        self.set_thumbnail()

    def clear_input_image(self):
        if self.app.input_image_use_grid_image:
            self._active_grid_area_image = None
        elif self.app.input_image_use_imported_image:
            self.input_image = None
        self.set_thumbnail()

    def toggle_use_active_grid_area(self, value):
        self.app.input_image_use_grid_image = value
        self.app.input_image_use_imported_image = not value
        self.set_thumbnail()
        self.update_buttons(use_grid=value)

    def toggle_use_imported_image(self, value):
        self.app.input_image_use_grid_image = not value
        self.app.input_image_use_imported_image = value
        self.set_thumbnail()
        self.update_buttons(use_grid=not value)

    def update_buttons(self, use_grid):
        if use_grid:
            self.template.import_image_button.setEnabled(False)
            self.template.recycle_grid_image_button.setEnabled(True)
            # hide the self.template.refresh_input_image_button button widget
            self.template.refresh_input_image_button.show()
            self.template.clear_image_button.hide()
            self.set_button_icon(self.is_dark, "recycle_grid_image_button", self.icons["recycle_grid_image_button"])
            self.template.use_imported_image_button.setChecked(False)
            self.template.use_grid_image_button.setChecked(self.app.input_image_use_grid_image)
            self.template.recycle_grid_image_button.setChecked(self.app.input_image_recycle_grid_image)
        else:
            self.template.import_image_button.setEnabled(True)
            self.template.recycle_grid_image_button.setEnabled(False)
            self.template.refresh_input_image_button.hide()
            self.template.clear_image_button.show()
            self.set_button_icon(not self.is_dark, "recycle_grid_image_button", self.icons["recycle_grid_image_button"])
            self.template.use_imported_image_button.setChecked(True)
            self.template.use_grid_image_button.setChecked(False)
            self.template.recycle_grid_image_button.setChecked(False)

    def toggle_keep_refreshed(self, value):
        self.app.input_image_recycle_grid_image = value
        self.set_thumbnail()

    def export_input_image_mask(self):
        print("export input image mask")

    def clear_input_image_mask(self):
        print("clear input image mask")

    def handle_new_image(self, data):
        if not self.app.input_image_recycle_grid_image or not self._active_grid_area_image:
            self._active_grid_area_image = data["processed_image"].copy()
        self.set_thumbnail()

    def set_thumbnail(self):
        image = self.current_input_image
        if image:
            self.template.image_thumbnail.setPixmap(image_to_pixmap(image, size=72))
        else:
            self.template.image_thumbnail.clear()

        self.app.update_controlnet_thumbnail()

    def send_active_image_to_canvas(self, value):
        # send the current input image to the canvas
        if not self.current_input_image:
            return
        self.app.canvas.update_image_canvas(
            self.app.current_section,
            {
                "action": self.app.current_section,
                "options": {
                    "outpaint_box_rect": self.app.canvas.active_grid_area_rect,
                    "generator_section": self.app.currentTabSection
                }
            },
            self.current_input_image
        )
        self.app.canvas.update()
