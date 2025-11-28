from PySide6.QtCore import QObject, Signal, Slot


class ChatBridge(QObject):
    appendMessage = Signal(dict)
    clearMessages = Signal()
    setMessages = Signal(list)
    updateLastMessageContent = Signal(
        str
    )  # Update last message content during streaming
    scrollRequested = Signal()
    contentHeightChanged = Signal(int)
    deleteMessageRequested = Signal(object)  # Accepts int or str
    copyMessageRequested = Signal(object)
    newChatRequested = Signal()
    toolStatusUpdate = Signal(
        str, str, str, str, str
    )  # tool_id, tool_name, query, status, details
    thinkingStatusUpdate = Signal(
        str, str
    )  # status, content - for Qwen3 <think> blocks

    @Slot(list)
    def set_messages(self, messages):
        self.setMessages.emit(messages)

    @Slot(dict)
    def append_message(self, msg):
        self.appendMessage.emit(msg)

    @Slot(str)
    def update_last_message_content(self, content):
        """Update the content of the last message (for streaming).

        Args:
            content: New content for the last message
        """
        self.updateLastMessageContent.emit(content)

    @Slot()
    def clear_messages(self):
        self.clearMessages.emit()

    @Slot()
    def request_scroll(self):
        self.scrollRequested.emit()

    @Slot(int)
    def update_content_height(self, height):
        self.contentHeightChanged.emit(height)

    @Slot(int)
    @Slot(str)
    def deleteMessage(self, message_id):
        self.deleteMessageRequested.emit(message_id)

    @Slot(int)
    @Slot(str)
    def copyMessage(self, message_id):
        self.copyMessageRequested.emit(message_id)

    @Slot()
    def newChat(self):
        self.newChatRequested.emit()

    @Slot(str, str, str, str, str)
    def updateToolStatus(self, tool_id, tool_name, query, status, details):
        """Emit tool status update to JavaScript.

        Args:
            tool_id: Unique ID for this tool execution
            tool_name: Name of the tool
            query: The query/prompt sent to the tool
            status: "starting" or "completed"
            details: Optional details (e.g., URLs)
        """
        self.toolStatusUpdate.emit(tool_id, tool_name, query, status, details)

    @Slot(str, str)
    def updateThinkingStatus(self, status, content):
        """Emit thinking status update to JavaScript.

        Args:
            status: "started", "streaming", or "completed"
            content: The thinking text content
        """
        self.thinkingStatusUpdate.emit(status, content)
