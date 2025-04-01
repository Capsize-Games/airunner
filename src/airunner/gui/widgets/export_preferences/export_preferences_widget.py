
from airunner.gui.widgets.base_widget import BaseWidget
from airunner.gui.widgets.export_preferences.templates.export_preferences_ui import Ui_export_preferences
from PySide6.QtWidgets import QFileDialog


class ExportPreferencesWidget(BaseWidget):
    widget_class_ = Ui_export_preferences

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        elements = (
            self.ui.metadata_prompt,
            self.ui.metadata_negative_prompt,
            self.ui.metadata_scale,
            self.ui.metadata_seed,
            self.ui.metadata_steps,
            self.ui.metadata_ddim_eta,
            self.ui.metadata_iterations,
            self.ui.metadata_samples,
            self.ui.metadata_model,
            self.ui.metadata_model_branch,
            self.ui.metadata_scheduler,
            self.ui.image_path,
            self.ui.metadata_strength,
            self.ui.metadata_clip_skip,
            self.ui.metadata_version,
            self.ui.metadata_lora,
            self.ui.metadata_embeddings,
            self.ui.metadata_timestamp,
            self.ui.metadata_controlnet,
            self.ui.export_metadata,
            self.ui.actionAuto_export_images,
            self.ui.image_type_dropdown,
        )
        for element in elements:
            element.blockSignals(True)
        # initialize values:
        self.ui.metadata_prompt.setChecked(self.metadata_settings.image_export_metadata_prompt is True)
        self.ui.metadata_negative_prompt.setChecked(
            self.metadata_settings.image_export_metadata_negative_prompt is True
        )
        self.ui.metadata_scale.setChecked(self.metadata_settings.image_export_metadata_scale is True)
        self.ui.metadata_seed.setChecked(self.metadata_settings.image_export_metadata_seed is True)
        self.ui.metadata_steps.setChecked(self.metadata_settings.image_export_metadata_steps is True)
        self.ui.metadata_ddim_eta.setChecked(self.metadata_settings.image_export_metadata_ddim_eta is True)
        self.ui.metadata_iterations.setChecked(self.metadata_settings.image_export_metadata_iterations is True)
        self.ui.metadata_samples.setChecked(self.metadata_settings.image_export_metadata_samples is True)
        self.ui.metadata_model.setChecked(self.metadata_settings.image_export_metadata_model is True)
        self.ui.metadata_model_branch.setChecked(self.metadata_settings.image_export_metadata_model_branch is True)
        self.ui.metadata_scheduler.setChecked(self.metadata_settings.image_export_metadata_scheduler is True)
        self.ui.metadata_strength.setChecked(self.metadata_settings.image_export_metadata_strength is True)
        self.ui.metadata_clip_skip.setChecked(self.metadata_settings.image_export_metadata_clip_skip is True)
        self.ui.metadata_version.setChecked(self.metadata_settings.image_export_metadata_version is True)
        self.ui.metadata_lora.setChecked(self.metadata_settings.image_export_metadata_lora is True)
        self.ui.metadata_embeddings.setChecked(self.metadata_settings.image_export_metadata_embeddings is True)
        self.ui.metadata_timestamp.setChecked(self.metadata_settings.image_export_metadata_timestamp is True)
        self.ui.metadata_controlnet.setChecked(self.metadata_settings.image_export_metadata_controlnet is True)
        self.ui.export_metadata.setChecked(self.metadata_settings.export_metadata is True)
        self.ui.actionAuto_export_images.setChecked(self.application_settings.auto_export_images is True)
        self.ui.image_type_dropdown.setCurrentText(self.application_settings.image_export_type)
        self.ui.image_path.setText(self.path_settings.image_path)
        image_types = [
            "png",
            "jpg",
            "jpeg",
            "bmp",
            "tiff",
        ]
        self.ui.image_type_dropdown.addItems(image_types)
        self.ui.image_type_dropdown.setCurrentText(self.application_settings.image_export_type)
        for element in elements:
            element.blockSignals(False)

    def action_toggled_steps(self, val):
        self.update_metadata_settings("image_export_metadata_steps", val)

    def action_toggled_seed(self, val):
        self.update_metadata_settings("image_export_metadata_seed", val)

    def action_toggled_scheduler(self, val):
        self.update_metadata_settings("image_export_metadata_scheduler", val)

    def action_toggled_scale(self, val):
        self.update_metadata_settings("image_export_metadata_scale", val)

    def action_toggled_samples(self, val):
        self.update_metadata_settings("image_export_metadata_samples", val)

    def action_toggled_prompt(self, val):
        self.update_metadata_settings("image_export_metadata_prompt", val)

    def action_toggled_negative_prompt(self, val):
        self.update_metadata_settings("image_export_metadata_negative_prompt", val)

    def action_toggled_model_branch(self, val):
        self.update_metadata_settings("image_export_metadata_model_branch", val)

    def action_toggled_model(self, val):
        self.update_metadata_settings("image_export_metadata_model", val)

    def action_toggled_iterations(self, val):
        self.update_metadata_settings("image_export_metadata_iterations", val)

    def action_toggled_ddim(self, val):
        self.update_metadata_settings("image_export_metadata_ddim_eta", val)

    def action_toggled_strength(self, val):
        self.update_metadata_settings("image_export_metadata_strength", val)

    def action_toggled_clip_skip(self, val):
        self.update_metadata_settings("image_export_metadata_clip_skip", val)

    def action_toggled_version(self, val):
        self.update_metadata_settings("image_export_metadata_version", val)

    def action_toggled_lora(self, val):
        self.update_metadata_settings("image_export_metadata_lora", val)

    def action_toggled_embeddings(self, val):
        self.update_metadata_settings("image_export_metadata_embeddings", val)

    def action_toggled_timestamp(self, val):
        self.update_metadata_settings("image_export_metadata_timestamp", val)

    def action_toggled_controlnet(self, val):
        self.update_metadata_settings("image_export_metadata_controlnet", val)

    def action_toggled_export_metadata(self, val):
        self.update_metadata_settings("export_metadata", val)

    def action_toggle_automatically_export_images(self, val):
        self.update_application_settings("auto_export_images", val)

    def action_image_type_text_changed(self, val):
        self.update_application_settings("image_export_type", val)

    def image_export_path_text_edited(self, val):
        self.update_application_settings("path_settings", val)

    def action_clicked_button_browse(self):
        path = QFileDialog.getExistingDirectory(self, "Select Directory", self.path_settings.image_path)
        if path:
            self.ui.image_path.setText(path)
            self.update_path_settings("embeddings_model_path", path)
