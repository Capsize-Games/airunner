from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.memory_preferences.templates.memory_preferences_ui import Ui_memory_preferences


class MemoryPreferencesWidget(BaseWidget):
    widget_class_ = Ui_memory_preferences

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        ui_elements = {
            "use_accelerated_transformers": "use_accelerated_transformers",
            "use_attention_slicing": "use_attention_slicing",
            "use_enable_sequential_cpu_offload": "use_enable_sequential_cpu_offload",
            "enable_model_cpu_offload": "enable_model_cpu_offload",
            "use_lastchannels": "use_last_channels",
            "use_tf32": "use_tf32",
            "use_tiled_vae": "use_tiled_vae",
            "use_enable_vae_slicing": "use_enable_vae_slicing",
            "use_tome": "use_tome_sd"
        }

        for ui_element, setting in ui_elements.items():
            getattr(self.ui, ui_element).blockSignals(True)
            getattr(self.ui, ui_element).setChecked(self.settings["memory_settings"][setting] is True)
            getattr(self.ui, ui_element).blockSignals(False)

        self.ui.tome_sd_ratio.initialize()

    def action_toggled_setting(self, setting_name, val):
        settings = self.settings
        settings["memory_settings"][setting_name] = val
        self.settings = settings

    def action_toggled_tome(self, val):
        self.action_toggled_setting("use_tome_sd", val)

    def action_toggled_tile_vae(self, val):
        self.action_toggled_setting("use_tiled_vae", val)

    def action_toggled_tf32(self, val):
        self.action_toggled_setting("use_tf32", val)

    def action_toggled_last_memory(self, val):
        self.action_toggled_setting("use_last_channels", val)

    def action_toggled_vae_slicing(self, val):
        self.action_toggled_setting("use_enable_vae_slicing", val)

    def action_toggled_sequential_cpu_offload(self, val):
        self.action_toggled_setting("use_enable_sequential_cpu_offload", val)

    def action_toggled_model_cpu_offload(self, val):
        self.action_toggled_setting("enable_model_cpu_offload", val)

    def action_toggled_attention_slicing(self, val):
        self.action_toggled_setting("use_attention_slicing", val)

    def action_toggled_accelerated_transformers(self, val):
        self.action_toggled_setting("use_accelerated_transformers", val)

    def action_button_clicked_optimize_memory_settings(self):
        self.ui.use_accelerated_transformers.setChecked(True)
        self.ui.use_attention_slicing.setChecked(False)
        self.ui.use_lastchannels.setChecked(True)
        self.ui.use_enable_sequential_cpu_offload.setChecked(False)
        self.ui.enable_model_cpu_offload.setChecked(False)
        self.ui.use_tf32.setChecked(False)
        self.ui.use_tiled_vae.setChecked(True)
        self.ui.use_enable_vae_slicing.setChecked(True)
        self.ui.use_tome.setChecked(True)
        self.ui.tome_sd_ratio.ui.slider.setValue(600)
