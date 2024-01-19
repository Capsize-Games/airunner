from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.memory_preferences.templates.memory_preferences_ui import Ui_memory_preferences


class MemoryPreferencesWidget(BaseWidget):
    widget_class_ = Ui_memory_preferences

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.ui.use_accelerated_transformers.blockSignals(True)
        self.ui.use_attention_slicing.blockSignals(True)
        self.ui.use_enable_sequential_cpu_offload.blockSignals(True)
        self.ui.enable_model_cpu_offload.blockSignals(True)
        self.ui.use_lastchannels.blockSignals(True)
        self.ui.use_tf32.blockSignals(True)
        self.ui.use_tiled_vae.blockSignals(True)
        self.ui.use_enable_vae_slicing.blockSignals(True)
        self.ui.use_tome.blockSignals(True)

        self.ui.use_accelerated_transformers.setChecked(self.memory_settings["use_accelerated_transformers"] is True)
        self.ui.use_attention_slicing.setChecked(self.memory_settings["use_attention_slicing"] is True)
        self.ui.use_enable_sequential_cpu_offload.setChecked(
            self.memory_settings["use_enable_sequential_cpu_offload"] is True)
        self.ui.enable_model_cpu_offload.setChecked(
            self.memory_settings["enable_model_cpu_offload"] is True
        )
        self.ui.use_lastchannels.setChecked(self.memory_settings["use_last_channels"] is True)
        self.ui.use_tf32.setChecked(self.memory_settings["use_tf32"] is True)
        self.ui.use_tiled_vae.setChecked(self.memory_settings["use_tiled_vae"] is True)
        self.ui.use_enable_vae_slicing.setChecked(self.memory_settings["use_enable_vae_slicing"] is True)
        self.ui.use_tome.setChecked(self.memory_settings["use_tome_sd"] is True)

        self.ui.use_accelerated_transformers.blockSignals(False)
        self.ui.use_attention_slicing.blockSignals(False)
        self.ui.use_enable_sequential_cpu_offload.blockSignals(False)
        self.ui.enable_model_cpu_offload.blockSignals(False)
        self.ui.use_lastchannels.blockSignals(False)
        self.ui.use_tf32.blockSignals(False)
        self.ui.use_tiled_vae.blockSignals(False)
        self.ui.use_enable_vae_slicing.blockSignals(False)
        self.ui.use_tome.blockSignals(False)
        self.ui.tome_sd_ratio.initialize()


    def action_toggled_tome(self, val):
        settings = self.settings
        settings["memory_settings"]["use_tome_sd"] = val
        self.settings = settings

    def action_toggled_tile_vae(self, val):
        settings = self.settings
        settings["memory_settings"]["use_tiled_vae"] = val
        self.settings = settings

    def action_toggled_tf32(self, val):
        settings = self.settings
        settings["memory_settings"]["use_tf32"] = val
        self.settings = settings

    def action_toggled_last_memory(self, val):
        settings = self.settings
        settings["memory_settings"]["use_last_channels"] = val
        self.settings = settings

    def action_toggled_vae_slicing(self, val):
        settings = self.settings
        settings["memory_settings"]["use_enable_vae_slicing"] = val
        self.settings = settings

    def action_toggled_sequential_cpu_offload(self, val):
        settings = self.settings
        settings["memory_settings"]["use_enable_sequential_cpu_offload"] = val
        self.settings = settings

    def action_toggled_model_cpu_offload(self, val):
        settings = self.settings
        settings["memory_settings"]["enable_model_cpu_offload"] = val
        self.settings = settings

    def action_toggled_attention_slicing(self, val):
        settings = self.settings
        settings["memory_settings"]["use_attention_slicing"] = val
        self.settings = settings

    def action_toggled_accelerated_transformers(self, val):
        settings = self.settings
        settings["memory_settings"]["use_accelerated_transformers"] = val
        self.settings = settings

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
