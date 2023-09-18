from airunner.windows.custom_widget import CustomWidget


class MemoryWidget(CustomWidget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs, filename="memory_preferences")
        
        checkbox_settings = {
            "use_last_channels": self.use_lastchannels,
            "use_attention_slicing": self.use_attention_slicing,
            "use_tf32": self.use_tf32,
            "use_enable_vae_slicing": self.use_enable_vae_slicing,
            "use_accelerated_transformers": self.use_accelerated_transformers,
            "use_tiled_vae": self.use_tiled_vae,
            "enable_model_cpu_offload": self.enable_model_cpu_offload,
            "use_enable_sequential_cpu_offload": self.use_enable_sequential_cpu_offload,
            #"use_torch_compile": self.use_torch_compile,
        }
        for name, checkbox in checkbox_settings.items():
            checkbox.setChecked(self.settings_manager.memory_settings.__getattribute__(name) is True)
            checkbox.stateChanged.connect(lambda val, _name=name: self.handle_state_change(val, _name))
        self.optimize_memory_button.clicked.connect(self.optimize_memory)

        # TODO: torch compile once it is available on windows and in compiled python

    def optimize_memory(self):
        self.settings_manager.set_value("memory_settings.use_last_channels", True)
        self.settings_manager.set_value("memory_settings.use_attention_slicing", False)
        self.settings_manager.set_value("memory_settings.use_tf32", False)
        self.settings_manager.set_value("memory_settings.use_enable_vae_slicing", True)
        self.settings_manager.set_value("memory_settings.use_accelerated_transformers", True)
        self.settings_manager.set_value("memory_settings.use_tiled_vae", True)
        self.settings_manager.set_value("memory_settings.enable_model_cpu_offload", False)
        self.settings_manager.set_value("memory_settings.use_enable_sequential_cpu_offload", False)
        self.settings_manager.set_value("memory_settings.use_cudnn_benchmark", True)

        self.use_lastchannels.setChecked(True)
        self.use_attention_slicing.setChecked(False)
        self.use_tf32.setChecked(False)
        self.use_enable_vae_slicing.setChecked(True)
        self.use_accelerated_transformers.setChecked(True)
        self.use_tiled_vae.setChecked(True)
        self.enable_model_cpu_offload.setChecked(False)
        self.use_enable_sequential_cpu_offload.setChecked(False)

    def handle_state_change(self, val, name):
        self.settings_manager.set_value(name, val == 2)
        if name == "use_enable_sequential_cpu_offload" and val == 2:
            self.enable_model_cpu_offload.setChecked(False)
        elif name == "enable_model_cpu_offload" and val == 2:
            self.use_enable_sequential_cpu_offload.setChecked(False)

