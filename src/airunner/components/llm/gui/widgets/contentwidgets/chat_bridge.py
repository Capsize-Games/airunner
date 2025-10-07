from PySide6.QtCore import QObject, Signal, Slot


class ChatBridge(QObject):
    appendMessage = Signal(dict)
    clearMessages = Signal()
    setMessages = Signal(list)
    scrollRequested = Signal()
    contentHeightChanged = Signal(int)
    deleteMessageRequested = Signal(object)  # Accepts int or str
    copyMessageRequested = Signal(object)
    newChatRequested = Signal()

    @Slot(list)
    def set_messages(self, messages):
        self.setMessages.emit(messages)

    @Slot(dict)
    def append_message(self, msg):
        self.appendMessage.emit(msg)

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
