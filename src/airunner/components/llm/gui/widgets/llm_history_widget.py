from PySide6.QtWidgets import QSpacerItem, QSizePolicy

from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner_model.models.conversation import Conversation
from airunner.components.llm.gui.widgets.llm_history_item_widget import (
    LLMHistoryItemWidget,
)
from airunner.components.llm.gui.widgets.templates.llm_history_widget_ui import (
    Ui_llm_history_widget,
)


class LLMHistoryWidget(BaseWidget):
    widget_class_ = Ui_llm_history_widget

    def __init__(self, *args, **kwargs):
        """Initialize the lazily rendered history sidebar widget."""
        super(LLMHistoryWidget, self).__init__(*args, **kwargs)
        self.spacer = QSpacerItem(
            20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
        )
        self._history_loaded = False
        self._history_snapshot = ()

    def preload_content(self) -> None:
        """Populate the history list before the user opens the panel."""
        self.load_conversations(force=True)

    def showEvent(self, event):
        super(LLMHistoryWidget, self).showEvent(event)
        self.load_conversations()

    def load_conversations(self, force: bool = False) -> None:
        """Render the history list only when the conversation set changes."""
        conversations = self._ordered_conversations()
        snapshot = self._conversation_snapshot(conversations)
        if not force and self._history_loaded:
            if snapshot == self._history_snapshot:
                return
        self._history_loaded = True
        self._history_snapshot = snapshot
        self._render_conversations(conversations)

    def _ordered_conversations(self):
        """Return conversations sorted newest-first for display."""
        conversations = Conversation.objects.filter(Conversation.id >= 1)
        if not conversations:
            return []
        return sorted(conversations, key=lambda item: item.id, reverse=True)

    def _conversation_snapshot(self, conversations):
        """Return a cheap fingerprint for the visible conversation rows."""
        return tuple(
            (
                item.id,
                bool(getattr(item, "current", False)),
                getattr(item, "title", "") or "",
                getattr(item, "summary", "") or "",
            )
            for item in conversations
        )

    def _render_conversations(self, conversations) -> None:
        """Replace the current row widgets with the latest history list."""
        layout = self.ui.gridLayout_2
        while layout.count() > 0:
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.spacerItem():
                layout.removeItem(item.spacerItem())

        self.ui.scrollAreaWidgetContents.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred
        )
        for row, conversation in enumerate(conversations):
            llm_history_item_widget = LLMHistoryItemWidget(
                conversation=conversation
            )
            layout.addWidget(llm_history_item_widget, row, 0, 1, 1)
        layout.addItem(self.spacer, len(conversations), 0, 1, 1)
        self.ui.conversations_scroll_area.setWidgetResizable(True)
