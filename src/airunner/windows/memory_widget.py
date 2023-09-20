from airunner.windows.custom_widget import CustomWidget


class MemoryWidget(CustomWidget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs, filename="memory_preferences")

        self.checkbox_settings = {
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
        self.initialize_checkboxes()
        self.connect_checkbox_signals()
        self.optimize_memory_button.clicked.connect(self.optimize_memory)

    def initialize_checkboxes(self):
        for name, checkbox in self.checkbox_settings.items():
            checkbox.setChecked(self.settings_manager.memory_settings.__getattribute__(name) is True)

    def connect_checkbox_signals(self):
        for name, checkbox in self.checkbox_settings.items():
            checkbox.stateChanged.connect(lambda val, _name=name: self.handle_state_change(val, _name))

    def optimize_memory(self):
        self.initialize_checkboxes()

    def handle_state_change(self, val, name):
        self.settings_manager.set_value(name, val == 2)
        if name == "use_enable_sequential_cpu_offload" and val == 2:
            self.enable_model_cpu_offload.setChecked(False)
        elif name == "enable_model_cpu_offload" and val == 2:
            self.use_enable_sequential_cpu_offload.setChecked(False)

