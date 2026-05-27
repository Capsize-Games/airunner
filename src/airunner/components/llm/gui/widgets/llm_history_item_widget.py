from PySide6.QtCore import Slot
from PySide6.QtWidgets import QSpacerItem, QSizePolicy

from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.conversations.conversation_history_manager import (
    ConversationHistoryManager,
)
from airunner.components.llm.gui.widgets.templates.llm_history_item_ui import (
    Ui_llm_history_item_widget,
)


class LLMHistoryItemWidget(BaseWidget):
    widget_class_ = Ui_llm_history_item_widget

    def __init__(self, *args, **kwargs):
        """Initialize one lightweight row for the history sidebar."""
        self.conversation = kwargs.pop("conversation")
        self._conversation_history_manager = kwargs.pop(
            "conversation_history_manager",
            None,
        )
        super(LLMHistoryItemWidget, self).__init__(*args, **kwargs)
        if self._conversation_history_manager is None:
            self._conversation_history_manager = ConversationHistoryManager(
                getattr(self.api, "daemon_client", None)
            )
        self.spacer = QSpacerItem(
            20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
        )
        self.ui.conversation_description.setText(
            self._conversation_summary_text()
        )
        self.ui.botname.setText(self._chatbot_name_text())
        self.ui.timestamp.setText(self._timestamp_text())

    def _conversation_summary_text(self) -> str:
        """Return the persisted summary text for one conversation row."""
        summary = getattr(self.conversation, "summary", None)
        if isinstance(summary, str) and summary.strip():
            return summary
        title = getattr(self.conversation, "title", None)
        if isinstance(title, str) and title.strip():
            return title
        return "[Conversation]"

    def _chatbot_name_text(self) -> str:
        """Return the stored chatbot label for one conversation row."""
        chatbot_name = getattr(self.conversation, "chatbot_name", None)
        if isinstance(chatbot_name, str) and chatbot_name.strip():
            return chatbot_name
        return "Unknown"

    def _timestamp_text(self) -> str:
        """Return the stored timestamp label for one conversation row."""
        timestamp = getattr(self.conversation, "timestamp", None)
        if timestamp is None:
            return "[unavailable]"
        return str(timestamp)

    @Slot()
    def action_load_conversation_clicked(self):
        session = self._conversation_history_manager.select_conversation(
            self.conversation.id
        )
        if session.get("conversation") is None:
            return
        self.api.llm.load_conversation(conversation_id=self.conversation.id)

    @Slot()
    def action_delete_conversation_clicked(self):
        conversation_id = self.conversation.id
        deleted = self._conversation_history_manager.delete_conversation(
            conversation_id
        )
        if not deleted:
            return
        self.api.llm.converation_deleted(conversation_id)
        self.setParent(None)
        self.deleteLater()
