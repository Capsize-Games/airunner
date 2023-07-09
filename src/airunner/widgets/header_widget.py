from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QPushButton
from airunner.widgets.base_widget import BaseWidget


class HeaderWidget(BaseWidget):
    name = "header"

    icons = {
        "undo_button": "007-undo",
        "redo_button": "008-redo",
        "open_button": "034-folder",
        "save_button": "033-diskette",
        "file_new_button": "036-new-document",
    }

    def initialize(self):
        size = self.app.grid_size

        self.brush_size_slider_widget = self.create_slider_widget(
            label_text="Brush Size:",
            slider_callback=self.brush_size_slider_callback
        )
        self.width_slider_widget = self.create_slider_widget(
            label_text="Active Grid Width:",
            slider_callback=self.width_slider_callback,
            slider_minimum=size,
            slider_maximum=4096,
            slider_tick_interval=size,
            slider_single_step=size,
            slider_page_step=size,
        )
        self.height_slider_widget = self.create_slider_widget(
            label_text="Active Grid Height:",
            slider_callback=self.height_slider_callback,
            slider_minimum=size,
            slider_maximum=4096,
            slider_tick_interval=size,
            slider_single_step=size,
            slider_page_step=size,
        )

        self.file_new_button.clicked.connect(self.app.new_document)
        self.save_button.clicked.connect(self.app.save_document)
        self.open_button.clicked.connect(self.app.load_document)

        # add layoutBottomMargin to the layout
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.frame.layout().setContentsMargins(5, 5, 5, 5)

        # had layoutHorizontalSpacing to the layout
        self.frame.layout().setHorizontalSpacing(10)

        try:
            self.frame.layout().addWidget(self.width_slider_widget, 0, 7, 1, 1)
            self.frame.layout().addWidget(self.height_slider_widget, 0, 8, 1, 1)
            self.frame.layout().addWidget(self.brush_size_slider_widget, 0, 9, 1, 1)
        except Exception as e:
            print(e)

        self.update_widget_values()
        self.app.register_setting_handler("size", self.update_widget_values)
        self.app.register_setting_handler("working_width", self.update_widget_values)
        self.app.register_setting_handler("working_height", self.update_widget_values)

    def update_widget_values(self):
        if self.settings_manager:
            brush_size = self.settings_manager.settings.mask_brush_size.get()
            self.brush_size_slider_widget.update_value(brush_size)

            self.width_slider_widget.set_tick_value(self.app.grid_size)
            self.height_slider_widget.set_tick_value(self.app.grid_size)
            self.width_slider_widget.update_value(self.app.working_width)
            self.height_slider_widget.update_value(self.app.working_height)
            self.app.set_size_form_element_step_values()

    def brush_size_slider_callback(self, val):
        self.settings_manager.settings.mask_brush_size.set(val)

    def width_slider_callback(self, val):
        self.app.working_width = val

    def height_slider_callback(self, val):
        self.app.working_height = val

    def set_size_increment_levels(self):
        size = self.app.grid_size
        self.width_slider_widget.slider_single_step = size
        self.width_slider_widget.slider_tick_interval = size

        self.height_slider_widget.slider_single_step = size
        self.height_slider_widget.slider_tick_interval = size

        self.app.canvas.update()

    def set_stylesheet(self):
        super().set_stylesheet()
        self.setStyleSheet(self.app.css("header_widget"))