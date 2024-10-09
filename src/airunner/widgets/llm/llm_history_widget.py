# airunner/widgets/llm/llm_history_widget.py

from PySide6.QtWidgets import QVBoxLayout, QPushButton, QSpacerItem, QSizePolicy, QHBoxLayout, QWidget, QLabel

from airunner.data.models.settings_models import Message, LLMGeneratorSettings
from airunner.enums import SignalCode
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.llm.templates.llm_history_widget_ui import Ui_llm_history_widget

class LLMHistoryWidget(BaseWidget):
    widget_class_ = Ui_llm_history_widget

    def __init__(self, *args, **kwargs):
        super(LLMHistoryWidget, self).__init__(*args, **kwargs)
        self.spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

    def showEvent(self, event):
        super(LLMHistoryWidget, self).showEvent(event)
        self.load_conversations()

    def load_conversations(self):
        conversations = self.db_handler.get_all_conversations()
        layout = self.ui.gridLayout_2

        if layout is None:
            self.logger.error("Layout is None")

        # clear all widgets from the layout
        try:
            layout.removeItem(self.spacer)
        except:
            pass

        if layout:
            for i in reversed(range(layout.count())):
                widget = layout.itemAt(i).widget()
                if widget:
                    widget.setParent(None)

        if layout is None:
            layout = QVBoxLayout(self.ui.scrollAreaWidgetContents)
            self.ui.scrollAreaWidgetContents.setLayout(layout)

        for conversation in conversations:
            h_layout = QHBoxLayout()
            button = QPushButton(conversation.title)
            button.clicked.connect(lambda _, c=conversation: self.on_conversation_click(c))

            # Extract chatbot_id from the first message of the conversation
            session = self.db_handler.get_db_session()
            first_message = session.query(Message).filter_by(conversation_id=conversation.id).first()
            chatbot_name = "Unknown"
            if first_message and first_message.chatbot_id:
                chatbot = self.db_handler.get_chatbot_by_id(first_message.chatbot_id)
                if chatbot:
                    chatbot_name = chatbot.name
            session.close()

            chatbot_label = QLabel(f"Chatbot: {chatbot_name}")
            delete_button = QPushButton("Delete")
            delete_button.clicked.connect(lambda _, widget=h_layout, c=conversation: self.on_delete_conversation(widget, c))
            h_layout.addWidget(button)
            h_layout.addWidget(chatbot_label)
            h_layout.addWidget(delete_button)

            container_widget = QWidget()
            container_widget.setLayout(h_layout)
            layout.addWidget(container_widget)

        # Add a vertical spacer at the end
        layout.addItem(self.spacer)

        self.ui.conversations_scroll_area.setLayout(layout)

    def on_conversation_click(self, conversation):
        session = self.db_handler.get_db_session()
        first_message = session.query(Message).filter_by(conversation_id=conversation.id).first()
        chatbot_id = first_message.chatbot_id
        session.query(LLMGeneratorSettings).update({"current_chatbot": chatbot_id})
        session.commit()
        session.close()
        self.emit_signal(SignalCode.LOAD_CONVERSATION, {
            "conversation_id": conversation.id
        })

    def on_delete_conversation(self, layout, conversation):
        conversation_id = conversation.id
        self.db_handler.delete_conversation(conversation_id)
        for i in reversed(range(layout.count())):
            widget = layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        parent_layout = self.ui.conversations_scroll_area.layout()
        if parent_layout:
            parent_layout.removeItem(layout)
        self.emit_signal(SignalCode.CONVERSATION_DELETED, {
            "conversation_id": conversation_id
        })
