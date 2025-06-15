from airunner.components.conversations.conversation_history_manager import (
    ConversationHistoryManager,
)
from airunner.enums import (
    SignalCode,
)
from airunner.components.application.workers.worker import Worker


class LLMChatPromptWorker(Worker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._conversation_history_manager = ConversationHistoryManager()

    def handle_message(self, message):
        """
        Expects message to be a dict with at least 'action': 'load_conversation', and optionally 'index' (conversation_id).
        This worker is now primarily a pass-through or simple fetcher, as ChatPromptWidget uses ConversationHistoryManager.
        It can still be used to trigger a load if needed by other parts of the system,
        but the complex message formatting is removed.
        """
        action = message.get("action")
        if action == "load_conversation":
            conversation_id = message.get(
                "index"
            )  # 'index' is used for conversation_id

            if conversation_id is None:
                # If no specific ID, get the most recent one
                conversation_id = (
                    self._conversation_history_manager.get_most_recent_conversation_id()
                )

            # Emit a signal with just the conversation_id.
            # ChatPromptWidget will use ConversationHistoryManager to fetch and format.
            # This signal might be redundant if ChatPromptWidget.load_conversation is called directly.
            # However, keeping it allows other system parts to trigger a conversation load via this worker.
            if conversation_id is not None:
                self.emit_signal(
                    SignalCode.QUEUE_LOAD_CONVERSATION,  # Or a new signal if QUEUE_LOAD_CONVERSATION is not appropriate
                    {
                        "index": conversation_id
                    },  # Keep 'index' for consistency with ChatPromptWidget.on_queue_load_conversation
                )
            else:
                # Emit a signal indicating no conversation was found or to load, perhaps to clear the UI
                self.emit_signal(
                    SignalCode.QUEUE_LOAD_CONVERSATION,
                    {"index": None},  # Keep 'index' for consistency
                )
