from typing import Type, Optional

from llama_index.core.llms.llm import LLM
from llama_index.llms.openrouter import OpenRouter
from llama_index.core.chat_engine.types import AgentChatResponse

from airunner.enums import LLMActionType
from airunner.handlers.llm.llm_request import OpenrouterMistralRequest
from airunner.handlers.llm.agent.agents.local import MistralAgentQObject


class OpenRouterQObject(
    MistralAgentQObject
):
    @property
    def llm(self) -> Type[LLM]:
        if not self._llm:
            llm_request = OpenrouterMistralRequest.from_default()
            self._llm = OpenRouter(
                model=self.llm_settings.model,
                api_key=self.llm_settings.openrouter_api_key,
                **llm_request.to_dict()
            )
        return self._llm
    
    def chat(
        self,
        message: str,
        action: LLMActionType = LLMActionType.CHAT,
        system_prompt: Optional[str] = None,
        rag_system_prompt: Optional[str] = None,
        llm_request: Optional[OpenrouterMistralRequest] = None
    ) -> AgentChatResponse:
        llm_request = llm_request or OpenrouterMistralRequest.from_default()
        return super().chat(
            message=message,
            action=action,
            system_prompt=system_prompt,
            rag_system_prompt=rag_system_prompt,
            llm_request=llm_request,
            **llm_request.to_dict()
        )

