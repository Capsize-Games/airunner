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
            checkbox.setChecked(self.settings_manager.settings.__getattribute__(name).get() is True)
            checkbox.stateChanged.connect(lambda val, _name=name: self.handle_state_change(val, _name))
        self.optimize_memory_button.clicked.connect(self.optimize_memory)

        # TODO: torch compile once it is available on windows and in compiled python

    def optimize_memory(self):
        self.settings_manager.settings.use_last_channels.set(True)
        self.settings_manager.settings.use_attention_slicing.set(False)
        self.settings_manager.settings.use_tf32.set(False)
        self.settings_manager.settings.use_enable_vae_slicing.set(True)
        self.settings_manager.settings.use_accelerated_transformers.set(True)
        self.settings_manager.settings.use_tiled_vae.set(True)
        self.settings_manager.settings.enable_model_cpu_offload.set(False)
        self.settings_manager.settings.use_enable_sequential_cpu_offload.set(False)

        self.use_lastchannels.setChecked(True)
        self.use_attention_slicing.setChecked(False)
        self.use_tf32.setChecked(False)
        self.use_enable_vae_slicing.setChecked(True)
        self.use_accelerated_transformers.setChecked(True)
        self.use_tiled_vae.setChecked(True)
        self.enable_model_cpu_offload.setChecked(False)
        self.use_enable_sequential_cpu_offload.setChecked(False)

    def handle_state_change(self, val, name):
        self.settings_manager.settings.__getattribute__(name).set(val == 2)
        if name == "use_enable_sequential_cpu_offload" and val == 2:
            self.enable_model_cpu_offload.setChecked(False)
        elif name == "enable_model_cpu_offload" and val == 2:
            self.use_enable_sequential_cpu_offload.setChecked(False)

