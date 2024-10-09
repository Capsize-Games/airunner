from PySide6.QtCore import Slot, QTimer
from PySide6.QtWidgets import QSpacerItem, QSizePolicy
from PySide6.QtCore import Qt

from airunner.enums import SignalCode, LLMActionType, ModelType, ModelStatus
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
        self.chat_loaded = False
        self.conversation_id = None

        self.ui.action.blockSignals(True)
        self.ui.action.addItem("Auto")
        self.ui.action.addItem("Chat")
        self.ui.action.addItem("Image")
        action = LLMActionType[self.action]
        if action is LLMActionType.APPLICATION_COMMAND:
            self.ui.action.setCurrentIndex(0)
        elif action is LLMActionType.CHAT:
            self.ui.action.setCurrentIndex(1)
        elif action is LLMActionType.GENERATE_IMAGE:
            self.ui.action.setCurrentIndex(2)
        self.ui.action.blockSignals(False)
        self.originalKeyPressEvent = None
        self.originalKeyPressEvent = self.ui.prompt.keyPressEvent
        self.register(SignalCode.AUDIO_PROCESSOR_RESPONSE_SIGNAL, self.on_hear_signal)
        self.register(SignalCode.SET_CONVERSATION, self.on_set_conversation)
        self.register(SignalCode.MODEL_STATUS_CHANGED_SIGNAL, self.on_model_status_changed_signal)
        self.register(SignalCode.CHATBOT_CHANGED, self.on_chatbot_changed)
        self.register(SignalCode.CONVERSATION_DELETED, self.on_conversation_deleted)
        self.held_message = None
        self._disabled = False

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

    def on_model_status_changed_signal(self, data):
        if data["model"] == ModelType.LLM:
            self.chat_loaded = data["status"] is ModelStatus.LOADED

        if not self.chat_loaded:
            self.disable_send_button()
        else:
            self.enable_send_button()

    def on_chatbot_changed(self):
        self._clear_conversation()

    def on_conversation_deleted(self, data):
        if self.conversation_id == data["conversation_id"]:
            self.conversation_id = None
            self._clear_conversation()

    def on_set_conversation(self, message):
        self._clear_conversation_widgets()
        if len(message["messages"]) > 0:
            self.conversation_id = message["messages"][0]["conversation_id"]
        QTimer.singleShot(0, lambda: self._set_conversation_widgets(message["messages"]))

    def _set_conversation_widgets(self, messages):
        for message in messages:
            self.add_message_to_conversation(
                name=message["name"],
                message=message["content"],
                is_bot=message["is_bot"],
                first_message=True,
                use_loading_widget=False
            )

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
        self._clear_conversation()

    def _clear_conversation(self):
        self.conversation_history = []
        self._clear_conversation_widgets()
        self._create_conversation()

    def _create_conversation(self):
        conversation_id = self.db_handler.create_conversation()
        self.emit_signal(SignalCode.LLM_CLEAR_HISTORY_SIGNAL, {
            "conversation_id": conversation_id
        })
        self.conversation_id = conversation_id

    def _clear_conversation_widgets(self):
        for widget in self.ui.scrollAreaWidgetContents.findChildren(MessageWidget):
            widget.deleteLater()
    
    @Slot(bool)
    def action_button_clicked_send(self):
        self.do_generate()

    def interrupt_button_clicked(self):
        self.emit_signal(SignalCode.INTERRUPT_PROCESS_SIGNAL)

    @property
    def action(self) -> str:
        return self.llm_generator_settings.action

    def do_generate(self, image_override=None, prompt_override=None, callback=None, generator_name="causallm"):
        if self.conversation_id is None:
            self._create_conversation()
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

        self.add_message_to_conversation(
            name=self.chatbot.username,
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
            self.register(SignalCode.LLM_TOKEN_SIGNAL, self.on_token_signal)
            self.register(SignalCode.LLM_TEXT_STREAMED_SIGNAL, self.on_add_bot_message_to_conversation)
            self.register(SignalCode.MODEL_STATUS_CHANGED_SIGNAL, self.on_model_status_changed)
            self.registered = True

        # handle return pressed on QPlainTextEdit
        # there is no returnPressed signal for QPlainTextEdit
        # so we have to use the keyPressEvent
        self.promptKeyPressEvent = self.ui.prompt.keyPressEvent

        # Override the method
        self.ui.prompt.keyPressEvent = self.handle_key_press

        if not self.chat_loaded:
            self.disable_send_button()

        self.ui.conversation.hide()
        self.ui.chat_container.show()

    def on_model_status_changed(self, data):
        if data["model"] == ModelType.LLM:
            if data["status"] is ModelStatus.LOADED:
                self.enable_send_button()
            else:
                self.disable_send_button()

    def llm_action_changed(self, val: str):
        if val == "Chat":
            llm_action_value = LLMActionType.CHAT
        elif val == "Image":
            llm_action_value = LLMActionType.GENERATE_IMAGE
        else:
            llm_action_value = LLMActionType.APPLICATION_COMMAND
        self.update_llm_generator_settings("action", llm_action_value.name)

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
        self._disabled = True

    def enable_send_button(self):
        self.ui.send_button.setEnabled(True)
        self._disabled = False

    def response_text_changed(self):
        pass

    def handle_key_press(self, event):
        if event.key() == Qt.Key.Key_Return:
            if not self._disabled and event.modifiers() != Qt.KeyboardModifier.ShiftModifier:
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
        first_message=True,
        use_loading_widget=True
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

        if is_bot and use_loading_widget:
            self.remove_loading_widget()

        if message != "":
            widget = MessageWidget(name=name, message=message, is_bot=is_bot)
            self.ui.scrollAreaWidgetContents.layout().addWidget(widget)

        if not is_bot and use_loading_widget:
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
        self.update_llm_generator_settings("message_type", val)

    def action_button_clicked_generate_characters(self):
        pass

    def scroll_to_bottom(self):
        self.ui.chat_container.verticalScrollBar().setValue(
            self.ui.chat_container.verticalScrollBar().maximum()
        )
