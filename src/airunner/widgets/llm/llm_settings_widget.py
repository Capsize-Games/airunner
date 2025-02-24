"""
This class should be used to create a window widget for the LLM.
"""
from PySide6.QtCore import Slot
from PySide6.QtWidgets import QWidget

from airunner.enums import SignalCode
from airunner.settings import DEFAULT_LLM_HF_PATH
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.llm.templates.llm_settings_ui import Ui_llm_settings_widget
from airunner.windows.main.ai_model_mixin import AIModelMixin


class LLMSettingsWidget(
    BaseWidget,
    AIModelMixin
):
    widget_class_ = Ui_llm_settings_widget

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        AIModelMixin.__init__(self)
        self.ui.model_type_container.hide()
        self.ui.model_version_container.hide()
        self.ui.prompt_template_container.hide()
        self.initialize_form()

    @Slot(bool)
    def toggle_use_cache(self, val: bool):
        self.update_chatbot("use_cache", val)

    def showEvent(self, event):
        super().showEvent(event)

    def early_stopping_toggled(self, val):
        self.update_chatbot("early_stopping", val)

    def do_sample_toggled(self, val):
        self.update_chatbot("do_sample", val)
    
    def toggle_leave_model_in_vram(self, val):
        if val:
            self.update_memory_settings("unload_unused_models", False)
            self.update_memory_settings("move_unused_model_to_cpu", False)

    def initialize_form(self):
        elements = [
            self.ui.prompt_template,
            self.ui.model,
            self.ui.model_version,
            self.ui.random_seed,
            self.ui.do_sample,
            self.ui.early_stopping,
            self.ui.override_parameters,
            self.ui.use_cache,
        ]

        for element in elements:
            element.blockSignals(True)

        self.ui.top_p.init(slider_callback=self.callback, current_value=self.llm_generator_settings.top_p)
        self.ui.max_new_tokens.init(slider_callback=self.callback, current_value=self.llm_generator_settings.max_new_tokens)
        self.ui.repetition_penalty.init(slider_callback=self.callback, current_value=self.llm_generator_settings.repetition_penalty)
        self.ui.min_length.init(slider_callback=self.callback, current_value=self.llm_generator_settings.min_length)
        self.ui.length_penalty.init(slider_callback=self.callback, current_value=self.llm_generator_settings.length_penalty)
        self.ui.num_beams.init(slider_callback=self.callback, current_value=self.llm_generator_settings.num_beams)
        self.ui.ngram_size.init(slider_callback=self.callback, current_value=self.llm_generator_settings.ngram_size)
        self.ui.temperature.init(slider_callback=self.callback, current_value=self.llm_generator_settings.temperature)
        self.ui.sequences.init(slider_callback=self.callback, current_value=self.llm_generator_settings.sequences)
        self.ui.top_k.init(slider_callback=self.callback, current_value=self.llm_generator_settings.top_k)

        self.ui.override_parameters.setChecked(self.llm_generator_settings.override_parameters)

        self.ui.use_cache.setChecked(self.chatbot.use_cache)

        # get unique model names
        self.ui.model.clear()
        self.ui.model.addItems([
            "seq2seq",
            "causallm",
            "visualqa",
        ])
        self.ui.model.setCurrentText(self.application_settings.current_llm_generator)

        templates = {
            "Mistral 7B Instruct: Default Chatbot": dict(
                name="Mistral 7B Instruct: Default Chatbot",
                model=DEFAULT_LLM_HF_PATH,
                llm_category="causallm",
            ),
        }
        names = [v["name"] for k, v in templates.items()]

        self.ui.prompt_template.blockSignals(True)
        self.ui.prompt_template.clear()
        self.ui.prompt_template.addItems(names)
        template_name = self.llm_generator_settings.prompt_template
        if template_name == "":
            template_name = names[0]
            self.update_llm_generator_settings("prompt_template", template_name)
        self.ui.prompt_template.setCurrentText(template_name)
        self.ui.prompt_template.blockSignals(False)

        self.update_model_version_combobox()
        self.ui.model_version.setCurrentText(
            self.chatbot.model_version
        )
        self.ui.random_seed.setChecked(
            self.chatbot.random_seed
        )
        self.ui.do_sample.setChecked(
            self.chatbot.do_sample
        )
        self.ui.early_stopping.setChecked(
            self.chatbot.early_stopping
        )

        for element in elements:
            element.blockSignals(False)

    def callback(self, attr_name, value, widget=None):
        keys = attr_name.split(".")
        self.update_llm_generator_settings(keys[1], value)
        print(getattr(self.llm_generator_settings, keys[1]) == value)

    def model_text_changed(self, val):
        self.update_application_settings("current_llm_generator", val)
        self.update_model_version_combobox()
        self.model_version_changed(self.ui.model_version.currentText())
        self.initialize_form()

    def model_version_changed(self, val):
        self.update_llm_generator_settings("model_version", val)
    
    def toggle_move_model_to_cpu(self, val):
        self.update_memory_settings("move_unused_model_to_cpu", val)
        if val:
            self.update_memory_settings("unload_unused_models", False)

    def override_parameters_toggled(self, val):
        self.update_llm_generator_settings("override_parameters", val)
        
    def prompt_template_text_changed(self, value):
        self.update_llm_generator_settings("prompt_template", value)
        
    def random_seed_toggled(self, val):
        self.update_chatbot("random_seed", val)
        
    def seed_changed(self, val):
        self.update_chatbot("seed", val)
        
    def toggle_unload_model(self, val):
        self.update_memory_settings("unload_unused_models", val)
        if val:
            self.update_memory_settings("move_unused_model_to_cpu", False)

    def reset_settings_to_default_clicked(self):
        self.initialize_form()
        chatbot = self.chatbot
        self.ui.top_p.set_slider_and_spinbox_values(chatbot.top_p)
        self.ui.repetition_penalty.set_slider_and_spinbox_values(chatbot.repetition_penalty)
        self.ui.min_length.set_slider_and_spinbox_values(chatbot.min_length)
        self.ui.length_penalty.set_slider_and_spinbox_values(chatbot.length_penalty)
        self.ui.num_beams.set_slider_and_spinbox_values(chatbot.num_beams)
        self.ui.ngram_size.set_slider_and_spinbox_values(chatbot.ngram_size)
        self.ui.temperature.set_slider_and_spinbox_values(chatbot.temperature)
        self.ui.sequences.set_slider_and_spinbox_values(chatbot.sequences)
        self.ui.top_k.set_slider_and_spinbox_values(chatbot.top_k)
        self.ui.random_seed.setChecked(chatbot.random_seed)

    def update_model_version_combobox(self):
        self.ui.model_version.blockSignals(True)
        self.ui.model_version.clear()
        ai_model_paths = self.ai_model_paths(model_type="llm", pipeline_action=self.ui.model.currentText())
        self.ui.model_version.addItems(ai_model_paths)
        self.ui.model_version.blockSignals(False)

    def set_tab(self, tab_name):
        index = self.ui.tabWidget.indexOf(self.ui.tabWidget.findChild(QWidget, tab_name))
        self.ui.tabWidget.setCurrentIndex(index)

    def update_chatbot(self, key, val):
        chatbot = self.chatbot
        try:
            setattr(chatbot, key, val)
        except TypeError:
            self.logger.error(f"Attribute {key} does not exist in Chatbot")
            return
        self.save_object(chatbot)
