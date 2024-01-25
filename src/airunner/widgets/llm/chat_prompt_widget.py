from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QSpacerItem, QSizePolicy
from PyQt6.QtCore import Qt

from airunner.enums import SignalCode, ServiceCode
from airunner.mediator_mixin import MediatorMixin
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.llm.loading_widget import LoadingWidget
from airunner.widgets.llm.templates.chat_prompt_ui import Ui_chat_prompt
from airunner.widgets.llm.message_widget import MessageWidget


class ChatPromptWidget(BaseWidget):
    widget_class_ = Ui_chat_prompt

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.conversation = None
        self.is_modal = True
        self.generating = False
        self.prefix = ""
        self.prompt = ""
        self.suffix = ""
        self.conversation_history = []
        self.spacer = None
        self.promptKeyPressEvent = None
        self.originalKeyPressEvent = None
        self.action_menu_displayed = None
        self.action_menu_displayed = None

    @property
    def current_generator(self):
        return self.settings["current_llm_generator"]
    
    @pyqtSlot(str)
    def handle_token_signal(self, val: str):
        if val != "[END]":
            text = self.ui.conversation.toPlainText()
            text += val
            self.ui.conversation.setText(text)
        else:
            self.stop_progress_bar()
            self.generating = False
            self.enable_send_button()

    def on_add_to_conversation_signal(self, name, text, is_bot):
        self.add_message_to_conversation(name=name, message=text, is_bot=is_bot)

    def on_add_bot_message_to_conversation(self, data: dict):
        name = data["name"]
        message = data["message"]
        is_first_message = data["is_first_message"]
        is_end_of_message = data["is_end_of_message"]
        if is_first_message:
            self.stop_progress_bar()

        self.add_message_to_conversation(
            name=name,
            message=message,
            is_bot=True, 
            first_message=is_first_message
        )

        if is_end_of_message:
            self.generating = False
            self.enable_send_button()

    @pyqtSlot()
    def action_button_clicked_clear_conversation(self):
        self.conversation_history = []
        for widget in self.ui.scrollAreaWidgetContents.findChildren(MessageWidget):
            widget.deleteLater()
        self.emit(SignalCode.CLEAR_LLM_HISTORY_SIGNAL)
    
    @pyqtSlot(bool)
    def action_button_clicked_send(self, _ignore):
        self.do_generate()

    def do_generate(self, image_override=None, prompt_override=None, callback=None, generator_name="casuallm"):
        if self.generating:
            self.logger.warning("Already generating")
            return
            
        self.generating = True
        self.disable_send_button()

        image = self.get_service(ServiceCode.CURRENT_ACTIVE_IMAGE)() if (image_override is None or image_override is False) else image_override

        prompt = self.prompt if (prompt_override is None or prompt_override == "") else prompt_override
        if prompt is None or prompt == "":
            self.logger.warning("Prompt is empty")
            return

        prompt_template = None
        template_name = self.settings["llm_generator_settings"]["prompt_template"]
        if template_name in self.settings["llm_templates"]:
            prompt_template = self.settings["llm_templates"][template_name]
        else:
            raise Exception("Prompt template not found for "+self.settings["llm_generator_settings"]["prompt_template"])

        llm_generator_settings = self.settings["llm_generator_settings"]

        parsed_template = self.parse_template(prompt_template)

        self.emit(
            SignalCode.TEXT_GENERATE_REQUEST_SIGNAL,
            {
                "llm_request": True,
                "request_data": {
                    "unload_unused_model": self.settings["memory_settings"]["unload_unused_models"],
                    "move_unused_model_to_cpu": self.settings["memory_settings"]["move_unused_model_to_cpu"],
                    "generator_name": generator_name,
                    "model_path": llm_generator_settings["model_version"],
                    "stream": True,
                    "prompt": prompt,
                    "do_summary": False,
                    "is_bot_alive": True,
                    "conversation_history": self.conversation_history,
                    "generator": self.settings["llm_generator_settings"],
                    "prefix": self.prefix,
                    "suffix": self.suffix,
                    "dtype": llm_generator_settings["dtype"],
                    "use_gpu": llm_generator_settings["use_gpu"],
                    "request_type": "image_caption_generator",
                    "username": self.settings["llm_generator_settings"]["username"],
                    "botname": self.settings["llm_generator_settings"]["botname"],
                    "prompt_template": parsed_template,
                    "hf_api_key_read_key": self.settings["hf_api_key_read_key"],
                    "parameters": {
                        "override_parameters": self.settings["llm_generator_settings"]["override_parameters"],
                        "top_p": llm_generator_settings["top_p"] / 100.0,
                        "max_length": llm_generator_settings["max_length"],
                        "repetition_penalty": llm_generator_settings["repetition_penalty"] / 100.0,
                        "min_length": llm_generator_settings["min_length"],
                        "length_penalty": llm_generator_settings["length_penalty"] / 100,
                        "num_beams": llm_generator_settings["num_beams"],
                        "ngram_size": llm_generator_settings["ngram_size"],
                        "temperature": llm_generator_settings["temperature"] / 10000.0,
                        "sequences": llm_generator_settings["sequences"],
                        "top_k": llm_generator_settings["top_k"],
                        "eta_cutoff": llm_generator_settings['eta_cutoff'] / 100.0,
                        "seed": llm_generator_settings["do_sample"],
                        "early_stopping": llm_generator_settings["early_stopping"],
                    },
                    "image": image,
                    "callback": callback,
                    "tts_settings": self.settings["tts_settings"],
                    "bot_mood": self.settings["llm_generator_settings"]["bot_mood"],
                    "bot_personality": self.settings["llm_generator_settings"]["bot_personality"],
                }
            }
        )
        self.add_message_to_conversation(
            name=self.settings["llm_generator_settings"]["username"],
            message=self.prompt, 
            is_bot=False
        )
        self.clear_prompt()
        self.start_progress_bar()

    def on_hear_signal(self, transcript):
        self.respond_to_voice(transcript)

    def on_token_signal(self, val):
        self.handle_token_signal(val)

    def showEvent(self, event):
        super().showEvent(event)
        self.register(SignalCode.HEAR_SIGNAL, self.on_hear_signal)
        self.register(SignalCode.TOKEN_SIGNAL, self.on_token_signal)
        self.register(SignalCode.ADD_BOT_MESSAGE_TO_CONVERSATION, self.on_add_bot_message_to_conversation)

        # handle return pressed on QPlainTextEdit
        # there is no returnPressed signal for QPlainTextEdit
        # so we have to use the keyPressEvent
        self.promptKeyPressEvent = self.ui.prompt.keyPressEvent
        self.originalKeyPressEvent = self.ui.prompt.keyPressEvent

        # Override the method
        self.ui.prompt.keyPressEvent = self.handle_key_press

        self.ui.conversation.hide()
        self.ui.chat_container.show()

    def prompt_text_changed(self):
        self.prompt = self.ui.prompt.toPlainText()

    def clear_prompt(self):
        self.ui.prompt.setPlainText("")

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

    def response_text_changed(self):
        pass

    def handle_key_press(self, event):
        if event.key() == Qt.Key.Key_Return:
            if event.modifiers() != Qt.KeyboardModifier.ShiftModifier:
                self.do_generate()
        # Call the original method
        self.originalKeyPressEvent(event)

    def hide_action_menu(self):
        self.action_menu_displayed = False
        self.ui.action_menu.hide()

    def display_action_menu(self):
        self.action_menu_displayed = True
        self.ui.action_menu.show()

    def insert_newline(self):
        self.ui.prompt.insertPlainText("\n")

    def respond_to_voice(self, transcript):
        transcript = transcript.strip()
        if transcript == "." or transcript is None or transcript == "":
            return
        self.do_generate(prompt_override=transcript)

    def parse_template(self, template):
        system_instructions = template["system_instructions"]
        model = template["model"]
        llm_category = template["llm_category"]
        template = template["template"]
        if llm_category == "casuallm":
            if model == "mistralai/Mistral-7B-Instruct-v0.1":
                return "\n".join((
                    "[INST]<<SYS>>",
                    system_instructions,# + "\nYou must say everything in Japanese with Japanese characters.",
                    "<</SYS>>",
                    template,
                    "[/INST]"
                ))
    
    def describe_image(self, image, callback):
        self.do_generate(
            image_override=image, 
            prompt_override="What is in this picture?",
            callback=callback,
            generator_name="visualqa"
        )
    
    def add_message_to_conversation(
        self,
        name,
        message,
        is_bot, 
        first_message=True
    ):
        if not first_message:
            # get the last widget from the scrollAreaWidgetContents.layout()
            # and append the message to it. must be a MessageWidget object
            # must start at the end of the layout and work backwards
            for i in range(self.ui.scrollAreaWidgetContents.layout().count()-1, -1, -1):
                current_widget = self.ui.scrollAreaWidgetContents.layout().itemAt(i).widget()
                if isinstance(current_widget, MessageWidget):
                    current_widget.update_message(message)
                    return

        widget = MessageWidget(name=name, message=message, is_bot=is_bot)
        if is_bot:
            # remove the last LoadingWidget from scrollAreaWidgetContents.layout()
            for i in range(self.ui.scrollAreaWidgetContents.layout().count()):
                current_widget = self.ui.scrollAreaWidgetContents.layout().itemAt(i).widget()
                if isinstance(current_widget, LoadingWidget):
                    self.ui.scrollAreaWidgetContents.layout().removeWidget(current_widget)
                    current_widget.deleteLater()
                    break

        self.ui.scrollAreaWidgetContents.layout().addWidget(widget)
        
        if self.spacer is not None:
            self.ui.scrollAreaWidgetContents.layout().removeItem(self.spacer)

        # if is not is_bot, then we want to add a widget that shows a
        # text icon
        if not is_bot:
            self.ui.scrollAreaWidgetContents.layout().addWidget(
                LoadingWidget()
            )

        # add a vertical spacer to self.ui.chat_container
        if self.spacer is None:
            self.spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self.ui.scrollAreaWidgetContents.layout().addItem(self.spacer)

    def message_type_text_changed(self, val):
        settings = self.settings
        settings["llm_generator_settings"]["message_type"] = val
        self.settings = settings

    def action_button_clicked_generate_characters(self):
        pass
