"""
This class should be used to create a window widget for the LLM.
"""
from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QSpacerItem, QSizePolicy
from sqlalchemy import inspect

from airunner.aihandler.enums import MessageCode
from airunner.data.db import session
from airunner.data.models import LLMGenerator, Conversation, LLMGeneratorSetting, Message
from airunner.utils import save_session
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.llm.message_widget import MessageWidget
from airunner.widgets.llm.templates.llm_widget_ui import Ui_llm_widget


class LLMWidget(BaseWidget):
    widget_class_ = Ui_llm_widget
    generator = None
    conversation = None
    is_modal = True
    generating = False
    prefix = ""
    prompt = ""
    suffix = ""
    current_generator = "Flan"
    conversation_history = []

    @property
    def instructions(self):
        return f"{self.generator.botname} loves {self.generator.username}. {self.generator.botname} is very nice. {self.generator.botname} uses compliments, kind responses, and nice words. Everything {self.generator.botname} says is nice. {self.generator.botname} is kind."

    def load_data(self):
        self.load_generator()
        self.conversation = session.query(Conversation).first()
        if self.conversation is None:
            self.conversation = Conversation()
            session.add(self.conversation)
            session.commit()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.load_data()

        self.ui.prefix.blockSignals(True)
        self.ui.suffix.blockSignals(True)
        self.ui.prefix.setPlainText(self.generator.prefix)
        self.ui.suffix.setPlainText(self.generator.suffix)
        self.initialize_form()
        self.ui.prefix.blockSignals(False)
        self.ui.suffix.blockSignals(False)

        self.app.message_var.my_signal.connect(self.message_handler)

        self.ui.prompt.returnPressed.connect(self.action_button_clicked_send)

        self.spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self.ui.scrollAreaWidgetContents.layout().addSpacerItem(self.spacer)

        self.ui.prompt.textChanged.connect(self.prompt_text_changed)

    @pyqtSlot(dict)
    def message_handler(self, response: dict):
        print("message_handler", response)
        try:
            code = response["code"]
        except TypeError:
            return
        message = response["message"]
        {
            MessageCode.TEXT_GENERATED: self.handle_text_generated,
        }.get(code, lambda *args: None)(message)

    def initialize_form(self):
        self.ui.model.blockSignals(True)
        self.ui.prompt.blockSignals(True)
        self.ui.botname.blockSignals(True)
        self.ui.username.blockSignals(True)
        self.ui.prefix.blockSignals(True)
        self.ui.suffix.blockSignals(True)
        self.ui.personality_type.blockSignals(True)
        self.ui.radio_button_4bit.blockSignals(True)
        self.ui.radio_button_8bit.blockSignals(True)
        self.ui.radio_button_16bit.blockSignals(True)
        self.ui.radio_button_32bit.blockSignals(True)
        self.ui.random_seed.blockSignals(True)
        self.ui.do_sample.blockSignals(True)
        self.ui.early_stopping.blockSignals(True)
        self.ui.use_gpu_checkbox.blockSignals(True)
        self.ui.override_parameters.blockSignals(True)

        self.ui.radio_button_4bit.setChecked(self.generator.generator_settings[0].dtype == "4bit")
        self.ui.radio_button_8bit.setChecked(self.generator.generator_settings[0].dtype == "8bit")
        self.ui.radio_button_16bit.setChecked(self.generator.generator_settings[0].dtype == "16bit")
        self.ui.radio_button_32bit.setChecked(self.generator.generator_settings[0].dtype == "32bit")
        self.set_dtype_by_gpu(self.generator.generator_settings[0].use_gpu)
        self.set_dtype(self.generator.generator_settings[0].dtype)

        model_names = [model.name for model in session.query(LLMGenerator).all()]
        self.ui.model.clear()
        self.ui.model.addItems(model_names)
        self.ui.username.setText(self.generator.username)
        self.ui.botname.setText(self.generator.botname)
        self.update_model_version_combobox()
        self.ui.model_version.setCurrentText(self.generator.generator_settings[0].model_version)
        self.ui.personality_type.setCurrentText(self.generator.bot_personality)
        self.ui.random_seed.setChecked(self.generator.generator_settings[0].random_seed)
        self.ui.do_sample.setChecked(self.generator.generator_settings[0].do_sample)
        self.ui.early_stopping.setChecked(self.generator.generator_settings[0].early_stopping)
        self.ui.use_gpu_checkbox.setChecked(self.generator.generator_settings[0].use_gpu)
        self.ui.override_parameters.setChecked(self.generator.override_parameters)

        self.ui.model.blockSignals(False)
        self.ui.prompt.blockSignals(False)
        self.ui.botname.blockSignals(False)
        self.ui.username.blockSignals(False)
        self.ui.prefix.blockSignals(False)
        self.ui.suffix.blockSignals(False)
        self.ui.personality_type.blockSignals(False)
        self.ui.radio_button_4bit.blockSignals(False)
        self.ui.radio_button_8bit.blockSignals(False)
        self.ui.radio_button_16bit.blockSignals(False)
        self.ui.radio_button_32bit.blockSignals(False)
        self.ui.random_seed.blockSignals(False)
        self.ui.do_sample.blockSignals(False)
        self.ui.early_stopping.blockSignals(False)
        self.ui.use_gpu_checkbox.blockSignals(False)
        self.ui.override_parameters.blockSignals(False)

    def handle_text_generated(self, message):
        self.stop_progress_bar()
        self.generating = False
        self.enable_send_button()

        # strip quotes from start and end of message
        if message.startswith("\""):
            message = message[1:]
        if message.endswith("\""):
            message = message[:-1]
        message_object = Message(
            name=self.generator.botname,
            message=message,
            conversation=self.conversation
        )
        session.add(message_object)
        session.commit()
        self.add_message_to_conversation(message_object, is_bot=True)

    def personality_type_changed(self, val):
        self.generator.bot_personality = val
        save_session()

    def prefix_text_changed(self):
        self.generator.prefix = self.ui.prefix.toPlainText()
        save_session()

    def prompt_text_changed(self, val):
        self.prompt = val
    
    def suffix_text_changed(self):
        self.generator.suffix = self.ui.suffix.toPlainText()
        save_session()

    def clear_prompt(self):
        self.ui.prompt.setText("")

    def start_progress_bar(self):
        self.ui.progressBar.setRange(0, 0)
        self.ui.progressBar.setValue(0)

    def stop_progress_bar(self):
        self.ui.progressBar.setRange(0, 1)
        self.ui.progressBar.setValue(1)
        self.ui.progressBar.reset()

    def disable_send_button(self):
        self.ui.send_button.setEnabled(False)

    def enable_send_button(self):
        self.ui.send_button.setEnabled(True)

    def seed_changed(self, val):
        self.generator.generator_settings[0].seed = val
        save_session()

    def response_text_changed(self):
        pass

    def username_text_changed(self, val):
        self.generator.username = val
        save_session()

    def random_seed_toggled(self, val):
        self.generator.generator_settings[0].random_seed = val
        save_session()

    def model_version_changed(self, val):
        self.generator.generator_settings[0].model_version = val
        save_session()

    def early_stopping_toggled(self, val):
        self.generator.generator_settings[0].early_stopping = val
        save_session()

    def do_sample_toggled(self, val):
        self.generator.generator_settings[0].do_sample = val
        save_session()

    def botname_text_changed(self, val):
        self.generator.botname = val
        save_session()

    def action_button_clicked_send(self):
        if self.generating:
            return
        self.generating = True
        self.disable_send_button()
        user_input = f"{self.generator.username} Says: \"{self.prompt}\""
        # conversation = "\n".join(self.conversation_history)
        # suffix = "\n".join([self.suffix, f'{self.generator.botname} Says: '])
        # prompt = "\n".join([self.instructions, self.prefix, conversation, input, suffix])
        data = {
            "llm_request": True,
            "request_data": {
                "generator_name": self.generator.name,
                "model_path": self.generator.generator_settings[0].model_version,
                "request_type": "bot_response",
                "input": user_input,
                "do_summary": False,
                "is_bot_alive": True,
                "conversation_history": self.conversation_history,
                "generator": self.generator,
                "prefix": self.prefix,
                "suffix": self.suffix,
                "dtype": self.generator.generator_settings[0].dtype,
                "use_gpu": self.generator.generator_settings[0].use_gpu,
            }
        }
        message_object = Message(
            name=self.generator.username,
            message=self.prompt,
            conversation=self.conversation
        )
        session.add(message_object)
        session.commit()
        self.app.client.message = data
        self.add_message_to_conversation(message_object=message_object, is_bot=False)
        self.clear_prompt()
        self.start_progress_bar()

    def add_message_to_conversation(self, message_object, is_bot):
        message = f"{message_object.name} Says: \"{message_object.message}\""
        self.conversation_history.append(message)
        widget = MessageWidget(message=message_object, is_bot=is_bot)
        # add the widget to the scroll area but above the spacer
        self.remove_spacer()
        self.ui.scrollAreaWidgetContents.layout().addWidget(widget)
        self.add_spacer()
        self.ui.conversation.ensureWidgetVisible(widget)

    def remove_spacer(self):
        self.ui.scrollAreaWidgetContents.layout().removeItem(self.spacer)

    def add_spacer(self):
        self.ui.scrollAreaWidgetContents.layout().addSpacerItem(self.spacer)

    def action_button_clicked_generate_characters(self):
        pass

    def action_button_clicked_clear_conversation(self):
        self.conversation_history = []
        for widget in self.ui.scrollAreaWidgetContents.children():
            if isinstance(widget, MessageWidget):
                widget.deleteLater()

    def message_type_text_changed(self, val):
        self.generator.message_type = val
        save_session()
    
    dtype_descriptions = {
        "4bit": "Fastest, least amount of VRAM, GPU only, least accurate results.",
        "8bit": "Fast, less VRAM, GPU only, less accurate results.",
        "16bit": "Normal speed, some VRAM, uses GPU, slightly less accurate results.",
        "32bit": "Slow, no VRAM, uses CPU, most accurate results.",
    }

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
    
    def set_dtype(self, dtype):
        self.generator.generator_settings[0].dtype = dtype
        save_session()
        self.set_dtype_description(dtype)
    
    def set_dtype_description(self, dtype):
        self.ui.dtype_description.setText(self.dtype_descriptions[dtype])

    def model_text_changed(self, val):
        self.generator.generator_settings[0].model = val
        self.current_generator = val
        save_session()
        self.load_generator()
        self.update_model_version_combobox()

    def update_model_version_combobox(self):
        self.ui.model_version.blockSignals(True)
        self.ui.model_version.clear()
        model_versions = [version.name for version in self.generator.model_versions]
        self.ui.model_version.addItems(model_versions)
        self.ui.model_version.blockSignals(False)

    def load_generator(self):
        self.generator = session.query(LLMGenerator).filter(
            LLMGenerator.name == self.current_generator
        ).first()

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
        self.generator.generator_settings[0].seed = LLMGeneratorSetting.seed.default.arg
        self.generator.generator_settings[0].do_sample = LLMGeneratorSetting.do_sample.default.arg
        self.generator.generator_settings[0].early_stopping = LLMGeneratorSetting.early_stopping.default.arg
        self.generator.generator_settings[0].random_seed = LLMGeneratorSetting.random_seed.default.arg
        self.generator.generator_settings[0].model_version = LLMGeneratorSetting.model_version.default.arg
        self.generator.generator_settings[0].dtype = LLMGeneratorSetting.dtype.default.arg
        self.generator.generator_settings[0].use_gpu = LLMGeneratorSetting.use_gpu.default.arg
        save_session()
        self.initialize_form()
        self.ui.top_p_2.set_slider_and_spinbox_values(self.generator.generator_settings[0].top_p)
        self.ui.max_length_2.set_slider_and_spinbox_values(self.generator.generator_settings[0].max_length)
        self.ui.repetition_penalty_2.set_slider_and_spinbox_values(self.generator.generator_settings[0].repetition_penalty)
        self.ui.min_length_2.set_slider_and_spinbox_values(self.generator.generator_settings[0].min_length)
        self.ui.length_penalty_2.set_slider_and_spinbox_values(self.generator.generator_settings[0].length_penalty)
        self.ui.num_beams_2.set_slider_and_spinbox_values(self.generator.generator_settings[0].num_beams)
        self.ui.ngram_size_2.set_slider_and_spinbox_values(self.generator.generator_settings[0].ngram_size)
        self.ui.temperature_2.set_slider_and_spinbox_values(self.generator.generator_settings[0].temperature)
        self.ui.sequences_2.set_slider_and_spinbox_values(self.generator.generator_settings[0].sequences)
        self.ui.top_k_2.set_slider_and_spinbox_values(self.generator.generator_settings[0].top_k)
        self.ui.random_seed.setChecked(self.generator.generator_settings[0].random_seed)

    def use_gpu_toggled(self, val):
        self.generator.generator_settings[0].use_gpu = val
        # toggle the 16bit radio button and disable 4bit and 8bit radio buttons
        self.set_dtype_by_gpu(val)
        save_session()
    
    def set_dtype_by_gpu(self, use_gpu):
        if not use_gpu:
            self.ui.radio_button_4bit.setEnabled(False)
            self.ui.radio_button_8bit.setEnabled(False)
            self.ui.radio_button_32bit.setEnabled(True)

            if self.generator.generator_settings[0].dtype in ["4bit", "8bit"]:
                self.ui.radio_button_16bit.setChecked(True)
        else:
            self.ui.radio_button_4bit.setEnabled(True)
            self.ui.radio_button_8bit.setEnabled(True)
            self.ui.radio_button_32bit.setEnabled(False)
            if self.generator.generator_settings[0].dtype == "32bit":
                self.ui.radio_button_16bit.setChecked(True)
    
    def override_parameters_toggled(self, val):
        self.generator.override_parameters = val
        save_session()