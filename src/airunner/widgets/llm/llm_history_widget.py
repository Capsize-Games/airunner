from PySide6.QtWidgets import QVBoxLayout, QPushButton, QSpacerItem, QSizePolicy, QHBoxLayout, QWidget

from airunner.enums import SignalCode
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.llm.templates.llm_history_widget_ui import Ui_llm_history_widget
from airunner.aihandler.llm.agent.agent_database_handler import AgentDatabaseHandler

class LLMHistoryWidget(BaseWidget):
    widget_class_ = Ui_llm_history_widget

    def __init__(self, *args, **kwargs):
        super(LLMHistoryWidget, self).__init__(*args, **kwargs)
        self.database_handler = AgentDatabaseHandler()
        self.spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

    def showEvent(self, event):
        super(LLMHistoryWidget, self).showEvent(event)
        self.load_conversations()

    def load_conversations(self):
        conversations = self.database_handler.get_all_conversations()
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
            delete_button = QPushButton("Delete")
            delete_button.clicked.connect(lambda _, widget=h_layout, c=conversation: self.on_delete_conversation(widget, c))
            h_layout.addWidget(button)
            h_layout.addWidget(delete_button)

            container_widget = QWidget()
            container_widget.setLayout(h_layout)
            layout.addWidget(container_widget)

        # Add a vertical spacer at the end
        layout.addItem(self.spacer)

        self.ui.conversations_scroll_area.setLayout(layout)

    def on_conversation_click(self, conversation):
        self.emit_signal(SignalCode.LOAD_CONVERSATION, {
            "conversation_id": conversation.id
        })

    def on_delete_conversation(self, layout, conversation):
        self.database_handler.delete_conversation(conversation.id)
        for i in reversed(range(layout.count())):
            widget = layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        parent_layout = self.ui.conversations_scroll_area.layout()
        if parent_layout:
            parent_layout.removeItem(layout)
