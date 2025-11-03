"""Node functions mixin for WorkflowManager.

Handles LangGraph node implementations (_call_model, _force_response_node, _route_after_model).
These are broken into focused helper methods for maintainability.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    BaseMessage,
    trim_messages,
)

if TYPE_CHECKING:
    from airunner.components.llm.managers.workflow_manager import WorkflowState


class NodeFunctionsMixin:
    """Implements LangGraph node functions for the workflow."""

    def __init__(self):
        """Initialize node functions mixin."""
        self.logger = logging.getLogger(__name__)
        self._system_prompt = ""
        self._chat_model = None
        self._tools = []
        self._max_tokens = 2000
        self._token_counter = None
        self._token_callback = None
        self._interrupted = False
        self._conversation_id: Optional[int] = None

    # ========================================================================
    # FORCE RESPONSE NODE
    # ========================================================================

    def _force_response_node(self, state: "WorkflowState") -> "WorkflowState":
        """Node that generates forced response when redundancy detected.

        This is a proper LangGraph node (not just a router) so state updates
        are properly persisted to the checkpoint/database.

        Args:
            state: Workflow state with messages

        Returns:
            Updated state with forced response message
        """
        last_message = state["messages"][-1]

        if not self._has_tool_calls(last_message):
            self.logger.error(
                "Force response node called but last message has no tool_calls"
            )
            return state

        # Get tool information
        tool_name = last_message.tool_calls[0].get("name")
        tool_messages = self._get_tool_messages(state["messages"])
        all_tool_content = self._combine_tool_results(tool_messages)

        self.logger.info(
            f"Force response node: Generating answer from {len(all_tool_content)} chars across {len(tool_messages)} tool result(s)"
        )

        # Generate response based on tool results
        response_content = self._generate_forced_response(
            all_tool_content, tool_name
        )

        # Create AIMessage with NO tool_calls (empty list)
        forced_message = AIMessage(
            content=response_content,
            tool_calls=[],  # Explicitly set to empty list
        )
        state["messages"][-1] = forced_message

        self.logger.info(
            f"✓ Force response node: Replaced tool call with {len(response_content)} char conversational response (tool_calls=[])"
        )

        return state

    def _has_tool_calls(self, message: BaseMessage) -> bool:
        """Check if message has tool calls.

        Args:
            message: Message to check

        Returns:
            True if message has tool_calls attribute with non-empty value
        """
        return hasattr(message, "tool_calls") and message.tool_calls

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
        self, all_tool_content: str, tool_name: str
    ) -> str:
        """Generate forced response based on tool results.

        Args:
            all_tool_content: Combined tool results
            tool_name: Name of the tool that was called

        Returns:
            Generated response content
        """
        if len(all_tool_content) > 100:
            return self._generate_response_from_results(
                all_tool_content, tool_name
            )
        else:
            return self._generate_fallback_response(tool_name)

    def _generate_response_from_results(
        self, all_tool_content: str, tool_name: str
    ) -> str:
        """Generate response from actual tool results.

        Args:
            all_tool_content: Combined tool results
            tool_name: Name of the tool

        Returns:
            Generated response content
        """
        self.logger.info(
            f"Forcing model to answer based on {tool_name} results..."
        )

        try:
            simple_prompt_text = f"""Based on the following tool results, answer the user's question:

{all_tool_content}

Provide a clear, conversational answer using only the information above."""

            # Convert to message format
            simple_prompt = [HumanMessage(content=simple_prompt_text)]

            # Stream response
            response_content = self._stream_model_response(simple_prompt)

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

    def _stream_model_response(self, prompt: List[BaseMessage]) -> str:
        """Stream model response and accumulate content.

        Args:
            prompt: List of messages to send to model

        Returns:
            Complete response content
        """
        response_content = ""
        for chunk in self._chat_model.stream(
            prompt, disable_tool_parsing=True
        ):
            chunk_content = (
                chunk.content if hasattr(chunk, "content") else str(chunk)
            )
            if chunk_content:
                response_content += chunk_content
                if self._token_callback:
                    self._token_callback(chunk_content)
        return response_content

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

    def _log_routing_debug(
        self, last_message: BaseMessage, messages: List[BaseMessage]
    ):
        """Log routing debug information.

        Args:
            last_message: Last message in state
            messages: All messages in state
        """
        print(
            f"[WORKFLOW DEBUG] Last message type: {type(last_message).__name__}",
            flush=True,
        )
        print(
            f"[WORKFLOW DEBUG] Has tool_calls attribute: {hasattr(last_message, 'tool_calls')}",
            flush=True,
        )

        if hasattr(last_message, "tool_calls"):
            print(
                f"[WORKFLOW DEBUG] tool_calls value: {last_message.tool_calls}",
                flush=True,
            )

        if hasattr(last_message, "content"):
            content_preview = (
                last_message.content[:300] if last_message.content else "None"
            )
            print(
                f"[WORKFLOW DEBUG] Message content preview: {content_preview}",
                flush=True,
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
        previous_tool_calls = self._extract_previous_tool_calls(ai_messages)

        # Check each current tool call against previous ones
        for current_tc in last_message.tool_calls:
            if self._check_tool_call_duplicate(
                current_tc, previous_tool_calls, tool_messages
            ):
                return True

        return False

    def _extract_previous_tool_calls(
        self, ai_messages: List[BaseMessage]
    ) -> List[Dict]:
        """Extract all previous tool calls from AI messages.

        Args:
            ai_messages: List of AI messages

        Returns:
            List of tool call dictionaries
        """
        previous_tool_calls = []
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

        # Add tool instructions if tools available
        escaped_system_prompt = self._add_tool_instructions(
            escaped_system_prompt
        )

        # Add post-tool instructions if needed
        escaped_system_prompt = self._add_post_tool_instructions(
            escaped_system_prompt, trimmed_messages
        )

        # Debug logging
        print(
            f"[WORKFLOW DEBUG] Full system prompt being sent to model:",
            flush=True,
        )
        print(f"{escaped_system_prompt[:1000]}...", flush=True)
        print(f"[WORKFLOW DEBUG] End of system prompt\n", flush=True)

        # Build prompt template
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", escaped_system_prompt),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        return prompt.invoke({"messages": trimmed_messages})

    def _escape_system_prompt(self) -> str:
        """Escape curly braces in system prompt for LangChain.

        Returns:
            Escaped system prompt
        """
        return self._system_prompt.replace("{", "{{").replace("}", "}}")

    def _add_tool_instructions(self, system_prompt: str) -> str:
        """Add tool instructions to system prompt if tools available.

        Args:
            system_prompt: Current system prompt

        Returns:
            System prompt with tool instructions
        """
        if self._tools and len(self._tools) > 0:
            compact_tools = self._create_compact_tool_list()
            if compact_tools:
                # Escape curly braces
                compact_tools_escaped = compact_tools.replace(
                    "{", "{{"
                ).replace("}", "}}")
                system_prompt = f"{system_prompt}\n\n{compact_tools_escaped}"
                print(
                    f"[WORKFLOW DEBUG] Appended tool instructions ({len(self._tools)} tools) to system prompt",
                    flush=True,
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
            # After tool execution, instruct model to respond normally
            tool_msgs = [
                m
                for m in trimmed_messages
                if m.__class__.__name__ == "ToolMessage"
            ]

            instruction = (
                "\n\nYou have tool results in the conversation above. "
                "Answer the user's question using that information. "
                "Respond conversationally, not in JSON."
            )
            system_prompt += instruction
            self.logger.debug(
                f"Added post-tool instruction: {instruction.strip()}"
            )

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

                # Skip content processing if empty
                if not text:
                    continue

                streamed_content.append(text)

            if streamed_content:
                return self._create_streamed_message(
                    streamed_content, last_chunk_message
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
    ) -> AIMessage:
        """Create AIMessage from streamed content.

        Args:
            streamed_content: List of content chunks
            last_chunk_message: Last chunk message

        Returns:
            Complete AIMessage
        """
        additional_kwargs = {}
        tool_calls = None

        if last_chunk_message is not None:
            additional_kwargs = getattr(
                last_chunk_message, "additional_kwargs", {}
            )
            tool_calls = getattr(last_chunk_message, "tool_calls", None)

        complete_content = "".join(streamed_content)

        # Stream content to GUI
        if complete_content and self._token_callback:
            try:
                self._token_callback(complete_content)
            except Exception as callback_error:
                self.logger.error(
                    "Token callback failed: %s",
                    callback_error,
                    exc_info=True,
                )

        response_message = AIMessage(
            content=complete_content,
            additional_kwargs=additional_kwargs,
            tool_calls=tool_calls or [],
        )

        print(
            f"[DEBUG WORKFLOW] AIMessage content: {response_message.content[:200]}"
        )

        return response_message

    def _generate_invoke_response(self, formatted_prompt) -> AIMessage:
        """Generate response using invoke (non-streaming).

        Args:
            formatted_prompt: Formatted prompt

        Returns:
            AIMessage response
        """
        response_message = self._chat_model.invoke(formatted_prompt)

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
