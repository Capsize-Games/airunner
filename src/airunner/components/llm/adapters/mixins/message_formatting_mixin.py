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

    def _check_model_supports_thinking(self) -> bool:
        """Check if the current model supports thinking mode.
        
        Currently only Qwen3 models support the enable_thinking parameter
        with <think>...</think> reasoning blocks.
        
        Returns:
            True if the model supports thinking mode, False otherwise.
        """
        # Check model_path attribute
        model_path = getattr(self, "model_path", None)
        if not model_path:
            return False
        
        model_path_lower = str(model_path).lower()
        
        # Check LLMProviderConfig.LOCAL_MODELS for supports_thinking
        from airunner.components.llm.config.provider_config import LLMProviderConfig
        
        for model_config in LLMProviderConfig.LOCAL_MODELS.values():
            repo_id = model_config.get("repo_id", "")
            if not repo_id:
                continue
            
            # Extract model name from repo_id
            model_name = repo_id.split("/")[-1].lower()
            
            # Match if model name appears in path
            if model_name in model_path_lower or model_path_lower in model_name:
                return model_config.get("supports_thinking", False)
        
        # Fallback: Check for "qwen3" in the model path (covers custom paths)
        if "qwen3" in model_path_lower:
            return True
        
        return False

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
        from langchain_core.messages import ToolMessage
        
        chat_messages = []
        extracted_images = []  # Store image payloads for vision models
        image_placeholders = 0  # Count of image placeholders in content
        
        for msg in messages:
            if isinstance(msg, SystemMessage):
                chat_messages.append(
                    {"role": "system", "content": msg.content}
                )
            elif isinstance(msg, HumanMessage):
                # Only keep images from the most recent human turn to avoid
                # re-sending stale or missing binaries from older turns.
                extracted_images = []
                image_placeholders = 0
                # Handle multimodal content (list with text and images)
                if isinstance(msg.content, list):
                    content_parts = []
                    for part in msg.content:
                        if isinstance(part, dict):
                            if part.get("type") == "text":
                                content_parts.append(part)
                            elif part.get("type") == "image_url":
                                content_parts.append({"type": "image"})
                                image_url = part.get("image_url", {}).get("url", "")
                                if image_url:
                                    extracted_images.append(image_url)
                                image_placeholders += 1
                            elif part.get("type") == "image":
                                content_parts.append({"type": "image"})
                                image_payload = (
                                    part.get("data")
                                    or part.get("image")
                                    or part.get("path")
                                    or part.get("url")
                                    or part
                                )
                                extracted_images.append(image_payload)
                                image_placeholders += 1
                        else:
                            if self._is_pil_image(part):
                                content_parts.append({"type": "image"})
                                extracted_images.append(part)
                                image_placeholders += 1
                            else:
                                content_parts.append({"type": "text", "text": str(part)})
                    chat_messages.append({"role": "user", "content": content_parts})
                else:
                    chat_messages.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                # Include tool_calls if present (for models that support function calling)
                msg_dict = {"role": "assistant", "content": msg.content or ""}
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    msg_dict["tool_calls"] = msg.tool_calls
                chat_messages.append(msg_dict)
            elif isinstance(msg, ToolMessage):
                # Tool results - critical for the model to see search/tool outputs
                chat_messages.append({
                    "role": "tool",
                    "content": msg.content,
                    "tool_call_id": getattr(msg, "tool_call_id", ""),
                })

        # Debug logging to trace what we send into the chat template
        try:
            preview = chat_messages[:]
            if preview:
                preview[0] = {
                    **preview[0],
                    "content": str(preview[0].get("content", ""))[:200],
                }
            self.logger.debug("Chat template input messages: %s", preview)
        except Exception:
            pass

        # Check if we have tools to pass to the template
        template_kwargs = {
            "tokenize": False,
            "add_generation_prompt": True,
        }

        # If placeholders exist but no images were extracted, replace placeholders
        # with a text marker to avoid corrupting the prompt for vision models.
        if image_placeholders > 0 and not extracted_images:
            try:
                for message in chat_messages:
                    content = message.get("content", [])
                    if isinstance(content, list):
                        for idx, part in enumerate(content):
                            if isinstance(part, dict) and part.get("type") == "image":
                                content[idx] = {
                                    "type": "text",
                                    "text": "[image unavailable]",
                                }
                self.logger.warning(
                    "Image placeholders found but no images extracted; replaced with text fallback"
                )
            except Exception:
                pass

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

        # Enable thinking mode ONLY for models that support it (Qwen3)
        # This enables <think>...</think> reasoning blocks
        # Only pass enable_thinking if the model actually uses it to avoid template warnings
        model_supports_thinking = self._check_model_supports_thinking()
        if model_supports_thinking:
            # First check if enable_thinking was set directly on the instance (for fast calls)
            instance_thinking = getattr(self, 'enable_thinking', None)
            if instance_thinking is not None:
                user_wants_thinking = instance_thinking
                self.logger.debug(f"[THINKING] enable_thinking={user_wants_thinking} (from instance attr)")
            else:
                # Read from database for real-time toggle support
                from airunner.components.llm.data.llm_generator_settings import LLMGeneratorSettings
                db_settings = LLMGeneratorSettings.objects.first()
                user_wants_thinking = True  # Default to enabled
                if db_settings is not None:
                    user_val = getattr(db_settings, "enable_thinking", None)
                    if user_val is not None:
                        user_wants_thinking = user_val
                self.logger.debug(f"[THINKING] enable_thinking={user_wants_thinking} (from DB setting)")
            
            # Use the determined preference for thinking mode
            template_kwargs["enable_thinking"] = user_wants_thinking

        # Store extracted images for vision model processing
        if extracted_images:
            self._pending_images = extracted_images
            self.logger.info(f"Stored {len(extracted_images)} images for vision processing")
        else:
            self._pending_images = []

        # Prefer processor chat template for vision models so multimodal tokenization
        # matches the image processor expectations (reduces garbled outputs).
        template_target = None
        if (
            getattr(self, "is_vision_model", False)
            and getattr(self, "processor", None) is not None
            and hasattr(self.processor, "apply_chat_template")
        ):
            template_target = self.processor
        elif self.tokenizer and hasattr(self.tokenizer, "apply_chat_template"):
            template_target = self.tokenizer

        if template_target is None:
            return self._fallback_format(messages)

        try:
            return template_target.apply_chat_template(chat_messages, **template_kwargs)
        except Exception:
            # If processor chat templating fails, fall back to tokenizer, then fallback format.
            if template_target is not self.tokenizer and self.tokenizer and hasattr(self.tokenizer, "apply_chat_template"):
                try:
                    return self.tokenizer.apply_chat_template(chat_messages, **template_kwargs)
                except Exception:
                    pass
            return self._fallback_format(messages)

    def _fallback_format(self, messages: List[BaseMessage]) -> str:
        """Simple fallback formatting when no chat template available.

        Args:
            messages: List of LangChain messages

        Returns:
            Simple formatted prompt string
        """
        from langchain_core.messages import ToolMessage
        
        prompt_parts = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                prompt_parts.append(f"System: {msg.content}")
            elif isinstance(msg, HumanMessage):
                prompt_parts.append(f"User: {msg.content}")
            elif isinstance(msg, AIMessage):
                prompt_parts.append(f"Assistant: {msg.content}")
            elif isinstance(msg, ToolMessage):
                prompt_parts.append(f"Tool Result: {msg.content}")

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

    def _is_pil_image(self, value) -> bool:
        """Check if a value is a PIL image without importing globally."""
        try:
            from PIL import Image
        except Exception:
            return False
        return isinstance(value, Image.Image)
