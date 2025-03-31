from typing import Type, Optional, Any

from llama_index.core.llms.llm import LLM
from llama_index.llms.openrouter import OpenRouter
from llama_index.core.chat_engine.types import AgentChatResponse

from airunner.enums import LLMActionType
from airunner.handlers.llm.llm_request import OpenrouterMistralRequest
from airunner.handlers.llm.agent.agents.local import LocalAgent


import asyncio
from typing import AsyncGenerator, Sequence
from llama_index.core.base.llms.types import ChatResponseGen, ChatResponseAsyncGen
from llama_index.core.base.llms.types import ChatMessage, ChatResponse, CompletionResponse
from llama_index.llms.openai.base import OpenAI


class OpenRouterEnhanced(OpenRouter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cancel_event = asyncio.Event()

    async def astream_complete(
        self, prompt: str, formatted: bool = False, **kwargs: Any
    ) -> AsyncGenerator[CompletionResponse, None]:
        if not formatted:
            prompt = self.completion_to_prompt(prompt)

        # Reset the cancel event before starting the streaming
        self._cancel_event.clear()

        try:
            async for response in super().astream_complete(prompt, **kwargs):
                if self._cancel_event.is_set():
                    break
                yield response
        except asyncio.CancelledError:
            # Handle any cleanup if necessary
            raise

    async def astream_chat(
        self, messages: Sequence[ChatMessage], **kwargs: Any
    ) -> ChatResponseAsyncGen:
        # Reset the cancel event before starting the streaming
        self._cancel_event.clear()

        try:
            async for response in super().astream_chat(messages, **kwargs):
                if self._cancel_event.is_set():
                    break
                yield response
        except asyncio.CancelledError:
            # Handle any cleanup if necessary
            raise

    def stream_chat(
        self, messages: Sequence[ChatMessage], **kwargs: Any
    ) -> ChatResponseGen:
        # Reset the cancel event before starting the streaming
        self._cancel_event.clear()

        try:
            for response in super().stream_chat(messages, **kwargs):
                if self._cancel_event.is_set():
                    break
                yield response
        except asyncio.CancelledError:
            # Handle any cleanup if necessary
            raise
        # Handle any cleanup if necessary

    def interrupt_process(self):
        """Interrupt the process."""
        # Set the cancel event to stop streaming
        self._cancel_event.set()



class OpenRouterQObject(
    LocalAgent
):
    @property
    def llm(self) -> Type[LLM]:
        if not self._llm:
            llm_request = OpenrouterMistralRequest.from_default()
            self._llm = OpenRouterEnhanced(
                model=self.llm_settings.model,
                api_key=self.llm_settings.openrouter_api_key,
                **llm_request.to_dict()
            )
        return self._llm
    
    def interrupt_process(self):
        if self._llm:
            self._llm.interrupt_process()

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

