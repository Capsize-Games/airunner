"""Text generation functionality for LLM models.

This mixin handles:
- Workflow setup for generation
- Streaming token callbacks
- Interrupt handling
- Error handling during generation
- Response extraction
- Main generation orchestration
"""

import os
import random
import traceback
from typing import Any, Dict, List, Optional

import torch
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.errors import GraphRecursionError

from airunner_services.database.models.conversation import Conversation
from airunner_services.llm.llm_request import LLMRequest
from airunner_services.llm.managers.request_preparation import (
    WorkflowRequestSetup,
    build_workflow_request_setup,
    extract_request_images,
)
from airunner_services.llm.llm_response import LLMResponse
from airunner_services.llm.gpt_oss_parser import (
    has_gpt_oss_markup,
    looks_like_tool_argument_payload,
    parse_gpt_oss_response,
)
from airunner_services.llm.stream_text import prepare_stream_chunk
from airunner_services.contract_enums import LLMActionType, ModelStatus, ModelType, SignalCode


READ_ONLY_TASK_TOOLS = {
    "list_workspace_files",
    "read_code_file",
    "read_file",
    "search_files",
    "grep_search",
    "semantic_search",
    "get_document_content",
    "get_document_info",
    "search_document",
    "goto_document_line",
    "validate_code",
    "run_tests",
    "lint_code",
    "analyze_code_complexity",
    "execute_python",
}

MUTATING_TASK_TOOLS = {
    "create_code_file",
    "edit_code_file",
    "delete_code_file",
    "format_code_file",
    "format_code",
    "write_file",
    "edit_file",
    "delete_file",
    "edit_document_lines",
    "insert_document_lines",
    "delete_document_lines",
    "replace_in_document",
    "save_document",
}

TITLE_PASS_SYSTEM_PROMPT = (
    "You generate short conversation titles for chat history. "
    "Return only one concise title in 3 to 7 words. "
    "Do not use quotes, markdown, emojis, or trailing punctuation. "
    "If the exchange is just a greeting or opening pleasantry, return "
    "'Greeting and introduction'."
)


class GenerationMixin:
    """Mixin for LLM text generation functionality."""

    def _conversation_for_title_pass(self) -> Optional[Conversation]:
        """Return one untitled conversation ready for the title pass."""
        workflow_manager = getattr(self, "_workflow_manager", None)
        conversation_id = getattr(workflow_manager, "_conversation_id", None)
        if not conversation_id:
            return None
        try:
            conversation = Conversation.objects.get(conversation_id)
        except Exception:
            self.logger.warning(
                "Failed to load conversation %s for title pass",
                conversation_id,
            )
            return None
        if not conversation or str(getattr(conversation, "title", "") or "").strip():
            return None
        return conversation

    def _title_pass_messages(
        self,
        conversation: Conversation,
    ) -> list[dict[str, str]]:
        """Return visible user and assistant messages for title generation."""
        messages = []
        for item in list(getattr(conversation, "value", None) or []):
            role = str(item.get("role") or "").strip().lower()
            if role not in {"user", "assistant", "bot"}:
                continue
            if item.get("metadata_type") in {"tool_calls", "tool_result"}:
                continue
            content = str(item.get("content") or "").strip()
            if content:
                messages.append({"role": role, "content": content})
        return messages

    def _build_title_pass_prompt(
        self,
        messages: list[dict[str, str]],
    ) -> list[Any]:
        """Build one short title-generation prompt from the visible exchange."""
        exchange = "\n".join(
            f"{item['role'].title()}: {item['content'][:500]}"
            for item in messages[:6]
        )
        return [
            SystemMessage(content=TITLE_PASS_SYSTEM_PROMPT),
            HumanMessage(content=f"Conversation:\n{exchange}\n\nTitle:"),
        ]

    @staticmethod
    def _sanitize_generated_title(raw_title: Any) -> str:
        """Normalize one model-produced title into a single plain line."""
        title = str(raw_title or "").strip()
        if not title:
            return ""
        title = title.splitlines()[0].strip().strip('"\'` ')
        title = title.rstrip(".!?:;,- ")
        return title[:80].strip()

    def _maybe_generate_conversation_title(self) -> None:
        """Persist one LLM-generated title after the first assistant reply."""
        conversation = self._conversation_for_title_pass()
        if conversation is None or self._chat_model is None:
            return
        messages = self._title_pass_messages(conversation)
        roles = {item["role"] for item in messages}
        if "user" not in roles or not ({"assistant", "bot"} & roles):
            return
        try:
            response = self._chat_model.invoke(
                self._build_title_pass_prompt(messages)
            )
            title = self._sanitize_generated_title(
                getattr(response, "content", response)
            )
            if not title:
                return
            Conversation.objects.update(conversation.id, title=title)
            emit = getattr(self, "emit_signal", None)
            if callable(emit):
                emit(
                    SignalCode.CONVERSATION_TITLE_UPDATED,
                    {"conversation_id": conversation.id, "title": title},
                )
        except Exception as exc:
            self.logger.warning(
                "Failed to generate conversation title for %s: %s",
                getattr(conversation, "id", None),
                exc,
            )

    def _current_assistant_turn_index(self) -> int:
        """Return the current workflow assistant-turn index."""
        workflow_manager = getattr(self, "_workflow_manager", None)
        turn_index = getattr(workflow_manager, "_assistant_turn_index", 0)
        return int(turn_index or 0)

    def _emit_visible_response(
        self,
        llm_request: Optional[Any],
        message: str,
        complete_response: List[str],
        sequence_counter: List[int],
    ) -> None:
        """Emit one visible response chunk when streaming produced none."""
        if not message or complete_response[0]:
            return
        complete_response[0] = message
        sequence_counter[0] += 1
        self.api.llm.send_llm_text_streamed_signal(
            LLMResponse(
                node_id=llm_request.node_id if llm_request else None,
                message=message,
                is_end_of_message=False,
                is_first_message=(sequence_counter[0] == 1),
                sequence_number=sequence_counter[0],
                request_id=getattr(self, "_current_request_id", None),
                message_type="assistant",
                turn_index=self._current_assistant_turn_index(),
            )
        )

    def _fallback_response_for_empty_result(
        self,
        result: Dict[str, Any],
        executed_tools: List[str],
    ) -> str:
        """Return a visible fallback when the model produced no final text."""
        messages = []
        if isinstance(result, dict):
            messages = result.get("raw_messages") or result.get("messages")
        ai_messages = [
            message
            for message in messages or []
            if isinstance(message, AIMessage)
        ]

        effective_executed_tools = list(executed_tools)
        if not effective_executed_tools:
            for message in ai_messages:
                extra_tools = (
                    (message.additional_kwargs or {}).get("executed_tools")
                )
                if isinstance(extra_tools, (list, tuple, set)):
                    effective_executed_tools.extend(
                        str(tool_name)
                        for tool_name in extra_tools
                        if tool_name
                    )

        if effective_executed_tools:
            tool_summary = ", ".join(dict.fromkeys(effective_executed_tools))
            normalized_tools = set(effective_executed_tools)
            if (
                not normalized_tools & MUTATING_TASK_TOOLS
                and normalized_tools <= READ_ONLY_TASK_TOOLS
            ):
                return (
                    "The model inspected the workspace with read-only tools "
                    f"({tool_summary}) but did not make any changes."
                )
            if not normalized_tools & MUTATING_TASK_TOOLS:
                return (
                    "The model used non-mutating tools "
                    f"({tool_summary}) but did not make any changes."
                )
            return (
                "The request completed tool actions "
                f"({tool_summary}), but the model did not provide a final "
                "reply."
            )

        if any(getattr(message, "tool_calls", None) for message in ai_messages):
            return (
                "The model attempted a tool-based response but did not "
                "produce a final reply. No changes were applied."
            )

        if ai_messages:
            return (
                "The model produced an empty reply for this request. "
                "No changes were applied."
            )

        return ""

    def _sync_request_scope_to_workflow_manager(self) -> None:
        """Propagate the active request ID to workflow-scoped emitters."""
        if not self._workflow_manager:
            return

        request_id = getattr(self, "_current_request_id", None)
        setattr(
            self._workflow_manager,
            "llm_request",
            getattr(self, "llm_request", None),
        )
        if hasattr(self._workflow_manager, "set_request_id"):
            self._workflow_manager.set_request_id(request_id)
            return

        setattr(self._workflow_manager, "_current_request_id", request_id)

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
        request_setup = build_workflow_request_setup(llm_request)
        
        if system_prompt:
            action_system_prompt = self._augment_custom_system_prompt(
                base_prompt=system_prompt,
                action=action,
                include_mood=request_setup.include_mood,
                include_datetime=request_setup.include_datetime,
                include_style=request_setup.include_style,
                include_memory=request_setup.include_memory,
                include_ui_context=request_setup.include_ui_context,
            )
        else:
            action_system_prompt = self.get_system_prompt_with_context(
                action,
                request_setup.tool_categories,
                request_setup.force_tool,
            )

        self._apply_workflow_request_setup(
            action=action,
            action_system_prompt=action_system_prompt,
            skip_tool_setup=skip_tool_setup,
            request_setup=request_setup,
        )

        return action_system_prompt

    def _apply_workflow_request_setup(
        self,
        action: LLMActionType,
        action_system_prompt: str,
        skip_tool_setup: bool,
        request_setup: WorkflowRequestSetup,
    ) -> None:
        """Apply one request's workflow settings to the active manager."""
        if not self._workflow_manager:
            return

        self._workflow_manager.update_system_prompt(action_system_prompt)
        self._set_workflow_force_tool(request_setup.force_tool)
        self._set_workflow_response_format(request_setup.response_format)
        self._update_workflow_tools_for_action(action, skip_tool_setup)

    def _set_workflow_force_tool(self, force_tool: Optional[str]) -> None:
        """Synchronize the request force-tool state into the workflow."""
        if not hasattr(self._workflow_manager, "set_force_tool"):
            return

        self._workflow_manager.set_force_tool(force_tool)
        self.logger.info("Set workflow force_tool to: %s", force_tool)

    def _set_workflow_response_format(
        self,
        response_format: Optional[str],
    ) -> None:
        """Apply one request response-format override when present."""
        if not response_format:
            return
        if not hasattr(self._workflow_manager, "set_response_format"):
            return

        self._workflow_manager.set_response_format(response_format)
        self.logger.info(
            "Set workflow response format to: %s",
            response_format,
        )

    def _update_workflow_tools_for_action(
        self,
        action: LLMActionType,
        skip_tool_setup: bool,
    ) -> None:
        """Refresh action tools unless request-time filtering already ran."""
        if skip_tool_setup:
            self.logger.info(
                "Skipping tool setup - tools already filtered by "
                "tool_categories"
            )
            return
        if not self._tool_manager:
            return

        action_tools = self._tool_manager.get_tools_for_action(action)
        self._workflow_manager.update_tools(action_tools)

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
            token_text = prepare_stream_chunk(complete_response[0], token_text)
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
                    message_type="assistant",
                    turn_index=self._current_assistant_turn_index(),
                )
            )

        return handle_streaming_token

    def _create_thinking_callback(
        self,
        llm_request: Optional[Any],
        sequence_counter: List[int],
    ):
        """Create a callback that emits typed thinking chunks to the GUI.

        The daemon needs to surface thinking/reasoning content over the
        NDJSON stream without leaking ``<think>`` markup into the visible
        assistant chunks. This callback wraps each fragment in an
        ``LLMResponse`` with ``message_type='thinking'`` so the GUI bridge
        can render it through the unified thinking widget path.
        """

        def handle_thinking_event(status: str, content: str) -> None:
            """Forward one thinking event to the streaming consumer."""
            sequence_counter[0] += 1
            is_end = status == "completed"
            payload_message = content or ""
            self.api.llm.send_llm_text_streamed_signal(
                LLMResponse(
                    node_id=llm_request.node_id if llm_request else None,
                    message=payload_message,
                    is_end_of_message=is_end,
                    is_first_message=(status == "started"),
                    sequence_number=sequence_counter[0],
                    request_id=getattr(self, "_current_request_id", None),
                    message_type="thinking",
                    turn_index=self._current_assistant_turn_index(),
                )
            )

        return handle_thinking_event

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
                message_type="assistant",
                turn_index=self._current_assistant_turn_index(),
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
        if isinstance(exc, GraphRecursionError):
            executed_tools_value = getattr(
                self._workflow_manager,
                "_executed_tools",
                [],
            )
            if isinstance(executed_tools_value, (list, tuple, set)):
                executed_tools = list(executed_tools_value)
            else:
                executed_tools = []
            if any(tool in MUTATING_TASK_TOOLS for tool in executed_tools):
                error_message = (
                    "Error: The request hit the workflow recursion limit "
                    "after applying some tool actions. Changes may already "
                    "exist in the workspace, but the model did not finish "
                    "verification."
                )
            else:
                error_message = (
                    "Error: The request got stuck repeating tool calls "
                    "without making progress and hit the workflow recursion "
                    "limit. No changes were applied."
                )
        else:
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
                message_type="system",
                turn_index=self._current_assistant_turn_index(),
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
            saw_gpt_oss_markup = False
            for message in reversed(final_messages):
                final_content = message.content or ""
                if not final_content:
                    continue
                if looks_like_tool_argument_payload(final_content):
                    continue
                if has_gpt_oss_markup(final_content):
                    saw_gpt_oss_markup = True
                    parsed = parse_gpt_oss_response(final_content)
                    if parsed.content:
                        return parsed.content
                    continue
                if "\nAction:" in final_content:
                    response_part = final_content.split("\nAction:")[0].strip()
                    if response_part:
                        return response_part
                    continue
                return final_content

            if saw_gpt_oss_markup:
                self.logger.info(
                    "GPT-OSS response had no visible final content"
                )
                return ""

            self.logger.info("Final AIMessage was empty")
            return ""

        self.logger.info("No final AIMessage found in generation result")

        return ""

    def _do_generate(
        self,
        prompt: str,
        action: LLMActionType,
        system_prompt: Optional[str] = None,
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

        # DEEP RESEARCH MODE: Uses the standard tool workflow with
        # search, validation, scraping, and synthesized response output.
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
                "validate_url, validate_content, and related validation tools."
            )

        llm_request = llm_request or LLMRequest()
        self._setup_generation_workflow(
            action, system_prompt, skip_tool_setup, llm_request
        )

        complete_response = [""]
        sequence_counter = [0]
        self._interrupted = False

        if not self._workflow_manager and hasattr(self, "_load_workflow_manager"):
            try:
                self._load_workflow_manager()
            except Exception:
                pass

        if not self._workflow_manager:
            model_status = getattr(self, "model_status", {}).get(ModelType.LLM)
            last_load_error = str(
                getattr(self, "_last_load_error", "") or ""
            ).strip()
            if model_status == ModelStatus.FAILED and last_load_error:
                self.logger.error(
                    "Workflow manager unavailable because model load failed: %s",
                    last_load_error,
                )
                return {
                    "response": f"Error: {last_load_error}",
                    "error": last_load_error,
                }

            model_path = None
            expected_gguf_path = None
            try:
                model_path = self.model_path
            except Exception:
                model_path = None

            try:
                if hasattr(self, "_get_expected_gguf_path"):
                    expected_gguf_path = self._get_expected_gguf_path()
            except Exception:
                expected_gguf_path = None

            if self.llm_settings.use_local_llm and model_path:
                try:
                    model_name = self.model_name
                except Exception:
                    model_name = os.path.basename(model_path.rstrip("/")) or "(unknown)"
                is_gguf = False
                try:
                    if hasattr(self, "_is_gguf_quantization_selected"):
                        is_gguf = bool(self._is_gguf_quantization_selected())
                except Exception:
                    is_gguf = False

                gguf_present = False
                if expected_gguf_path:
                    gguf_present = os.path.exists(expected_gguf_path)
                elif is_gguf:
                    # In GGUF mode, the configured model path may be a directory.
                    # Consider the model "ready" only once a .gguf file exists.
                    try:
                        if os.path.isdir(model_path):
                            gguf_present = any(
                                name.lower().endswith(".gguf")
                                for name in os.listdir(model_path)
                            )
                        else:
                            gguf_present = model_path.lower().endswith(".gguf") and os.path.exists(model_path)
                    except Exception:
                        gguf_present = False

                model_ready = os.path.exists(model_path)
                if expected_gguf_path:
                    model_ready = gguf_present
                elif is_gguf:
                    model_ready = model_ready and gguf_present

                if model_ready and hasattr(self, "load"):
                    try:
                        self.load()
                    except Exception:
                        self.logger.exception(
                            "Failed to load local model before generation"
                        )
                    if not self._workflow_manager and hasattr(self, "_load_workflow_manager"):
                        try:
                            self._load_workflow_manager()
                        except Exception:
                            pass

                if not model_ready:
                    self.logger.error(
                        "Workflow manager unavailable because model is missing; "
                        "download likely in progress"
                    )
                    return {
                        "response": (
                            f"Error: model '{model_name}' is not ready yet (download in progress). "
                            "Please wait for the download to finish and try again."
                        ),
                        "retry_after_download": True,
                    }

            self.logger.error("Workflow manager is not initialized")
            return {"response": "Error: workflow unavailable"}

        self._sync_request_scope_to_workflow_manager()

        callback = self._create_streaming_callback(
            llm_request, complete_response, sequence_counter
        )
        self._workflow_manager.set_token_callback(callback)
        thinking_callback = self._create_thinking_callback(
            llm_request, sequence_counter
        )
        if hasattr(self._workflow_manager, "set_thinking_callback"):
            self._workflow_manager.set_thinking_callback(thinking_callback)

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
            generation_kwargs = (
                llm_request.to_generation_kwargs() if llm_request else {}
            )

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
            images = extract_request_images(llm_request)
            if images:
                self.logger.info(
                    f"Passing {len(images)} image(s) to workflow stream"
                )

            result_messages = []
            raw_messages = []
            for message in self._workflow_manager.stream(
                prompt, generation_kwargs, images=images
            ):
                # Check interrupt flag during streaming
                if self._interrupted:
                    self.logger.info(
                        "Stream interrupted - breaking out of generation"
                    )
                    break
                raw_messages.append(message)
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
            result = {
                "messages": result_messages,
                "raw_messages": raw_messages,
            }

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
            if hasattr(self._workflow_manager, "set_thinking_callback"):
                self._workflow_manager.set_thinking_callback(None)
            self._interrupted = False
            if hasattr(self._workflow_manager, "set_interrupted"):
                self._workflow_manager.set_interrupted(False)

        # Best-effort: extract provider token usage from the final AI message.
        prompt_tokens = None
        completion_tokens = None
        total_tokens = None
        try:
            last_msg = None
            msgs = result.get("messages") if isinstance(result, dict) else None
            if isinstance(msgs, list) and msgs:
                last_msg = msgs[-1]

            if last_msg is not None:
                usage = getattr(last_msg, "usage_metadata", None)
                if isinstance(usage, dict):
                    # LangChain commonly uses input/output naming.
                    prompt_tokens = usage.get("input_tokens") or usage.get("prompt_tokens")
                    completion_tokens = usage.get("output_tokens") or usage.get("completion_tokens")
                    total_tokens = usage.get("total_tokens")

                # Some providers stash usage in response_metadata.
                if prompt_tokens is None or completion_tokens is None:
                    rm = getattr(last_msg, "response_metadata", None)
                    if isinstance(rm, dict):
                        token_usage = rm.get("token_usage") or rm.get("usage")
                        if isinstance(token_usage, dict):
                            prompt_tokens = prompt_tokens or token_usage.get("prompt_tokens")
                            completion_tokens = completion_tokens or token_usage.get("completion_tokens")
                            total_tokens = total_tokens or token_usage.get("total_tokens")

                if total_tokens is None and (prompt_tokens is not None or completion_tokens is not None):
                    total_tokens = int(prompt_tokens or 0) + int(completion_tokens or 0)
        except Exception:
            # Usage extraction is best-effort and must not fail generation.
            prompt_tokens = None
            completion_tokens = None
            total_tokens = None

        # Get list of tools that were executed during workflow
        executed_tools = []
        if hasattr(self._workflow_manager, "get_executed_tools"):
            raw_executed_tools = self._workflow_manager.get_executed_tools()
            if isinstance(raw_executed_tools, (list, tuple, set)):
                executed_tools = list(raw_executed_tools)

        final_response = self._extract_final_response(result)
        if final_response:
            self._emit_visible_response(
                llm_request,
                final_response,
                complete_response,
                sequence_counter,
            )
            complete_response[0] = final_response

        if not complete_response[0]:
            fallback_response = self._fallback_response_for_empty_result(
                result,
                executed_tools,
            )
            self._emit_visible_response(
                llm_request,
                fallback_response,
                complete_response,
                sequence_counter,
            )
            
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
                prompt_tokens=int(prompt_tokens) if prompt_tokens is not None else None,
                completion_tokens=int(completion_tokens) if completion_tokens is not None else None,
                total_tokens=int(total_tokens) if total_tokens is not None else None,
                message_type="assistant",
                turn_index=self._current_assistant_turn_index(),
            )
        )

        self._maybe_generate_conversation_title()

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
                message_type="assistant",
                turn_index=self._current_assistant_turn_index(),
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
