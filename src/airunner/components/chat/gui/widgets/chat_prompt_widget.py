import logging
from typing import Dict

from PySide6.QtCore import Slot, Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QTextCursor

from airunner.components.chat.gui.widgets.templates.chat_prompt_ui import (
    Ui_chat_prompt,
)
from airunner.components.llm.data.conversation import Conversation
from airunner.enums import (
    SignalCode,
    LLMActionType,
    ModelType,
    ModelStatus,
)
from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.utils.application import create_worker
from airunner.components.llm.managers.llm_request import LLMRequest
from airunner.components.llm.workers.llm_response_worker import (
    LLMResponseWorker,
)
from airunner.settings import AIRUNNER_ART_ENABLED, SLASH_COMMANDS


class ChatPromptWidget(BaseWidget):
    widget_class_ = Ui_chat_prompt
    icons = [
        ("chevron-up", "send_button"),
        ("plus", "clear_conversation_button"),
        ("clock", "history_button"),
        ("settings", "settings_button"),
        ("x", "pushButton"),
    ]
    logger = logging.getLogger(__name__)

    def __init__(self, *args, **kwargs):
        self.signal_handlers = {
            SignalCode.AUDIO_PROCESSOR_RESPONSE_SIGNAL: self.on_hear_signal,
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL: self.on_model_status_changed_signal,
            SignalCode.LLM_TEXT_STREAMED_SIGNAL: self.on_add_bot_message_to_conversation,
        }
        self._splitters = ["chat_prompt_splitter"]
        self._default_splitter_settings_applied = False
        super().__init__()
        self._highlighted = False
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
        self.ui.action.blockSignals(True)
        self.ui.action.clear()
        action_map = [
            ("Auto", LLMActionType.APPLICATION_COMMAND),
            ("Chat", LLMActionType.CHAT),
            ("RAG", LLMActionType.PERFORM_RAG_SEARCH),
        ]
        if AIRUNNER_ART_ENABLED:
            action_map.append(("Image", LLMActionType.GENERATE_IMAGE))
        for label, _ in action_map:
            self.ui.action.addItem(label)
        current_action = self.action
        for idx, (_, action_type) in enumerate(action_map):
            if current_action is action_type:
                self.ui.action.setCurrentIndex(idx)
                break
        self.ui.action.blockSignals(False)
        self.originalKeyPressEvent = self.ui.prompt.keyPressEvent
        self.ui.prompt.keyPressEvent = self.handle_key_press
        self.held_message = None
        self._disabled = False
        self.scroll_animation = None
        self._llm_response_worker = create_worker(
            LLMResponseWorker, sleep_time_in_ms=1
        )
        self.loading = True
        self.conversation_id: int = None
        self.conversation = None
        self._llm_history_tab_index = None
        self._llm_history_widget = None
        self.ui.chat_history_widget.setVisible(False)
        self.ui.tabWidget.tabBar().hide()

    def _apply_default_splitter_settings(self):
        if hasattr(self, "ui") and self.ui is not None:
            QApplication.processEvents()
            default_chat_splitter_config = {
                "chat_prompt_splitter": {
                    "index_to_maximize": 0,
                    "min_other_size": 50,
                }
            }
            self.load_splitter_settings(
                orientations={"chat_prompt_splitter": Qt.Orientation.Vertical},
                default_maximize_config=default_chat_splitter_config,
            )
        else:
            self.logger.warning(
                "ChatPromptWidget: UI not available when attempting to apply default splitter settings."
            )

    @Slot()
    def on_clear_conversation_button_clicked(self):
        self.api.llm.clear_history()

    @Slot(bool)
    def on_history_button_toggled(self, checked: bool):
        self.ui.settings_button.blockSignals(True)
        self.ui.settings_button.setChecked(False)
        self.ui.settings_button.blockSignals(False)
        self.ui.tabWidget.setCurrentIndex(2 if checked else 0)

    @Slot(bool)
    def on_settings_button_toggled(self, checked: bool):
        self.ui.history_button.blockSignals(True)
        self.ui.history_button.setChecked(False)
        self.ui.history_button.blockSignals(False)
        self.ui.tabWidget.setCurrentIndex(1 if checked else 0)

    @Slot(bool)
    def action_button_clicked_send(self):
        self.do_generate()

    def _find_parent_tab_widget(self):
        """Find the parent QTabWidget containing this widget."""
        parent = self.parent()
        while parent is not None:
            from PySide6.QtWidgets import QTabWidget

            if isinstance(parent, QTabWidget):
                return parent
            parent = parent.parent()
        return None

    @property
    def action(self) -> LLMActionType:
        return LLMActionType[self.llm_generator_settings.action]

    def on_model_status_changed_signal(self, data):
        if data["model"] == ModelType.LLM:
            self.chat_loaded = data["status"] is ModelStatus.LOADED

        if not self.chat_loaded:
            self.disable_send_button()
        else:
            self.enable_send_button()

    def on_hear_signal(self, data: Dict):
        transcription = data["transcription"]
        self.prompt = transcription
        self.do_generate()

    def enable_generate(self):
        self.generating = False
        if self.held_message is not None:
            self.do_generate(prompt_override=self.held_message)
            self.held_message = None
        self.enable_send_button()

    def interrupt_button_clicked(self):
        self.api.llm.interrupt()
        self.stop_progress_bar()
        self.generating = False
        self.enable_send_button()

    def do_generate(self, prompt_override=None):
        prompt = (
            self.prompt
            if (prompt_override is None or prompt_override == "")
            else prompt_override
        )
        if prompt is None or prompt == "":
            self.logger.warning("Prompt is empty")
            return

        model_load_balancer = getattr(self.api, "model_load_balancer", None)
        art_model_loaded = (
            model_load_balancer
            and ModelType.SD in model_load_balancer.get_loaded_models()
        )
        llm_loaded = (
            model_load_balancer
            and ModelType.LLM in model_load_balancer.get_loaded_models()
        )
        if art_model_loaded and not llm_loaded:
            model_load_balancer.switch_to_non_art_mode()

        if self.generating:
            if self.held_message is None:
                self.held_message = prompt
                self.disable_send_button()
                self.interrupt_button_clicked()
            return
        self.generating = True

        self.clear_prompt()
        self.start_progress_bar()
        self.api.llm.send_request(
            prompt=prompt,
            llm_request=LLMRequest.from_default(),
            action=self.action,
            do_tts_reply=False,
        )

    def showEvent(self, event):
        super().showEvent(event)
        if not self._default_splitter_settings_applied and self.isVisible():
            self._apply_default_splitter_settings()
            self._default_splitter_settings_applied = True

        self.promptKeyPressEvent = self.ui.prompt.keyPressEvent

        self.ui.prompt.keyPressEvent = self.handle_key_press

        if not self.chat_loaded:
            self.disable_send_button()

        if not self.loading and hasattr(self.ui, "conversation"):
            self.load_conversation()

        self.loading = False

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
        self.update_llm_generator_settings(action=llm_action_value.name)

    def prompt_text_changed(self) -> None:
        """Handle changes to the prompt text and highlight slash commands if present."""
        prompt = self.ui.prompt.toPlainText()
        self.prompt = prompt.strip()
        self.highlight_slash_command(prompt)

    def highlight_slash_command(self, prompt: str) -> None:
        """Highlight the slash command in the prompt.

        Args:
            command (str): The slash command to highlight.
        """
        command = None
        if prompt.startswith("/"):
            candidate = prompt[1:].split(" ")[0]
            if candidate in SLASH_COMMANDS:
                command = candidate
        highlight = command is not None
        prompt_widget = self.ui.prompt
        text = prompt_widget.toPlainText()
        prompt_widget.blockSignals(True)
        cursor = QTextCursor(prompt_widget.document())
        cursor.setPosition(0)

        if command is not None:
            length = len(command) + 1  # +1 for the leading slash
        else:
            length = len(text)

        cursor.setPosition(length, QTextCursor.MoveMode.KeepAnchor)
        fmt = cursor.charFormat()
        fmt.setFontWeight(500 if highlight else 400)
        fmt.setForeground(
            Qt.GlobalColor.black if highlight else Qt.GlobalColor.white
        )
        fmt.setBackground(
            Qt.GlobalColor.yellow if highlight else Qt.GlobalColor.transparent
        )
        cursor.setCharFormat(fmt)

        if command is not None:
            # Move the cursor to the end of the command for further typing
            cursor.setPosition(length)
            cursor.setPosition(len(text), QTextCursor.MoveMode.KeepAnchor)
            fmt = cursor.charFormat()
            fmt.setFontWeight(400)
            fmt.setForeground(Qt.GlobalColor.white)
            fmt.setBackground(Qt.GlobalColor.transparent)
            cursor.setCharFormat(fmt)

        prompt_widget.blockSignals(False)

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
        pass

    def enable_send_button(self):
        self.ui.send_button.setEnabled(True)
        self._disabled = False

    def handle_key_press(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if (
                not self._disabled
                and event.modifiers() != Qt.KeyboardModifier.ShiftModifier
            ):
                self.do_generate()
                event.accept()
                return
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

    def message_type_text_changed(self, val):
        self.update_llm_generator_settings(message_type=val)

    def on_add_bot_message_to_conversation(self, data: Dict):
        llm_response = data.get("response", None)
        if llm_response is not None and getattr(
            llm_response, "is_first_message", False
        ):
            self.stop_progress_bar()
            self.enable_generate()

    def load_conversation(self, conversation_id: int = None):
        """Load a conversation and synchronize with ConversationWidget."""
        if conversation_id is None:
            conversation_id = (
                self._conversation_history_manager.get_most_recent_conversation_id()
            )
        if conversation_id is None:
            if hasattr(self.ui, "conversation"):
                self.ui.conversation.clear_conversation()
            self.conversation = None
            self.conversation_id = None
            return
        self.conversation_id = conversation_id

        conversation = Conversation.objects.filter_by_first(id=conversation_id)
        self.conversation = conversation
        if hasattr(self.api, "llm") and hasattr(self.api.llm, "clear_history"):
            self.api.llm.clear_history(conversation_id=conversation_id)
        messages = (
            self._conversation_history_manager.load_conversation_history(
                conversation_id=conversation_id, max_messages=50
            )
        )
        if hasattr(self.ui, "conversation"):
            self.ui.conversation.conversation = conversation
            self.ui.conversation.set_conversation_widgets(messages)

    def on_queue_load_conversation(self, data):
        conversation_id = data.get("index")
        self.load_conversation(conversation_id=conversation_id)

    def on_delete_conversation(self, data):
        deleted_id = data.get("conversation_id")
        if self.conversation_id == deleted_id:
            if hasattr(self.ui, "conversation"):
                self.ui.conversation.clear_conversation()
            self.conversation = None
            self.conversation_id = None

    def _clear_conversation(self, skip_update: bool = False):
        pass

    def _set_conversation_widgets(self, messages, skip_scroll: bool = False):
        pass

    def _clear_conversation_widgets(self, skip_update: bool = False):
        pass

    def add_message_to_conversation(self, *args, **kwargs):
        pass

    def on_mood_summary_update_started(self, *args, **kwargs):
        pass

    def _handle_mood_summary_update_started(self, *args, **kwargs):
        pass

    def register_web_channel(self, channel):
        pass
