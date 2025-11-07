"""
DEPRECATED: Use ChatBridge in airunner.gui.widgets.llm.contentwidgets.chat_bridge instead.
This file is no longer used. All QWebChannel slots should be added to ChatBridge.
"""

"""
ChatPromptBridge: QWebChannel bridge for chat prompt widget.

This QObject exposes slots for JS to call, and emits signals to the ChatPromptWidget.
"""

from PySide6.QtCore import QObject, Slot

from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger


class ChatPromptBridge(QObject):
    """
    QWebChannel bridge for chat prompt widget.
    """

    def __init__(self, widget):
        super().__init__()
        self.widget = widget
        self.logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)

    @Slot(int)
    @Slot(str)
    def deleteMessage(self, message_id):
        """
        Delete a user message and all subsequent messages from the conversation history.
        Args:
            message_id (int | str): The message id to delete from.
        """
        self.logger.info(
            f"ChatPromptBridge.deleteMessage called with id={message_id} (type={type(message_id)})"
        )
        self.widget.deleteMessage(message_id)
