from PySide6.QtCore import Slot
from PySide6.QtWidgets import QSpacerItem, QSizePolicy
from PySide6.QtCore import Qt
from airunner.enums import SignalCode, LLMActionType
from airunner.exceptions import PromptTemplateNotFoundExeption
from airunner.utils.convert_base64_to_image import convert_base64_to_image
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.canvas.custom_scene import CustomScene
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
        self.ui.action.setCurrentText(self.action)
        self.ui.action.blockSignals(False)
        self.originalKeyPressEvent = None
        self.originalKeyPressEvent = self.ui.prompt.keyPressEvent
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
            self.ui.conversation.setPlainText(text)
        else:
            self.stop_progress_bar()
            self.generating = False
            self.enable_send_button()

    def on_hear_signal(self, data: dict):
        transcription = data["transcription"]
        self.respond_to_voice(transcription)
        self.ui.prompt.setPlainText(transcription)

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
    def action_button_clicked_send(self):
        self.do_generate()

    def interrupt_button_clicked(self):
        self.emit_signal(SignalCode.INTERRUPT_PROCESS_SIGNAL)

    @property
    def current_active_scene(self) -> CustomScene:
        return

    @property
    def llm_generator_settings(self):
        return self.settings["llm_generator_settings"]

    @property
    def action(self) -> str:
        return self.llm_generator_settings["action"]

    @property
    def chatbot_name(self) -> str:
        if self.action == LLMActionType.APPLICATION_COMMAND:
            chatbot_name = "Agent"
        elif self.action == LLMActionType.CHAT:
            chatbot_name = "Chatbot"
        else:
            chatbot_name = self.llm_generator_settings["current_chatbot"]
        return chatbot_name

    def do_generate(self, image_override=None, prompt_override=None, callback=None, generator_name="causallm"):
        prompt = self.prompt if (prompt_override is None or prompt_override == "") else prompt_override
        if prompt is None or prompt == "":
            self.logger.warning("Prompt is empty")
            return

        if self.generating:
            if self.held_message is None:
                self.held_message = prompt
                self.disable_send_button()
                self.interrupt_button_clicked()
            return
        self.generating = True

        current_bot = self.settings["llm_generator_settings"]["saved_chatbots"][self.settings["llm_generator_settings"]["current_chatbot"]]
        self.add_message_to_conversation(
            name=current_bot["username"],
            message=self.prompt,
            is_bot=False
        )

        self.clear_prompt()
        self.start_progress_bar()
        self.emit_signal(
            SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL,
            {
                "llm_request": True,
                "request_data": {
                    "action": self.action,
                    "prompt": prompt,
                }
            }
        )

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

    def respond_to_voice(self, transcript: str):
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

    def add_loading_widget(self):
        self.ui.scrollAreaWidgetContents.layout().addWidget(
            LoadingWidget()
        )

    def remove_loading_widget(self):
        # remove the last LoadingWidget from scrollAreaWidgetContents.layout()
        for i in range(self.ui.scrollAreaWidgetContents.layout().count()):
            current_widget = self.ui.scrollAreaWidgetContents.layout().itemAt(i).widget()
            if isinstance(current_widget, LoadingWidget):
                self.ui.scrollAreaWidgetContents.layout().removeWidget(current_widget)
                current_widget.deleteLater()
                break

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
            for i in range(self.ui.scrollAreaWidgetContents.layout().count() - 1, -1, -1):
                current_widget = self.ui.scrollAreaWidgetContents.layout().itemAt(i).widget()
                if isinstance(current_widget, MessageWidget):
                    if current_widget.is_bot:
                        if message != "":
                            current_widget.update_message(message)
                        self.scroll_to_bottom()
                        return
                    break

        self.remove_spacer()

        if is_bot:
            self.remove_loading_widget()

        if message != "":
            widget = MessageWidget(name=name, message=message, is_bot=is_bot)
            self.ui.scrollAreaWidgetContents.layout().addWidget(widget)

        if not is_bot:
            self.add_loading_widget()

        self.add_spacer()

        # automatically scroll to the bottom of the scrollAreaWidgetContents
        self.scroll_to_bottom()

    def remove_spacer(self):
        if self.spacer is not None:
            self.ui.scrollAreaWidgetContents.layout().removeItem(self.spacer)

    def add_spacer(self):
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
        self.ui.chat_container.verticalScrollBar().setValue(
            self.ui.chat_container.verticalScrollBar().maximum()
        )
