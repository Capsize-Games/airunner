"""
This class should be used to create a window widget for the LLM.
"""
from PySide6.QtCore import Slot
from PySide6.QtWidgets import QWidget
from airunner.enums import SignalCode
from airunner.settings import DEFAULT_CHATBOT
from airunner.utils.get_current_chatbot import get_current_chatbot_property, get_current_chatbot
from airunner.utils.get_current_chatbot import set_current_chatbot_property
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

    @property
    def chatbot(self) -> dict:
        current_chatbot_name = self.settings["llm_generator_settings"]["current_chatbot"]
        chatbot = self.settings["llm_generator_settings"]["saved_chatbots"].get(
            current_chatbot_name,
            DEFAULT_CHATBOT
        )
        return chatbot

    @property
    def generator_settings(self) -> dict:
        return self.settings["llm_generator_settings"]["generator_settings"]

    @property
    def current_generator(self):
        return self.settings["current_llm_generator"]

    def showEvent(self, event):
        super().showEvent(event)
        self.emit_signal(SignalCode.WINDOW_LOADED_SIGNAL)

    def early_stopping_toggled(self, val):
        settings = self.settings
        settings = set_current_chatbot_property(settings, "early_stopping", val)
        self.settings = settings

    def do_sample_toggled(self, val):
        settings = self.settings
        settings = set_current_chatbot_property(settings, ["generator_settings", "do_sample"], val)
        self.settings = settings
    
    def toggle_leave_model_in_vram(self, val):
        if val:
            settings = self.settings
            settings["memory_settings"]["unload_unused_models"] = not val
            settings["memory_settings"]["move_unused_model_to_cpu"] = False
            self.settings = settings

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

        self.ui.top_p.init(slider_callback=self.callback, current_value=self.generator_settings["top_p"])
        self.ui.max_new_tokens.init(slider_callback=self.callback, current_value=self.generator_settings["max_new_tokens"])
        self.ui.repetition_penalty.init(slider_callback=self.callback, current_value=self.generator_settings["repetition_penalty"])
        self.ui.min_length.init(slider_callback=self.callback, current_value=self.generator_settings["min_length"])
        self.ui.length_penalty.init(slider_callback=self.callback, current_value=self.generator_settings["length_penalty"])
        self.ui.num_beams.init(slider_callback=self.callback, current_value=self.generator_settings["num_beams"])
        self.ui.ngram_size.init(slider_callback=self.callback, current_value=self.generator_settings["ngram_size"])
        self.ui.temperature.init(slider_callback=self.callback, current_value=self.generator_settings["temperature"])
        self.ui.sequences.init(slider_callback=self.callback, current_value=self.generator_settings["num_return_sequences"])
        self.ui.top_k.init(slider_callback=self.callback, current_value=self.generator_settings["top_k"])

        self.ui.override_parameters.setChecked(self.settings["llm_generator_settings"]["override_parameters"])

        use_cache = get_current_chatbot_property(self.settings, "use_cache")
        self.ui.use_cache.setChecked(use_cache)

        # get unique model names
        self.ui.model.clear()
        self.ui.model.addItems([
            "seq2seq",
            "causallm",
            "visualqa",
        ])
        self.ui.model.setCurrentText(self.current_generator)

        templates = self.settings["llm_templates"]
        names = [v["name"] for k, v in templates.items()]

        self.ui.prompt_template.blockSignals(True)
        self.ui.prompt_template.clear()
        self.ui.prompt_template.addItems(names)
        template_name = self.settings["llm_generator_settings"]["prompt_template"]
        if template_name == "":
            template_name = names[0]
            settings = self.settings
            settings["llm_generator_settings"]["prompt_template"] = template_name
            self.settings = settings
        self.ui.prompt_template.setCurrentText(template_name)
        self.ui.prompt_template.blockSignals(False)

        self.update_model_version_combobox()
        self.ui.model_version.setCurrentText(
            get_current_chatbot_property(self.settings, "model_version")
        )
        self.ui.random_seed.setChecked(
            get_current_chatbot_property(self.settings, "random_seed")
        )
        self.ui.do_sample.setChecked(
            get_current_chatbot_property(self.settings, ["generator_settings", "do_sample"])
        )
        self.ui.early_stopping.setChecked(
            get_current_chatbot_property(self.settings, ["generator_settings", "early_stopping"])
        )

        for element in elements:
            element.blockSignals(False)

    def callback(self, attr_name, value, widget=None):
        settings = self.settings
        current_chatbot_name = self.settings["llm_generator_settings"]["current_chatbot"]
        generator_settings = settings["llm_generator_settings"]["saved_chatbots"][current_chatbot_name]["generator_settings"]
        generator_settings[attr_name] = value
        settings["llm_generator_settings"]["saved_chatbots"][current_chatbot_name]["generator_settings"] = generator_settings
        self.settings = settings

    def model_text_changed(self, val):
        settings = self.settings
        settings["current_llm_generator"] = val
        self.settings = settings
        self.update_model_version_combobox()
        self.model_version_changed(self.ui.model_version.currentText())
        self.initialize_form()

    def model_version_changed(self, val):
        settings = self.settings
        settings = set_current_chatbot_property(settings, "model_version", val)
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
        
    def random_seed_toggled(self, val):
        settings = self.settings
        settings = set_current_chatbot_property(settings, "random_seed", val)
        self.settings = settings
        
    def seed_changed(self, val):
        settings = self.settings
        settings = set_current_chatbot_property(settings, "seed", val)
        self.settings = settings
        
    def toggle_unload_model(self, val):
        settings = self.settings
        settings["memory_settings"]["unload_unused_models"] = val
        if val:
            settings["memory_settings"]["move_unused_model_to_cpu"] = False
        self.settings = settings
    
    @property
    def llm_generator_settings(self):
        return self.settings["llm_generator_settings"]

    @property
    def current_chatbot_name(self):
        chatbot = self.llm_generator_settings["current_chatbot"]
        if chatbot == "":
            chatbot = "Default"
        return chatbot

    @current_chatbot_name.setter
    def current_chatbot_name(self, val):
        if val == "":
            val = "Default"
        settings = self.settings
        settings["llm_generator_settings"]["current_chatbot"] = val
        self.settings = settings

    @property
    def current_chatbot(self):
        return get_current_chatbot(self.settings)

    def reset_settings_to_default_clicked(self):
        llm_generator_settings = self.current_chatbot["generator_settings"]
        self.initialize_form()
        self.ui.top_p.set_slider_and_spinbox_values(llm_generator_settings["top_p"])
        self.ui.repetition_penalty.set_slider_and_spinbox_values(llm_generator_settings["repetition_penalty"])
        self.ui.min_length.set_slider_and_spinbox_values(llm_generator_settings["min_length"])
        self.ui.length_penalty.set_slider_and_spinbox_values(llm_generator_settings["length_penalty"])
        self.ui.num_beams.set_slider_and_spinbox_values(llm_generator_settings["num_beams"])
        self.ui.ngram_size.set_slider_and_spinbox_values(llm_generator_settings["ngram_size"])
        self.ui.temperature.set_slider_and_spinbox_values(llm_generator_settings["temperature"])
        self.ui.sequences.set_slider_and_spinbox_values(llm_generator_settings["sequences"])
        self.ui.top_k.set_slider_and_spinbox_values(llm_generator_settings["top_k"])
        self.ui.random_seed.setChecked(llm_generator_settings["random_seed"])

    def update_model_version_combobox(self):
        self.ui.model_version.blockSignals(True)
        self.ui.model_version.clear()
        ai_model_paths = self.ai_model_paths(model_type="llm", pipeline_action=self.ui.model.currentText())
        self.ui.model_version.addItems(ai_model_paths)
        self.ui.model_version.blockSignals(False)

    def set_tab(self, tab_name):
        index = self.ui.tabWidget.indexOf(self.ui.tabWidget.findChild(QWidget, tab_name))
        self.ui.tabWidget.setCurrentIndex(index)

    @Slot(bool)
    def toggle_use_cache(self, val: bool):
        settings = self.settings
        settings = set_current_chatbot_property(settings, "use_cache", val)
        self.settings = settings
