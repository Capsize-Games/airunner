from PySide6.QtCore import Slot
from PySide6.QtWidgets import QSpacerItem, QSizePolicy

from airunner.data.models import LLMGeneratorSettings
from airunner.gui.widgets.base_widget import BaseWidget
from airunner.gui.widgets.llm.templates.llm_history_item_ui import (
    Ui_llm_history_item_widget,
)
from airunner.data.models import Conversation


class LLMHistoryItemWidget(BaseWidget):
    widget_class_ = Ui_llm_history_item_widget

    def __init__(self, *args, **kwargs):
        self.conversation = kwargs.pop("conversation")
        super(LLMHistoryItemWidget, self).__init__(*args, **kwargs)
        self.spacer = QSpacerItem(
            20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
        )

        # Handle DetachedInstanceError gracefully
        try:
            summary = self.conversation.summarize()
        except Exception as e:
            # Import here to avoid hard dependency if not using SQLAlchemy
            if (
                e.__class__.__name__ == "DetachedInstanceError"
                or e.__class__.__name__ == "DummyDetachedError"
            ):
                summary = "[Conversation unavailable]"
            else:
                summary = f"[Error: {e}]"
        self.ui.conversation_description.setText(summary)

        chatbot_name = "Unknown"
        try:
            chatbot_id = getattr(self.conversation, "chatbot_id", None)
        except Exception as e:
            if e.__class__.__name__ == "DetachedInstanceError":
                chatbot_id = None
            else:
                raise
        chatbot = None
        try:
            chatbot = self.get_chatbot_by_id(chatbot_id)
        except Exception as e:
            # Handle any database-related errors gracefully
            self.logger.warning(f"Failed to get chatbot: {e}")
            chatbot = None

        try:
            if chatbot:
                chatbot_name = chatbot.name
        except Exception as e:
            if (
                e.__class__.__name__ == "DetachedInstanceError"
                or e.__class__.__name__ == "DummyDetachedError"
            ):
                chatbot_name = "[unavailable]"
            else:
                chatbot_name = f"[Error: {e}]"

        self.ui.botname.setText(chatbot_name)
        try:
            timestamp = str(self.conversation.timestamp)
        except Exception as e:
            if e.__class__.__name__ == "DetachedInstanceError":
                timestamp = "[unavailable]"
            else:
                timestamp = f"[Error: {e}]"
        self.ui.timestamp.setText(timestamp)

    @Slot()
    def action_load_conversation_clicked(self):
        chatbot_id = self.conversation.chatbot_id
        llm_generator_settings = LLMGeneratorSettings.objects.first()
        LLMGeneratorSettings.objects.update(
            llm_generator_settings.id,
            current_chatbot=chatbot_id,
            current_conversation=self.conversation.id,
        )
        self.api.llm.load_conversation(conversation_id=self.conversation.id)

    @Slot()
    def action_delete_conversation_clicked(self):
        conversation_id = self.conversation.id
        Conversation.delete(conversation_id)
        LLMGeneratorSettings.objects.update(
            self.llm_generator_settings.id, current_conversation=None
        )
        self.api.llm.converation_deleted(conversation_id)
        self.setParent(None)
        self.deleteLater()
