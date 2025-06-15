from PySide6.QtWidgets import QSpacerItem, QSizePolicy

from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.llm.data.conversation import Conversation
from airunner.components.llm.gui.widgets.llm_history_item_widget import (
    LLMHistoryItemWidget,
)
from airunner.components.llm.gui.widgets.templates.llm_history_widget_ui import (
    Ui_llm_history_widget,
)


class LLMHistoryWidget(BaseWidget):
    widget_class_ = Ui_llm_history_widget

    def __init__(self, *args, **kwargs):
        super(LLMHistoryWidget, self).__init__(*args, **kwargs)
        self.spacer = QSpacerItem(
            20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
        )

    def showEvent(self, event):
        super(LLMHistoryWidget, self).showEvent(event)
        self.load_conversations()

    def load_conversations(self):
        # Get all conversations and sort them by ID descending
        # Use filter to avoid session issues with order_by().all() chain
        all_conversations = Conversation.objects.filter(
            Conversation.id >= 1  # Get all conversations
        )
        if all_conversations:
            conversations = sorted(
                all_conversations, key=lambda x: x.id, reverse=True
            )
        else:
            conversations = []

        # Get the existing layout - keep using the original QGridLayout from the UI file
        layout = self.ui.gridLayout_2

        # Clear all widgets from the layout
        while layout.count() > 0:
            item = layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
            elif item.spacerItem():
                layout.removeItem(item.spacerItem())

        # Make sure scroll area widget contents has the right size policy
        self.ui.scrollAreaWidgetContents.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred
        )

        # Add conversation widgets to the grid layout
        row = 0
        for conversation in conversations:
            # if conversation.title == "":
            #     continue
            llm_history_item_widget = LLMHistoryItemWidget(
                conversation=conversation
            )
            # Add to grid layout - spanning the full row
            layout.addWidget(llm_history_item_widget, row, 0, 1, 1)
            row += 1

        # Add a vertical spacer at the end to push widgets to top
        layout.addItem(self.spacer, row, 0, 1, 1)

        # Set widget resizable for proper scrolling
        self.ui.conversations_scroll_area.setWidgetResizable(True)
