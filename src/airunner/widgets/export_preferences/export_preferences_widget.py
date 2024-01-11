from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.export_preferences.templates.export_preferences_ui import Ui_export_preferences

from PyQt6.QtWidgets import QFileDialog


class ExportPreferencesWidget(BaseWidget):
    widget_class_ = Ui_export_preferences

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.ui.metadata_prompt.blockSignals(True)
        self.ui.metadata_negative_prompt.blockSignals(True)
        self.ui.metadata_scale.blockSignals(True)
        self.ui.metadata_seed.blockSignals(True)
        self.ui.metadata_steps.blockSignals(True)
        self.ui.metadata_ddim_eta.blockSignals(True)
        self.ui.metadata_iterations.blockSignals(True)
        self.ui.metadata_samples.blockSignals(True)
        self.ui.metadata_model.blockSignals(True)
        self.ui.metadata_model_branch.blockSignals(True)
        self.ui.metadata_scheduler.blockSignals(True)
        self.ui.export_metadata.blockSignals(True)
        self.ui.actionAuto_export_images.blockSignals(True)
        self.ui.image_type_dropdown.blockSignals(True)
        self.ui.image_path.blockSignals(True)
        # initialize values:
        self.ui.metadata_prompt.setChecked(self.app.settings_manager.metadata_settings.image_export_metadata_prompt is True)
        self.ui.metadata_negative_prompt.setChecked(self.app.settings_manager.metadata_settings.image_export_metadata_negative_prompt is True)
        self.ui.metadata_scale.setChecked(self.app.settings_manager.metadata_settings.image_export_metadata_scale is True)
        self.ui.metadata_seed.setChecked(self.app.settings_manager.metadata_settings.image_export_metadata_seed is True)
        self.ui.metadata_steps.setChecked(self.app.settings_manager.metadata_settings.image_export_metadata_steps is True)
        self.ui.metadata_ddim_eta.setChecked(self.app.settings_manager.metadata_settings.image_export_metadata_ddim_eta is True)
        self.ui.metadata_iterations.setChecked(self.app.settings_manager.metadata_settings.image_export_metadata_iterations is True)
        self.ui.metadata_samples.setChecked(self.app.settings_manager.metadata_settings.image_export_metadata_samples is True)
        self.ui.metadata_model.setChecked(self.app.settings_manager.metadata_settings.image_export_metadata_model is True)
        self.ui.metadata_model_branch.setChecked(self.app.settings_manager.metadata_settings.image_export_metadata_model_branch is True)
        self.ui.metadata_scheduler.setChecked(self.app.settings_manager.metadata_settings.image_export_metadata_scheduler is True)
        self.ui.export_metadata.setChecked(self.app.settings_manager.metadata_settings.export_metadata is True)
        self.ui.actionAuto_export_images.setChecked(self.app.auto_export_images is True)
        self.ui.image_type_dropdown.setCurrentText(self.app.image_export_type)
        self.ui.image_path.setText(self.app.settings_manager.image_path)
        image_types = [
            "png",
            "jpg",
            "jpeg",
            "bmp",
            "tiff",
        ]
        self.ui.image_type_dropdown.addItems(image_types)
        self.ui.image_type_dropdown.setCurrentText(self.app.image_export_type)

        self.ui.metadata_prompt.blockSignals(False)
        self.ui.metadata_negative_prompt.blockSignals(False)
        self.ui.metadata_scale.blockSignals(False)
        self.ui.metadata_seed.blockSignals(False)
        self.ui.metadata_steps.blockSignals(False)
        self.ui.metadata_ddim_eta.blockSignals(False)
        self.ui.metadata_iterations.blockSignals(False)
        self.ui.metadata_samples.blockSignals(False)
        self.ui.metadata_model.blockSignals(False)
        self.ui.metadata_model_branch.blockSignals(False)
        self.ui.metadata_scheduler.blockSignals(False)
        self.ui.export_metadata.blockSignals(False)
        self.ui.actionAuto_export_images.blockSignals(False)
        self.ui.image_type_dropdown.blockSignals(False)
        self.ui.image_path.blockSignals(False)

    def action_toggled_steps(self, val):
        self.app.settings_manager.set_value(f"metadata_settings.image_export_metadata_steps", val)

    def action_toggled_seed(self, val):
        self.app.settings_manager.set_value(f"metadata_settings.image_export_metadata_seed", val)
    
    def action_toggled_latents_seed(self, val):
        self.app.settings_manager.set_value(f"metadata_settings.image_export_metadata_latents_seed", val)

    def action_toggled_scheduler(self, val):
        self.app.settings_manager.set_value(f"metadata_settings.image_export_metadata_scheduler", val)

    def action_toggled_scale(self, val):
        self.app.settings_manager.set_value(f"metadata_settings.image_export_metadata_scale", val)

    def action_toggled_samples(self, val):
        self.app.settings_manager.set_value(f"metadata_settings.image_export_metadata_samples", val)

    def action_toggled_prompt(self, val):
        self.app.settings_manager.set_value(f"metadata_settings.image_export_metadata_prompt", val)

    def action_toggled_negative_prompt(self, val):
        self.app.settings_manager.set_value(f"metadata_settings.image_export_metadata_negative_prompt", val)

    def action_toggled_model_branch(self, val):
        self.app.settings_manager.set_value(f"metadata_settings.image_export_metadata_model_branch", val)

    def action_toggled_model(self, val):
        self.app.settings_manager.set_value(f"metadata_settings.image_export_metadata_model", val)

    def action_toggled_iterations(self, val):
        self.app.settings_manager.set_value(f"metadata_settings.image_export_metadata_iterations", val)

    def action_toggled_ddim(self, val):
        self.app.settings_manager.set_value(f"metadata_settings.image_export_metadata_ddim_eta", val)

    def action_toggled_export_metadata(self, val):
        self.app.settings_manager.set_value(f"metadata_settings.export_metadata", val)

    def action_toggle_automatically_export_images(self, val):
        self.app.auto_export_images = val
    
    def action_image_type_text_changed(self, val):
        self.app.image_export_type = val
    
    def image_export_path_text_edited(self, val):
        self.app.settings_manager.set_value(f"image_path", val)
    
    def action_clicked_button_browse(self):
        path = QFileDialog.getExistingDirectory(None, "Select Directory")
        if path:
            self.ui.image_path.setText(path)
            self.app.settings_manager.set_value("path_settings.image_path", path)

