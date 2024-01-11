from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QSpacerItem, QSizePolicy

from airunner.aihandler.enums import MessageCode
from airunner.data.models import Conversation, LLMPromptTemplate, Message
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.llm.templates.chat_prompt_ui import Ui_chat_prompt
from airunner.widgets.llm.message_widget import MessageWidget
from airunner.data.session_scope import session_scope
from airunner.aihandler.logger import Logger


class ChatPromptWidget(BaseWidget):
    widget_class_ = Ui_chat_prompt
    conversation = None
    is_modal = True
    generating = False
    prefix = ""
    prompt = ""
    suffix = ""
    conversation_history = []
    spacer = None

    @property
    def llm_generator(self):
        try:
            return self.app.settings_manager.llm_generator
        except Exception as e:
            Logger.error(e)
            import traceback
            traceback.print_exc()
    
    @property
    def llm_generator_settings(self):
        try:
            return self.app.settings_manager.llm_generator_settings
        except Exception as e:
            Logger.error(e)

    @property
    def instructions(self):
        return f"{self.llm_generator.botname} loves {self.llm_generator.username}. {self.llm_generator.botname} is very nice. {self.llm_generator.botname} uses compliments, kind responses, and nice words. Everything {self.llm_generator.botname} says is nice. {self.llm_generator.botname} is kind."

    @property
    def current_generator(self):
        return self.app.current_llm_generator

    @property
    def instructions(self):
        return f"{self.llm_generator.botname} loves {self.llm_generator.username}. {self.llm_generator.botname} is very nice. {self.llm_generator.botname} uses compliments, kind responses, and nice words. Everything {self.llm_generator.botname} says is nice. {self.llm_generator.botname} is kind."

    def load_data(self):
        with session_scope() as session:
            self.conversation = session.query(Conversation).first()
            if self.conversation is None:
                self.conversation = Conversation()
                session.add(self.conversation)

    def initialize(self):
        self.load_data()

        self.app.token_signal.connect(self.handle_token_signal)
        self.app.message_var.my_signal.connect(self.message_handler)
        self.ui.prompt.returnPressed.connect(self.action_button_clicked_send)
        self.ui.prompt.textChanged.connect(self.prompt_text_changed)
        self.ui.conversation.hide()
        self.ui.chat_container.show()

        self.ui.username.blockSignals(True)
        self.ui.botname.blockSignals(True)
        self.ui.username.setText(self.llm_generator.username)
        self.ui.botname.setText(self.llm_generator.botname)
        self.ui.username.blockSignals(False)
        self.ui.botname.blockSignals(False)
    
    def handle_token_signal(self, val):
        if val != "[END]":
            text = self.ui.conversation.toPlainText()
            text += val
            self.ui.conversation.setText(text)
        else:
            self.stop_progress_bar()
            self.generating = False
            self.enable_send_button()

    @pyqtSlot(dict)
    def message_handler(self, response: dict):
        try:
            code = response["code"]
        except TypeError:
            return
        message = response["message"]

        if code == MessageCode.TEXT_GENERATED:
            self.handle_text_generated(message)

    def handle_text_generated(self, message):
        self.stop_progress_bar()

        # # check if messages is string or list
        # if isinstance(messages, str):
        #     messages = [messages]
        
        # #print("MESSAGES", messages)
            
        # if messages is None:
        #     return

        # # get last message
        # message = messages[-1]["content"]

        # strip quotes from start and end of message
        if not message:
            return
        if message.startswith("\""):
            message = message[1:]
        if message.endswith("\""):
            message = message[:-1]
        message_object = Message(
            name=self.llm_generator.botname,
            message=message,
            conversation=self.conversation
        )
        with session_scope() as session:
            session.add(message_object)

        if self.app.enable_tts:
            # split on sentence enders
            sentence_enders = [".", "?", "!", "\n"]
            text = message_object.message
            sentences = []
            # split text into sentences
            current_sentence = ""
            for char in text:
                current_sentence += char
                if char in sentence_enders:
                    sentences.append(current_sentence)
                    current_sentence = ""
            if current_sentence != "":
                sentences.append(current_sentence)

            for index, sentence in enumerate(sentences):
                sentence = sentence.strip()
                self.app.client.message = dict(
                    tts_request=True,
                    request_data=dict(
                        text=sentence,
                        message_object=Message(
                            name=message_object.name,
                            message=sentence,
                        ),
                        is_bot=True,
                        callback=self.add_message_to_conversation,
                        first_message=index == 0,
                        last_message=index == len(sentences) - 1,
                    )
                )

        self.add_message_to_conversation(message_object, is_bot=True)

        self.generating = False
        self.enable_send_button()

    def prompt_text_changed(self, val):
        self.prompt = val

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

    def response_text_changed(self):
        pass

    def parent(self):
        return self.app.ui.llm_widget

    def action_button_clicked_send(self, image_override=None, prompt_override=None, callback=None, generator_name="casuallm"):
        if self.generating:
            Logger.warning("Already generating")
            return
            
        self.generating = True
        self.disable_send_button()
        #user_input = f"{self.llm_generator.username} Says: \"{self.prompt}\""
        # conversation = "\n".join(self.conversation_history)
        # suffix = "\n".join([self.suffix, f'{self.llm_generator.botname} Says: '])
        # prompt = "\n".join([self.instructions, self.prefix, conversation, input, suffix])

        image = self.app.current_active_image() if (image_override is None or image_override is False) else image_override

        prompt = self.prompt if (prompt_override is None or prompt_override == "") else prompt_override
        if prompt is None or prompt == "":
            Logger.warning("Prompt is empty")
            return

        with session_scope() as session:
            prompt_template = session.query(LLMPromptTemplate).filter(
                LLMPromptTemplate.name == self.llm_generator.prompt_template
            ).first()

            llm_generator_settings = self.app.llm_generator_settings

            data = {
                "llm_request": True,
                "request_data": {
                    "unload_unused_model": self.app.unload_unused_models,
                    "move_unused_model_to_cpu": self.app.move_unused_model_to_cpu,
                    "generator_name": generator_name,
                    "model_path": llm_generator_settings["model_version"],
                    "stream": True,
                    "prompt": prompt,
                    "do_summary": False,
                    "is_bot_alive": True,
                    "conversation_history": self.conversation_history,
                    "generator": self.llm_generator,
                    "prefix": self.prefix,
                    "suffix": self.suffix,
                    "dtype": llm_generator_settings["dtype"],
                    "use_gpu": llm_generator_settings["use_gpu"],
                    "request_type": "image_caption_generator",
                    "username": self.llm_generator.username,
                    "botname": self.llm_generator.botname,
                    "prompt_template": prompt_template.template,
                    "hf_api_key_read_key": self.app.hf_api_key_read_key,
                    "parameters": {
                        "override_parameters": self.llm_generator.override_parameters,
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
                    "callback": callback
                }
            }
            print(data)
            message_object = Message(
                name=self.llm_generator.username,
                message=self.prompt,
                conversation=self.conversation
            )
            session.add(message_object)
            self.app.client.message = data
            self.add_message_to_conversation(message_object=message_object, is_bot=False)
            self.clear_prompt()
            self.start_progress_bar()
    
    def describe_image(self, image, callback):
        self.action_button_clicked_send(
            image_override=image, 
            prompt_override="What is in this picture?",
            callback=callback,
            generator_name="visualqa"
        )

    def add_message_to_conversation(self, message_object, is_bot, first_message=True, last_message=True):
        # remove spacer from self.ui.chat_container
        widget = MessageWidget(message=message_object, is_bot=is_bot)
        self.ui.scrollAreaWidgetContents.layout().addWidget(widget)
        
        if self.spacer is not None:
            self.ui.scrollAreaWidgetContents.layout().removeItem(self.spacer)

        message = ""
        if first_message:
            message = f"{message_object.name} Says: \""
        message += message_object.message
        if last_message:
            message += "\""

        if first_message:
            self.conversation_history.append(message)
        if not first_message:
            self.conversation_history[-1] += message
            self.ui.conversation.undo()
        self.ui.conversation.append(self.conversation_history[-1])

        # add a vertical spacer to self.ui.chat_container
        if self.spacer is None:
            self.spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self.ui.scrollAreaWidgetContents.layout().addItem(self.spacer)

    def action_button_clicked_clear_conversation(self):
        self.conversation_history = []
        self.ui.conversation.setText("")
        self.app.client.message = {
            "llm_request": True,
            "request_data": {
                "request_type": "clear_conversation",
            }
        }
    
    def message_type_text_changed(self, val):
        with session_scope() as session:
            session.add(self.llm_generator)
            self.llm_generator.message_type = val

    def action_button_clicked_generate_characters(self):
        pass
    
    def prefix_text_changed(self):
        with session_scope() as session:
            session.add(self.llm_generator)
            self.llm_generator.prefix = self.ui.prefix.toPlainText()

    def suffix_text_changed(self):
        with session_scope() as session:
            session.add(self.llm_generator)
            self.llm_generator.suffix = self.ui.suffix.toPlainText()

    def username_text_changed(self, val):
        with session_scope() as session:
            session.add(self.llm_generator)
            self.app.settings_manager.set_value("llm_generator.username", val)
        
    def botname_text_changed(self, val):
        with session_scope() as session:
            session.add(self.llm_generator)
            self.app.settings_manager.set_value("llm_generator.botname", val)
