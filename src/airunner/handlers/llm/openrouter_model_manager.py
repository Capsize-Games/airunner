from airunner.handlers.llm.agent.agents import OpenRouterQObject
from airunner.handlers.llm.llm_model_manager import LLMModelManager
from airunner.enums import ModelType, ModelStatus


class OpenRouterModelManager(LLMModelManager):
    def _load_tokenizer(self):
        pass

    def _load_model(self):
        pass

    def _update_model_status(self):
        if self._chat_agent:
            self.change_model_status(ModelType.LLM, ModelStatus.LOADED)

    def _load_agent(self) -> None:
        """
        Load the appropriate chat agent based on settings.

        Sets self._chat_agent to the loaded agent instance or None if loading fails.
        """
        # Skip if already loaded
        if self._chat_agent is not None:
            return
        self._chat_agent = OpenRouterQObject(llm_settings=self.llm_settings)
        self.logger.info("Chat agent loaded")
