from typing import Any, Callable, List, Optional, Sequence, Union, Dict
import torch
from llama_index.core.base.llms.types import (
    ChatMessage,
    ChatResponse,
    ChatResponseGen,
    CompletionResponse,
    CompletionResponseGen,
    LLMMetadata,
)
from llama_index.core.bridge.pydantic import Field, PrivateAttr
from llama_index.core.callbacks import CallbackManager
from llama_index.core.constants import (
    DEFAULT_CONTEXT_WINDOW,
    DEFAULT_NUM_OUTPUTS,
)
from llama_index.core.llms.callbacks import (
    llm_chat_callback,
    llm_completion_callback,
)
from llama_index.core.llms.custom import CustomLLM
from llama_index.core.base.llms.generic_utils import (
    completion_response_to_chat_response,
    stream_completion_response_to_chat_response,
    messages_to_prompt as generic_messages_to_prompt,
)
from llama_index.core.prompts.base import PromptTemplate
from llama_index.core.types import (
    BaseOutputParser,
    PydanticProgramMode,
    Thread,
)
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    StoppingCriteria,
    StoppingCriteriaList,
)

from airunner.gui.windows.main.settings_mixin import SettingsMixin
from airunner.settings import AIRUNNER_DEFAULT_LLM_HF_PATH
from airunner.handlers.llm.llm_request import LLMRequest


class HuggingFaceLLM(CustomLLM, SettingsMixin):
    """
    HuggingFace LLM integration for AI Runner.

    This class provides an interface between AI Runner and HuggingFace models,
    allowing for text completion and chat functionality with various models.
    """

    model_name: str = Field(
        default=AIRUNNER_DEFAULT_LLM_HF_PATH,
        description="The model name to use from HuggingFace. Unused if `model` is passed directly.",
    )
    model: Optional[Any] = Field(
        default=None,
        description="The model to use. If not passed in, will be loaded from `model_name`.",
    )
    context_window: int = Field(
        default=DEFAULT_CONTEXT_WINDOW,
        description="The maximum number of tokens available for input.",
        gt=0,
    )
    max_new_tokens: int = Field(
        default=DEFAULT_NUM_OUTPUTS,
        description="The maximum number of tokens to generate.",
        gt=0,
    )
    system_prompt: str = Field(
        default="",
        description="The system prompt with extra instructions or context.",
    )
    query_wrapper_prompt: PromptTemplate = Field(
        default=PromptTemplate("{query_str}"),
        description="The query wrapper prompt containing the query placeholder.",
    )
    tokenizer_name: str = Field(
        default=AIRUNNER_DEFAULT_LLM_HF_PATH,
        description="The name of the tokenizer to use from HuggingFace.",
    )
    device_map: str = Field(
        default="auto",
        description="The device_map to use. Defaults to 'auto'.",
    )
    stopping_ids: List[int] = Field(
        default_factory=list,
        description="Token IDs that signal generation should stop when predicted.",
    )
    tokenizer_outputs_to_remove: list = Field(
        default_factory=list,
        description="Outputs to remove from the tokenizer to prevent errors.",
    )
    tokenizer_kwargs: Dict = Field(
        default_factory=dict,
        description="The kwargs to pass to the tokenizer.",
    )
    model_kwargs: Dict = Field(
        default_factory=dict,
        description="The kwargs to pass to the model during initialization.",
    )

    _llm_request: Optional[LLMRequest] = None

    @property
    def generate_kwargs(self) -> Dict:
        """
        Get generation parameters from the LLM request.

        Returns:
            Dict: Dictionary of generation parameters.
        """
        if self.llm_request:
            data = self.llm_request.to_dict()

            # Remove unused keys
            del data["do_tts_reply"]
            return data
        return {}

    @property
    def llm_request(self) -> Optional[LLMRequest]:
        """
        Get the current LLM request, initializing with defaults if needed.

        Returns:
            Optional[LLMRequest]: The current LLM request configuration.
        """
        if self._llm_request is None:
            self._llm_request = LLMRequest.from_default()
        return self._llm_request

    @llm_request.setter
    def llm_request(self, value: Optional[LLMRequest]):
        """
        Set the LLM request configuration.

        Args:
            value: The new LLM request configuration.
        """
        self._llm_request = value

    is_chat_model: bool = Field(
        default=False,
        description="Whether the model is designed for chat interactions.",
    )

    _model: Any = PrivateAttr()
    _tokenizer: Any = PrivateAttr()
    _stopping_criteria: Any = PrivateAttr()
    _streaming_stopping_criteria: Any = PrivateAttr(default=None)

    def __init__(
        self,
        context_window: int = DEFAULT_CONTEXT_WINDOW,
        max_new_tokens: int = DEFAULT_NUM_OUTPUTS,
        query_wrapper_prompt: Union[str, PromptTemplate] = "{query_str}",
        tokenizer_name: str = AIRUNNER_DEFAULT_LLM_HF_PATH,
        model_name: str = AIRUNNER_DEFAULT_LLM_HF_PATH,
        model: Optional[Any] = None,
        tokenizer: Optional[Any] = None,
        device_map: Optional[str] = "auto",
        stopping_ids: Optional[List[int]] = None,
        tokenizer_kwargs: Optional[Dict] = None,
        tokenizer_outputs_to_remove: Optional[list] = None,
        model_kwargs: Optional[Dict] = None,
        generate_kwargs: Optional[Dict] = None,
        is_chat_model: Optional[bool] = False,
        callback_manager: Optional[CallbackManager] = None,
        system_prompt: str = "",
        messages_to_prompt: Optional[
            Callable[[Sequence[ChatMessage]], str]
        ] = None,
        completion_to_prompt: Optional[Callable[[str], str]] = None,
        pydantic_program_mode: PydanticProgramMode = PydanticProgramMode.DEFAULT,
        output_parser: Optional[BaseOutputParser] = None,
        streaming_stopping_criteria: Optional[StoppingCriteria] = None,
    ) -> None:
        """
        Initialize the HuggingFace LLM.

        Args:
            context_window: Maximum tokens for input context.
            max_new_tokens: Maximum tokens to generate.
            query_wrapper_prompt: Template for wrapping queries.
            tokenizer_name: Name of the HuggingFace tokenizer.
            model_name: Name of the HuggingFace model.
            model: Pre-loaded model instance (optional).
            tokenizer: Pre-loaded tokenizer instance (optional).
            device_map: Device mapping strategy.
            stopping_ids: Token IDs that signal generation should stop.
            tokenizer_kwargs: Additional kwargs for tokenizer initialization.
            tokenizer_outputs_to_remove: Tokenizer outputs to remove.
            model_kwargs: Additional kwargs for model initialization.
            generate_kwargs: Additional kwargs for generation.
            is_chat_model: Whether the model is designed for chat interactions.
            callback_manager: Manager for callbacks.
            system_prompt: System prompt for additional context.
            messages_to_prompt: Function to convert chat messages to prompt.
            completion_to_prompt: Function to convert completion to prompt.
            pydantic_program_mode: Mode for Pydantic program generation.
            output_parser: Parser for model outputs.
            streaming_stopping_criteria: Criteria for stopping streaming.
        """
        model_kwargs = model_kwargs or {}
        model = model or AutoModelForCausalLM.from_pretrained(
            model_name, device_map=device_map, **model_kwargs
        )

        # Check context_window against model's capabilities
        config_dict = model.config.to_dict()
        model_context_window = int(
            config_dict.get("max_position_embeddings", context_window)
        )
        if model_context_window and model_context_window < context_window:
            self.logger.warning(
                f"Supplied context_window {context_window} is greater "
                f"than the model's max input size {model_context_window}. "
                "Using model's max input size instead."
            )
            context_window = model_context_window

        # Initialize tokenizer
        tokenizer_kwargs = tokenizer_kwargs or {}
        tokenizer = tokenizer or AutoTokenizer.from_pretrained(
            tokenizer_name, **tokenizer_kwargs
        )

        # Set up stopping criteria
        stopping_ids_list = stopping_ids or []

        class StopOnTokens(StoppingCriteria):
            """Stopping criteria that stops generation when specific tokens are generated."""

            def __call__(
                self,
                input_ids: torch.LongTensor,
                scores: torch.FloatTensor,
                **kwargs: Any,
            ) -> bool:
                for stop_id in stopping_ids_list:
                    if input_ids[0][-1] == stop_id:
                        return True
                return False

        stopping_criteria = StoppingCriteriaList([StopOnTokens()])

        # Convert string prompt template to PromptTemplate if needed
        if isinstance(query_wrapper_prompt, str):
            query_wrapper_prompt = PromptTemplate(query_wrapper_prompt)

        # Use tokenizer-specific method or fallback to generic for messages_to_prompt
        messages_to_prompt = (
            messages_to_prompt or self._tokenizer_messages_to_prompt
        )

        super().__init__(
            context_window=context_window,
            max_new_tokens=max_new_tokens,
            query_wrapper_prompt=query_wrapper_prompt,
            tokenizer_name=tokenizer_name,
            model_name=model_name,
            device_map=device_map,
            stopping_ids=stopping_ids or [],
            tokenizer_kwargs=tokenizer_kwargs or {},
            tokenizer_outputs_to_remove=tokenizer_outputs_to_remove or [],
            model_kwargs=model_kwargs or {},
            generate_kwargs=generate_kwargs or {},
            is_chat_model=is_chat_model,
            callback_manager=callback_manager,
            system_prompt=system_prompt,
            messages_to_prompt=messages_to_prompt,
            completion_to_prompt=completion_to_prompt,
            pydantic_program_mode=pydantic_program_mode,
            output_parser=output_parser,
        )

        self._model = model
        self._tokenizer = tokenizer
        self._stopping_criteria = stopping_criteria

        # Set up streaming stopping criteria if provided
        if streaming_stopping_criteria:
            self._streaming_stopping_criteria = StoppingCriteriaList(
                [streaming_stopping_criteria, StopOnTokens()]
            )
        else:
            self._streaming_stopping_criteria = stopping_criteria

    @property
    def model(self):
        """Get the underlying HuggingFace model."""
        return self._model

    @property
    def tokenizer(self):
        """Get the underlying HuggingFace tokenizer."""
        return self._tokenizer

    @classmethod
    def class_name(cls) -> str:
        """Get the class name for registration."""
        return "HuggingFace_LLM"

    @property
    def metadata(self) -> LLMMetadata:
        """
        Get LLM metadata.

        Returns:
            LLMMetadata: Metadata about the model capabilities.
        """
        return LLMMetadata(
            context_window=self.context_window,
            num_output=self.max_new_tokens,
            model_name=self.model_name,
            is_chat_model=self.is_chat_model,
            is_function_calling_model=True,
        )

    def unload(self):
        """
        Unload the model and tokenizer from memory.

        This method helps with resource management by releasing GPU memory.
        """
        self.logger.debug("Unloading HuggingFace LLM")
        del self._model
        del self._tokenizer
        del self._stopping_criteria
        self._model = None
        self._tokenizer = None
        self._stopping_criteria = None

    def _tokenizer_messages_to_prompt(
        self, messages: Sequence[ChatMessage]
    ) -> str:
        """
        Convert chat messages to a prompt string using the tokenizer.

        Uses the tokenizer's chat template if available, otherwise falls back
        to generic conversion.

        Args:
            messages: Sequence of chat messages to convert.

        Returns:
            str: Prompt string suitable for the model.
        """
        if hasattr(self._tokenizer, "apply_chat_template"):
            messages_dict = [
                {"role": message.role.value, "content": message.content}
                for message in messages
            ]
            return self._tokenizer.apply_chat_template(
                messages_dict, tokenize=False, add_generation_prompt=True
            )
        return generic_messages_to_prompt(messages)

    @llm_completion_callback()
    def complete(
        self, prompt: str, formatted: bool = False, **kwargs: Any
    ) -> CompletionResponse:
        """
        Generate a completion for the given prompt.

        Args:
            prompt: The input prompt for text generation.
            formatted: Whether the prompt is already formatted.
            **kwargs: Additional keyword arguments for completion.

        Returns:
            CompletionResponse: The model's generated response.
        """
        full_prompt = prompt
        if not formatted:
            if self.query_wrapper_prompt:
                full_prompt = self.query_wrapper_prompt.format(
                    query_str=prompt
                )
            if self.completion_to_prompt:
                full_prompt = self.completion_to_prompt(full_prompt)
            elif self.system_prompt:
                full_prompt = f"{self.system_prompt} {full_prompt}"

        # Tokenize the prompt
        inputs = self._tokenizer(full_prompt, return_tensors="pt")
        inputs = inputs.to(self._model.device)

        # Remove keys from the tokenizer if needed, to avoid HF errors
        for key in self.tokenizer_outputs_to_remove:
            if key in inputs:
                inputs.pop(key, None)

        # Generate response
        tokens = self._model.generate(
            **inputs,
            stopping_criteria=self._stopping_criteria,
            **self.generate_kwargs,
        )

        # Extract and decode the generated text
        completion_tokens = tokens[0][inputs["input_ids"].size(1) :]
        completion = self._tokenizer.decode(
            completion_tokens, skip_special_tokens=True
        )

        return CompletionResponse(
            text=completion, raw={"model_output": tokens}
        )

    @llm_completion_callback()
    def stream_complete(
        self, prompt: str, formatted: bool = False, **kwargs: Any
    ) -> CompletionResponseGen:
        """
        Stream a completion for the given prompt.

        Args:
            prompt: The input prompt for text generation.
            formatted: Whether the prompt is already formatted.
            **kwargs: Additional keyword arguments for completion.

        Returns:
            CompletionResponseGen: Generator yielding parts of the response as they're generated.
        """
        from transformers import TextIteratorStreamer

        full_prompt = prompt
        if not formatted:
            if self.query_wrapper_prompt:
                full_prompt = self.query_wrapper_prompt.format(
                    query_str=prompt
                )
            if self.system_prompt:
                full_prompt = f"{self.system_prompt} {full_prompt}"

        # Tokenize the prompt
        inputs = self._tokenizer(full_prompt, return_tensors="pt")
        inputs = inputs.to(self._model.device)

        # Remove keys from the tokenizer if needed, to avoid HF errors
        for key in self.tokenizer_outputs_to_remove:
            if key in inputs:
                inputs.pop(key, None)

        # Set up streaming
        streamer = TextIteratorStreamer(
            self._tokenizer, skip_prompt=True, skip_special_tokens=True
        )

        generation_kwargs = dict(
            inputs,
            stopping_criteria=self._streaming_stopping_criteria,
            **self.generate_kwargs,
        )
        generation_kwargs["streamer"] = streamer

        # Generate in background thread
        thread = Thread(target=self._model.generate, kwargs=generation_kwargs)
        thread.start()

        # Create generator based on streamer
        def gen() -> CompletionResponseGen:
            text = ""
            for x in streamer:
                text += x
                yield CompletionResponse(text=text, delta=x)

        return gen()

    @llm_chat_callback()
    def chat(
        self, messages: Sequence[ChatMessage], **kwargs: Any
    ) -> ChatResponse:
        """
        Generate a chat response for the given messages.

        Args:
            messages: Sequence of chat messages for the conversation.
            **kwargs: Additional keyword arguments for chat.

        Returns:
            ChatResponse: The model's generated chat response.
        """
        prompt = self.messages_to_prompt(messages)
        completion_response = self.complete(prompt, formatted=True, **kwargs)
        return completion_response_to_chat_response(completion_response)

    @llm_chat_callback()
    def stream_chat(
        self, messages: Sequence[ChatMessage], **kwargs: Any
    ) -> ChatResponseGen:
        """
        Stream a chat response for the given messages.

        Args:
            messages: Sequence of chat messages for the conversation.
            **kwargs: Additional keyword arguments for chat.

        Returns:
            ChatResponseGen: Generator yielding parts of the chat response as they're generated.
        """
        prompt = self.messages_to_prompt(messages)
        completion_response = self.stream_complete(
            prompt, formatted=True, **kwargs
        )
        return stream_completion_response_to_chat_response(completion_response)
