from PySide6.QtWidgets import QVBoxLayout, QPushButton, QSpacerItem, QSizePolicy

from airunner.enums import SignalCode
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.llm.templates.llm_history_widget_ui import Ui_llm_history_widget
from airunner.aihandler.llm.agent.agent_database_handler import AgentDatabaseHandler

class LLMHistoryWidget(BaseWidget):
    widget_class_ = Ui_llm_history_widget

    def __init__(self, *args, **kwargs):
        super(LLMHistoryWidget, self).__init__(*args, **kwargs)
        self.database_handler = AgentDatabaseHandler()

    def showEvent(self, event):
        super(LLMHistoryWidget, self).showEvent(event)
        self.load_conversations()

    def load_conversations(self):
        conversations = self.database_handler.get_all_conversations()
        layout = QVBoxLayout()

        for conversation in conversations:
            button = QPushButton(conversation.title)
            button.clicked.connect(lambda _, c=conversation: self.on_conversation_click(c))
            layout.addWidget(button)

        # Add a vertical spacer at the end
        spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        layout.addItem(spacer)

        self.ui.conversations_scroll_area.setLayout(layout)

    def on_conversation_click(self, conversation):
        self.emit_signal(SignalCode.LOAD_CONVERSATION, {
            "conversation_id": conversation.id
        })
