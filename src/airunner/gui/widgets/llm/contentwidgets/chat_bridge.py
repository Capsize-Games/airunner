from PySide6.QtCore import QObject, Signal, Slot


class ChatBridge(QObject):
    appendMessage = Signal(dict)
    clearMessages = Signal()
    setMessages = Signal(list)
    scrollRequested = Signal()
    contentHeightChanged = Signal(int)

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

