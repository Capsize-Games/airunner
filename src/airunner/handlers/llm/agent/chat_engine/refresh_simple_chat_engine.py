from typing import Type, Optional

from llama_index.core.chat_engine.simple import SimpleChatEngine
from llama_index.core.base.llms.types import ChatMessage
from llama_index.core.memory import BaseMemory
from llama_index.core.llms.llm import LLM


class RefreshSimpleChatEngine(SimpleChatEngine):
    def __init__(
        self,
        llm: Type[LLM],
        memory: Optional[BaseMemory] = None,
        prefix_messages: Optional[list] = None,
        *args,
        **kwargs
    ):
        super().__init__(
            llm=llm,
            memory=memory,
            prefix_messages=prefix_messages,
            *args,
            **kwargs
        )
        self._llm = llm
        self._memory = memory
        self._prefix_messages = prefix_messages or []

    @property
    def llm(self) -> Type[LLM]:
        return self._llm

    @property
    def memory(self) -> BaseMemory:
        return self._memory

    @memory.setter
    def memory(self, memory: BaseMemory):
        self._memory = memory

    def update_system_prompt(self, system_prompt: str):
        message = ChatMessage(
            content=system_prompt, role=self._llm.metadata.system_role
        )
        if len(self._prefix_messages) == 0:
            self._prefix_messages = [message]
        else:
            self._prefix_messages[0] = message

    async def achat(self, *args, **kwargs):
        pass

    async def astream_chat(self, *args, **kwargs):
        pass

    def append_conversation_messages(
        self,
        conversation,
        user_message: str,
        assistant_message: Optional[str] = None,
    ) -> None:
        """
        Append user and assistant messages to the conversation value.
        Always store with both 'content' and 'blocks' fields for compatibility and persistence.
        """
        import datetime

        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        # Use fallback values if self.agent is not set
        username = getattr(getattr(self, "agent", None), "username", "User")
        botname = getattr(getattr(self, "agent", None), "botname", "Computer")
        conversation.value.append(
            {
                "role": "user",
                "name": username,
                "content": user_message,
                "timestamp": now,
                "blocks": [{"block_type": "text", "text": user_message}],
            }
        )
        if assistant_message is not None:
            conversation.value.append(
                {
                    "role": "assistant",
                    "name": botname,
                    "content": assistant_message,
                    "timestamp": now,
                    "blocks": [
                        {"block_type": "text", "text": assistant_message}
                    ],
                }
            )
        # Optionally, trigger persistence if needed (depends on agent/manager logic)
        if hasattr(self, "agent") and hasattr(
            self.agent, "_update_conversation_state"
        ):
            self.agent._update_conversation_state(conversation)
