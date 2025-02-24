from llama_index.core.chat_engine import ContextChatEngine
from llama_index.core.base.llms.types import ChatMessage


class RefreshContextChatEngine(ContextChatEngine):
    def update_system_prompt(self, system_prompt:str):
        self._prefix_messages[0] = ChatMessage(
            content=system_prompt, 
            role=self._llm.metadata.system_role
        )