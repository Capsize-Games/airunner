from PyQt6.QtCore import pyqtSlot, pyqtSignal
from PyQt6.QtWidgets import QSpacerItem, QSizePolicy
from PyQt6.QtCore import Qt

from airunner.aihandler.enums import MessageCode
from airunner.data.models import LLMPromptTemplate
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.llm.loading_widget import LoadingWidget
from airunner.widgets.llm.templates.chat_prompt_ui import Ui_chat_prompt
from airunner.widgets.llm.message_widget import MessageWidget
from airunner.data.session_scope import session_scope
from airunner.aihandler.logger import Logger


class Message:
    def __init__(self, *args, **kwargs):
        self.name = kwargs.get("name")
        self.message = kwargs.get("message")
        self.conversation = kwargs.get("conversation")


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
    promptKeyPressEvent = None
    add_message_signal = pyqtSignal(Message, bool, bool, bool)

    @property
    def llm_generator(self):
        return self.app.settings["llm_generator_settings"]
    
    @property
    def llm_generator_settings(self):
        try:
            return self.app.settings_manager.llm_generator_settings
        except Exception as e:
            Logger.error(e)

    @property
    def current_generator(self):
        return self.app.settings["current_llm_generator"]
    
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

    @pyqtSlot(Message, bool, bool, bool)
    def add_bot_message_to_conversation(self, message_object, is_bot, first_message=True, last_message=True):
        if first_message:
            self.stop_progress_bar()

        self.add_message_to_conversation(message_object, is_bot, first_message, last_message)

        if last_message:
            self.generating = False
            self.enable_send_button()

    @pyqtSlot()
    def action_button_clicked_clear_conversation(self):
        self.conversation_history = []
        for widget in self.ui.scrollAreaWidgetContents.findChildren(MessageWidget):
            widget.deleteLater()
        self.app.client.engine.clear_llm_history()

    @pyqtSlot(dict)
    def message_handler(self, response: dict):
        try:
            code = response["code"]
        except TypeError:
            return
        message = response["message"]

        if code == MessageCode.ADD_TO_CONVERSATION:
            self.handle_text_generated(message)
    
    @pyqtSlot()
    def action_button_clicked_send(self, image_override=None, prompt_override=None, callback=None, generator_name="casuallm"):
        if self.generating:
            Logger.warning("Already generating")
            return
            
        self.generating = True
        self.disable_send_button()

        image = self.app.current_active_image() if (image_override is None or image_override is False) else image_override

        prompt = self.prompt if (prompt_override is None or prompt_override == "") else prompt_override
        if prompt is None or prompt == "":
            Logger.warning("Prompt is empty")
            return

        with session_scope() as session:
            prompt_template = session.query(LLMPromptTemplate).filter(
                LLMPromptTemplate.name == self.app.settings["llm_generator_settings"]["prompt_template"]
            ).first()
            if prompt_template is None:
                raise Exception("Prompt template not found for "+self.app.settings["llm_generator_settings"]["prompt_template"])

            llm_generator_settings = self.app.settings["llm_generator_settings"]

            parsed_template = self.parse_template(prompt_template)

            data = {
                "llm_request": True,
                "request_data": {
                    "unload_unused_model": self.app.settings["memory_settings"]["unload_unused_models"],
                    "move_unused_model_to_cpu": self.app.settings["memory_settings"]["move_unused_model_to_cpu"],
                    "generator_name": generator_name,
                    "model_path": llm_generator_settings["model_version"],
                    "stream": True,
                    "prompt": prompt,
                    "do_summary": False,
                    "is_bot_alive": True,
                    "conversation_history": self.conversation_history,
                    "generator": self.app.settings["llm_generator_settings"],
                    "prefix": self.prefix,
                    "suffix": self.suffix,
                    "dtype": llm_generator_settings["dtype"],
                    "use_gpu": llm_generator_settings["use_gpu"],
                    "request_type": "image_caption_generator",
                    "username": self.app.settings["llm_generator_settings"]["username"],
                    "botname": self.app.settings["llm_generator_settings"]["botname"],
                    "prompt_template": parsed_template,
                    "hf_api_key_read_key": self.app.settings["hf_api_key_read_key"],
                    "parameters": {
                        "override_parameters": self.app.settings["llm_generator_settings"]["override_parameters"],
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
                    "tts_settings": self.app.settings["tts_settings"],
                    "bot_mood": self.app.settings["llm_generator_settings"]["bot_mood"],
                    "bot_personality": self.app.settings["llm_generator_settings"]["bot_personality"],
                }
            }
        message_object = Message(
            name=self.app.settings["llm_generator_settings"]["username"],
            message=self.prompt,
            conversation=self.conversation
        )
        self.app.client.message = data
        self.add_message_to_conversation(message_object=message_object, is_bot=False)
        self.clear_prompt()
        self.start_progress_bar()
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_message_signal.connect(self.add_bot_message_to_conversation)

    def initialize(self):
        self.app.token_signal.connect(self.handle_token_signal)
        self.app.message_var.my_signal.connect(self.message_handler)

        # handle return pressed on QPlainTextEdit
        # there is no returnPressed signal for QPlainTextEdit
        # so we have to use the keyPressEvent
        self.promptKeyPressEvent = self.ui.prompt.keyPressEvent
        self.ui.prompt.keyPressEvent = self.handle_key_press

        self.ui.prompt.textChanged.connect(self.prompt_text_changed)
        self.ui.conversation.hide()
        self.ui.chat_container.show()

    def handle_text_generated(self, message):
        name = message["name"]
        self.add_message_signal.emit(Message(
            name=name,
            message=message["text"],
            conversation=self.conversation
        ), 
        message["is_bot"], 
        message["first_message"],
        message["last_message"])

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

    def parent(self):
        return self.app.ui.llm_widget

    def handle_key_press(self, event):
        # check if return pressed. if shift return pressed call insert_newline
        # else call action_butjton_clicked_send()
        if event.key() == Qt.Key.Key_Return:
            if event.modifiers() != Qt.KeyboardModifier.ShiftModifier:
                self.action_button_clicked_send()
                return
        #else:
            # check if the user has pressed the action key.
            # if there are no other characters in self.ui.prompt then we
            # display the action menu.
            # key_name = "llm_action_key"
            # if event.key() == self.app.key_matches(key_name, event.key()):
            #     text = self.ui.prompt.toPlainText()
            #     if not self.action_menu_displayed and (
            #         len(text) == 0 or text == self.app.key_text(key_name)
            #     ):
            #         self.display_action_menu()

        # handle the keypress normally. There is no super() call because
        # we are overriding the keyPressEvent
        self.promptKeyPressEvent(event)

    def hide_action_menu(self):
        self.action_menu_displayed = False
        self.ui.action_menu.hide()

    def display_action_menu(self):
        self.action_menu_displayed = True
        self.ui.action_menu.show()

    def insert_newline(self):
        self.ui.prompt.insertPlainText("\n")

    def respond_to_voice(self, heard):
        self.action_button_clicked_send(prompt_override=heard)

    def parse_template(self, template):
        system_instructions = template.system_instructions
        model = template.model
        llm_category = template.llm_category
        template = template.template
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
        self.action_button_clicked_send(
            image_override=image, 
            prompt_override="What is in this picture?",
            callback=callback,
            generator_name="visualqa"
        )
    
    def add_message_to_conversation(self, message_object, is_bot, first_message=True, last_message=True):
        if not first_message:
            # get the last widget from the scrollAreaWidgetContents.layout()
            # and append the message to it. must be a MessageWidget object
            # must start at the end of the layout and work backwards
            for i in range(self.ui.scrollAreaWidgetContents.layout().count()-1, -1, -1):
                current_widget = self.ui.scrollAreaWidgetContents.layout().itemAt(i).widget()
                if isinstance(current_widget, MessageWidget):
                    current_widget.update_message(message_object.message)
                    return

        widget = MessageWidget(message=message_object, is_bot=is_bot)
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
        with session_scope() as session:
            session.add(self.app.settings["llm_generator_settings"])
            self.app.settings["llm_generator_settings"]["message_type"] = val

    def action_button_clicked_generate_characters(self):
        pass
