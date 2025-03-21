from typing import Type, Optional

from PySide6.QtCore import QObject

from llama_index.core.llms.llm import LLM
from llama_index.llms.openrouter import OpenRouter
from llama_index.core.chat_engine.types import AgentChatResponse

from airunner.mediator_mixin import MediatorMixin
from airunner.windows.main.settings_mixin import SettingsMixin
from airunner.handlers.llm.agent.agents.base import BaseAgent
from airunner.handlers.llm.llm_request import LLMRequest
from airunner.enums import LLMActionType
from airunner.handlers.llm.agent.agents.local import MistralAgentQObject


class OpenRouterQObject(
    MistralAgentQObject
):
    @property
    def llm(self) -> Type[LLM]:
        if not self._llm:
            llm_request = LLMRequest.from_default()
            self._llm = OpenRouter(
                model=self.llm_settings.model,
                api_key=self.llm_settings.openrouter_api_key,
                temperature=llm_request.temperature,
                max_tokens=llm_request.max_new_tokens,
            )
        return self._llm
    
    def chat(
        self,
        message: str,
        action: LLMActionType = LLMActionType.CHAT,
        system_prompt: Optional[str] = None,
        rag_system_prompt: Optional[str] = None,
        llm_request: Optional[LLMRequest] = None
    ) -> AgentChatResponse:
        llm_request = llm_request or LLMRequest.from_default()
        self.llm.temperature = llm_request.temperature
        self.llm.max_tokens = llm_request.max_new_tokens
        return super().chat(
            message=message,
            action=action,
            system_prompt=system_prompt,
            rag_system_prompt=rag_system_prompt,
            llm_request=llm_request
        )

