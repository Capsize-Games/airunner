from llama_index.core.chat_engine import ContextChatEngine
from llama_index.core.base.llms.types import ChatMessage


class RefreshContextChatEngine(ContextChatEngine):
    def stream_chat(self, *args, system_prompt:str=None, **kwargs):
        if system_prompt:
            self._prefix_messages[0] = ChatMessage(content=system_prompt, role=self._llm.metadata.system_role)
        return super().stream_chat(*args, **kwargs)