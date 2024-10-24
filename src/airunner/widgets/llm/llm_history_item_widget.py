# airunner/widgets/llm/llm_history_widget.py
from PySide6.QtCore import Slot
from PySide6.QtWidgets import QVBoxLayout, QPushButton, QSpacerItem, QSizePolicy, QHBoxLayout, QWidget, QLabel

from airunner.data.models.settings_models import Message, LLMGeneratorSettings
from airunner.enums import SignalCode
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.llm.templates.llm_history_item_ui import Ui_llm_history_item_widget


class LLMHistoryItemWidget(BaseWidget):
    widget_class_ = Ui_llm_history_item_widget

    def __init__(self, *args, **kwargs):
        self.conversation = kwargs.pop("conversation")
        super(LLMHistoryItemWidget, self).__init__(*args, **kwargs)
        self.spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.ui.conversation_description.setText(self.conversation.title)

        first_message = self.session.query(Message).filter_by(conversation_id=self.conversation.id).first()
        chatbot_name = "Unknown"
        if first_message and first_message.chatbot_id:
            chatbot = self.get_chatbot_by_id(first_message.chatbot_id)
            if chatbot:
                chatbot_name = chatbot.name

        self.ui.botname.setText(chatbot_name)
        self.ui.timestamp.setText(str(self.conversation.timestamp))

    @Slot()
    def action_load_conversation_clicked(self):
        first_message = self.session.query(Message).filter_by(conversation_id=self.conversation.id).first()
        chatbot_id = first_message.chatbot_id
        self.session.query(LLMGeneratorSettings).update({"current_chatbot": chatbot_id})
        self.session.commit()
        self.emit_signal(SignalCode.LOAD_CONVERSATION, {
            "conversation_id": self.conversation.id,
            "conversation": self.conversation,
            "chatbot_id": chatbot_id
        })

    @Slot()
    def action_delete_conversation_clicked(self):
        conversation_id = self.conversation.id
        self.delete_conversation(conversation_id)
        self.emit_signal(SignalCode.CONVERSATION_DELETED, {
            "conversation_id": conversation_id
        })
        self.setParent(None)
        self.deleteLater()
