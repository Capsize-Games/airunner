"""Text generation functionality for LLM models.

This mixin handles:
- Workflow setup for generation
- Streaming token callbacks
- Interrupt handling
- Error handling during generation
- Response extraction
- Main generation orchestration
"""

import random
import traceback
from typing import Any, Dict, List, Optional

import torch
from langchain_core.messages import AIMessage

from airunner.components.llm.managers.llm_request import LLMRequest
from airunner.components.llm.managers.llm_response import LLMResponse
from airunner.enums import LLMActionType, SignalCode


class GenerationMixin:
    """Mixin for LLM text generation functionality."""

    def _clamp_generation_tokens(self, generation_kwargs: Dict[str, Any]) -> None:
        """Ensure max_new_tokens does not exceed target context.

        Uses `_target_context_length` set during model/tokenizer load.
        """
        target_ctx = getattr(self, "_target_context_length", None)
        if not target_ctx:
            return

        requested = generation_kwargs.get("max_new_tokens")
        if requested is None:
            return

        if requested > target_ctx:
            self.logger.info(
                f"Clamping max_new_tokens from {requested} to target context {target_ctx}"
            )
            generation_kwargs["max_new_tokens"] = target_ctx

    def _setup_generation_workflow(
        self,
        action: LLMActionType,
        system_prompt: Optional[str],
        skip_tool_setup: bool = False,
        llm_request: Optional[Any] = None,
    ) -> str:
        """Configure workflow with system prompt and tools for the action.

        Args:
            action: The LLM action type
            system_prompt: Optional system prompt override
            skip_tool_setup: If True, skip tool setup (already filtered)
            llm_request: Optional LLM request object for context-aware prompts

        Returns:
            The action-specific system prompt
        """
        # Extract force_tool from request if present (needed for both branches)
        force_tool = (
            llm_request.force_tool 
            if llm_request and hasattr(llm_request, "force_tool") 
            else None
        )
        
        if system_prompt:
            action_system_prompt = system_prompt
        else:
            # Use context-aware system prompt based on tool categories
            tool_categories = (
                llm_request.tool_categories if llm_request else None
            )
            action_system_prompt = self.get_system_prompt_with_context(
                action, tool_categories, force_tool
            )

        if self._workflow_manager:
            self._workflow_manager.update_system_prompt(action_system_prompt)

            # Set force_tool for agentic research mode
            if force_tool and hasattr(self._workflow_manager, "set_force_tool"):
                self._workflow_manager.set_force_tool(force_tool)
                self.logger.info(f"Set workflow force_tool to: {force_tool}")
            elif hasattr(self._workflow_manager, "set_force_tool"):
                # Clear force_tool if not set in request
                self._workflow_manager.set_force_tool(None)

            # Set response format if provided in request
            response_format = (
                llm_request.response_format
                if llm_request and hasattr(llm_request, "response_format")
                else None
            )
            if response_format and hasattr(
                self._workflow_manager, "set_response_format"
            ):
                self._workflow_manager.set_response_format(response_format)
                self.logger.info(
                    f"Set workflow response format to: {response_format}"
                )

            # Only setup tools if not already filtered
            if not skip_tool_setup and self._tool_manager:
                action_tools = self._tool_manager.get_tools_for_action(action)
                self._workflow_manager.update_tools(action_tools)
            elif skip_tool_setup:
                # Tools were already filtered, don't override
                self.logger.info(
                    "Skipping tool setup - tools already filtered by tool_categories"
                )

        return action_system_prompt

    def _create_streaming_callback(
        self,
        llm_request: Optional[Any],
        complete_response: List[str],
        sequence_counter: List[int],
    ):
        """Create callback function for streaming tokens.

        Args:
            llm_request: The LLM request object
            complete_response: List with single string for response accumulation
            sequence_counter: List with single int for sequence tracking

        Returns:
            Callback function that handles streaming tokens
        """

        def handle_streaming_token(token_text: str) -> None:
            """Forward streaming tokens to the GUI and accumulate response."""
            if not token_text:
                return
            complete_response[0] += token_text
            sequence_counter[0] += 1
            if not getattr(self, "_current_request_id", None):
                # This should always be set for HTTP streaming; log if missing.
                self.logger.warning(
                    "[STREAM] Missing _current_request_id while streaming token"
                )
            self.api.llm.send_llm_text_streamed_signal(
                LLMResponse(
                    node_id=llm_request.node_id if llm_request else None,
                    message=token_text,
                    is_end_of_message=False,
                    is_first_message=(sequence_counter[0] == 1),
                    sequence_number=sequence_counter[0],
                    request_id=getattr(self, "_current_request_id", None),
                )
            )

        return handle_streaming_token

    def _handle_interrupted_generation(
        self, llm_request: Optional[Any], sequence_counter: int
    ) -> str:
        """Handle interrupted generation.

        Args:
            llm_request: The LLM request object
            sequence_counter: Current sequence number

        Returns:
            Empty string (no visible message for interruption)
        """
        self.logger.info("Generation interrupted by user")
        # Send end-of-message signal without adding visible text
        self.api.llm.send_llm_text_streamed_signal(
            LLMResponse(
                node_id=llm_request.node_id if llm_request else None,
                message="",
                is_end_of_message=True,
                sequence_number=sequence_counter + 1,
                request_id=getattr(self, "_current_request_id", None),
            )
        )
        return ""

    def _handle_generation_error(
        self, exc: Exception, llm_request: Optional[Any]
    ) -> str:
        """Handle generation error.

        Args:
            exc: The exception that occurred
            llm_request: The LLM request object

        Returns:
            Error message
        """
        self.logger.error(f"Error during generation: {exc}", exc_info=True)
        # Print full traceback for debugging
        print(f"[ERROR HANDLER] Exception type: {type(exc)}", flush=True)
        print(f"[ERROR HANDLER] Exception message: {str(exc)}", flush=True)
        print(f"[ERROR HANDLER] Full traceback:", flush=True)
        traceback.print_exc()
        # Ensure we capture the full exception message
        error_message = f"Error: {str(exc) if exc else 'Unknown error'}"
        print(
            f"[ERROR HANDLER] Error message to send: {error_message}",
            flush=True,
        )
        self.api.llm.send_llm_text_streamed_signal(
            LLMResponse(
                node_id=llm_request.node_id if llm_request else None,
                message=error_message,
                is_end_of_message=False,
                request_id=getattr(self, "_current_request_id", None),
            )
        )
        return error_message

    def _extract_final_response(self, result: Dict[str, Any]) -> str:
        """Extract final response from generation result.

        Args:
            result: Generation result dictionary

        Returns:
            Final response content or empty string
        """
        final_messages = (
            []
            if not result or "messages" not in result
            else [
                message
                for message in result["messages"]
                if isinstance(message, AIMessage)
            ]
        )

        if len(final_messages) > 0:
            final_content = final_messages[-1].content or ""
            if final_content:
                # If the model is using ReAct format, extract only the response
                # before "Action:" to avoid showing tool calls to the user
                if "\nAction:" in final_content:
                    # Extract everything before the first "Action:"
                    response_part = final_content.split("\nAction:")[0].strip()
                    if response_part:
                        return response_part
                return final_content

        self.logger.info("No final AIMessage found in generation result")

        return ""

    def _do_generate(
        self,
        prompt: str,
        action: LLMActionType,
        system_prompt: Optional[str] = None,
        rag_system_prompt: Optional[str] = None,
        llm_request: Optional[Any] = None,
        do_tts_reply: bool = True,
        extra_context: Optional[Dict[str, Dict[str, Any]]] = None,
        skip_tool_setup: bool = False,
    ) -> Dict[str, Any]:
        """Generate a response using the loaded LLM.

        Args:
            prompt: The input prompt
            action: The LLM action type
            system_prompt: Optional system prompt override
            rag_system_prompt: Optional RAG system prompt
            llm_request: Optional LLM request object
            do_tts_reply: Whether to enable TTS reply
            extra_context: Optional extra context dictionary
            skip_tool_setup: If True, skip tool setup (already filtered)

        Returns:
            Dictionary with 'response' key containing generated text
        """
        # Validate model path before generation
        try:
            current_path = self._current_model_path
            configured_path = self.model_path
        except ValueError as e:
            # Model path validation failed (e.g., embedding model set as main LLM)
            self.logger.error(
                f"Cannot generate - model path validation failed: {e}"
            )
            error_msg = str(e)
            if "embedding model" in error_msg.lower():
                return {
                    "response": "Error: Invalid model configuration. The embedding model is set as the main LLM. Please select a proper chat model in Settings > LLM.",
                    "error": str(e),
                }
            return {
                "response": "Error: No LLM model configured. Please select a model in Settings > LLM.",
                "error": str(e),
            }

        if current_path != configured_path:
            self.logger.warning(
                f"Model path mismatch detected: "
                f"current='{current_path}' vs "
                f"settings='{configured_path}'. "
                f"Reloading model..."
            )
            self.unload()
            self.load()

        # DEEP RESEARCH MODE: Now uses standard tool-based workflow
        # The LLM uses research tools (search_web, scrape_website, validate_url,
        # create_research_document, etc.) autonomously based on the system prompt
        if action == LLMActionType.DEEP_RESEARCH:
            self.logger.info(
                "Deep Research mode - using tool-based research workflow"
            )
            # Use the standard workflow but ensure RESEARCH tools are available
            # The system prompt in system_prompt_mixin.py provides instructions
            # for how to use the research tools effectively
            
            # Don't return early - fall through to standard generation
            # but log that we're in research mode
            self.logger.info(
                "Research tools will be used: search_web, search_news, scrape_website, "
                "validate_url, validate_content, create_research_document, etc."
            )

        llm_request = llm_request or LLMRequest()
        self._setup_generation_workflow(
            action, system_prompt, skip_tool_setup, llm_request
        )

        complete_response = [""]
        sequence_counter = [0]
        self._interrupted = False

        if not self._workflow_manager:
            self.logger.error("Workflow manager is not initialized")
            return {"response": "Error: workflow unavailable"}

        callback = self._create_streaming_callback(
            llm_request, complete_response, sequence_counter
        )
        self._workflow_manager.set_token_callback(callback)

        # Reset workflow manager's interrupted flag before generation
        if hasattr(self._workflow_manager, "set_interrupted"):
            self._workflow_manager.set_interrupted(False)

        try:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()

            # CRITICAL: Use stream() instead of invoke() to allow interrupts
            # invoke() is completely blocking and ignores interrupt flags
            # stream() checks interrupt flag on each token

            # Prepare generation kwargs from LLMRequest
            generation_kwargs = llm_request.to_dict() if llm_request else {}

            # Map max_tokens to max_new_tokens for HuggingFace compatibility
            if "max_tokens" in generation_kwargs:
                generation_kwargs["max_new_tokens"] = generation_kwargs.pop(
                    "max_tokens"
                )

            self._clamp_generation_tokens(generation_kwargs)

            self.logger.debug(
                "llm_request.max_new_tokens=%s",
                llm_request.max_new_tokens if llm_request else "NO REQUEST",
            )
            self.logger.debug(
                "generation_kwargs keys: %s",
                list(generation_kwargs.keys()),
            )
            self.logger.debug(
                "generation_kwargs.get('max_new_tokens')=%s",
                generation_kwargs.get("max_new_tokens", "NOT SET"),
            )
            # Remove non-generation parameters
            for key in [
                "do_tts_reply",
                "use_cache",
                "node_id",
                "use_memory",
                "role",
            ]:
                generation_kwargs.pop(key, None)

            self.logger.debug(
                "After cleanup, generation_kwargs.get('max_new_tokens')=%s",
                generation_kwargs.get("max_new_tokens", "NOT SET"),
            )

            # Extract images from llm_request for vision models
            images = None
            if llm_request and hasattr(llm_request, "images") and llm_request.images:
                images = llm_request.images
                self.logger.info(
                    f"Passing {len(images)} image(s) to workflow stream"
                )

            result_messages = []
            for message in self._workflow_manager.stream(
                prompt, generation_kwargs, images=images
            ):
                # Check interrupt flag during streaming
                if self._interrupted:
                    self.logger.info(
                        "Stream interrupted - breaking out of generation"
                    )
                    break
                # Only keep messages that are final responses (no tool_calls)
                # Tool-calling messages are intermediate workflow states
                has_tool_calls = getattr(message, "tool_calls", None)
                content_preview = (
                    message.content[:100]
                    if hasattr(message, "content") and message.content
                    else "(empty)"
                )
                if not has_tool_calls:
                    result_messages.append(message)

            # Convert streamed messages to result format
            result = {"messages": result_messages}

            if self._interrupted:
                interrupt_msg = self._handle_interrupted_generation(
                    llm_request, sequence_counter[0]
                )
                complete_response[0] += interrupt_msg
                result = {"messages": []}
        except Exception as exc:
            error_msg = self._handle_generation_error(exc, llm_request)
            complete_response[0] = error_msg
            result = {"messages": []}
        finally:
            self._workflow_manager.set_token_callback(None)
            self._interrupted = False
            if hasattr(self._workflow_manager, "set_interrupted"):
                self._workflow_manager.set_interrupted(False)

        final_response = self._extract_final_response(result)
        if final_response:
            complete_response[0] = final_response

        # Get list of tools that were executed during workflow
        executed_tools = []
        if hasattr(self._workflow_manager, "get_executed_tools"):
            executed_tools = self._workflow_manager.get_executed_tools()
            
        sequence_counter[0] += 1
        if not getattr(self, "_current_request_id", None):
            self.logger.warning(
                "[STREAM] Missing _current_request_id when sending end-of-message"
            )
        self.api.llm.send_llm_text_streamed_signal(
            LLMResponse(
                node_id=llm_request.node_id if llm_request else None,
                is_end_of_message=True,
                sequence_number=sequence_counter[0],
                request_id=getattr(self, "_current_request_id", None),
                tools=executed_tools,  # Include the tools here!
            )
        )

        return {
            "response": complete_response[0],
            "tools": executed_tools,  # Include list of executed tools
        }

    def _send_final_message(
        self, llm_request: Optional[LLMRequest] = None
    ) -> None:
        """Send a signal indicating the end of a message stream.

        Args:
            llm_request: Optional LLM request object
        """
        # Get executed tools from workflow manager
        executed_tools = []
        if hasattr(self, "_workflow_manager") and self._workflow_manager:
            executed_tools = self._workflow_manager.get_executed_tools()

        self.api.llm.send_llm_text_streamed_signal(
            LLMResponse(
                node_id=llm_request.node_id if llm_request else None,
                is_end_of_message=True,
                request_id=getattr(self, "_current_request_id", None),
                tools=executed_tools,
            )
        )

    def _do_set_seed(self) -> None:
        """Set random seeds for deterministic generation."""
        if self.llm_generator_settings.override_parameters:
            seed = self.llm_generator_settings.seed
            random_seed = self.llm_generator_settings.random_seed
        else:
            seed = self.chatbot.seed
            random_seed = self.chatbot.random_seed

        if not random_seed:
            torch.manual_seed(seed)
            random.seed(seed)
            if torch.cuda.is_available():
                torch.cuda.manual_seed_all(seed)
