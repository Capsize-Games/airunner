
from PySide6.QtCore import Slot
from airunner.gui.widgets.base_widget import BaseWidget
from airunner.gui.widgets.memory_preferences.templates.memory_preferences_ui import Ui_memory_preferences


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
            "use_tome": "use_tome_sd",
            "prevent_unload_on_llm_image_generation": "prevent_unload_on_llm_image_generation",
        }

        for ui_element, setting in ui_elements.items():
            val = getattr(self.memory_settings, setting)
            getattr(self.ui, ui_element).blockSignals(True)
            getattr(self.ui, ui_element).setChecked(val is True)
            getattr(self.ui, ui_element).blockSignals(False)

        import torch
        device_count = torch.cuda.device_count()
        available_devices = [f"{torch.cuda.get_device_name(i)}" for i in range(device_count)]
        self.available_devices = available_devices
        self.ui.sd_combobox.blockSignals(True)
        self.ui.llm_combobox.blockSignals(True)
        self.ui.tts_combobox.blockSignals(True)
        self.ui.stt_combobox.blockSignals(True)
        self.ui.sd_combobox.addItems(available_devices)
        self.ui.llm_combobox.addItems(available_devices)
        self.ui.tts_combobox.addItems(available_devices)
        self.ui.stt_combobox.addItems(available_devices)
        self.ui.sd_combobox.setCurrentText(available_devices[self.memory_settings.default_gpu_sd])
        self.ui.llm_combobox.setCurrentText(available_devices[self.memory_settings.default_gpu_llm])
        self.ui.tts_combobox.setCurrentText(available_devices[self.memory_settings.default_gpu_tts])
        self.ui.stt_combobox.setCurrentText(available_devices[self.memory_settings.default_gpu_stt])
        self.ui.sd_combobox.blockSignals(False)
        self.ui.llm_combobox.blockSignals(False)
        self.ui.tts_combobox.blockSignals(False)
        self.ui.stt_combobox.blockSignals(False)

        self.ui.tome_sd_ratio.init(
            slider_callback=self.tome_sd_ratio_value_change,
        )

    @Slot(str)
    def action_changed_sd_combobox(self, val: str):
        self.update_memory_settings("default_gpu_sd", self.available_devices.index(val))

    @Slot(str)
    def action_changed_llm_combobox(self, val: str):
        self.update_memory_settings("default_gpu_llm", self.available_devices.index(val))

    @Slot(str)
    def action_changed_tts_combobox(self, val: str):
        self.update_memory_settings("default_gpu_tts", self.available_devices.index(val))

    @Slot(str)
    def action_changed_stt_combobox(self, val: str):
        self.update_memory_settings("default_gpu_stt", self.available_devices.index(val))
    
    @Slot(bool)
    def action_toggled_prevent_unload_on_llm_image_generation(self, val: bool):
        self.update_memory_settings("prevent_unload_on_llm_image_generation", val)

    def action_toggled_setting(self, setting_name, val):
        self.update_memory_settings(setting_name, val)

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

    def action_toggled_use_tome(self, val):
        self.update_memory_settings("use_tome_sd", val)

    def tome_sd_ratio_value_change(self, _prop, val):
        self.update_memory_settings("tome_sd_ratio", val)
