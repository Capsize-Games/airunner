from airunner.widgets.active_grid_settings.templates.active_grid_settings_ui import Ui_active_grid_settings_widget
from airunner.widgets.base_widget import BaseWidget


class ActiveGridSettingsWidget(BaseWidget):
    widget_class_ = Ui_active_grid_settings_widget

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui.width_slider_widget.setProperty("current_value", self.settings_manager.working_width)
        self.ui.height_slider_widget.setProperty("current_value", self.settings_manager.working_height)
        self.ui.width_slider_widget.initialize()
        self.ui.height_slider_widget.initialize()
        self.ui.border_opacity_slider_widget.setProperty("current_value", self.settings_manager.active_grid_settings.border_opacity)
        self.ui.fill_opacity_slider_widget.setProperty("current_value", self.settings_manager.active_grid_settings.fill_opacity)
        self.ui.border_opacity_slider_widget.initialize()
        self.ui.fill_opacity_slider_widget.initialize()
        self.ui.active_grid_area_groupbox.setChecked(self.settings_manager.active_grid_settings.enabled)
        self.ui.active_grid_border_groupbox.setChecked(self.settings_manager.active_grid_settings.render_border)
        self.ui.active_grid_fill_groupbox.setChecked(self.settings_manager.active_grid_settings.render_fill)

    def action_clicked_checkbox_toggle_active_grid_border(self, checked):
        self.settings_manager.set_value("active_grid_settings.render_border", checked)

    def action_clicked_checkbox_toggle_active_grid_fill(self, checked):
        self.settings_manager.set_value("active_grid_settings.render_fill", checked)

    def action_clicked_checkbox_toggle_active_grid_area(self, checked):
        self.settings_manager.set_value("active_grid_settings.render_active_grid_area", checked)
