from PySide6.QtWidgets import QColorDialog

from airunner.enums import SignalCode
from airunner.widgets.active_grid_settings.templates.active_grid_settings_ui import Ui_active_grid_settings_widget
from airunner.widgets.base_widget import BaseWidget


class ActiveGridSettingsWidget(BaseWidget):
    widget_class_ = Ui_active_grid_settings_widget

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        settings = self.settings
        self.ui.width_slider_widget.setProperty("current_value", self.settings["is_maximized"])
        self.ui.height_slider_widget.setProperty("current_value", self.settings["working_height"])
        self.ui.width_slider_widget.initialize()
        self.ui.height_slider_widget.initialize()
        self.ui.border_opacity_slider_widget.setProperty(
            "current_value",
            settings["active_grid_settings"]["border_opacity"]
        )
        self.ui.fill_opacity_slider_widget.setProperty(
            "current_value",
            settings["active_grid_settings"]["fill_opacity"]
        )
        self.ui.border_opacity_slider_widget.initialize()
        self.ui.fill_opacity_slider_widget.initialize()
        self.ui.active_grid_area_groupbox.blockSignals(True)
        self.ui.active_grid_border_groupbox.blockSignals(True)
        self.ui.active_grid_fill_groupbox.blockSignals(True)
        self.ui.active_grid_area_groupbox.setChecked(settings["active_grid_settings"]["enabled"])
        self.ui.active_grid_border_groupbox.setChecked(settings["active_grid_settings"]["render_border"])
        self.ui.active_grid_fill_groupbox.setChecked(settings["active_grid_settings"]["render_fill"])
        self.ui.active_grid_area_groupbox.blockSignals(False)
        self.ui.active_grid_border_groupbox.blockSignals(False)
        self.ui.active_grid_fill_groupbox.blockSignals(False)

        self.signal_handlers = {
            SignalCode.APPLICATION_ACTIVE_GRID_AREA_UPDATED: self.update_size
        }

        for k in [
            "border_opacity_slider_widget",
            "fill_opacity_slider_widget",
            "width_slider_widget",
            "height_slider_widget",
        ]:
            getattr(self.ui, k).settings_loaded(self.callback)

    def callback(self, prop, val):
        settings = self.settings
        if prop in ["border_opacity", "fill_opacity"]:
            settings["active_grid_settings"][prop] = val
        else:
            settings[prop] = val
        self.settings = settings

    def update_size(self, message: dict):
        settings = message["settings"]
        self.ui.width_slider_widget.blockSignals(True)
        self.ui.height_slider_widget.blockSignals(True)
        self.ui.width_slider_widget.set_slider_and_spinbox_values(settings["working_width"])
        self.ui.height_slider_widget.set_slider_and_spinbox_values(settings["working_height"])
        self.ui.width_slider_widget.blockSignals(False)
        self.ui.height_slider_widget.blockSignals(False)

    def update_active_grid_settings(self, setting_key, checked):
        settings = self.settings
        settings["active_grid_settings"][setting_key] = checked
        self.settings = settings

    def action_clicked_checkbox_toggle_active_grid_border(self, checked):
        self.update_active_grid_settings("render_border", checked)

    def action_clicked_checkbox_toggle_active_grid_fill(self, checked):
        self.update_active_grid_settings("render_fill", checked)

    def action_clicked_checkbox_toggle_active_grid_area(self, checked):
        self.update_active_grid_settings("enabled", checked)

    def action_choose_border_color_clicked(self):
        color = QColorDialog.getColor()
        if color.isValid():
            settings = self.settings
            settings["active_grid_settings"]["border_color"] = color.name()
            self.settings = settings

    def action_choose_fill_color_clicked(self):
        color = QColorDialog.getColor()
        if color.isValid():
            settings = self.settings
            settings["active_grid_settings"]["fill_color"] = color.name()
            self.settings = settings
