from airunner.windows.base_window import BaseWindow
import platform


class AdvancedSettings(BaseWindow):
    template_name = "advanced_settings"
    window_title = "Memory Settings"

    def initialize_window(self):
        settings = self.settings_manager.settings
        checkbox_settings = [
            (self.template.use_lastchannels, settings.use_last_channels),
            (self.template.use_enable_sequential_cpu_offload, settings.use_enable_sequential_cpu_offload),
            (self.template.use_attention_slicing, settings.use_attention_slicing),
            (self.template.use_tf32, settings.use_tf32),
            (self.template.use_enable_vae_slicing, settings.use_enable_vae_slicing),
            (self.template.use_xformers, settings.use_xformers),
            (self.template.use_accelerated_transformers, settings.use_accelerated_transformers),
            (self.template.use_tiled_vae, settings.use_tiled_vae),
            (self.template.enable_model_cpu_offload, settings.enable_model_cpu_offload),
        ]
        for checkbox, setting in checkbox_settings:
            checkbox.setChecked(setting.get() == True)
            checkbox.stateChanged.connect(lambda val, setting=setting: setting.set(val == 2))

        # TODO: torch compile once it is available on windows and in compiled python
        # self.template.use_torch_compile.setChecked(False)
        # self.template.use_torch_compile.setEnabled(False)
        # self.settings_manager.settings.use_torch_compile.set(False)
