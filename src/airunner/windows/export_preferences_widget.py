from PyQt6.QtWidgets import QFileDialog
from airunner.windows.custom_widget import CustomWidget


class ExportPreferencesWidget(CustomWidget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs, filename="export_preferences")
        self.initialize_window()

    def initialize_window(self):
        self.actionAuto_export_images.setChecked(self.settings_manager.auto_export_images is True)
        self.actionAuto_export_images.stateChanged.connect(
            lambda val: self.settings_manager.set_value("auto_export_images", val == 2))
        self.image_path.textChanged.connect(
            lambda val: self.settings_manager.set_value("image_path", val))
        self.image_path_browse_button.clicked.connect(
            lambda: self.browse_for_image_path(self.image_path))
        self.image_path.setText(self.settings_manager.path_settings.image_path)
        image_types = [
            "png",
            "jpg",
            "jpeg",
            "bmp",
            "tiff",
            "gif",
        ]
        self.image_type_dropdown.addItems(image_types)
        self.image_type_dropdown.setCurrentText(self.settings_manager.image_export_type)
        self.image_type_dropdown.currentTextChanged.connect(self.image_type_changed)
        self.checkbox_settings = {
            "image_export_metadata_prompt": self.metadata_prompt,
            "image_export_metadata_negative_prompt": self.metadata_negative_prompt,
            "image_export_metadata_scale": self.metadata_scale,
            "image_export_metadata_seed": self.metadata_seed,
            "image_export_metadata_steps": self.metadata_steps,
            "image_export_metadata_ddim_eta": self.metadata_ddim_eta,
            "image_export_metadata_iterations": self.metadata_iterations,
            "image_export_metadata_samples": self.metadata_samples,
            "image_export_metadata_model": self.metadata_model,
            "image_export_metadata_model_branch": self.metadata_model_branch,
            "image_export_metadata_scheduler": self.metadata_scheduler,
            "export_metadata": self.export_metadata,
            "import_metadata": self.import_metadata,
        }
        for name, checkbox in self.checkbox_settings.items():
            checkbox.setChecked(self.settings_manager.__getattribute__(name) is True)
            checkbox.stateChanged.connect(lambda val, _name=name: self.handle_state_change(val, _name))
        self.update_metadata_options()

    def handle_state_change(self, val, name):
        self.settings_manager.set_value(f"metadata_settings.{name}", val == 2)

    def browse_for_image_path(self, line_edit):
        path = QFileDialog.getExistingDirectory(None, "Select Directory")
        line_edit.setText(path)
        self.settings_manager.set_value("image_path", path)

    def image_type_changed(self, text):
        self.settings_manager.set_value("image_export_type", text)
        self.update_metadata_options()

    def update_metadata_options(self):
        enabled = self.settings_manager.image_export_type == "png"
        for name, checkbox in self.checkbox_settings.items():
            if name.startswith("image_export_metadata"):
                checkbox.setEnabled(enabled)
