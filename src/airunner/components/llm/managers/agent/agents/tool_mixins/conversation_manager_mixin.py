from typing import Optional, Any

from airunner.components.llm.data.conversation import Conversation


class ConversationManagerMixin:
    """
    Mixin for managing conversation retrieval, creation, updating, and summary logic.
    """

    def __init__(self):
        self._chatbot = None
        self._user = None
        self._conversation_id = None
        self._conversation = None

    @property
    def conversation(self) -> Optional[Conversation]:
        if not self.use_memory:
            return None
        if not hasattr(self, "_conversation") or self._conversation is None:
            self.conversation = self._create_conversation()
        return self._conversation

    @conversation.setter
    def conversation(self, value: Optional[Conversation]):
        self._conversation = value
        if value and self.conversation_id != value.id:
            self.chat_memory.chat_store_key = str(value.id)
            self._conversation_id = value.id
        self._user = None
        self._chatbot = None

    @property
    def conversation_id(self) -> int:
        if not self.use_memory:
            return ""
        conversation_id = getattr(self, "_conversation_id", None)
        if not conversation_id:
            # Ensure conversation is created and _conversation_id is set
            conversation = self.conversation  # triggers creation if needed
            if conversation:
                self._conversation_id = conversation.id
                conversation_id = conversation.id
        return conversation_id

    @conversation_id.setter
    def conversation_id(self, value: int):
        if value != getattr(self, "_conversation_id", None):
            self._conversation_id = value
            if (
                self.conversation
                and self.conversation.id != self._conversation_id
            ):
                self.conversation = None

    def _create_conversation(self) -> Conversation:
        conversation = None
        # Use the private attribute to avoid recursion
        if getattr(self, "_conversation_id", None):
            self.logger.info(
                f"Loading conversation with ID: {self._conversation_id}"
            )
            conversation = Conversation.objects.get(self._conversation_id)
        if not conversation:
            self.logger.info("No conversation found, looking for most recent")
            conversation = Conversation.most_recent()
        if not conversation:
            self.logger.info("Creating new conversation")
            conversation = Conversation.create()
        return conversation

    def _update_conversation(self, key: str, value: Any):
        if self.conversation:
            setattr(self.conversation, key, value)
            Conversation.objects.update(self.conversation_id, **{key: value})

    @property
    def do_summarize_conversation(self) -> bool:
        if not self.conversation:
            return False
        messages = self.conversation.value or []
        total_messages = len(messages)
        if (
            (
                total_messages > self.llm_settings.summarize_after_n_turns
                and self.conversation.summary is None
            )
            or total_messages % self.llm_settings.summarize_after_n_turns == 0
        ):
            return True
        return False

    @property
    def conversation_summaries(self) -> str:
        summaries = ""
        conversations = Conversation.objects.order_by(Conversation.id.desc())[
            :5
        ]
        conversations = list(conversations)
        conversations = sorted(conversations, key=lambda x: x.id, reverse=True)
        for conversation in conversations:
            if conversation.summary:
                summaries += f"- {conversation.summary}\n"
        if summaries != "":
            summaries = f"Recent conversation summaries:\n{summaries}"
        return summaries

    @property
    def conversation_summary_prompt(self) -> str:
        return (
            f"- Conversation summary:\n{self.conversation.summary}\n"
            if self.conversation and self.conversation.summary
            else ""
        )
