
from PySide6.QtWidgets import QColorDialog
from airunner.enums import SignalCode
from airunner.gui.widgets.active_grid_settings.templates.active_grid_settings_ui import Ui_active_grid_settings_widget
from airunner.gui.widgets.base_widget import BaseWidget
from PySide6.QtCore import Slot


class ActiveGridSettingsWidget(BaseWidget):
    widget_class_ = Ui_active_grid_settings_widget

    def __init__(self, *args, **kwargs):
        self.signal_handlers = {
            SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL: self.update_size,
            SignalCode.APPLICATION_ACTIVE_GRID_AREA_UPDATED: self.update_size
        }
        super().__init__(*args, **kwargs)
        self.ui.width_slider_widget.setProperty("current_value", self.application_settings.is_maximized)
        self.ui.height_slider_widget.setProperty("current_value", self.application_settings.working_height)
        self.ui.width_slider_widget.initialize()
        self.ui.height_slider_widget.initialize()
        self.ui.border_opacity_slider_widget.setProperty(
            "current_value",
            self.active_grid_settings.border_opacity
        )
        self.ui.fill_opacity_slider_widget.setProperty(
            "current_value",
            self.active_grid_settings.fill_opacity
        )

        self.ui.border_opacity_slider_widget.initialize()
        self.ui.fill_opacity_slider_widget.initialize()
        self.ui.active_grid_border_groupbox.blockSignals(True)
        self.ui.active_grid_fill_groupbox.blockSignals(True)
        self.ui.active_grid_area_checkbox.blockSignals(True)
        self.ui.size_lock_button.blockSignals(True)
        self.ui.active_grid_border_groupbox.setChecked(self.active_grid_settings.render_border)
        self.ui.active_grid_fill_groupbox.setChecked(self.active_grid_settings.render_fill)
        self.ui.active_grid_area_checkbox.setChecked(self.active_grid_settings.enabled)
        self.ui.size_lock_button.setChecked(self.application_settings.active_grid_size_lock)
        self.ui.active_grid_area_checkbox.blockSignals(False)
        self.ui.active_grid_border_groupbox.blockSignals(False)
        self.ui.active_grid_fill_groupbox.blockSignals(False)
        self.ui.size_lock_button.blockSignals(False)

        # set background color of buttons
        self.ui.border_choose_color_button.setStyleSheet(
            f"background-color: {self.active_grid_settings.border_color}"
        )
        self.ui.fill_choose_color_button.setStyleSheet(
            f"background-color: {self.active_grid_settings.fill_color}"
        )
        self.current_active_grid_width = self.application_settings.working_width
        self.current_active_grid_height = self.application_settings.working_height

    @Slot(bool)
    def size_lock_toggled(self, val):
        self.update_application_settings("active_grid_size_lock", val)

    def update_size(self, _message: dict):
        width = self.application_settings.working_width
        height = self.application_settings.working_height
        if self.application_settings.active_grid_size_lock:
            if width != self.current_active_grid_width:
                height = width
            elif height != self.current_active_grid_height:
                width = height
        if self.current_active_grid_height != height or self.current_active_grid_width != width:
            self.current_active_grid_width = width
            self.current_active_grid_height = height
            self.ui.width_slider_widget.blockSignals(True)
            self.ui.height_slider_widget.blockSignals(True)
            self.ui.width_slider_widget.set_slider_and_spinbox_values(width)
            self.ui.height_slider_widget.set_slider_and_spinbox_values(height)
            self.ui.width_slider_widget.blockSignals(False)
            self.ui.height_slider_widget.blockSignals(False)
            self.update_application_settings("working_width", width)
            self.update_application_settings("working_height", height)

    def action_clicked_checkbox_toggle_active_grid_border(self, checked):
        self.update_active_grid_settings("render_border", checked)

    def action_clicked_checkbox_toggle_active_grid_fill(self, checked):
        self.update_active_grid_settings("render_fill", checked)

    def action_clicked_checkbox_toggle_active_grid_area(self, checked):
        self.update_active_grid_settings("enabled", checked)

    def action_choose_border_color_clicked(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.update_active_grid_settings("border_color", color.name())

    def action_choose_fill_color_clicked(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.update_active_grid_settings("fill_color", color.name())
