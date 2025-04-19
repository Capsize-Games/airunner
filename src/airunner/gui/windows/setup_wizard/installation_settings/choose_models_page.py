from PySide6.QtWidgets import QCheckBox
from PySide6.QtCore import Slot

from airunner.gui.windows.setup_wizard.base_wizard import BaseWizard
from airunner.gui.windows.setup_wizard.installation_settings.templates.choose_models_ui import (
    QSizePolicy,
    QSpacerItem,
    Ui_install_success_page,
)
from airunner.data.bootstrap.controlnet_bootstrap_data import (
    controlnet_bootstrap_data,
)


class ChooseModelsPage(BaseWizard):
    class_name_ = Ui_install_success_page

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.models_enabled = {
            "stable_diffusion": True,
            "speecht5": True,
            "whisper": True,
            "mistral": True,
            "embedding_model": True,
        }

        self.models = [
            {
                "name": "safety_checker",
                "display_name": "Safety Checker",
                "size": 1.2 * 1024 * 1024,
            },
            {
                "name": "feature_extractor",
                "display_name": "Feature Extractor",
                "size": 1.7 * 1024 * 1024,
            },
        ] + controlnet_bootstrap_data

        for item in self.models:
            display_name = item["display_name"]
            checkbox = QCheckBox(self)
            checkbox.setText(display_name)
            checkbox.setChecked(True)
            checkbox.setObjectName(display_name)
            self.ui.stable_diffusion_layout.layout().addWidget(checkbox)
            self.models_enabled[item["name"]] = True

            # Connect with lambda to properly pass the item
            checkbox.toggled.connect(
                lambda checked, i=item: self.controlnet_model_toggled(
                    i, checked
                )
            )

        spacer = QSpacerItem(
            20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding
        )
        self.ui.stable_diffusion_layout.layout().addItem(spacer)
        self.update_total_size_label()

    def update_total_size_label(self):
        mistral_size = 5.8 * 1024 * 1024
        whisper_size = 144.5 * 1024
        speecht5_size = 654.4 * 1024
        embedding_model_size = 1.3 * 1024 * 1024
        total_kb = 0

        if self.models_enabled["stable_diffusion"]:
            for item in self.models:
                if (
                    item["name"] in self.models_enabled
                    and self.models_enabled[item["name"]]
                ):
                    total_kb += float(item["size"])

        if self.models_enabled["mistral"]:
            total_kb += mistral_size
        if self.models_enabled["whisper"]:
            total_kb += whisper_size
        if self.models_enabled["speecht5"]:
            total_kb += speecht5_size
        if self.models_enabled["embedding_model"]:
            total_kb += embedding_model_size

        if total_kb >= 1024 * 1024:
            size_str = f"{total_kb / (1024 * 1024):.2f} GB"
        elif total_kb >= 1024:
            size_str = f"{total_kb / 1024:.2f} MB"
        else:
            size_str = f"{total_kb:.2f} KB"
        self.ui.total_size_label.setText(size_str)

    @Slot(bool)
    def stable_diffusion_toggled(self, val: bool):
        self.models_enabled["stable_diffusion"] = val
        self.update_total_size_label()

    @Slot(bool)
    def whisper_toggled(self, val: bool):
        self.models_enabled["whisper"] = val
        self.update_total_size_label()

    @Slot(bool)
    def ministral_toggled(self, val: bool):
        self.models_enabled["mistral"] = val
        self.update_total_size_label()

    @Slot(bool)
    def embedding_model_toggled(self, val: bool):
        self.models_enabled["embedding_model"] = val
        self.update_total_size_label()

    @Slot(bool)
    def speecht5_toggled(self, val: bool):
        self.models_enabled["speecht5"] = val
        self.update_total_size_label()

    @Slot(bool)
    def controlnet_model_toggled(self, item, val: bool):
        print(
            f"DEBUG: controlnet_model_toggled called with item={item['name']}, val={val}"
        )
        self.models_enabled[item["name"]] = val

        # Check if any stable diffusion model is still enabled
        any_enabled = False
        for model_item in self.models:
            if (
                model_item["name"] in self.models_enabled
                and self.models_enabled[model_item["name"]]
            ):
                any_enabled = True
                break

        # Update the stable_diffusion flag based on whether any model is enabled
        self.models_enabled["stable_diffusion"] = any_enabled
        print(
            f"DEBUG: stable_diffusion flag is now: {self.models_enabled['stable_diffusion']}"
        )

        self.update_total_size_label()
