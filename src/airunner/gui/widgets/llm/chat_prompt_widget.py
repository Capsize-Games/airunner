import json
import queue

from typing import Dict, Optional

from PySide6.QtCore import Slot, QTimer, QPropertyAnimation
from PySide6.QtWidgets import QSpacerItem, QSizePolicy
from PySide6.QtCore import Qt

from airunner.enums import (
    SignalCode,
    LLMActionType,
    ModelType,
    ModelStatus,
)
from airunner.gui.widgets.base_widget import BaseWidget
from airunner.gui.widgets.llm.templates.chat_prompt_ui import Ui_chat_prompt
from airunner.gui.widgets.llm.message_widget import MessageWidget
from airunner.data.models import Conversation
from airunner.utils.llm.strip_names_from_message import (
    strip_names_from_message,
)
from airunner.utils import create_worker
from airunner.handlers.llm.llm_request import LLMRequest
from airunner.handlers.llm.llm_response import LLMResponse
from airunner.workers.llm_response_worker import LLMResponseWorker
from airunner.settings import AIRUNNER_ART_ENABLED


class ChatPromptWidget(BaseWidget):
    widget_class_ = Ui_chat_prompt
    icons = [
        ("corner-down-left", "send_button"),
        ("file-plus", "clear_conversation_button"),
        ("stop-circle", "pushButton"),
    ]

    def __init__(self, *args, **kwargs):
        self.signal_handlers = {
            SignalCode.AUDIO_PROCESSOR_RESPONSE_SIGNAL: self.on_hear_signal,
            SignalCode.SET_CONVERSATION: self.on_set_conversation,
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL: self.on_model_status_changed_signal,
            SignalCode.CHATBOT_CHANGED: self.on_chatbot_changed,
            SignalCode.CONVERSATION_DELETED: self.on_delete_conversation,
            SignalCode.LLM_CLEAR_HISTORY_SIGNAL: self.on_clear_conversation,
            SignalCode.LOAD_CONVERSATION: self.on_load_conversation,
            SignalCode.LLM_TOKEN_SIGNAL: self.on_token_signal,
            SignalCode.LLM_TEXT_STREAMED_SIGNAL: self.on_add_bot_message_to_conversation,
        }
        self._splitters = ["chat_prompt_splitter"]
        super().__init__()
        self.token_buffer = []
        self.ui_update_timer = QTimer(self)
        self.ui_update_timer.setInterval(50)
        self.ui_update_timer.timeout.connect(self.flush_token_buffer)
        self.ui_update_timer.start()
        self.registered: bool = False
        self.scroll_bar = None
        self.is_modal = True
        self.generating = False
        self.prefix = ""
        self.prompt = ""
        self.suffix = ""
        self.spacer = None
        self.promptKeyPressEvent = None
        self.originalKeyPressEvent = None
        self.action_menu_displayed = None
        self.action_menu_displayed = None
        self.messages_spacer = None
        self.chat_loaded = False
        self._conversation: Optional[Conversation] = None
        self._conversation_id: Optional[int] = None
        self.conversation_history = []

        self.ui.action.blockSignals(True)
        self.ui.action.addItem("Auto")
        self.ui.action.addItem("Chat")
        self.ui.action.addItem("RAG")

        if AIRUNNER_ART_ENABLED:
            self.ui.action.addItem("Image")

        action = self.action
        if action is LLMActionType.APPLICATION_COMMAND:
            self.ui.action.setCurrentIndex(0)
        elif action is LLMActionType.CHAT:
            self.ui.action.setCurrentIndex(1)
        elif action is LLMActionType.GENERATE_IMAGE:
            self.ui.action.setCurrentIndex(2)
        elif action is LLMActionType.PERFORM_RAG_SEARCH:
            self.ui.action.setCurrentIndex(3)
        elif action is LLMActionType.STORE_DATA:
            self.ui.action.setCurrentIndex(4)
        self.ui.action.blockSignals(False)
        self.originalKeyPressEvent = None
        self.originalKeyPressEvent = self.ui.prompt.keyPressEvent
        self.held_message = None
        self._disabled = False
        self.scroll_animation = None
        self._llm_response_worker = create_worker(
            LLMResponseWorker, sleep_time_in_ms=1
        )
        self.load_conversation()

    @property
    def conversation(self) -> Optional[Conversation]:
        return self._conversation

    @conversation.setter
    def conversation(self, val: Optional[Conversation]):
        self._conversation = val
        self._conversation_id = val.id if val else None

    @property
    def conversation_id(self) -> Optional[int]:
        return self._conversation_id

    @conversation_id.setter
    def conversation_id(self, val: Optional[int]):
        self._conversation_id = val
        if val:
            self._conversation = Conversation.objects.filter_by_first(id=val)
        else:
            self._conversation = None

    def on_load_conversation(self, data):
        self.load_conversation(data["conversation_id"])

    def on_delete_conversation(self, data):
        if (
            self.conversation_id == data["conversation_id"]
            or self.conversation_id is None
        ):
            self._clear_conversation_widgets()
        self.conversation = None

    def load_conversation(self, index: Optional[int] = None):
        conversation = None
        if index is not None:
            conversation = Conversation.objects.get(index)

        if conversation is None:
            conversation = Conversation.objects.order_by(
                Conversation.id.desc()
            ).first()
        if conversation is not None:
            self.conversation = conversation
            self.api.llm.clear_history(conversation_id=self.conversation_id)
            self.on_clear_conversation()
            self._set_conversation_widgets(
                [
                    {
                        "name": (
                            self.user.username
                            if message["role"] == "user"
                            else self.chatbot.name
                        ),
                        "content": message["blocks"][0]["text"],
                        "is_bot": message["role"] == "assistant",
                        "id": message_id,
                    }
                    for message_id, message in enumerate(
                        self.conversation.value or []
                    )
                ]
            )

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
        self.api.llm.clear_history()
        self.on_clear_conversation()

    def on_set_conversation(self, message):
        self._clear_conversation_widgets()
        if len(message["messages"]) > 0:
            conversation_id = message["messages"][0]["conversation_id"]
            self.conversation = Conversation.objects.filter_by_first(
                id=conversation_id
            )
        self._set_conversation_widgets(
            [
                {
                    "name": message["additional_kwargs"]["name"],
                    "content": message["text"],
                    "is_bot": message["role"] == "assistant",
                    "id": index,
                }
                for index, message in enumerate(
                    json.loads(self.conversation.value)
                )
            ]
        )

    def _set_conversation_widgets(self, messages):
        for message in messages:
            self.add_message_to_conversation(
                name=message["name"],
                message=message["content"],
                is_bot=message["is_bot"],
                first_message=True,
            )
        QTimer.singleShot(100, self.scroll_to_bottom)

    def on_hear_signal(self, data: Dict):
        transcription = data["transcription"]
        self.prompt = transcription
        self.do_generate()

    def on_add_to_conversation_signal(self, name, text, is_bot):
        self.add_message_to_conversation(
            name=name, message=text, is_bot=is_bot
        )

    def on_add_bot_message_to_conversation(self, data: Dict):
        llm_response: LLMResponse = data.get("response", None)
        if not llm_response:
            raise ValueError("No LLMResponse object found in data")

        if llm_response.node_id is not None:
            return

        self.token_buffer.append(llm_response.message)

        if llm_response.is_first_message:
            self.stop_progress_bar()

        if llm_response.is_end_of_message:
            self.enable_generate()

    def flush_token_buffer(self):
        """
        Flush the token buffer and update the UI.
        """

        combined_message = "".join(self.token_buffer)
        self.token_buffer.clear()

        if combined_message != "":
            self.add_message_to_conversation(
                name=self.chatbot.name,
                message=combined_message,
                is_bot=True,
                first_message=False,
            )

    def enable_generate(self):
        self.generating = False
        if self.held_message is not None:
            self.do_generate(prompt_override=self.held_message)
            self.held_message = None
        self.enable_send_button()

    @Slot()
    def action_button_clicked_clear_conversation(self):
        self.api.llm.clear_history()

    def on_clear_conversation(self):
        self._clear_conversation()

    def _clear_conversation(self):
        self.conversation_history = []
        self._clear_conversation_widgets()

    def _clear_conversation_widgets(self):
        # Iterate through the layout items and delete the widgets
        while self.ui.scrollAreaWidgetContents.layout().count():
            item = self.ui.scrollAreaWidgetContents.layout().takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        # Ensure the layout is updated
        self.ui.scrollAreaWidgetContents.layout().update()

    @Slot(bool)
    def action_button_clicked_send(self):
        self.do_generate()

    def interrupt_button_clicked(self):
        self.api.llm.interrupt()
        self.stop_progress_bar()
        self.generating = False
        self.enable_send_button()

    @property
    def action(self) -> LLMActionType:
        return LLMActionType[self.llm_generator_settings.action]

    def do_generate(self, prompt_override=None):
        prompt = (
            self.prompt
            if (prompt_override is None or prompt_override == "")
            else prompt_override
        )
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

        widget = self.add_message_to_conversation(
            name=self.user.username, message=self.prompt, is_bot=False
        )
        if widget is not None:
            QTimer.singleShot(100, widget.set_content_size)
            QTimer.singleShot(100, self.scroll_to_bottom)

        self.clear_prompt()
        self.start_progress_bar()
        self.api.llm.send_request(
            prompt=prompt,
            llm_request=LLMRequest.from_default(),
            action=self.action,
            do_tts_reply=False
        )

    def on_token_signal(self, val):
        self.handle_token_signal(val)

    def showEvent(self, event):
        super().showEvent(event)
        if not self.registered:
            self.registered = True

        # handle return pressed on QPlainTextEdit
        # there is no returnPressed signal for QPlainTextEdit
        # so we have to use the keyPressEvent
        self.promptKeyPressEvent = self.ui.prompt.keyPressEvent

        # Override the method
        self.ui.prompt.keyPressEvent = self.handle_key_press

        if not self.chat_loaded:
            self.disable_send_button()

        try:
            self.ui.conversation.hide()
        except RuntimeError as e:
            self.logger.warning(f"Error hiding conversation: {e}")

        try:
            self.ui.chat_container.show()
        except RuntimeError as e:
            if AIRUNNER_ART_ENABLED:
                self.logger.warning(f"Error setting SD status text: {e}")

    def llm_action_changed(self, val: str):
        if val == "Chat":
            llm_action_value = LLMActionType.CHAT
        elif val == "Image":
            llm_action_value = LLMActionType.GENERATE_IMAGE
        elif val == "RAG":
            llm_action_value = LLMActionType.PERFORM_RAG_SEARCH
        elif val == "Auto":
            llm_action_value = LLMActionType.APPLICATION_COMMAND
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
        # self.ui.send_button.setEnabled(False)
        # self._disabled = True
        pass

    def enable_send_button(self):
        self.ui.send_button.setEnabled(True)
        self._disabled = False

    def response_text_changed(self):
        pass

    def handle_key_press(self, event):
        if event.key() == Qt.Key.Key_Return:
            if (
                not self._disabled
                and event.modifiers() != Qt.KeyboardModifier.ShiftModifier
            ):
                self.do_generate()
                return
        # Call the original method
        if (
            self.originalKeyPressEvent is not None
            and self.originalKeyPressEvent != self.handle_key_press
        ):
            self.originalKeyPressEvent(event)

    def hide_action_menu(self):
        self.action_menu_displayed = False
        self.ui.action_menu.hide()

    def display_action_menu(self):
        self.action_menu_displayed = True
        self.ui.action_menu.show()

    def insert_newline(self):
        self.ui.prompt.insertPlainText("\n")

    def add_message_to_conversation(
        self,
        name: str,
        message: str,
        is_bot: bool,
        first_message: bool = True,
        _message_id: Optional[int] = None,
    ):
        message = strip_names_from_message(
            message.lstrip() if first_message else message,
            self.user.username,
            self.chatbot.botname,
        )
        if not first_message:
            # get the last widget from the scrollAreaWidgetContents.layout()
            # and append the message to it. must be a MessageWidget object
            # must start at the end of the layout and work backwards
            for i in range(
                self.ui.scrollAreaWidgetContents.layout().count() - 1, -1, -1
            ):
                current_widget = (
                    self.ui.scrollAreaWidgetContents.layout()
                    .itemAt(i)
                    .widget()
                )
                if isinstance(current_widget, MessageWidget):
                    if current_widget.is_bot:
                        if message != "":
                            current_widget.update_message(message)
                        self.scroll_to_bottom()
                        return
                    break

        self.remove_spacer()

        widget = None
        if message != "":
            total_widgets = (
                self.ui.scrollAreaWidgetContents.layout().count() - 1
            )
            if total_widgets < 0:
                total_widgets = 0
            widget = MessageWidget(
                name=name,
                message=message,
                is_bot=is_bot,
                message_id=total_widgets,
                conversation_id=self.conversation_id,
            )
            self.ui.scrollAreaWidgetContents.layout().addWidget(widget)

        self.add_spacer()

        # automatically scroll to the bottom of the scrollAreaWidgetContents
        self.scroll_to_bottom()

        return widget

    def remove_spacer(self):
        if self.spacer is not None:
            self.ui.scrollAreaWidgetContents.layout().removeItem(self.spacer)

    def add_spacer(self):
        if self.spacer is None:
            self.spacer = QSpacerItem(
                20,
                40,
                QSizePolicy.Policy.Minimum,
                QSizePolicy.Policy.Expanding,
            )
        self.ui.scrollAreaWidgetContents.layout().addItem(self.spacer)

    def message_type_text_changed(self, val):
        self.update_llm_generator_settings("message_type", val)

    def action_button_clicked_generate_characters(self):
        pass

    def scroll_to_bottom(self):
        if self.scroll_bar is None:
            self.scroll_bar = self.ui.chat_container.verticalScrollBar()

        if self.scroll_animation is None:
            self.scroll_animation = QPropertyAnimation(
                self.scroll_bar, b"value"
            )
            self.scroll_animation.setDuration(500)

        # Stop any ongoing animation
        if (
            self.scroll_animation
            and self.scroll_animation.state()
            == QPropertyAnimation.State.Running
        ):
            self.scroll_animation.stop()

        self.scroll_animation.setStartValue(self.scroll_bar.value())
        self.scroll_animation.setEndValue(self.scroll_bar.maximum())
        self.scroll_animation.start()
