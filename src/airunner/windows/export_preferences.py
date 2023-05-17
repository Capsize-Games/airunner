from PyQt6.QtWidgets import QFileDialog

from airunner.windows.base_window import BaseWindow
import platform


class ExportPreferences(BaseWindow):
    template_name = "export_preferences"
    window_title = "Image Export Preferences"

    def initialize_window(self):
        self.template.actionAuto_export_images.setChecked(self.settings_manager.settings.auto_export_images.get() is True)
        self.template.actionAuto_export_images.stateChanged.connect(
            lambda val: self.settings_manager.settings.auto_export_images.set(val == 2))
        self.template.image_path.textChanged.connect(
            lambda val: self.settings_manager.settings.image_path.set(val))
        self.template.image_path_browse_button.clicked.connect(
            lambda: self.browse_for_image_path(self.template.image_path))
        self.template.image_path.setText(self.settings_manager.settings.image_path.get())
        image_types = [
            "png",
            "jpg",
            "jpeg",
            "bmp",
            "tiff",
            "gif",
        ]
        self.template.image_type_dropdown.addItems(image_types)
        self.template.image_type_dropdown.setCurrentText(self.settings_manager.settings.image_export_type.get())
        self.template.image_type_dropdown.currentTextChanged.connect(self.image_type_changed)
        self.checkbox_settings = {
            "image_export_metadata_prompt": self.template.metadata_prompt,
            "image_export_metadata_negative_prompt": self.template.metadata_negative_prompt,
            "image_export_metadata_scale": self.template.metadata_scale,
            "image_export_metadata_seed": self.template.metadata_seed,
            "image_export_metadata_steps": self.template.metadata_steps,
            "image_export_metadata_ddim_eta": self.template.metadata_ddim_eta,
            "image_export_metadata_iterations": self.template.metadata_iterations,
            "image_export_metadata_samples": self.template.metadata_samples,
            "image_export_metadata_model": self.template.metadata_model,
            "image_export_metadata_model_branch": self.template.metadata_model_branch,
            "image_export_metadata_scheduler": self.template.metadata_scheduler,
            "export_metadata": self.template.export_metadata,
            "import_metadata": self.template.import_metadata,
        }
        for name, checkbox in self.checkbox_settings.items():
            checkbox.setChecked(self.settings_manager.settings.__getattribute__(name).get() is True)
            checkbox.stateChanged.connect(lambda val, _name=name: self.handle_state_change(val, _name))
        self.update_metadata_options()

    def handle_state_change(self, val, name):
        self.settings_manager.settings.__getattribute__(name).set(val == 2)

    def browse_for_image_path(self, line_edit):
        path = QFileDialog.getExistingDirectory(None, "Select Directory")
        line_edit.setText(path)
        self.settings_manager.settings.image_path.set(path)

    def image_type_changed(self, text):
        self.settings_manager.settings.image_export_type.set(text)
        self.update_metadata_options()

    def update_metadata_options(self):
        enabled = self.settings_manager.settings.image_export_type.get() == "png"
        for name, checkbox in self.checkbox_settings.items():
            if name.startswith("image_export_metadata"):
                checkbox.setEnabled(enabled)
