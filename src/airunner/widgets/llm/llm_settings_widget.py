"""
This class should be used to create a window widget for the LLM.
"""
from PyQt6.QtWidgets import QWidget

from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.llm.templates.llm_settings_ui import Ui_llm_settings_widget


class LLMSettingsWidget(BaseWidget):
    widget_class_ = Ui_llm_settings_widget
    current_generator = None
    dtype_descriptions = {
        "2bit": "Fastest, least amount of VRAM, GPU only, least accurate results.",
        "4bit": "Faster, much less VRAM, GPU only, much less accurate results.",
        "8bit": "Fast, less VRAM, GPU only, less accurate results.",
        "16bit": "Normal speed, some VRAM, uses GPU, slightly less accurate results.",
        "32bit": "Slow, no VRAM, uses CPU, most accurate results.",
    }

    @property
    def current_generator(self):
        return self.settings["current_llm_generator"]

    def showEvent(self, event):
        super().showEvent(event)
        self.initialize_form()

    def early_stopping_toggled(self, val):
        settings = self.settings
        settings["llm_generator_settings"]["early_stopping"] = val
        self.settings = settings

    def do_sample_toggled(self, val):
        settings = self.settings
        settings["llm_generator_settings"]["do_sample"] = val
        self.settings = settings
    
    def toggle_leave_model_in_vram(self, val):
        if val:
            settings = self.settings
            settings["memory_settings"]["unload_unused_models"] = not val
            settings["memory_settings"]["move_unused_model_to_cpu"] = False
            self.settings = settings
            
    
    def initialize_form(self):
        self.ui.prompt_template.blockSignals(True)
        self.ui.model.blockSignals(True)
        self.ui.model_version.blockSignals(True)
        self.ui.radio_button_2bit.blockSignals(True)
        self.ui.radio_button_4bit.blockSignals(True)
        self.ui.radio_button_8bit.blockSignals(True)
        self.ui.radio_button_16bit.blockSignals(True)
        self.ui.radio_button_32bit.blockSignals(True)
        self.ui.random_seed.blockSignals(True)
        self.ui.do_sample.blockSignals(True)
        self.ui.early_stopping.blockSignals(True)
        self.ui.use_gpu_checkbox.blockSignals(True)
        self.ui.override_parameters.blockSignals(True)
        self.ui.leave_in_vram.blockSignals(True)
        self.ui.move_to_cpu.blockSignals(True)
        self.ui.unload_model.blockSignals(True)
        self.ui.top_p.initialize()
        self.ui.max_length.initialize()
        self.ui.max_length.initialize()
        self.ui.repetition_penalty.initialize()
        self.ui.min_length.initialize()
        self.ui.length_penalty.initialize()
        self.ui.num_beams.initialize()
        self.ui.ngram_size.initialize()
        self.ui.temperature.initialize()
        self.ui.sequences.initialize()
        self.ui.top_k.initialize()

        self.ui.leave_in_vram.setChecked(not self.memory_settings["unload_unused_models"] and not self.memory_settings["move_unused_model_to_cpu"])
        self.ui.move_to_cpu.setChecked(self.memory_settings["move_unused_model_to_cpu"])
        self.ui.unload_model.setChecked(self.memory_settings["unload_unused_models"])

        llm_generator_settings = self.llm_generator_settings

        dtype = llm_generator_settings["dtype"]
        self.ui.radio_button_2bit.setChecked(dtype == "2bit")
        self.ui.radio_button_4bit.setChecked(dtype == "4bit")
        self.ui.radio_button_8bit.setChecked(dtype == "8bit")
        self.ui.radio_button_16bit.setChecked(dtype == "16bit")
        self.ui.radio_button_32bit.setChecked(dtype == "32bit")
        self.set_dtype_by_gpu(llm_generator_settings["use_gpu"])
        self.set_dtype(dtype)

        # get unique model names
        self.ui.model.clear()
        self.ui.model.addItems([
            "seq2seq",
            "casuallm",
            "visualqa",
        ])
        self.ui.model.setCurrentText(self.current_generator)

        templates = self.llm_templates
        names = [v["name"] for k, v in templates.items()]
        
        self.ui.prompt_template.blockSignals(True)
        self.ui.prompt_template.clear()
        self.ui.prompt_template.addItems(names)
        template_name = self.llm_generator_settings["prompt_template"]
        if template_name == "":
            template_name = names[0]
            settings = self.settings
            settings["llm_generator_settings"]["prompt_template"] = template_name
            self.settings = settings
        self.ui.prompt_template.setCurrentText(template_name)
        self.ui.prompt_template.blockSignals(False)

        self.update_model_version_combobox()
        self.ui.model_version.setCurrentText(llm_generator_settings["model_version"])
        self.ui.random_seed.setChecked(llm_generator_settings["random_seed"])
        self.ui.do_sample.setChecked(llm_generator_settings["do_sample"])
        self.ui.early_stopping.setChecked(llm_generator_settings["early_stopping"])
        self.ui.use_gpu_checkbox.setChecked(llm_generator_settings["use_gpu"])
        self.ui.override_parameters.setChecked(self.llm_generator_settings["override_parameters"])

        self.ui.model.blockSignals(False)
        self.ui.model_version.blockSignals(False)
        self.ui.radio_button_2bit.blockSignals(False)
        self.ui.radio_button_4bit.blockSignals(False)
        self.ui.radio_button_8bit.blockSignals(False)
        self.ui.radio_button_16bit.blockSignals(False)
        self.ui.radio_button_32bit.blockSignals(False)
        self.ui.random_seed.blockSignals(False)
        self.ui.do_sample.blockSignals(False)
        self.ui.early_stopping.blockSignals(False)
        self.ui.use_gpu_checkbox.blockSignals(False)
        self.ui.override_parameters.blockSignals(False)
        self.ui.prompt_template.blockSignals(False)
        self.ui.leave_in_vram.blockSignals(False)
        self.ui.move_to_cpu.blockSignals(False)
        self.ui.unload_model.blockSignals(False)

    def model_text_changed(self, val):
        settings = self.settings
        settings["current_llm_generator"] = val
        self.settings = settings
        self.update_model_version_combobox()
        self.model_version_changed(self.ui.model_version.currentText())
        self.initialize_form()

    def model_version_changed(self, val):
        settings = self.settings
        settings["llm_generator_settings"]["model_version"] = val
        self.settings = settings
    
    def toggle_move_model_to_cpu(self, val):
        settings = self.settings
        settings["memory_settings"]["move_unused_model_to_cpu"] = val
        if val:
            settings["memory_settings"]["unload_unused_models"] = False
        self.settings = settings

    def override_parameters_toggled(self, val):
        settings = self.settings
        settings["llm_generator_settings"]["override_parameters"] = val
        self.settings = settings
        
    def prompt_template_text_changed(self, value):
        settings = self.settings
        settings["llm_generator_settings"]["prompt_template"] = value
        self.settings = settings
        
    def toggled_2bit(self, val):
        if val:
            self.set_dtype("2bit")

    def toggled_4bit(self, val):
        if val:
            self.set_dtype("4bit")

    def toggled_8bit(self, val):
        if val:
            self.set_dtype("8bit")

    def toggled_16bit(self, val):
        if val:
            self.set_dtype("16bit")

    def toggled_32bit(self, val):
        if val:
            self.set_dtype("32bit")
        
    def random_seed_toggled(self, val):
        settings = self.settings
        settings["llm_generator_settings"]["random_seed"] = val
        self.settings = settings
        
    def seed_changed(self, val):
        settings = self.settings
        settings["llm_generator_settings"]["seed"] = val
        self.settings = settings
        
    def toggle_unload_model(self, val):
        settings = self.settings
        settings["memory_settings"]["unload_unused_models"] = val
        if val:
            settings["memory_settings"]["move_unused_model_to_cpu"] = False
        self.settings = settings
    
    def use_gpu_toggled(self, val):
        settings = self.settings
        settings["llm_generator_settings"]["use_gpu"] = val
        self.settings = settings
        self.set_dtype_by_gpu(val)
    
    def set_dtype_by_gpu(self, use_gpu):
        settings = self.settings
        dtype = settings["llm_generator_settings"]["dtype"]
        if not use_gpu:            
            if dtype in ["2bit","4bit", "8bit"]:
                self.ui.radio_button_16bit.setChecked(True)
            self.ui.radio_button_2bit.setEnabled(False)
            self.ui.radio_button_4bit.setEnabled(False)
            self.ui.radio_button_8bit.setEnabled(False)
            self.ui.radio_button_32bit.setEnabled(True)
        else:
            self.ui.radio_button_2bit.setEnabled(True)
            self.ui.radio_button_4bit.setEnabled(True)
            self.ui.radio_button_8bit.setEnabled(True)
            self.ui.radio_button_32bit.setEnabled(False)
            if dtype == "32bit":
                self.ui.radio_button_16bit.setChecked(True)
    
    def reset_settings_to_default_clicked(self):
        print("TODO")
        llm_generator_settings = self.llm_generator_settings
        self.initialize_form()
        self.ui.top_p.set_slider_and_spinbox_values(llm_generator_settings["top_p"])
        self.ui.max_length.set_slider_and_spinbox_values(llm_generator_settings["max_length"])
        self.ui.repetition_penalty.set_slider_and_spinbox_values(llm_generator_settings["repetition_penalty"])
        self.ui.min_length.set_slider_and_spinbox_values(llm_generator_settings["min_length"])
        self.ui.length_penalty.set_slider_and_spinbox_values(llm_generator_settings["length_penalty"])
        self.ui.num_beams.set_slider_and_spinbox_values(llm_generator_settings["num_beams"])
        self.ui.ngram_size.set_slider_and_spinbox_values(llm_generator_settings["ngram_size"])
        self.ui.temperature.set_slider_and_spinbox_values(llm_generator_settings["temperature"])
        self.ui.sequences.set_slider_and_spinbox_values(llm_generator_settings["sequences"])
        self.ui.top_k.set_slider_and_spinbox_values(llm_generator_settings["top_k"])
        self.ui.eta_cutoff.set_slider_and_spinbox_values(llm_generator_settings["eta_cutoff"])
        self.ui.random_seed.setChecked(llm_generator_settings["random_seed"])

    def set_dtype(self, dtype):
        settings = self.settings
        settings["llm_generator_settings"]["dtype"] = dtype
        self.settings = settings
        self.set_dtype_description(dtype)
    
    def set_dtype_description(self, dtype):
        self.ui.dtype_description.setText(self.dtype_descriptions[dtype])

    def update_model_version_combobox(self):
        self.ui.model_version.blockSignals(True)
        self.ui.model_version.clear()
        ai_model_paths = self.get_service("ai_model_paths")(model_type="llm", pipeline_action=self.ui.model.currentText())
        self.ui.model_version.addItems(ai_model_paths)
        self.ui.model_version.blockSignals(False)

    def set_tab(self, tab_name):
        index = self.ui.tabWidget.indexOf(self.ui.tabWidget.findChild(QWidget, tab_name))
        self.ui.tabWidget.setCurrentIndex(index)
    
    def bot_personality_changed(self):
        value = self.ui.bot_personality.currentText()
        llm_generator_settings = self.llm_generator_settings
        llm_generator_settings["bot_personality"] = value
        self.llm_generator_settings = llm_generator_settings

    def bot_mood_changed(self):
        value = self.ui.bot_mood.currentText()
        llm_generator_settings = self.llm_generator_settings
        llm_generator_settings["bot_mood"] = value
        self.llm_generator_settings = llm_generator_settings