
from PySide6.QtWidgets import QVBoxLayout, QSpacerItem, QSizePolicy

from airunner.data.models import LLMGeneratorSettings
from airunner.enums import SignalCode
from airunner.gui.widgets.base_widget import BaseWidget
from airunner.gui.widgets.llm.llm_history_item_widget import LLMHistoryItemWidget
from airunner.gui.widgets.llm.templates.llm_history_widget_ui import Ui_llm_history_widget
from airunner.data.models import Conversation


class LLMHistoryWidget(BaseWidget):
    widget_class_ = Ui_llm_history_widget

    def __init__(self, *args, **kwargs):
        super(LLMHistoryWidget, self).__init__(*args, **kwargs)
        self.spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

    def showEvent(self, event):
        super(LLMHistoryWidget, self).showEvent(event)
        self.load_conversations()

    def load_conversations(self):
        conversations = Conversation.objects.order_by(
            Conversation.id.desc()
        ).all()        

        layout = self.ui.gridLayout_2

        if layout is None:
            self.logger.error("Layout is None")

        # clear all widgets from the layout
        try:
            layout.removeItem(self.spacer)
        except Exception as e:
            self.logger.error(f"Error removing spacer: {e}")

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
