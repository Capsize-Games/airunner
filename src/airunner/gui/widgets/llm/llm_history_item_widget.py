from PySide6.QtCore import Slot
from PySide6.QtWidgets import QSpacerItem, QSizePolicy

from airunner.data.models import LLMGeneratorSettings
from airunner.enums import SignalCode
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

        self.ui.conversation_description.setText(self.conversation.summarize())

        chatbot_name = "Unknown"
        chatbot = self.get_chatbot_by_id(self.conversation.chatbot_id)
        if chatbot:
            chatbot_name = chatbot.name

        self.ui.botname.setText(chatbot_name)
        self.ui.timestamp.setText(str(self.conversation.timestamp))

    @Slot()
    def action_load_conversation_clicked(self):
        chatbot_id = self.conversation.chatbot_id
        llm_generator_settings = LLMGeneratorSettings.objects.first()
        LLMGeneratorSettings.objects.update(
            llm_generator_settings.id,
            current_chatbot=chatbot_id,
            current_conversation=self.conversation.id,
        )
        self.api.llm.load_conversation(
            conversation_id=self.conversation.id,
            conversation=self.conversation,
            chatbot_id=chatbot_id,
        )

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
