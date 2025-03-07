# airunner/widgets/llm/llm_history_widget.py

from PySide6.QtWidgets import QVBoxLayout, QSpacerItem, QSizePolicy

from airunner.data.models import LLMGeneratorSettings
from airunner.enums import SignalCode
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.llm.llm_history_item_widget import LLMHistoryItemWidget
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
        conversations = self.get_all_conversations()
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
            # if conversation.title == "":
            #     continue
            llm_history_item_widget = LLMHistoryItemWidget(
                conversation=conversation
            )
            # add to layout
            layout.addWidget(llm_history_item_widget)

        # Add a vertical spacer at the end
        layout.addItem(self.spacer)

        self.ui.scrollAreaWidgetContents.setLayout(layout)

    def on_conversation_click(self, conversation):
        llm_generator_settings = LLMGeneratorSettings.objects.first()
        LLMGeneratorSettings.objects.update(
            llm_generator_settings.id,
            {"current_chatbot": conversation.chatbot_id}
        )
        self.emit_signal(SignalCode.LOAD_CONVERSATION, {
            "conversation_id": conversation.id,
            "conversation": conversation,
            "chatbot_id": conversation.chatbot_id
        })

    def on_delete_conversation(self, layout, conversation):
        conversation_id = conversation.id
        self.delete_conversation(conversation_id)
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
