"""Node functions mixin for WorkflowManager.

Handles LangGraph node implementations (_call_model, _force_response_node, _route_after_model).
These are broken into focused helper methods for maintainability.
"""

import re
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    BaseMessage,
    trim_messages,
)

from airunner.components.llm.utils.thinking_parser import strip_thinking_tags, has_thinking_content
from airunner.enums import SignalCode
from airunner.settings import (
    AIRUNNER_LOG_LEVEL,
    AIRUNNER_LLM_DUPLICATE_TOOL_CALL_WINDOW,
)
from airunner.utils.application import get_logger

if TYPE_CHECKING:
    from airunner.components.llm.managers.workflow_manager import WorkflowState


class NodeFunctionsMixin:
    """Implements LangGraph node functions for the workflow."""

    def _force_response_node(self, state: "WorkflowState") -> Dict[str, Any]:
        """Node that generates forced response when redundancy detected.

        This is a proper LangGraph node (not just a router) so state updates
        are properly persisted to the checkpoint/database.

        Args:
            state: Workflow state with messages

        Returns:
            Dict with new forced response message to be added to state
        """
        # Find the AIMessage with tool_calls (should be second-to-last, before ToolMessage)
        ai_message_with_tools = None
        for msg in reversed(state["messages"]):
            if self._has_tool_calls(msg):
                ai_message_with_tools = msg
                break

        if not ai_message_with_tools:
            self.logger.error(
                "Force response node called but no AIMessage with tool_calls found"
            )
            return {"messages": []}

        # Get tool information
        tool_name = ai_message_with_tools.tool_calls[0].get("name")
        tool_messages = self._get_tool_messages(state["messages"])
        all_tool_content = self._combine_tool_results(tool_messages)

        # Extract original user question from first HumanMessage
        user_question = self._get_user_question(state["messages"])

        # Extract generation_kwargs from state for streaming configuration
        generation_kwargs = state.get("generation_kwargs", {})

        self.logger.info(
            f"Force response node: Generating answer from {len(all_tool_content)} chars across {len(tool_messages)} tool result(s)"
        )

        # Generate response based on tool results
        response_content = self._generate_forced_response(
            all_tool_content, tool_name, user_question, generation_kwargs
        )

        # Create AIMessage with NO tool_calls
        forced_message = AIMessage(
            content=response_content,
            tool_calls=[],  # Explicitly set to empty list
        )

        self.logger.info(
            f"✓ Force response node: Replaced tool call with {len(response_content)} char conversational response (tool_calls=[])"
        )

        # Return dict with new message for LangGraph to merge via add_messages reducer
        return {"messages": [forced_message]}

    def _has_tool_calls(self, message: BaseMessage) -> bool:
        """Check if message has tool calls.

        Args:
            message: Message to check

        Returns:
            True if message has tool_calls attribute with non-empty value
        """
        return hasattr(message, "tool_calls") and message.tool_calls

    def _get_user_question(self, messages: List[BaseMessage]) -> str:
        """Extract the most recent user question from message history.

        Args:
            messages: List of messages

        Returns:
            User question content, or empty string if not found
        """
        # Find the most recent HumanMessage
        for message in reversed(messages):
            if message.__class__.__name__ == "HumanMessage":
                return message.content
        return ""

    def _get_tool_messages(self, messages: List[BaseMessage]) -> List[Any]:
        """Extract all ToolMessage instances from message list.

        Args:
            messages: List of messages

        Returns:
            List of ToolMessage instances
        """
        return [
            msg for msg in messages if msg.__class__.__name__ == "ToolMessage"
        ]

    def _combine_tool_results(self, tool_messages: List[Any]) -> str:
        """Combine all tool results into single context string.

        Args:
            tool_messages: List of ToolMessage instances

        Returns:
            Combined tool results string
        """
        all_tool_content = ""
        if tool_messages:
            for i, tool_msg in enumerate(tool_messages):
                all_tool_content += f"\n--- Tool Result {i+1} ---\n"
                all_tool_content += tool_msg.content
                all_tool_content += "\n"
        return all_tool_content

    def _generate_forced_response(
        self,
        tool_content: str,
        tool_name: str,
        user_question: str,
        generation_kwargs: Optional[Dict] = None,
    ) -> str:
        """Generate a conversational response from tool results.

        Args:
            tool_content: Combined content from tool executions
            tool_name: Name of the tool that was called
            user_question: Original user's question
            generation_kwargs: Optional generation parameters for streaming control

        Returns:
            Response text
        """
        try:
            # Use RAG-specific logic for rag_search
            if tool_name == "rag_search":
                return self._generate_response_from_results(
                    tool_content, tool_name, user_question, generation_kwargs
                )

            # For other tools, use generic response generation
            return self._generate_response_from_results(
                tool_content, tool_name, user_question, generation_kwargs
            )
        except Exception as e:
            self.logger.error(f"Failed to generate forced response: {e}")
            fallback = "I found some information but encountered an issue generating a complete response."
            if self._token_callback:
                self._token_callback(fallback)
            return fallback

    def _generate_response_from_results(
        self,
        all_tool_content: str,
        tool_name: str,
        user_question: str = "",
        generation_kwargs: Optional[Dict] = None,
    ) -> str:
        """Generate response from actual tool results.

        Args:
            all_tool_content: Combined tool results
            tool_name: Name of the tool
            user_question: Original user question
            generation_kwargs: Optional generation parameters for streaming control

        Returns:
            Generated response content
        """
        self.logger.info(
            f"Forcing model to answer based on {tool_name} results..."
        )

        try:
            # Build prompt with explicit user question and strong no-tool instructions
            question_context = (
                f"User's question: {user_question}\n\n"
                if user_question
                else ""
            )

            simple_prompt_text = f"""You are answering a question based on search results. Respond naturally and conversationally.

{question_context}Search results:
{all_tool_content}

Based on the search results above, provide a clear, conversational answer to the user's question. Use ONLY the information from the search results. Do not call any tools, do not use JSON, just write a natural response. Avoid repetition and be concise."""

            # Convert to message format
            simple_prompt = [HumanMessage(content=simple_prompt_text)]

            # Stream response with generation kwargs for token-by-token streaming
            response_content = self._stream_model_response(
                simple_prompt, generation_kwargs
            )

            self.logger.info(
                f"Model streamed {len(response_content)} char answer"
            )
            return response_content

        except Exception as e:
            self.logger.error(f"Failed to generate forced response: {e}")
            fallback = "I found some information but encountered an issue generating a complete response. Let me try to help with what I found."
            # Stream fallback message through callback
            if self._token_callback:
                self._token_callback(fallback)
            return fallback

    def _stream_model_response(
        self,
        prompt: List[BaseMessage],
        generation_kwargs: Optional[Dict] = None,
    ) -> str:
        """Stream model response and accumulate content.

        Uses the standard streaming response generation to ensure proper
        token-by-token streaming with generation kwargs.

        Args:
            prompt: List of messages to send to model
            generation_kwargs: Optional generation parameters for streaming control

        Returns:
            Complete response content
        """
        # Use empty dict if no kwargs provided
        if generation_kwargs is None:
            generation_kwargs = {}

        chat_model = self._chat_model

        # Temporarily disable tools/JSON mode so the adapter does not buffer
        tools_backup = getattr(chat_model, "tools", None)
        mode_backup = getattr(chat_model, "tool_calling_mode", None)
        json_mode_backup = getattr(chat_model, "use_json_mode", None)

        try:
            if hasattr(chat_model, "tools"):
                chat_model.tools = None
            if hasattr(chat_model, "tool_calling_mode"):
                chat_model.tool_calling_mode = "react"
            if hasattr(chat_model, "use_json_mode"):
                chat_model.use_json_mode = False

            # Use the standard streaming response method which properly handles generation_kwargs
            response_message = self._generate_streaming_response(
                prompt, generation_kwargs
            )

            if response_message and hasattr(response_message, "content"):
                return response_message.content

            return ""
        finally:
            if hasattr(chat_model, "tools"):
                chat_model.tools = tools_backup
            if hasattr(chat_model, "tool_calling_mode"):
                chat_model.tool_calling_mode = mode_backup
            if hasattr(chat_model, "use_json_mode"):
                chat_model.use_json_mode = json_mode_backup

    def _generate_fallback_response(self, tool_name: str) -> str:
        """Generate fallback response when tool returned insufficient results.

        Args:
            tool_name: Name of the tool that failed

        Returns:
            Fallback response content
        """
        if tool_name == "search_web":
            response_content = "I searched the internet but couldn't find relevant information on that topic. Could you try rephrasing your question or asking about something else?"
        elif tool_name == "rag_search":
            response_content = "I searched through the available documents but couldn't find information about that. The documents may not contain details on this topic."
        else:
            response_content = "I tried to find information but wasn't able to get useful results. Could you rephrase your question or try a different approach?"

        # Stream this message through callback so GUI sees it
        if self._token_callback:
            self._token_callback(response_content)

        return response_content

    # ========================================================================
    # ROUTE AFTER MODEL
    # ========================================================================

    def _route_after_model(self, state: "WorkflowState") -> str:
        """Route to tools if model made tool calls, otherwise end.

        Args:
            state: Workflow state

        Returns:
            Routing decision: "tools", "force_response", or "end"
        """
        last_message = state["messages"][-1]
        has_tool_calls = self._has_tool_calls(last_message)

        # Debug logging
        self._log_routing_debug(last_message, state["messages"])

        if has_tool_calls:
            # Check for duplicate tool calls
            if self._is_duplicate_tool_call(last_message, state["messages"]):
                return "force_response"

            # Log tool call information
            self._log_tool_call_info(last_message, state["messages"])
            return "tools"

        return "end"

    def _route_after_tools(self, state: "WorkflowState") -> str:
        """Route after tools execute - decide if model needs to respond.

        Some tools (like update_mood) are status-only and don't need a response.
        Other tools (like scrape_website) return data that needs interpretation.

        CRITICAL: Check for potential duplicate tool calls BEFORE routing back to model.
        If we detect the model will likely call the same tool again, route to force_response.

        Args:
            state: Workflow state

        Returns:
            Routing decision: "model", "force_response", or "end"
        """
        # Get the last tool messages to check what tools executed
        tool_messages = self._get_tool_messages(state["messages"])

        if not tool_messages:
            return "end"

        # Tools that don't need a follow-up response (status/action tools)
        # NOTE: update_mood removed - we want the model to provide a conversational response after updating mood
        NO_RESPONSE_TOOLS = {
            "clear_conversation",
            "emit_signal",
            "toggle_tts",
            "clear_canvas",
            "quit_application",
            "clear_chat_history",
            "delete_conversation",
            "switch_conversation",
            "create_new_conversation",
            "update_conversation_title",
        }

        # Check the most recent tool message to see what tool was called
        last_tool_msg = tool_messages[-1]

        # Get the corresponding AI message with tool_calls
        ai_messages = [
            msg for msg in state["messages"] if isinstance(msg, AIMessage)
        ]
        if not ai_messages:
            return "end"

        last_ai_msg = ai_messages[-1]
        if (
            not hasattr(last_ai_msg, "tool_calls")
            or not last_ai_msg.tool_calls
        ):
            return "end"

        # Check if any of the called tools need a response
        for tool_call in last_ai_msg.tool_calls:
            tool_name = tool_call.get("name", "")
            self.logger.info(f"[ROUTE DEBUG] Checking tool: {tool_name}")
            if tool_name not in NO_RESPONSE_TOOLS:
                # CRITICAL: For certain tools (RAG, search), we want to force response after first execution
                # to prevent the model from looping and calling the same tool again

                # Tools that should force response after execution (don't let model call again)
                FORCE_RESPONSE_AFTER_EXECUTION = {
                    "rag_search",
                    "search_web",
                    "search_news",
                    "scrape_website",
                    "search_knowledge_base_documents",
                }

                if tool_name in FORCE_RESPONSE_AFTER_EXECUTION:
                    # Always force response for these tools - don't let model decide
                    self.logger.info(
                        f"[ROUTE DEBUG] Tool '{tool_name}' is in FORCE_RESPONSE list - routing to force_response"
                    )
                    self.logger.info(
                        f"[ROUTE DEBUG] Tool result length: {len(last_tool_msg.content) if hasattr(last_tool_msg, 'content') and last_tool_msg.content else 0} chars"
                    )
                    return "force_response"

                # Other tools: let model process results normally
                self.logger.info(
                    f"[ROUTE DEBUG] Tool '{tool_name}' needs model response - routing back to model"
                )
                self.logger.info(
                    f"[ROUTE DEBUG] Tool result: {last_tool_msg.content if hasattr(last_tool_msg, 'content') else 'No content'}"
                )
                return "model"

        # All tools were status-only
        self.logger.info(
            "[ROUTE DEBUG] All tools were status-only - ending workflow"
        )
        return "end"

    def _log_routing_debug(
        self, last_message: BaseMessage, messages: List[BaseMessage]
    ):
        """Log routing debug information.

        Args:
            last_message: Last message in state
            messages: All messages in state
        """
        self.logger.debug(
            f"Last message type: {type(last_message).__name__}",
        )
        self.logger.debug(
            f"Has tool_calls attribute: {hasattr(last_message, 'tool_calls')}",
        )

        if hasattr(last_message, "tool_calls"):
            self.logger.debug(
                f"tool_calls value: {last_message.tool_calls}",
            )

        if hasattr(last_message, "content"):
            content_preview = (
                last_message.content[:300] if last_message.content else "None"
            )
            self.logger.debug(
                f"Message content preview: {content_preview}",
            )

        # Log message history
        tool_messages = self._get_tool_messages(messages)
        ai_messages = [
            msg for msg in messages if msg.__class__.__name__ == "AIMessage"
        ]

        self.logger.debug(
            f"Routing: has_tool_calls={self._has_tool_calls(last_message)}, message_type={type(last_message).__name__}"
        )
        self.logger.debug(
            f"Message history: {len(ai_messages)} AI messages, {len(tool_messages)} tool results"
        )

    def _is_duplicate_tool_call(
        self, last_message: BaseMessage, messages: List[BaseMessage]
    ) -> bool:
        """Check if last message contains duplicate tool call.

        Args:
            last_message: Last AI message with tool calls
            messages: All messages in state

        Returns:
            True if duplicate detected
        """
        tool_messages = self._get_tool_messages(messages)
        ai_messages = [
            msg for msg in messages if msg.__class__.__name__ == "AIMessage"
        ]

        # Need at least 2 AI messages and some tool results
        if not tool_messages or len(ai_messages) < 2:
            return False

        # Get previous tool calls
        previous_tool_calls = self._extract_previous_tool_calls(
            ai_messages,
            max_last_messages=AIRUNNER_LLM_DUPLICATE_TOOL_CALL_WINDOW,
        )

        # Check each current tool call against previous ones
        for current_tc in last_message.tool_calls:
            if self._check_tool_call_duplicate(
                current_tc, previous_tool_calls, tool_messages
            ):
                return True

        return False

    def _extract_previous_tool_calls(
        self,
        ai_messages: List[BaseMessage],
        max_last_messages: Optional[int] = None,
    ) -> List[Dict]:
        """Extract all previous tool calls from AI messages.

        Args:
            ai_messages: List of AI messages

        Returns:
            List of tool call dictionaries
        """
        previous_tool_calls = []
        # Optionally limit previous AI messages to the last `max_last_messages`
        if max_last_messages is not None and max_last_messages > 0:
            ai_messages = ai_messages[-(max_last_messages + 1) :]

        for i, ai_msg in enumerate(ai_messages[:-1]):  # Exclude current
            if hasattr(ai_msg, "tool_calls") and ai_msg.tool_calls:
                for tc in ai_msg.tool_calls:
                    previous_tool_calls.append(
                        {
                            "name": tc.get("name"),
                            "args": tc.get("args", {}),
                            "message_index": i,
                        }
                    )
        return previous_tool_calls

    def _check_tool_call_duplicate(
        self,
        current_tc: Dict,
        previous_tool_calls: List[Dict],
        tool_messages: List,
    ) -> bool:
        """Check if current tool call is duplicate of previous one.

        Args:
            current_tc: Current tool call dictionary
            previous_tool_calls: List of previous tool calls
            tool_messages: List of tool messages

        Returns:
            True if duplicate found
        """
        current_name = current_tc.get("name")
        current_args = current_tc.get("args", {})
        current_normalized = self._normalize_args(current_args)

        for prev_tc in previous_tool_calls:
            if prev_tc["name"] == current_name:
                prev_normalized = self._normalize_args(prev_tc["args"])

                if current_normalized == prev_normalized:
                    self._log_duplicate_detection(
                        current_name, current_args, tool_messages
                    )
                    return True

        return False

    def _normalize_args(self, args: Any) -> Tuple:
        """Convert args dict to comparable format, handling nested structures.

        Args:
            args: Arguments to normalize

        Returns:
            Normalized tuple representation
        """
        if not isinstance(args, dict):
            return str(args)

        items = []
        for k, v in sorted(args.items()):
            if isinstance(v, dict):
                v = self._normalize_args(v)
            elif isinstance(v, list):
                v = tuple(v)
            items.append((k, v))
        return tuple(items)

    def _log_duplicate_detection(
        self, tool_name: str, tool_args: Dict, tool_messages: List
    ):
        """Log duplicate tool call detection.

        Args:
            tool_name: Name of duplicate tool
            tool_args: Arguments of duplicate tool
            tool_messages: List of tool messages
        """
        self.logger.error(f"🔁 DUPLICATE TOOL CALL DETECTED!")
        self.logger.error(f"   Tool: {tool_name}")
        self.logger.error(f"   Arguments: {tool_args}")
        self.logger.error(
            f"   This exact tool call was already executed in a previous turn."
        )
        self.logger.error(
            f"   Model is stuck in a loop - forcing conversational response."
        )

        if tool_messages:
            last_tool_content = (
                tool_messages[-1].content if tool_messages[-1].content else ""
            )
            self.logger.info(
                f"   Previous tool results available: {len(last_tool_content)} chars"
            )

    def _log_tool_call_info(
        self, last_message: BaseMessage, messages: List[BaseMessage]
    ):
        """Log tool call information.

        Args:
            last_message: Last AI message with tool calls
            messages: All messages in state
        """
        tool_names = [tc.get("name") for tc in last_message.tool_calls]
        self.logger.info(
            f"Model requested {len(last_message.tool_calls)} tool calls: {tool_names}"
        )

        # Log previous tool result
        tool_messages = self._get_tool_messages(messages)
        if tool_messages:
            last_tool_result = tool_messages[-1]
            if hasattr(last_tool_result, "content"):
                result_content = last_tool_result.content
                result_preview = (
                    result_content[:200] if result_content else "No content"
                )
                self.logger.info(
                    f"📋 Previous tool result length: {len(result_content)} chars, preview: {result_preview}..."
                )

    # ========================================================================
    # CALL MODEL NODE
    # ========================================================================

    def _call_model(self, state: "WorkflowState") -> Dict[str, Any]:
        """Call the model with trimmed message history.

        Args:
            state: Workflow state containing messages and optional generation_kwargs

        Returns:
            Updated state with new AI message
        """
        # Debug: Log the number of messages and their types
        messages = state["messages"]
        self.logger.info(
            f"[CALL MODEL DEBUG] Total messages in state: {len(messages)}"
        )
        for i, msg in enumerate(messages[-5:]):  # Show last 5 messages
            msg_type = type(msg).__name__
            content_preview = (
                str(msg.content)[:100]
                if hasattr(msg, "content")
                else "No content"
            )
            self.logger.info(
                f"[CALL MODEL DEBUG] Message {i}: {msg_type} - {content_preview}"
            )

        generation_kwargs = state.get("generation_kwargs", {})

        # Trim messages
        trimmed_messages = self._trim_messages(state["messages"])

        # Build prompt with tool instructions
        prompt = self._build_prompt(trimmed_messages)

        # Generate response
        response_message = self._generate_response(prompt, generation_kwargs)

        return {"messages": [response_message]}

    def _trim_messages(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        """Trim message history to max tokens.

        Args:
            messages: List of messages to trim

        Returns:
            Trimmed message list
        """
        return trim_messages(
            messages,
            max_tokens=self._max_tokens,
            strategy="last",
            token_counter=self._token_counter,
            # Preserve system/phase instructions so later nodes don't lose guardrails
            include_system=True,
            allow_partial=False,
            start_on="human",
        )

    def _build_prompt(self, trimmed_messages: List[BaseMessage]):
        """Build prompt with system message and tool instructions.

        Args:
            trimmed_messages: Trimmed message list

        Returns:
            Formatted prompt
        """
        # Escape curly braces for LangChain template compatibility
        escaped_system_prompt = self._escape_system_prompt()

        # Add tool instructions for JSON mode (bind_tools doesn't inject them)
        escaped_system_prompt = self._add_tool_instructions(
            escaped_system_prompt
        )

        # Add post-tool instructions if needed
        escaped_system_prompt = self._add_post_tool_instructions(
            escaped_system_prompt, trimmed_messages
        )

        # Debug logging
        self.logger.debug("Full system prompt being sent to model:")
        self.logger.debug("%s...", escaped_system_prompt[:1000])

        # Build prompt template
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", escaped_system_prompt),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        return prompt.invoke({"messages": trimmed_messages})

    def _should_include_tool_instructions(
        self, trimmed_messages: List[BaseMessage]
    ) -> bool:
        """Determine whether to include tool instructions in system prompt.

        Heuristic rules (fast, local):
        - If no tools bound, return False.
        - If last user message length < 25 chars AND contains only a greeting/ack
          and no action verbs or tool-related keywords, return False.
        - Otherwise return True.

        This prevents the model from seeing the full tool catalogue when the
        user just says "hello" and thus reduces spurious tool call attempts.
        """
        if not self._tools:
            return False

        if not trimmed_messages:
            return False

        last = trimmed_messages[-1]
        # Only gate on HumanMessage
        if last.__class__.__name__ != "HumanMessage":
            return True

        content = (getattr(last, "content", "") or "").strip().lower()
        if len(content) > 25:
            return True

        # Greeting / acknowledgement patterns
        greeting_patterns = [
            "hello",
            "hi",
            "hey",
            "good morning",
            "good afternoon",
            "good evening",
            "thanks",
            "thank you",
            "ok",
            "okay",
            "yo",
        ]
        action_keywords = [
            "solve",
            "calculate",
            "search",
            "find",
            "create",
            "generate",
            "update",
            "schedule",
            "plot",
            "graph",
        ]

        if any(k in content for k in action_keywords):
            return True

        # strip punctuation for greeting match
        normalized = re.sub(r"[!.?,]", "", content)
        if normalized in greeting_patterns:
            return False

        return True

    def _escape_system_prompt(self) -> str:
        """Escape curly braces in system prompt for LangChain.

        Returns:
            Escaped system prompt
        """
        # CRITICAL FIX: Always use _system_prompt (the stored value set by update_system_prompt),
        # NOT the system_prompt property which dynamically generates the chatbot prompt.
        # This ensures custom system prompts (e.g., for classification) are preserved.
        prompt_source = self._system_prompt

        return prompt_source.replace("{", "{{").replace("}", "}}")

    def _add_tool_instructions(self, system_prompt: str) -> str:
        """Add tool instructions to system prompt if tools available.

        NOTE: For Qwen JSON mode, tools should be formatted by apply_chat_template,
        NOT manually injected into the system prompt. bind_tools() provides tools
        to the chat model, which should handle formatting them properly.

        For native modes (Mistral), bind_tools() handles everything automatically.

        Args:
            system_prompt: Current system prompt

        Returns:
            Unchanged system prompt (tools handled by chat model adapter)
        """
        if not self._tools or len(self._tools) == 0:
            return system_prompt

        # Tools are handled by the chat model adapter's apply_chat_template
        # Do NOT manually inject tool lists - this causes model confusion
        tool_calling_mode = getattr(
            self._chat_model, "tool_calling_mode", "react"
        )

        self.logger.debug(
            "Tools (%s) bound via bind_tools() - chat adapter will format them (mode: %s)",
            len(self._tools),
            tool_calling_mode,
        )

        return system_prompt

    def _add_post_tool_instructions(
        self, system_prompt: str, trimmed_messages: List[BaseMessage]
    ) -> str:
        """Add post-tool execution instructions if needed.

        Args:
            system_prompt: Current system prompt
            trimmed_messages: Trimmed message list

        Returns:
            System prompt with post-tool instructions
        """
        has_tool_results = any(
            msg.__class__.__name__ == "ToolMessage" for msg in trimmed_messages
        )

        tool_calling_mode = getattr(
            self._chat_model, "tool_calling_mode", "react"
        )

        if has_tool_results and tool_calling_mode == "json":
            # Check if response format is explicitly set
            response_format = getattr(self, "_response_format", None)
            self.logger.info(
                f"[POST-TOOL] response_format={response_format}, tool_calling_mode={tool_calling_mode}"
            )

            if response_format == "json":
                # Force JSON response even after tools
                instruction = (
                    "\n\n=== CRITICAL RESPONSE FORMAT REQUIREMENT ===\n"
                    "You have tool results in the conversation above. "
                    "Now answer the user's question using that information.\n"
                    "YOU MUST respond ONLY with valid JSON in the EXACT format specified in the system prompt above.\n"
                    "Do NOT write conversational text. Do NOT explain or narrate. ONLY output the JSON object.\n"
                    "Your entire response must be parseable JSON - nothing else."
                )
            elif response_format == "conversational":
                # Explicitly request conversational response
                instruction = (
                    "\n\nYou have tool results in the conversation above. "
                    "Answer the user's question using that information. "
                    "Respond conversationally, not in JSON."
                )
            elif response_format is None:
                # Default behavior - conversational
                instruction = (
                    "\n\nYou have tool results in the conversation above. "
                    "Answer the user's question using that information. "
                    "Respond conversationally, not in JSON."
                )
            else:
                # Custom format specified
                instruction = (
                    f"\n\nYou have tool results in the conversation above. "
                    f"Answer the user's question using that information. "
                    f"Respond in {response_format} format."
                )

            system_prompt += instruction
            self.logger.info(
                f"[POST-TOOL] Full instruction text:\n{instruction}"
            )

            # After tool execution, instruct model to respond normally
            tool_msgs = [
                m
                for m in trimmed_messages
                if m.__class__.__name__ == "ToolMessage"
            ]

            if tool_msgs:
                self.logger.info(
                    f"Model has access to {len(tool_msgs)} tool result(s)"
                )
                for i, tool_msg in enumerate(tool_msgs):
                    result_preview = (
                        tool_msg.content[:200]
                        if hasattr(tool_msg, "content")
                        else "No content"
                    )
                    self.logger.info(
                        f"  Tool result {i+1} preview: {result_preview}..."
                    )

        return system_prompt

    def _generate_response(
        self, formatted_prompt, generation_kwargs: Dict
    ) -> AIMessage:
        """Generate response from model (streaming or invoke).

        Args:
            formatted_prompt: Formatted prompt
            generation_kwargs: Generation parameters

        Returns:
            AIMessage response
        """
        if hasattr(self._chat_model, "stream"):
            return self._generate_streaming_response(
                formatted_prompt, generation_kwargs
            )
        else:
            return self._generate_invoke_response(formatted_prompt)

    def _generate_streaming_response(
        self, formatted_prompt, generation_kwargs: Dict
    ) -> Optional[AIMessage]:
        """Generate response using streaming.

        Args:
            formatted_prompt: Formatted prompt
            generation_kwargs: Generation parameters

        Returns:
            AIMessage response or None if error
        """
        streamed_content: List[str] = []
        last_chunk_message: Optional[BaseMessage] = None
        collected_tool_calls: List = []  # Collect tool_calls from ALL chunks
        
        # Track thinking state for Qwen3 <think>...</think> blocks
        in_thinking_block = False
        thinking_started = False  # Track if we've already seen <think>
        thinking_content = []
        final_thinking_content = None  # Store completed thinking content for DB persistence
        
        has_emitter = hasattr(self, "_signal_emitter") and self._signal_emitter is not None
        self.logger.debug(f"[THINKING] Starting streaming response generation (has_signal_emitter={has_emitter})")

        try:
            for chunk in self._chat_model.stream(
                formatted_prompt, **generation_kwargs
            ):
                if self._interrupted:
                    break

                chunk_message = getattr(chunk, "message", chunk)
                text = getattr(chunk_message, "content", "") or ""

                # Always capture last chunk (might have tool_calls with no content)
                last_chunk_message = chunk_message

                # Collect tool_calls from ANY chunk that has them
                chunk_tool_calls = getattr(chunk_message, "tool_calls", None)
                if chunk_tool_calls:
                    collected_tool_calls.extend(chunk_tool_calls)

                # Only skip if content is empty AND no tool_calls
                if not text and not chunk_tool_calls:
                    continue

                streamed_content.append(text)
                
                # Debug: Log every chunk
                self.logger.debug(f"[THINKING] Chunk received: '{text[:50]}...' (in_thinking={in_thinking_block})")
                
                # Detect thinking block boundaries
                # Check for <think> opening tag - only if we haven't seen one yet
                if "<think>" in text and not thinking_started:
                    in_thinking_block = True
                    thinking_started = True
                    self.logger.debug("[THINKING] Detected <think> tag - starting thinking block")
                    # Emit thinking started signal
                    if hasattr(self, "_signal_emitter") and self._signal_emitter:
                        self._signal_emitter.emit_signal(
                            SignalCode.LLM_THINKING_SIGNAL,
                            {"status": "started", "content": ""}
                        )
                    # Don't stream the <think> tag itself to the thinking content
                    # Extract any text after <think> in this chunk
                    after_think = text.split("<think>", 1)[1] if "<think>" in text else ""
                    
                    # Check if </think> is also in this chunk (entire thinking block in one chunk)
                    if "</think>" in after_think:
                        # Both tags in same chunk - extract thinking and remaining content
                        before_close = after_think.split("</think>", 1)[0]
                        after_close = after_think.split("</think>", 1)[1]
                        
                        if before_close:
                            thinking_content.append(before_close)
                            if hasattr(self, "_signal_emitter") and self._signal_emitter:
                                self._signal_emitter.emit_signal(
                                    SignalCode.LLM_THINKING_SIGNAL,
                                    {"status": "streaming", "content": before_close}
                                )
                        
                        # Mark thinking as complete
                        in_thinking_block = False
                        final_thinking_content = "".join(thinking_content)
                        self.logger.debug(f"[THINKING] Complete thinking block in single chunk, content len={len(final_thinking_content)}")
                        
                        if hasattr(self, "_signal_emitter") and self._signal_emitter:
                            self._signal_emitter.emit_signal(
                                SignalCode.LLM_THINKING_SIGNAL,
                                {"status": "completed", "content": final_thinking_content}
                            )
                        thinking_content = []
                        
                        # Stream any content after </think> to the main callback
                        if after_close and self._token_callback:
                            try:
                                self._token_callback(after_close)
                            except Exception as callback_error:
                                self.logger.error(
                                    "Token callback failed: %s",
                                    callback_error,
                                    exc_info=True,
                                )
                    elif after_think:
                        # Only <think> in this chunk, stream content to thinking
                        thinking_content.append(after_think)
                        if hasattr(self, "_signal_emitter") and self._signal_emitter:
                            self._signal_emitter.emit_signal(
                                SignalCode.LLM_THINKING_SIGNAL,
                                {"status": "streaming", "content": after_think}
                            )
                    continue  # Skip normal processing for this chunk
                
                # If we're in a thinking block, emit thinking content
                if in_thinking_block:
                    # Check for </think> closing tag first
                    if "</think>" in text:
                        # Extract text before </think>
                        before_close = text.split("</think>", 1)[0]
                        after_close = text.split("</think>", 1)[1] if "</think>" in text else ""
                        
                        if before_close:
                            thinking_content.append(before_close)
                            if hasattr(self, "_signal_emitter") and self._signal_emitter:
                                self._signal_emitter.emit_signal(
                                    SignalCode.LLM_THINKING_SIGNAL,
                                    {"status": "streaming", "content": before_close}
                                )
                        
                        # Mark thinking as complete
                        in_thinking_block = False
                        self.logger.debug(f"[THINKING] Detected </think> tag - ending thinking block, content len={len(''.join(thinking_content))}")
                        
                        # Save thinking content for DB persistence BEFORE clearing the list
                        final_thinking_content = "".join(thinking_content)
                        
                        if hasattr(self, "_signal_emitter") and self._signal_emitter:
                            self._signal_emitter.emit_signal(
                                SignalCode.LLM_THINKING_SIGNAL,
                                {"status": "completed", "content": final_thinking_content}
                            )
                        thinking_content = []
                        
                        # Stream any content after </think> to the main callback
                        if after_close and self._token_callback:
                            try:
                                self._token_callback(after_close)
                            except Exception as callback_error:
                                self.logger.error(
                                    "Token callback failed: %s",
                                    callback_error,
                                    exc_info=True,
                                )
                    else:
                        # Stream thinking content to GUI
                        if hasattr(self, "_signal_emitter") and self._signal_emitter:
                            self._signal_emitter.emit_signal(
                                SignalCode.LLM_THINKING_SIGNAL,
                                {"status": "streaming", "content": text}
                            )
                        thinking_content.append(text)
                    continue  # Don't stream thinking to main callback
                
                # Stream each chunk to GUI immediately (non-thinking content only)
                if text and self._token_callback:
                    try:
                        self._token_callback(text)
                    except Exception as callback_error:
                        self.logger.error(
                            "Token callback failed: %s",
                            callback_error,
                            exc_info=True,
                        )

            # Return message if we have content or tool_calls
            if streamed_content or last_chunk_message:
                # Use final_thinking_content if available (from completed thinking block)
                # Otherwise fall back to current thinking_content list (for incomplete thinking)
                thinking_to_save = final_thinking_content or ("".join(thinking_content) if thinking_content else None)
                self.logger.debug(f"[THINKING STREAM] Collected thinking_content length: {len(thinking_to_save) if thinking_to_save else 0}")
                return self._create_streamed_message(
                    streamed_content, last_chunk_message, collected_tool_calls, thinking_to_save
                )

        except Exception as exc:
            self.logger.error(
                "Error during streamed model call: %s", exc, exc_info=True
            )

        return None

    def _create_streamed_message(
        self,
        streamed_content: List[str],
        last_chunk_message: Optional[BaseMessage],
        collected_tool_calls: Optional[List] = None,
        thinking_content: Optional[str] = None,
    ) -> AIMessage:
        """Create AIMessage from streamed content.

        Args:
            streamed_content: List of content chunks
            last_chunk_message: Last chunk message
            collected_tool_calls: Tool calls collected from all chunks
            thinking_content: Thinking content from <think> blocks (optional)

        Returns:
            Complete AIMessage
        """
        additional_kwargs = {}
        tool_calls = collected_tool_calls or []  # Use collected tool_calls

        if last_chunk_message is not None:
            additional_kwargs = getattr(
                last_chunk_message, "additional_kwargs", {}
            )
            # Don't override collected_tool_calls with last chunk's tool_calls
            if not collected_tool_calls:
                tool_calls = (
                    getattr(last_chunk_message, "tool_calls", None) or []
                )

        complete_content = "".join(streamed_content)
        
        # Strip <think>...</think> blocks from Qwen3 responses
        # The thinking is useful for reasoning but shouldn't be in final output
        complete_content = strip_thinking_tags(complete_content)
        
        # Store thinking content in additional_kwargs so it can be saved to DB
        if thinking_content:
            additional_kwargs = dict(additional_kwargs)  # Make a copy to avoid mutating
            additional_kwargs["thinking_content"] = thinking_content
            self.logger.debug(f"[THINKING MSG] Stored thinking_content in additional_kwargs: {len(thinking_content)} chars")

        response_message = AIMessage(
            content=complete_content,
            additional_kwargs=additional_kwargs,
            tool_calls=tool_calls or [],
        )
        
        self.logger.debug(f"[THINKING MSG] Created AIMessage with additional_kwargs keys: {list(additional_kwargs.keys())}")

        return response_message

    def _generate_invoke_response(self, formatted_prompt) -> AIMessage:
        """Generate response using invoke (non-streaming).

        Args:
            formatted_prompt: Formatted prompt

        Returns:
            AIMessage response
        """
        response_message = self._chat_model.invoke(formatted_prompt)

        # Strip <think>...</think> blocks from Qwen3 responses
        if hasattr(response_message, "content") and response_message.content:
            cleaned_content = strip_thinking_tags(response_message.content)
            if cleaned_content != response_message.content:
                response_message = AIMessage(
                    content=cleaned_content,
                    additional_kwargs=getattr(response_message, "additional_kwargs", {}),
                    tool_calls=getattr(response_message, "tool_calls", []) or [],
                )

        if (
            self._token_callback
            and hasattr(response_message, "content")
            and response_message.content
        ):
            try:
                self._token_callback(response_message.content)
            except Exception as callback_error:
                self.logger.error(
                    "Token callback failed: %s",
                    callback_error,
                    exc_info=True,
                )

        return response_message
