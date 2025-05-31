from airunner.handlers.llm.agent.engines.base_conversation_engine import (
    BaseConversationEngine,
)


class RefreshSimpleChatEngine(BaseConversationEngine):
    def __init__(self, agent, *args, **kwargs):
        super().__init__(agent)
        # ...existing code...
