"""Custom LangChain adapter for locally-loaded HuggingFace models."""

from typing import Any, List, Optional, Iterator
import torch
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    BaseMessage,
    AIMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.callbacks.manager import CallbackManagerForLLMRun


class ChatHuggingFaceLocal(BaseChatModel):
    """
    LangChain ChatModel adapter for locally-loaded HuggingFace models.

    This adapter wraps a pre-loaded HuggingFace model and tokenizer,
    allowing them to work with LangChain's agent system.

    Attributes:
        model: The loaded HuggingFace model
        tokenizer: The loaded HuggingFace tokenizer
        max_new_tokens: Maximum tokens to generate
        temperature: Sampling temperature
        top_p: Nucleus sampling parameter
        top_k: Top-k sampling parameter
        repetition_penalty: Penalty for repeating tokens
        do_sample: Whether to use sampling
    """

    model: Any
    tokenizer: Any
    max_new_tokens: int = 500
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 50
    repetition_penalty: float = 1.15
    do_sample: bool = True

    class Config:
        arbitrary_types_allowed = True

    @property
    def _llm_type(self) -> str:
        """Return type of language model."""
        return "huggingface_local"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Generate response from messages."""
        # Convert messages to prompt text
        prompt = self._messages_to_prompt(messages)

        # Tokenize
        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=2048,
        ).to(self.model.device)

        # Generate
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=kwargs.get(
                    "max_new_tokens", self.max_new_tokens
                ),
                temperature=kwargs.get("temperature", self.temperature),
                top_p=kwargs.get("top_p", self.top_p),
                top_k=kwargs.get("top_k", self.top_k),
                repetition_penalty=kwargs.get(
                    "repetition_penalty", self.repetition_penalty
                ),
                do_sample=kwargs.get("do_sample", self.do_sample),
                pad_token_id=self.tokenizer.eos_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
            )

        # Decode only the new tokens (skip the input prompt)
        input_length = inputs["input_ids"].shape[1]
        generated_tokens = outputs[0][input_length:]
        response_text = self.tokenizer.decode(
            generated_tokens, skip_special_tokens=True
        )

        # Create chat generation
        message = AIMessage(content=response_text)
        generation = ChatGeneration(message=message)

        return ChatResult(generations=[generation])

    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Iterator[ChatGeneration]:
        """Stream response from messages."""
        # For now, use non-streaming generation
        # TODO: Implement proper streaming with TextIteratorStreamer
        result = self._generate(messages, stop, run_manager, **kwargs)
        yield result.generations[0]

    def _messages_to_prompt(self, messages: List[BaseMessage]) -> str:
        """Convert LangChain messages to prompt text."""
        # Use tokenizer's chat template if available
        if hasattr(self.tokenizer, "apply_chat_template"):
            # Convert to format expected by chat template
            chat_messages = []
            for msg in messages:
                if isinstance(msg, SystemMessage):
                    chat_messages.append(
                        {"role": "system", "content": msg.content}
                    )
                elif isinstance(msg, HumanMessage):
                    chat_messages.append(
                        {"role": "user", "content": msg.content}
                    )
                elif isinstance(msg, AIMessage):
                    chat_messages.append(
                        {"role": "assistant", "content": msg.content}
                    )

            return self.tokenizer.apply_chat_template(
                chat_messages, tokenize=False, add_generation_prompt=True
            )

        # Fallback: simple concatenation
        prompt_parts = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                prompt_parts.append(f"System: {msg.content}")
            elif isinstance(msg, HumanMessage):
                prompt_parts.append(f"User: {msg.content}")
            elif isinstance(msg, AIMessage):
                prompt_parts.append(f"Assistant: {msg.content}")

        prompt_parts.append("Assistant:")
        return "\n\n".join(prompt_parts)
