"""
This class should be used to create a window widget for the LLM.
"""
from PyQt6.QtWidgets import QWidget

from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.llm.templates.llm_settings_ui import Ui_llm_settings_widget
from airunner.data.models import LLMGeneratorSetting, LLMGenerator, AIModel, LLMPromptTemplate
from airunner.aihandler.logger import Logger
from airunner.data.session_scope import session_scope


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
            return self.app.settings_manager.llm_generator
        except Exception as e:
            Logger.error(e)
            import traceback
            traceback.print_exc()
    
    @property
    def generator_settings(self):
        try:
            return self.app.settings_manager.generator_settings
        except Exception as e:
            Logger.error(e)

    @property
    def current_generator(self):
        return self.app.current_llm_generator

    def initialize(self):
        self.initialize_form()

    def early_stopping_toggled(self, val):
        with session_scope() as session:
            session.add(self.app.settings_manager.llm_generator_settings)
            self.app.settings_manager.llm_generator_settings.early_stopping = val

    def do_sample_toggled(self, val):
        with session_scope() as session:
            session.add(self.generator)
            self.app.settings_manager.llm_generator_settings.do_sample = val
    
    def toggle_leave_model_in_vram(self, val):
        if val:
            self.app.unload_unused_model = False
            self.app.move_unused_model_to_cpu = False
    
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

        with session_scope() as session:
            prompt_templates = [template.name for template in session.query(LLMPromptTemplate).all()]
            model_names = [model.name for model in session.query(LLMGenerator).all()]

        self.ui.prompt_template.clear()
        self.ui.prompt_template.addItems(prompt_templates)

        self.ui.leave_in_vram.setChecked(not self.app.unload_unused_models and not self.app.move_unused_model_to_cpu)
        self.ui.move_to_cpu.setChecked(self.app.move_unused_model_to_cpu)
        self.ui.unload_model.setChecked(self.app.unload_unused_models)

        if self.generator:
            self.ui.radio_button_2bit.setChecked(self.app.settings_manager.llm_generator_settings.dtype == "2bit")
            self.ui.radio_button_4bit.setChecked(self.app.settings_manager.llm_generator_settings.dtype == "4bit")
            self.ui.radio_button_8bit.setChecked(self.app.settings_manager.llm_generator_settings.dtype == "8bit")
            self.ui.radio_button_16bit.setChecked(self.app.settings_manager.llm_generator_settings.dtype == "16bit")
            self.ui.radio_button_32bit.setChecked(self.app.settings_manager.llm_generator_settings.dtype == "32bit")
            self.set_dtype_by_gpu( self.app.settings_manager.llm_generator_settings.use_gpu)
            self.set_dtype(self.app.settings_manager.llm_generator_settings.dtype)

        # get unique model names
        model_names = list(set(model_names))
        self.ui.model.clear()
        self.ui.model.addItems(model_names)
        self.ui.model.setCurrentText(self.current_generator)
        self.update_model_version_combobox()
        if self.generator:
            self.ui.model_version.setCurrentText(self.app.settings_manager.llm_generator_settings.model_version)
            self.ui.random_seed.setChecked(self.app.settings_manager.llm_generator_settings.random_seed)
            self.ui.do_sample.setChecked(self.app.settings_manager.llm_generator_settings.do_sample)
            self.ui.early_stopping.setChecked(self.app.settings_manager.llm_generator_settings.early_stopping)
            self.ui.use_gpu_checkbox.setChecked(self.app.settings_manager.llm_generator_settings.use_gpu)
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
        self.ui.leave_in_vram.blockSignals(False)
        self.ui.move_to_cpu.blockSignals(False)
        self.ui.unload_model.blockSignals(False)

    def model_text_changed(self, val):
        print("model_text_changed", val)
        self.app.current_llm_generator = val
        self.update_model_version_combobox()
        self.model_version_changed(self.ui.model_version.currentText())
        self.initialize_form()

    def model_version_changed(self, val):
        with session_scope() as session:
            session.add(self.generator)
            self.app.settings_manager.llm_generator_settings.model_version = val
    
    def toggle_move_model_to_cpu(self, val):
        self.app.move_unused_model_to_cpu = val
        if val:
            self.app.settings_manager.set_value("settings.unload_unused_model", False)

    def override_parameters_toggled(self, val):
        with session_scope() as session:
            session.add(self.generator)
            self.generator.override_parameters = val
        
    def prompt_template_text_changed(self, value):
        with session_scope() as session:
            session.add(self.generator)
            self.generator.prompt_template = value
        
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
        with session_scope() as session:
            session.add(self.generator)
            self.app.settings_manager.llm_generator_settings.random_seed = val
        
    def seed_changed(self, val):
        with session_scope() as session:
            session.add(self.generator)
            self.app.settings_manager.llm_generator_settings.seed = val
        
    def toggle_unload_model(self, val):
        self.app.unload_unused_model = val
        if val:
            self.app.move_unused_model_to_cpu = False
    
    def use_gpu_toggled(self, val):
        with session_scope() as session:
            session.add(self.generator)
            self.app.settings_manager.llm_generator_settings.use_gpu = val
            # toggle the 16bit radio button and disable 4bit and 8bit radio buttons
            self.set_dtype_by_gpu(val)
    
    def set_dtype_by_gpu(self, use_gpu):
        if not use_gpu:
            if self.app.settings_manager.llm_generator_settings.dtype in ["2bit","4bit", "8bit"]:
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
            if self.app.settings_manager.llm_generator_settings.dtype == "32bit":
                self.ui.radio_button_16bit.setChecked(True)
    
    def reset_settings_to_default_clicked(self):
        with session_scope() as session:
            session.add(self.app.settings_manager.llm_generator_settings)
            session.add(self.generator)
            
            self.app.settings_manager.llm_generator_settings.top_p = LLMGeneratorSetting.top_p.default.arg
            self.app.settings_manager.llm_generator_settings.max_length = LLMGeneratorSetting.max_length.default.arg
            self.app.settings_manager.llm_generator_settings.repetition_penalty = LLMGeneratorSetting.repetition_penalty.default.arg
            self.app.settings_manager.llm_generator_settings.min_length = LLMGeneratorSetting.min_length.default.arg
            self.app.settings_manager.llm_generator_settings.length_penalty = LLMGeneratorSetting.length_penalty.default.arg
            self.app.settings_manager.llm_generator_settings.num_beams = LLMGeneratorSetting.num_beams.default.arg
            self.app.settings_manager.llm_generator_settings.ngram_size = LLMGeneratorSetting.ngram_size.default.arg
            self.app.settings_manager.llm_generator_settings.temperature = LLMGeneratorSetting.temperature.default.arg
            self.app.settings_manager.llm_generator_settings.sequences = LLMGeneratorSetting.sequences.default.arg
            self.app.settings_manager.llm_generator_settings.top_k = LLMGeneratorSetting.top_k.default.arg
            self.app.settings_manager.llm_generator_settings.eta_cutoff = LLMGeneratorSetting.eta_cutoff.default.arg
            self.app.settings_manager.llm_generator_settings.seed = LLMGeneratorSetting.seed.default.arg
            self.app.settings_manager.llm_generator_settings.do_sample = LLMGeneratorSetting.do_sample.default.arg
            self.app.settings_manager.llm_generator_settings.early_stopping = LLMGeneratorSetting.early_stopping.default.arg
            self.app.settings_manager.llm_generator_settings.random_seed = LLMGeneratorSetting.random_seed.default.arg
            self.app.settings_manager.llm_generator_settings.model_version = LLMGeneratorSetting.model_version.default.arg
            self.app.settings_manager.llm_generator_settings.dtype = LLMGeneratorSetting.dtype.default.arg
            self.app.settings_manager.llm_generator_settings.use_gpu = LLMGeneratorSetting.use_gpu.default.arg

        self.initialize_form()
        self.ui.top_p.set_slider_and_spinbox_values(self.app.settings_manager.llm_generator_settings.top_p)
        self.ui.max_length.set_slider_and_spinbox_values(self.app.settings_manager.llm_generator_settings.max_length)
        self.ui.repetition_penalty.set_slider_and_spinbox_values(self.app.settings_manager.llm_generator_settings.repetition_penalty)
        self.ui.min_length.set_slider_and_spinbox_values(self.app.settings_manager.llm_generator_settings.min_length)
        self.ui.length_penalty.set_slider_and_spinbox_values(self.app.settings_manager.llm_generator_settings.length_penalty)
        self.ui.num_beams.set_slider_and_spinbox_values(self.app.settings_manager.llm_generator_settings.num_beams)
        self.ui.ngram_size.set_slider_and_spinbox_values(self.app.settings_manager.llm_generator_settings.ngram_size)
        self.ui.temperature.set_slider_and_spinbox_values(self.app.settings_manager.llm_generator_settings.temperature)
        self.ui.sequences.set_slider_and_spinbox_values(self.app.settings_manager.llm_generator_settings.sequences)
        self.ui.top_k.set_slider_and_spinbox_values(self.app.settings_manager.llm_generator_settings.top_k)
        self.ui.eta_cutoff.set_slider_and_spinbox_values(self.app.settings_manager.llm_generator_settings.eta_cutoff)
        self.ui.random_seed.setChecked(self.app.settings_manager.llm_generator_settings.random_seed)

    def set_dtype(self, dtype):
        with session_scope() as session:
            session.add(self.app.settings_manager.llm_generator_settings)
            self.app.settings_manager.llm_generator_settings.dtype = dtype
        self.set_dtype_description(dtype)
    
    def set_dtype_description(self, dtype):
        self.ui.dtype_description.setText(self.dtype_descriptions[dtype])

    def update_model_version_combobox(self):
        self.ui.model_version.blockSignals(True)
        self.ui.model_version.clear()
        with session_scope() as session:
            ai_model_paths = [model.path for model in session.query(AIModel).filter(
                AIModel.pipeline_action == self.current_generator
            )]
        self.ui.model_version.addItems(ai_model_paths)
        self.ui.model_version.blockSignals(False)

    def set_tab(self, tab_name):
        index = self.ui.tabWidget.indexOf(self.ui.tabWidget.findChild(QWidget, tab_name))
        self.ui.tabWidget.setCurrentIndex(index)