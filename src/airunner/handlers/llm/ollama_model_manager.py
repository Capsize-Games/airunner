import asyncio
from typing import Optional, Type, AsyncGenerator, Sequence, Any
from llama_index.core.llms.llm import LLM
from llama_index.core.base.llms.types import ChatMessage, CompletionResponse
from llama_index.core.base.llms.types import (
    ChatResponseGen,
    ChatResponseAsyncGen,
)
from llama_index.core.chat_engine.types import AgentChatResponse
import openai
from airunner.handlers.llm.agent.agents import OpenRouterQObject
from airunner.handlers.llm.agent.agents.local import LocalAgent
from airunner.handlers.llm.llm_model_manager import LLMModelManager
from airunner.enums import LLMActionType, ModelType, ModelStatus
from airunner.handlers.llm.llm_request import OpenrouterMistralRequest
from airunner.utils.settings.get_qsettings import get_qsettings
from llama_index.llms.ollama import Ollama
import ollama

try:
    from PyQt5.QtCore import QMetaObject, Qt
except ImportError:
    try:
        from PyQt6.QtCore import QMetaObject, Qt
    except ImportError:
        try:
            from PySide2.QtCore import QMetaObject, Qt
        except ImportError:
            QMetaObject = None
            Qt = None


class OllamaEnhanced(Ollama):
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
            raise

    def stream_chat(
        self, messages: Sequence[ChatMessage], **kwargs: Any
    ) -> ChatResponseGen:
        self._cancel_event.clear()
        tried_pull = False
        while True:
            try:
                for response in super().stream_chat(messages, **kwargs):
                    if self._cancel_event.is_set():
                        break
                    yield response
                break  # Success, exit loop
            except Exception as e:
                if (
                    not tried_pull
                    and hasattr(e, "args")
                    and any(
                        "not found, try pulling it first" in str(arg)
                        for arg in e.args
                    )
                ):
                    import subprocess
                    import sys
                    import re
                    from airunner.api.api import API

                    model_name = getattr(self, "model", None) or kwargs.get(
                        "model"
                    )
                    if not model_name:
                        raise  # Can't determine model name
                    print(
                        f"Model '{model_name}' not found. Downloading with ollama..."
                    )
                    try:
                        process = subprocess.Popen(
                            ["ollama", "pull", model_name],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            text=True,
                        )
                        API().llm_model_download_progress(0)
                        for line in process.stdout:
                            match = re.search(r"(\d+)%", line)
                            if match:
                                progress = int(match.group(1))
                                API().llm_model_download_progress(progress)
                            else:
                                print(line, end="")
                        process.wait()
                        API().llm_model_download_progress(100)
                        print(f"\nModel '{model_name}' download complete.")
                    except Exception as ex:
                        API().llm_model_download_progress(0)
                        print(f"Error running ollama pull: {ex}")
                        raise
                    tried_pull = True
                    continue  # Retry
                raise  # Other errors, or already tried pull

    def interrupt_process(self):
        """Interrupt the process."""
        # Set the cancel event to stop streaming
        self._cancel_event.set()

    def unload(self):
        pass


class OllamaQObject(LocalAgent):
    @property
    def llm(self) -> Type[LLM]:
        if not self._llm:
            llm_request = OpenrouterMistralRequest.from_default()
            # Get API key from ApplicationSettings
            settings = get_qsettings()
            api_key = settings.value("openrouter/api_key", None)

            if not api_key:
                self.logger.warning("No OpenRouter API key found in settings")
                return None

            try:
                self._llm = OllamaEnhanced(
                    model=self.llm_generator_settings.model_path,
                    api_key=api_key,
                    **llm_request.to_dict(),
                )
            except openai.APIError as e:
                print(f"Failed to initialize OpenRouterEnhanced: {e}")

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
        llm_request: Optional[OpenrouterMistralRequest] = None,
    ) -> AgentChatResponse:
        llm_request = llm_request or OpenrouterMistralRequest.from_default()
        return super().chat(
            message=message,
            action=action,
            system_prompt=system_prompt,
            rag_system_prompt=rag_system_prompt,
            llm_request=llm_request,
            **llm_request.to_dict(),
        )


class OllamaModelManager(LLMModelManager):
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
        self._chat_agent = OllamaQObject(llm_settings=self.llm_settings)
        self.logger.info("Chat agent loaded")
