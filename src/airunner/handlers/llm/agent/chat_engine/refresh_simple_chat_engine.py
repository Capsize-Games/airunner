from llama_index.core.chat_engine.simple import SimpleChatEngine
from llama_index.core.base.llms.types import ChatMessage


class RefreshSimpleChatEngine(SimpleChatEngine):
    def update_system_prompt(self, system_prompt:str):
        self._prefix_messages[0] = ChatMessage(
            content=system_prompt, 
            role=self._llm.metadata.system_role
        )