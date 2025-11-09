"""Message formatting operations for HuggingFace chat models."""

from typing import List
from langchain_core.messages import (
    BaseMessage,
    AIMessage,
    HumanMessage,
    SystemMessage,
)

# Mistral native function calling support
try:
    from mistral_common.protocol.instruct.tool_calls import Function, Tool
    from mistral_common.protocol.instruct.messages import (
        UserMessage as MistralUserMessage,
        AssistantMessage as MistralAssistantMessage,
        SystemMessage as MistralSystemMessage,
    )
    from mistral_common.protocol.instruct.request import ChatCompletionRequest

    MISTRAL_AVAILABLE = True
except ImportError:
    MISTRAL_AVAILABLE = False


class MessageFormattingMixin:
    """Handles message formatting for chat models.

    This mixin provides functionality for:
    - Converting LangChain messages to prompts
    - Converting messages to Mistral native tokens
    - Applying chat templates
    """

    def _messages_to_prompt(self, messages: List[BaseMessage]) -> str:
        """Convert LangChain messages to prompt text.

        For Mistral native mode, this returns tokens as a string representation.
        For standard mode, it uses the tokenizer's chat template or fallback.

        Args:
            messages: List of LangChain messages

        Returns:
            Formatted prompt string or token list
        """
        if self.use_mistral_native and self._mistral_tokenizer and self.tools:
            return self._messages_to_mistral_tokens(messages)

        if not self.tokenizer and self.model_path:
            return self._handle_no_tokenizer(messages)

        if self.tokenizer and hasattr(self.tokenizer, "apply_chat_template"):
            return self._apply_chat_template(messages)

        return self._fallback_format(messages)

    def _handle_no_tokenizer(self, messages: List[BaseMessage]):
        """Handle case where no HuggingFace tokenizer is available.

        Args:
            messages: List of LangChain messages

        Returns:
            Formatted tokens or raises error
        """
        if not self._mistral_tokenizer:
            self._init_mistral_tokenizer()

        if self._mistral_tokenizer:
            return self._messages_to_mistral_tokens(messages)
        else:
            raise ValueError(
                "No tokenizer available for Mistral3 model. "
                "Ensure mistral_common is installed and tekken.json exists."
            )

    def _apply_chat_template(self, messages: List[BaseMessage]) -> str:
        """Apply tokenizer's chat template to messages.

        For Qwen models with JSON mode tool calling, this will format tools
        into the chat template according to the model's requirements.

        Args:
            messages: List of LangChain messages

        Returns:
            Formatted prompt string
        """
        chat_messages = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                chat_messages.append(
                    {"role": "system", "content": msg.content}
                )
            elif isinstance(msg, HumanMessage):
                chat_messages.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                chat_messages.append(
                    {"role": "assistant", "content": msg.content}
                )

        # Check if we have tools to pass to the template
        template_kwargs = {
            "tokenize": False,
            "add_generation_prompt": True,
        }

        # Pass tools ONLY if available, non-empty, AND we're in a tool-supporting mode
        # For JSON mode (Qwen), tools should be passed to the template
        # BUT only if tools are actually bound to the model
        if (
            hasattr(self, "tools")
            and self.tools
            and len(self.tools) > 0
            and hasattr(self, "tool_calling_mode")
            and self.tool_calling_mode == "json"
        ):
            template_kwargs["tools"] = self.tools

        return self.tokenizer.apply_chat_template(
            chat_messages, **template_kwargs
        )

    def _fallback_format(self, messages: List[BaseMessage]) -> str:
        """Simple fallback formatting when no chat template available.

        Args:
            messages: List of LangChain messages

        Returns:
            Simple formatted prompt string
        """
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

    def _messages_to_mistral_tokens(
        self, messages: List[BaseMessage]
    ) -> List[int]:
        """Convert messages to Mistral tokens using native function calling format.

        Args:
            messages: List of LangChain messages

        Returns:
            List of Mistral token IDs
        """
        mistral_tools = self._convert_tools_to_mistral()
        self.logger.debug(f"Encoding {len(mistral_tools)} tools for Mistral")

        mistral_messages = self._convert_messages_to_mistral(messages)
        self.logger.debug(
            f"Converting {len(mistral_messages)} messages to Mistral format"
        )

        completion_request = ChatCompletionRequest(
            tools=mistral_tools, messages=mistral_messages
        )

        tokens = self._mistral_tokenizer.encode_chat_completion(
            completion_request
        ).tokens

        self.logger.debug(f"Encoded to {len(tokens)} tokens")
        return tokens

    def _convert_tools_to_mistral(self) -> List:
        """Convert LangChain tools to Mistral Tool format.

        Returns:
            List of Mistral Tool objects
        """
        mistral_tools = []
        for tool in self.tools:
            mistral_tools.append(
                Tool(
                    function=Function(
                        name=tool["function"]["name"],
                        description=tool["function"]["description"],
                        parameters=tool["function"].get("parameters", {}),
                    )
                )
            )
        return mistral_tools

    def _convert_messages_to_mistral(
        self, messages: List[BaseMessage]
    ) -> List:
        """Convert LangChain messages to Mistral message format.

        Args:
            messages: List of LangChain messages

        Returns:
            List of Mistral message objects
        """
        mistral_messages = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                mistral_messages.append(
                    MistralSystemMessage(content=msg.content)
                )
            elif isinstance(msg, HumanMessage):
                mistral_messages.append(
                    MistralUserMessage(content=msg.content)
                )
            elif isinstance(msg, AIMessage):
                mistral_messages.append(
                    MistralAssistantMessage(content=msg.content)
                )
        return mistral_messages
