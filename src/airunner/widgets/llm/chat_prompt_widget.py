from PySide6.QtCore import Slot
from PySide6.QtWidgets import QSpacerItem, QSizePolicy
from PySide6.QtCore import Qt

from airunner.enums import SignalCode, ServiceCode, LLMActionType
from airunner.utils import parse_template
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
        self.messages_spacer = None

        self.ui.action.blockSignals(True)
        # iterate over each LLMActionType enum and add its value to the llm_tool_name
        for action_type in LLMActionType:
            self.ui.action.addItem(action_type.value)
        self.ui.action.setCurrentText(self.settings["llm_generator_settings"]["action"])
        self.ui.action.blockSignals(False)
        self.originalKeyPressEvent = None
        self.originalKeyPressEvent = self.ui.prompt.keyPressEvent
        self.vision_history = []
        self.register(SignalCode.VISION_PROCESSED_SIGNAL, self.on_vision_processed)
        self.register(SignalCode.AUDIO_PROCESSOR_RESPONSE_SIGNAL, self.on_hear_signal)
        self.held_message = None

    @property
    def current_generator(self):
        return self.settings["current_llm_generator"]
    
    @Slot(str)
    def handle_token_signal(self, val: str):
        if val != "[END]":
            text = self.ui.conversation.toPlainText()
            text += val
            self.ui.conversation.setText(text)
        else:
            self.stop_progress_bar()
            self.generating = False
            self.enable_send_button()

    def on_hear_signal(self, transcription):
        self.respond_to_voice(transcription)
        self.ui.prompt.setPlainText(transcription)

    def on_vision_processed(self, message):
        message = message.replace("this is an image of ", "")
        print(message)
        if message not in self.vision_history:
            self.vision_history.append(message)
        self.emit_signal(SignalCode.VISION_CAPTURE_UNPAUSE_SIGNAL)

    def on_add_to_conversation_signal(self, name, text, is_bot):
        self.add_message_to_conversation(name=name, message=text, is_bot=is_bot)

    def on_add_bot_message_to_conversation(self, data: dict):
        try:
            name = data["name"]
            message = data["message"]
            is_first_message = data["is_first_message"]
            is_end_of_message = data["is_end_of_message"]
        except TypeError as e:
            self.logger.error("Error parsing data: "+str(e))
            self.enable_generate()
            return

        if is_first_message:
            self.stop_progress_bar()

        self.add_message_to_conversation(
            name=name,
            message=message,
            is_bot=True, 
            first_message=is_first_message
        )

        if is_end_of_message:
            self.enable_generate()

    def enable_generate(self):
        self.generating = False
        if self.held_message is not None:
            self.do_generate(prompt_override=self.held_message)
            self.held_message = None
        self.enable_send_button()

    @Slot()
    def action_button_clicked_clear_conversation(self):
        self.conversation_history = []
        for widget in self.ui.scrollAreaWidgetContents.findChildren(MessageWidget):
            widget.deleteLater()
        self.emit_signal(SignalCode.LLM_CLEAR_HISTORY_SIGNAL)
    
    @Slot(bool)
    def action_button_clicked_send(self, _ignore):
        self.do_generate()

    def interrupt_button_clicked(self):
        self.emit_signal(SignalCode.INTERRUPT_PROCESS_SIGNAL)

    def do_generate(self, image_override=None, prompt_override=None, callback=None, generator_name="casuallm"):
        prompt = self.prompt if (prompt_override is None or prompt_override == "") else prompt_override

        if self.generating:
            if self.held_message is None:
                self.held_message = prompt
                self.disable_send_button()
                self.interrupt_button_clicked()
            return

        self.generating = True

        image = self.get_service(ServiceCode.CURRENT_ACTIVE_IMAGE)() if (image_override is None or image_override is False) else image_override

        if prompt is None or prompt == "":
            self.logger.warning("Prompt is empty")
            return

        current_bot_name = self.settings["llm_generator_settings"]["current_chatbot"]
        template_name = self.settings["llm_generator_settings"]["saved_chatbots"][current_bot_name]["prompt_template"]
        if template_name in self.settings["llm_templates"]:
            prompt_template = self.settings["llm_templates"][template_name]
        else:
            raise Exception("Prompt template not found for "+self.settings["llm_generator_settings"]["prompt_template"])

        llm_generator_settings = self.settings["llm_generator_settings"]

        #parsed_template = parse_template(prompt_template)

        current_bot = self.settings["llm_generator_settings"]["saved_chatbots"][self.settings["llm_generator_settings"]["current_chatbot"]]
        self.emit_signal(
            SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL,
            {
                "llm_request": True,
                "request_data": {
                    "action": self.settings["llm_generator_settings"]["action"],
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
                    "template": "",
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
                        "early_stopping": llm_generator_settings["early_stopping"]
                    },
                    "image": image,
                    "callback": callback,
                    "tts_settings": self.settings["tts_settings"],
                    "username": current_bot["username"],
                    "botname": current_bot["botname"],
                    "use_personality": current_bot["use_personality"],
                    "use_mood": current_bot["use_mood"],
                    "use_guardrails": current_bot["use_guardrails"],
                    "use_system_instructions": current_bot["use_system_instructions"],
                    "assign_names": current_bot["assign_names"],
                    "bot_personality": current_bot["bot_personality"],
                    "bot_mood": current_bot["bot_mood"],
                    "prompt_template": current_bot["prompt_template"],
                    "guardrails_prompt": current_bot["guardrails_prompt"],
                    "system_instructions": current_bot["system_instructions"],
                    "vision_history": self.vision_history,
                }
            }
        )
        self.add_message_to_conversation(
            name=current_bot["username"],
            message=self.prompt, 
            is_bot=False
        )
        self.clear_prompt()
        self.start_progress_bar()

    def on_token_signal(self, val):
        self.handle_token_signal(val)

    registered = False

    def showEvent(self, event):
        super().showEvent(event)
        if not self.registered:
            self.register(SignalCode.STT_HEAR_SIGNAL, self.on_hear_signal)
            self.register(SignalCode.LLM_TOKEN_SIGNAL, self.on_token_signal)
            self.register(SignalCode.APPLICATION_ADD_BOT_MESSAGE_TO_CONVERSATION, self.on_add_bot_message_to_conversation)
            self.registered = True

        # handle return pressed on QPlainTextEdit
        # there is no returnPressed signal for QPlainTextEdit
        # so we have to use the keyPressEvent
        self.promptKeyPressEvent = self.ui.prompt.keyPressEvent

        # Override the method
        self.ui.prompt.keyPressEvent = self.handle_key_press

        self.ui.conversation.hide()
        self.ui.chat_container.show()

    def llm_action_changed(self, val: str):
        settings = self.settings
        print("SETTING LLM ACTION TO ", val)
        settings["llm_generator_settings"]["action"] = val
        self.settings = settings

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
                return
        # Call the original method
        if self.originalKeyPressEvent is not None and self.originalKeyPressEvent != self.handle_key_press:
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

        # if self.messages_spacer is not None:
        #     self.ui.scrollAreaWidgetContents.layout().removeItem(self.messages_spacer)

        self.ui.scrollAreaWidgetContents.layout().addWidget(widget)

        # if self.messages_spacer is None:
        #     self.messages_spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        # self.ui.scrollAreaWidgetContents.layout().addItem(self.messages_spacer)
        
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

    def scroll_to_bottom(self):
        self.ui.scrollAreaWidgetContents.verticalScrollBar().setValue(
            self.ui.scrollAreaWidgetContents.verticalScrollBar().maximum()
        )