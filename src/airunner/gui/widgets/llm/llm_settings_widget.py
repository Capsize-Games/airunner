from PySide6.QtCore import Slot
from PySide6.QtWidgets import QWidget

from airunner.settings import AIRUNNER_DEFAULT_LLM_HF_PATH
from airunner.gui.widgets.base_widget import BaseWidget
from airunner.gui.widgets.llm.templates.llm_settings_ui import (
    Ui_llm_settings_widget,
)
from airunner.gui.windows.main.ai_model_mixin import AIModelMixin
from airunner.enums import ModelService, SignalCode


class LLMSettingsWidget(BaseWidget, AIModelMixin):
    widget_class_ = Ui_llm_settings_widget

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initialize_form()
        self._toggle_model_path_visibility(
            self.llm_generator_settings.model_service
            != ModelService.LOCAL.value
        )

    @Slot(str)
    def on_model_path_textChanged(self, val: str):
        self.update_llm_generator_settings("model_path", val)

    @Slot(str)
    def on_model_service_currentTextChanged(self, model_service: str):
        self.api.llm.model_changed(model_service)
        self._toggle_model_path_visibility(
            model_service != ModelService.LOCAL.value
        )

    @Slot(bool)
    def toggle_use_cache(self, val: bool):
        self.update_chatbot("use_cache", val)

    def _toggle_model_path_visibility(self, val: bool):
        if val:
            self.ui.remote_model_path.show()
        else:
            self.ui.remote_model_path.hide()

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
            self.ui.random_seed,
            self.ui.do_sample,
            self.ui.early_stopping,
            self.ui.override_parameters,
            self.ui.use_cache,
            self.ui.model_service,
            self.ui.model_path,
        ]

        for element in elements:
            element.blockSignals(True)

        self.ui.model_service.clear()
        self.ui.model_service.addItems([item.value for item in ModelService])

        self.ui.model_service.setCurrentText(
            self.llm_generator_settings.model_service
        )
        # QLineEdit requires setText, not setCurrentText
        self.ui.model_path.setText(self.llm_generator_settings.model_path)

        self.ui.top_p.init(
            slider_callback=self.callback,
            current_value=self.llm_generator_settings.top_p,
        )
        self.ui.max_new_tokens.init(
            slider_callback=self.callback,
            current_value=self.llm_generator_settings.max_new_tokens,
        )
        self.ui.repetition_penalty.init(
            slider_callback=self.callback,
            current_value=self.llm_generator_settings.repetition_penalty,
        )
        self.ui.min_length.init(
            slider_callback=self.callback,
            current_value=self.llm_generator_settings.min_length,
        )
        self.ui.length_penalty.init(
            slider_callback=self.callback,
            current_value=self.llm_generator_settings.length_penalty,
        )
        self.ui.num_beams.init(
            slider_callback=self.callback,
            current_value=self.llm_generator_settings.num_beams,
        )
        self.ui.ngram_size.init(
            slider_callback=self.callback,
            current_value=self.llm_generator_settings.ngram_size,
        )
        self.ui.temperature.init(
            slider_callback=self.callback,
            current_value=self.llm_generator_settings.temperature,
        )
        self.ui.sequences.init(
            slider_callback=self.callback,
            current_value=self.llm_generator_settings.sequences,
        )
        self.ui.top_k.init(
            slider_callback=self.callback,
            current_value=self.llm_generator_settings.top_k,
        )

        self.ui.override_parameters.setChecked(
            self.llm_generator_settings.override_parameters
        )

        self.ui.use_cache.setChecked(self.chatbot.use_cache)

        self.ui.random_seed.setChecked(self.chatbot.random_seed)
        self.ui.do_sample.setChecked(self.chatbot.do_sample)
        self.ui.early_stopping.setChecked(self.chatbot.early_stopping)

        for element in elements:
            element.blockSignals(False)

    def callback(self, attr_name, value, _widget=None):
        keys = attr_name.split(".")
        self.update_llm_generator_settings(keys[1], value)

    def model_text_changed(self, val):
        self.update_application_settings("current_llm_generator", val)
        self.initialize_form()

    def toggle_move_model_to_cpu(self, val):
        self.update_memory_settings("move_unused_model_to_cpu", val)
        if val:
            self.update_memory_settings("unload_unused_models", False)

    def override_parameters_toggled(self, val):
        self.update_llm_generator_settings("override_parameters", val)

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
        self.ui.repetition_penalty.set_slider_and_spinbox_values(
            chatbot.repetition_penalty
        )
        self.ui.min_length.set_slider_and_spinbox_values(chatbot.min_length)
        self.ui.length_penalty.set_slider_and_spinbox_values(
            chatbot.length_penalty
        )
        self.ui.num_beams.set_slider_and_spinbox_values(chatbot.num_beams)
        self.ui.ngram_size.set_slider_and_spinbox_values(chatbot.ngram_size)
        self.ui.temperature.set_slider_and_spinbox_values(chatbot.temperature)
        self.ui.sequences.set_slider_and_spinbox_values(chatbot.sequences)
        self.ui.top_k.set_slider_and_spinbox_values(chatbot.top_k)
        self.ui.random_seed.setChecked(chatbot.random_seed)

    def set_tab(self, tab_name):
        index = self.ui.tabWidget.indexOf(
            self.ui.tabWidget.findChild(QWidget, tab_name)
        )
        self.ui.tabWidget.setCurrentIndex(index)

    def update_chatbot(self, key, val):
        chatbot = self.chatbot
        try:
            setattr(chatbot, key, val)
        except TypeError:
            self.logger.error(f"Attribute {key} does not exist in Chatbot")
            return
        chatbot.save()
