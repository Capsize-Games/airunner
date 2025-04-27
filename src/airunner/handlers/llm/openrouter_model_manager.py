from airunner.handlers.llm.agent.agents import OpenRouterQObject
from airunner.handlers.llm.llm_model_manager import LLMModelManager


class OpenRouterModelManager(LLMModelManager):
    def _load_agent(self) -> None:
        """
        Load the chat agent.
        """
        if self._chat_agent is not None:
            return
        self.logger.debug("Loading agent")
        self.logger.info("Loading openrouter chat agent")
        self._chat_agent = OpenRouterQObject(llm_settings=self.llm_settings)
        self.logger.info("Chat agent loaded")
