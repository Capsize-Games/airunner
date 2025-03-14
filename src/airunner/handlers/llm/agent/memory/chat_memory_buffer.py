from typing import Any, List, Optional

from llama_index.core.base.llms.types import ChatMessage, MessageRole
from llama_index.core.memory import ChatMemoryBuffer as ChatMemoryBufferBroken


class ChatMemoryBuffer(ChatMemoryBufferBroken):
    def get(
        self, 
        input: Optional[str] = None, 
        initial_token_count: int = 0, 
        **kwargs: Any
    ) -> List[ChatMessage]:
        """Get chat history."""
        chat_history = self.get_all()

        if initial_token_count > self.token_limit:
            raise ValueError("Initial token count exceeds token limit")

        message_count = len(chat_history) if chat_history else 0
        if message_count > 0:
            cur_messages = chat_history[-message_count:]
            token_count = self._token_count_for_messages(cur_messages) + initial_token_count

            while token_count > self.token_limit and message_count > 1:
                message_count -= 1
                while chat_history[-message_count].role in (
                    MessageRole.TOOL,
                    MessageRole.ASSISTANT,
                ):
                    # we cannot have an assistant message at the start of the chat history
                    # if after removal of the first, we have an assistant message,
                    # we need to remove the assistant message too
                    #
                    # all tool messages should be preceded by an assistant message
                    # if we remove a tool message, we need to remove the assistant message too
                    message_count -= 1

                cur_messages = chat_history[-message_count:]
                token_count = (
                    self._token_count_for_messages(cur_messages) + initial_token_count
                )
            
            # catch one message longer than token limit
            if token_count > self.token_limit or message_count <= 0:
                return []

            return chat_history[-message_count:]
        return []
