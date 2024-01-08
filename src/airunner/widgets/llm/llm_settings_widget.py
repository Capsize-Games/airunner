"""
This class should be used to create a window widget for the LLM.
"""
from PyQt6.QtWidgets import QWidget

from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.llm.templates.llm_settings_ui import Ui_llm_settings_widget
from airunner.utils import save_session, get_session
from airunner.data.models import LLMGeneratorSetting, LLMGenerator, AIModel, LLMPromptTemplate
from airunner.aihandler.logger import Logger


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
    def generator(self):
        try:
            return self.app.ui.llm_widget.generator
        except Exception as e:
            Logger.error(e)
            import traceback
            traceback.print_exc()
    
    @property
    def generator_settings(self):
        try:
            return self.app.ui.llm_widget.generator_settings
        except Exception as e:
            Logger.error(e)

    @property
    def current_generator(self):
        return self.settings_manager.get_value("current_llm_generator")
    
    def initialize(self):
        self.initialize_form()

    def early_stopping_toggled(self, val):
        self.generator.generator_settings[0].early_stopping = val
        save_session()

    def do_sample_toggled(self, val):
        self.generator.generator_settings[0].do_sample = val
        save_session()
    
    def toggle_leave_model_in_vram(self, val):
        if val:
            self.settings_manager.set_value("unload_unused_model", False)
            self.settings_manager.set_value("move_unused_model_to_cpu", False)
    
    def initialize_form(self):
        session = get_session()
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
        self.ui.top_p.initialize_properties()
        self.ui.max_length.initialize_properties()
        self.ui.max_length.initialize_properties()
        self.ui.repetition_penalty.initialize_properties()
        self.ui.min_length.initialize_properties()
        self.ui.length_penalty.initialize_properties()
        self.ui.num_beams.initialize_properties()
        self.ui.ngram_size.initialize_properties()
        self.ui.temperature.initialize_properties()
        self.ui.sequences.initialize_properties()
        self.ui.top_k.initialize_properties()

        prompt_templates = [template.name for template in session.query(LLMPromptTemplate).all()]
        self.ui.prompt_template.clear()
        self.ui.prompt_template.addItems(prompt_templates)

        if self.generator:
            self.ui.radio_button_2bit.setChecked(self.generator.generator_settings[0].dtype == "2bit")
            self.ui.radio_button_4bit.setChecked(self.generator.generator_settings[0].dtype == "4bit")
            self.ui.radio_button_8bit.setChecked(self.generator.generator_settings[0].dtype == "8bit")
            self.ui.radio_button_16bit.setChecked(self.generator.generator_settings[0].dtype == "16bit")
            self.ui.radio_button_32bit.setChecked(self.generator.generator_settings[0].dtype == "32bit")
            self.set_dtype_by_gpu( self.generator.generator_settings[0].use_gpu)
            self.set_dtype(self.generator.generator_settings[0].dtype)

        # get unique model names
        model_names = [model.name for model in session.query(LLMGenerator).all()]
        model_names = list(set(model_names))
        self.ui.model.clear()
        self.ui.model.addItems(model_names)
        self.ui.model.setCurrentText(self.current_generator)
        self.update_model_version_combobox()
        if self.generator:
            self.ui.model_version.setCurrentText(self.generator.generator_settings[0].model_version)
            self.ui.random_seed.setChecked(self.generator.generator_settings[0].random_seed)
            self.ui.do_sample.setChecked(self.generator.generator_settings[0].do_sample)
            self.ui.early_stopping.setChecked(self.generator.generator_settings[0].early_stopping)
            self.ui.use_gpu_checkbox.setChecked(self.generator.generator_settings[0].use_gpu)
            self.ui.override_parameters.setChecked(self.generator.override_parameters)

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

    def model_text_changed(self, val):
        print("model_text_changed", val)
        self.settings_manager.set_value("current_llm_generator", val)
        self.update_model_version_combobox()
        self.model_version_changed(self.ui.model_version.currentText())
        self.initialize_form()

    def model_version_changed(self, val):
        self.generator.generator_settings[0].model_version = val
        save_session()
    
    def toggle_move_model_to_cpu(self, val):
        self.settings_manager.set_value("move_unused_model_to_cpu", val)
        if val:
            self.settings_manager.set_value("unload_unused_model", False)

    def override_parameters_toggled(self, val):
        self.generator.override_parameters = val
        save_session()

    def prompt_template_text_changed(self, value):
        self.generator.prompt_template = value
        save_session()
    
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
        self.generator.generator_settings[0].random_seed = val
        save_session()
    
    def seed_changed(self, val):
        self.generator.generator_settings[0].seed = val
        save_session()
    
    def toggle_unload_model(self, val):
        self.settings_manager.set_value("unload_unused_model", val)
        if val:
            self.settings_manager.set_value("move_unused_model_to_cpu", False)
    
    def use_gpu_toggled(self, val):
        self.generator.generator_settings[0].use_gpu = val
        # toggle the 16bit radio button and disable 4bit and 8bit radio buttons
        self.set_dtype_by_gpu(val)
        save_session()
    
    def set_dtype_by_gpu(self, use_gpu):
        if not use_gpu:
            self.ui.radio_button_2bit.setEnabled(False)
            self.ui.radio_button_4bit.setEnabled(False)
            self.ui.radio_button_8bit.setEnabled(False)
            self.ui.radio_button_32bit.setEnabled(True)

            if self.generator.generator_settings[0].dtype in ["4bit", "8bit"]:
                self.ui.radio_button_16bit.setChecked(True)
        else:
            self.ui.radio_button_2bit.setEnabled(True)
            self.ui.radio_button_4bit.setEnabled(True)
            self.ui.radio_button_8bit.setEnabled(True)
            self.ui.radio_button_32bit.setEnabled(False)
            if self.generator.generator_settings[0].dtype == "32bit":
                self.ui.radio_button_16bit.setChecked(True)
    
    def reset_settings_to_default_clicked(self):
        self.generator.generator_settings[0].top_p = LLMGeneratorSetting.top_p.default.arg
        self.generator.generator_settings[0].max_length = LLMGeneratorSetting.max_length.default.arg
        self.generator.generator_settings[0].repetition_penalty = LLMGeneratorSetting.repetition_penalty.default.arg
        self.generator.generator_settings[0].min_length = LLMGeneratorSetting.min_length.default.arg
        self.generator.generator_settings[0].length_penalty = LLMGeneratorSetting.length_penalty.default.arg
        self.generator.generator_settings[0].num_beams = LLMGeneratorSetting.num_beams.default.arg
        self.generator.generator_settings[0].ngram_size = LLMGeneratorSetting.ngram_size.default.arg
        self.generator.generator_settings[0].temperature = LLMGeneratorSetting.temperature.default.arg
        self.generator.generator_settings[0].sequences = LLMGeneratorSetting.sequences.default.arg
        self.generator.generator_settings[0].top_k = LLMGeneratorSetting.top_k.default.arg
        self.generator.generator_settings[0].eta_cutoff = LLMGeneratorSetting.eta_cutoff.default.arg
        self.generator.generator_settings[0].seed = LLMGeneratorSetting.seed.default.arg
        self.generator.generator_settings[0].do_sample = LLMGeneratorSetting.do_sample.default.arg
        self.generator.generator_settings[0].early_stopping = LLMGeneratorSetting.early_stopping.default.arg
        self.generator.generator_settings[0].random_seed = LLMGeneratorSetting.random_seed.default.arg
        self.generator.generator_settings[0].model_version = LLMGeneratorSetting.model_version.default.arg
        self.generator.generator_settings[0].dtype = LLMGeneratorSetting.dtype.default.arg
        self.generator.generator_settings[0].use_gpu = LLMGeneratorSetting.use_gpu.default.arg
        save_session()
        self.initialize_form()
        self.ui.top_p.set_slider_and_spinbox_values(self.generator.generator_settings[0].top_p)
        self.ui.max_length.set_slider_and_spinbox_values(self.generator.generator_settings[0].max_length)
        self.ui.repetition_penalty.set_slider_and_spinbox_values(self.generator.generator_settings[0].repetition_penalty)
        self.ui.min_length.set_slider_and_spinbox_values(self.generator.generator_settings[0].min_length)
        self.ui.length_penalty.set_slider_and_spinbox_values(self.generator.generator_settings[0].length_penalty)
        self.ui.num_beams.set_slider_and_spinbox_values(self.generator.generator_settings[0].num_beams)
        self.ui.ngram_size.set_slider_and_spinbox_values(self.generator.generator_settings[0].ngram_size)
        self.ui.temperature.set_slider_and_spinbox_values(self.generator.generator_settings[0].temperature)
        self.ui.sequences.set_slider_and_spinbox_values(self.generator.generator_settings[0].sequences)
        self.ui.top_k.set_slider_and_spinbox_values(self.generator.generator_settings[0].top_k)
        self.ui.eta_cutoff.set_slider_and_spinbox_values(self.generator.generator_settings[0].eta_cutoff)
        self.ui.random_seed.setChecked(self.generator.generator_settings[0].random_seed)

    def set_dtype(self, dtype):
        self.generator.generator_settings[0].dtype = dtype
        save_session()
        self.set_dtype_description(dtype)
    
    def set_dtype_description(self, dtype):
        self.ui.dtype_description.setText(self.dtype_descriptions[dtype])

    def update_model_version_combobox(self):
        session = get_session()
        self.ui.model_version.blockSignals(True)
        self.ui.model_version.clear()
        ai_model_paths = [model.path for model in session.query(AIModel).filter(
            AIModel.pipeline_action == self.current_generator
        )]
        self.ui.model_version.addItems(ai_model_paths)
        self.ui.model_version.blockSignals(False)

    def set_tab(self, tab_name):
        index = self.ui.tabWidget.indexOf(self.ui.tabWidget.findChild(QWidget, tab_name))
        self.ui.tabWidget.setCurrentIndex(index)