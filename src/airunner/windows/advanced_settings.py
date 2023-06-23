from airunner.windows.base_window import BaseWindow
import platform


class AdvancedSettings(BaseWindow):
    template_name = "advanced_settings"
    window_title = "Memory Settings"

    def initialize_window(self):
        checkbox_settings = {
            "use_last_channels": self.template.use_lastchannels,
            "use_attention_slicing": self.template.use_attention_slicing,
            "use_tf32": self.template.use_tf32,
            "use_enable_vae_slicing": self.template.use_enable_vae_slicing,
            "use_accelerated_transformers": self.template.use_accelerated_transformers,
            "use_tiled_vae": self.template.use_tiled_vae,
            "enable_model_cpu_offload": self.template.enable_model_cpu_offload,
            "use_enable_sequential_cpu_offload": self.template.use_enable_sequential_cpu_offload,
            #"use_torch_compile": self.template.use_torch_compile,
        }
        for name, checkbox in checkbox_settings.items():
            checkbox.setChecked(self.settings_manager.settings.__getattribute__(name).get() is True)
            checkbox.stateChanged.connect(lambda val, _name=name: self.handle_state_change(val, _name))

        # TODO: torch compile once it is available on windows and in compiled python

    def handle_state_change(self, val, name):
        self.settings_manager.settings.__getattribute__(name).set(val == 2)
        if name == "use_enable_sequential_cpu_offload" and val == 2:
            self.template.enable_model_cpu_offload.setChecked(False)
        elif name == "enable_model_cpu_offload" and val == 2:
            self.template.use_enable_sequential_cpu_offload.setChecked(False)

