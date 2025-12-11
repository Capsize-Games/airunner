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

from langchain_core.messages import SystemMessage
from airunner.components.llm.utils.thinking_parser import (
    strip_thinking_tags,
    has_thinking_content,
    detect_thinking_open_tag,
    detect_thinking_close_tag,
)
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

    # Class-level set to track workflow tools that need special handling
    WORKFLOW_TOOLS = {"start_workflow", "transition_phase", "add_todo_item", 
                     "start_todo_item", "complete_todo_item", "get_workflow_status"}

    def _force_response_node(self, state: "WorkflowState") -> Dict[str, Any]:
        """Node that generates forced response when redundancy detected.

        This is a proper LangGraph node (not just a router) so state updates
        are properly persisted to the checkpoint/database.

        For workflow tool duplicates, we add a HumanMessage with instructions
        and set a flag to route back to the model. For other tools, we generate
        a final response.

        Args:
            state: Workflow state with messages

        Returns:
            Dict with new message(s) and optional routing flag
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

        # WORKFLOW TOOLS: When a duplicate workflow tool is detected, 
        # add instructions as a HumanMessage and route back to model
        # so it can actually call the next tool.
        if tool_name in self.WORKFLOW_TOOLS:
            self.logger.info(
                f"Force response node: Duplicate workflow tool '{tool_name}' - "
                f"adding continuation instructions and routing back to model"
            )
            continuation_msg = self._create_workflow_continuation_message(
                all_tool_content, tool_name, user_question
            )
            self.logger.info(
                f"✓ Force response node: Added continuation message, routing to model"
            )
            # Set flag for conditional routing back to model
            return {
                "messages": [continuation_msg],
                "workflow_continuation": True,
            }
        else:
            self.logger.info(
                f"Force response node: Generating answer from {len(all_tool_content)} chars across {len(tool_messages)} tool result(s)"
            )
            # Generate response based on tool results - this returns the full AIMessage
            forced_message = self._generate_forced_response_message(
                all_tool_content, tool_name, user_question, generation_kwargs
            )

            self.logger.info(
                f"✓ Force response node: Generated {len(forced_message.content) if forced_message.content else 0} char response"
            )

            # Return dict with new message for LangGraph to merge via add_messages reducer
            return {"messages": [forced_message], "workflow_continuation": False}

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

    def _generate_forced_response_message(
        self,
        tool_content: str,
        tool_name: str,
        user_question: str,
        generation_kwargs: Optional[Dict] = None,
    ) -> AIMessage:
        """Generate a full AIMessage response from tool results.

        This preserves thinking_content and other additional_kwargs.

        Args:
            tool_content: Combined content from tool executions
            tool_name: Name of the tool that was called
            user_question: Original user's question
            generation_kwargs: Optional generation parameters for streaming control

        Returns:
            Complete AIMessage with content and additional_kwargs
        """
        try:
            response_message = self._generate_response_message_from_results(
                tool_content, tool_name, user_question, generation_kwargs
            )
            if response_message:
                return response_message
        except Exception as e:
            self.logger.error(f"Failed to generate forced response: {e}")
        
        # Fallback
        fallback = "I found some information but encountered an issue generating a complete response."
        if self._token_callback:
            self._token_callback(fallback)
        return AIMessage(content=fallback, tool_calls=[])

    def _create_workflow_continuation_message(
        self,
        tool_content: str,
        tool_name: str,
        user_question: str,
    ) -> HumanMessage:
        """Create a HumanMessage with workflow continuation instructions.
        
        When the model calls the same workflow tool twice (e.g., start_workflow),
        this creates a HumanMessage with explicit instructions to call the NEXT
        tool in the sequence. The model will then be re-invoked with tools bound.
        
        Args:
            tool_content: The tool result content (contains workflow instructions)
            tool_name: Name of the workflow tool
            user_question: Original user question
            
        Returns:
            HumanMessage with workflow continuation instructions
        """
        self.logger.info(
            f"Creating workflow continuation message for duplicate '{tool_name}' call"
        )
        
        # Parse the tool result to extract the next action
        next_action = ""
        if "YOUR NEXT TOOL CALL:" in tool_content:
            lines = tool_content.split("\n")
            for line in lines:
                if "YOUR NEXT TOOL CALL:" in line:
                    next_action = line.split("YOUR NEXT TOOL CALL:")[-1].strip()
                    break
        elif "IMMEDIATE NEXT ACTION" in tool_content:
            lines = tool_content.split("\n")
            for i, line in enumerate(lines):
                if "Call this tool NOW:" in line and i + 1 < len(lines):
                    next_action = lines[i + 1].strip()
                    break
        
        # Build a strong prompt that forces the model to call the NEXT tool
        prompt_text = f"""[SYSTEM CORRECTION] You called {tool_name} twice. The workflow is ALREADY ACTIVE.

DO NOT output any text response. DO NOT explain what you will do.
You MUST call a workflow tool NOW.

{f"REQUIRED: Call {next_action}" if next_action else "Call transition_phase('planning', 'Simple task, moving to planning')"}

Your task: {user_question}

CALL THE TOOL NOW. NO TEXT RESPONSE."""

        return HumanMessage(content=prompt_text)

    def _generate_workflow_continuation_response(
        self,
        tool_content: str,
        tool_name: str,
        user_question: str,
        generation_kwargs: Optional[Dict] = None,
    ) -> AIMessage:
        """Generate a response that continues the workflow after duplicate detection.
        
        When the model calls the same workflow tool twice (e.g., start_workflow),
        this generates a response that explicitly tells the model to follow
        the workflow instructions from the tool result.
        
        Args:
            tool_content: The tool result content (contains workflow instructions)
            tool_name: Name of the workflow tool
            user_question: Original user question
            generation_kwargs: Optional generation parameters
            
        Returns:
            AIMessage with workflow continuation instructions
        """
        self.logger.info(
            f"Generating workflow continuation for duplicate '{tool_name}' call"
        )
        
        # Parse the tool result to extract the next action
        # The workflow tools output instructions like "YOUR NEXT TOOL CALL: transition_phase('planning', 'reason')"
        next_action = ""
        if "YOUR NEXT TOOL CALL:" in tool_content:
            lines = tool_content.split("\n")
            for line in lines:
                if "YOUR NEXT TOOL CALL:" in line:
                    next_action = line.split("YOUR NEXT TOOL CALL:")[-1].strip()
                    break
        elif "IMMEDIATE NEXT ACTION" in tool_content:
            # Extract the tool call from the instructions
            lines = tool_content.split("\n")
            for i, line in enumerate(lines):
                if "Call this tool NOW:" in line and i + 1 < len(lines):
                    next_action = lines[i + 1].strip()
                    break
        
        # Build a strong prompt that forces the model to continue the workflow
        prompt_text = f"""You already started the workflow. The workflow has given you specific instructions.

WORKFLOW STATUS:
{tool_content[:1500]}

CRITICAL: You called {tool_name} twice. The workflow is already active!

{"The next step is: " + next_action if next_action else "Follow the instructions in the workflow status above."}

DO NOT call {tool_name} again. Instead, call the NEXT tool in the sequence.

For a coding workflow, the typical sequence is:
1. start_workflow (DONE - you already did this)
2. transition_phase('planning', 'reason') 
3. add_todo_item('title', 'description')
4. transition_phase('execution', 'reason')
5. start_todo_item('todo_id')
6. create_code_file(path, content) or other code tools
7. complete_todo_item('todo_id')
8. transition_phase('complete', 'All done')

User's original request: {user_question}

Now call the NEXT workflow tool to continue. Do NOT repeat start_workflow."""

        try:
            # Stream response with the continuation prompt
            simple_prompt = [HumanMessage(content=prompt_text)]
            response_message = self._stream_model_response(
                simple_prompt, generation_kwargs
            )
            
            if response_message:
                return AIMessage(
                    content=response_message.content or "",
                    additional_kwargs=getattr(response_message, "additional_kwargs", {}),
                    tool_calls=getattr(response_message, "tool_calls", []),
                )
        except Exception as e:
            self.logger.error(f"Failed to generate workflow continuation: {e}")
        
        # Fallback - tell user the workflow is stuck
        fallback = (
            f"The workflow has been started but I'm having trouble continuing. "
            f"The next step should be to call transition_phase to move to the planning phase."
        )
        if self._token_callback:
            self._token_callback(fallback)
        return AIMessage(content=fallback, tool_calls=[])

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

    def _generate_response_message_from_results(
        self,
        all_tool_content: str,
        tool_name: str,
        user_question: str = "",
        generation_kwargs: Optional[Dict] = None,
    ) -> Optional[AIMessage]:
        """Generate full AIMessage from tool results (preserving thinking_content).

        Args:
            all_tool_content: Combined tool results
            tool_name: Name of the tool
            user_question: Original user question
            generation_kwargs: Optional generation parameters for streaming control

        Returns:
            Complete AIMessage with content and additional_kwargs, or None on error
        """
        self.logger.info(
            f"Forcing model to answer based on {tool_name} results (preserving thinking)..."
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

            # Stream response - returns full AIMessage with thinking_content
            response_message = self._stream_model_response(
                simple_prompt, generation_kwargs
            )

            if response_message:
                # Ensure tool_calls is empty
                return AIMessage(
                    content=response_message.content or "",
                    additional_kwargs=getattr(response_message, "additional_kwargs", {}),
                    tool_calls=[],
                )

            return None

        except Exception as e:
            self.logger.error(f"Failed to generate forced response message: {e}")
            return None

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
            response_message = self._stream_model_response(
                simple_prompt, generation_kwargs
            )

            # Extract content from the response message
            response_content = ""
            if response_message and hasattr(response_message, "content"):
                response_content = response_message.content or ""

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
            # Only try to set tool_calling_mode if it's not a read-only property
            try:
                if hasattr(chat_model, "tool_calling_mode"):
                    chat_model.tool_calling_mode = "react"
            except AttributeError:
                pass  # Property is read-only (e.g., ChatGGUF)
            if hasattr(chat_model, "use_json_mode"):
                chat_model.use_json_mode = False

            # Use the standard streaming response method which properly handles generation_kwargs
            response_message = self._generate_streaming_response(
                prompt, generation_kwargs
            )

            # Return the full AIMessage to preserve additional_kwargs including thinking_content
            return response_message
        finally:
            if hasattr(chat_model, "tools"):
                chat_model.tools = tools_backup
            # Only try to restore tool_calling_mode if it's not a read-only property
            try:
                if hasattr(chat_model, "tool_calling_mode"):
                    chat_model.tool_calling_mode = mode_backup
            except AttributeError:
                pass  # Property is read-only (e.g., ChatGGUF)
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

        # Check if the model is responding after a tool error without fixing it
        # This catches cases where the model hallucinates success instead of following error guidance
        tool_messages = self._get_tool_messages(state["messages"])
        if tool_messages:
            last_tool_msg = tool_messages[-1]
            tool_content = str(getattr(last_tool_msg, 'content', ''))
            
            # Check if last tool result was an ERROR that requires action
            if tool_content.startswith('ERROR:') and 'Cannot use' in tool_content:
                # Model responded with text instead of calling a corrective tool
                # Log the issue - this is a model behavior problem
                response_content = getattr(last_message, 'content', '')
                self.logger.warning(
                    f"[ROUTE DEBUG] Model ignored tool ERROR and responded with text: {response_content[:200]}"
                )
                # We can't easily force the model to retry, so we log and let it through
                # The error instructions in post-tool should help, but some models may still ignore them

        return "end"

    def _route_after_tools(self, state: "WorkflowState") -> str:
        """Route after tools execute - decide if model needs to respond.

        Some tools (like update_mood) are status-only and don't need a response.
        Other tools (like scrape_website) return data that needs interpretation.
        Task-completing tools (like create_code_file) should go to force_response.

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
        
        # Task-completing tools - route to force_response, not model
        # This prevents the model from making more tool calls after the task is done
        TASK_COMPLETING_TOOLS = {
            "create_code_file",       # Code was written - present it to user
            "write_file",             # File was written - present result
            "execute_python",         # Code was executed - present output
            "complete_todo_item",     # Workflow item completed
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
            
            if tool_name in NO_RESPONSE_TOOLS:
                continue
            
            # Check if tool result indicates success for task-completing tools
            last_tool_content = str(getattr(last_tool_msg, 'content', ''))
            tool_succeeded = any(
                indicator in last_tool_content.lower() 
                for indicator in ['created', 'successfully', 'written', '✓', 'complete', 'done']
            )
            
            if tool_name in TASK_COMPLETING_TOOLS and tool_succeeded:
                # Task completed successfully - force response, don't allow more tool calls
                self.logger.info(
                    f"[ROUTE DEBUG] Task-completing tool '{tool_name}' succeeded - "
                    "forcing response to prevent unnecessary tool calls"
                )
                return "force_response"
            
            # For other tools, enable agentic multi-tool workflows
            # The model can decide to call more tools (e.g., search -> scrape -> create_document)
            # or respond with the results. Infinite loops are prevented by:
            # 1. _is_duplicate_tool_call() check in _route_after_model
            # 2. Max iterations guard based on tool call count
            
            # Check if we've hit max iterations (prevent runaway loops)
            max_tool_iterations = 10  # Safety limit
            tool_call_count = len([
                m for m in state["messages"] 
                if hasattr(m, 'tool_calls') and m.tool_calls
            ])
            
            if tool_call_count >= max_tool_iterations:
                self.logger.warning(
                    f"[ROUTE DEBUG] Max tool iterations ({max_tool_iterations}) reached - forcing response"
                )
                return "force_response"

            # Route back to model to allow continuous tool calling
            self.logger.info(
                f"[ROUTE DEBUG] Tool '{tool_name}' completed - routing back to model for next action"
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

        # Trim messages (skip trimming for vision models to preserve multimodal parts)
        chat_model = getattr(self, "_chat_model", None)
        if chat_model and getattr(chat_model, "is_vision_model", False):
            trimmed_messages = state["messages"]
        else:
            trimmed_messages = self._trim_messages(state["messages"])

        # Build prompt with tool instructions
        prompt = self._build_prompt(trimmed_messages)

        # Generate response
        response_message = self._generate_response(prompt, generation_kwargs)

        return {"messages": [response_message]}

    def _trim_messages(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        """Trim message history to fit context window.

        Args:
            messages: List of messages to trim

        Returns:
            Trimmed message list
        """
        return trim_messages(
            messages,
            max_tokens=self._max_history_tokens,
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
        chat_model = getattr(self, "_chat_model", None)

        # Vision models: use the same escaped system prompt with tool instructions
        # as non-vision models. This ensures tools work for vision-capable models.
        if chat_model and getattr(chat_model, "is_vision_model", False):
            # Build system prompt with tool instructions (same as standard flow)
            escaped_system_prompt = self._escape_system_prompt()
            escaped_system_prompt = self._add_tool_instructions(escaped_system_prompt)
            escaped_system_prompt = self._add_post_tool_instructions(
                escaped_system_prompt, trimmed_messages
            )
            vision_system = SystemMessage(content=escaped_system_prompt)
            merged_messages: List[BaseMessage] = []

            for message in trimmed_messages:
                if message is None:
                    # Skip invalid entries to avoid NoneType errors downstream
                    self.logger.warning(
                        "[VISION PROMPT] Skipping None message while building prompt"
                    )
                    continue

                if (
                    merged_messages
                    and isinstance(message, HumanMessage)
                    and isinstance(merged_messages[-1], HumanMessage)
                ):
                    # Merge consecutive human messages to keep role alternation for chat templates
                    current_content = merged_messages[-1].content
                    new_content = message.content

                    if isinstance(current_content, list) and isinstance(new_content, list):
                        merged_messages[-1].content = current_content + new_content
                    elif isinstance(current_content, list):
                        merged_messages[-1].content = current_content + [new_content]
                    elif isinstance(new_content, list):
                        merged_messages[-1].content = [current_content] + new_content
                    else:
                        merged_messages[-1].content = f"{current_content}\n{new_content}"

                    self.logger.debug(
                        "[VISION PROMPT] Merged consecutive HumanMessages to maintain alternation"
                    )
                    continue

                merged_messages.append(message)

            vision_messages = [vision_system, *merged_messages]

            # Debugging: ensure we kept the human/image message
            has_human = any(isinstance(m, HumanMessage) for m in vision_messages)
            if not has_human:
                self.logger.warning(
                    "[VISION PROMPT] No HumanMessage present after vision prompt build; messages len=%s",
                    len(vision_messages),
                )
            else:
                self.logger.debug(
                    "[VISION PROMPT] Vision messages count=%s (system + %s user/tool msgs)",
                    len(vision_messages), len(vision_messages) - 1,
                )

            return vision_messages

        # Standard flow: escape and inject tool instructions
        escaped_system_prompt = self._escape_system_prompt()

        # Add tool instructions for JSON mode (bind_tools doesn't inject them)
        escaped_system_prompt = self._add_tool_instructions(
            escaped_system_prompt
        )

        # Add post-tool instructions if needed
        escaped_system_prompt = self._add_post_tool_instructions(
            escaped_system_prompt, trimmed_messages
        )

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
            Escaped system prompt with memory context injected
        """
        # CRITICAL FIX: Always use _system_prompt (the stored value set by update_system_prompt),
        # NOT the system_prompt property which dynamically generates the chatbot prompt.
        # This ensures custom system prompts (e.g., for classification) are preserved.
        prompt_source = self._system_prompt

        # NOTE: Memory context is NOT injected here anymore.
        # Knowledge should be accessed via RAG tools (recall_knowledge, rag_search)
        # to avoid polluting every conversation with potentially irrelevant stored facts.

        return prompt_source.replace("{", "{{").replace("}", "}}")

    def _get_memory_context_for_prompt(self) -> str:
        """Get memory context to inject into system prompt.
        
        Uses the daily markdown knowledge files for context.
        
        Returns:
            Memory context string or empty string
        """
        try:
            from airunner.components.knowledge.knowledge_base import get_knowledge_base
            kb = get_knowledge_base()
            context = kb.get_context(max_chars=2000)
            if context:
                self.logger.info(f"[MEMORY] Injecting {len(context)} chars of memory context")
            return context
        except Exception as e:
            self.logger.debug(f"[MEMORY] Failed to get memory context: {e}")
            return ""

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

        # NOTE: Vision models (e.g., Ministral-3) previously skipped tool instructions,
        # but this prevented them from calling tools at all. Now all models get tool
        # instructions via the ReAct pattern below.

        # Tools are handled by the chat model adapter's apply_chat_template
        # Do NOT manually inject tool lists - this causes model confusion
        tool_calling_mode = getattr(
            self._chat_model, "tool_calling_mode", "react"
        )

        # ReAct mode needs explicit, compact tool instructions to nudge tool calls
        if tool_calling_mode == "react":
            compact_tools = self._create_compact_tool_list()
            if compact_tools:
                # Escape braces to avoid LangChain template variable parsing
                escaped_tools = compact_tools.replace("{", "{{").replace("}", "}}")
                system_prompt = f"{system_prompt}\n\n{escaped_tools}"

        self.logger.debug(
            "Tools (%s) bound via bind_tools() - chat adapter will format them (mode: %s)",
            len(self._tools),
            tool_calling_mode,
        )

        # CRITICAL: When force_tool is set, add strong instruction for sequential execution
        force_tool = getattr(self, "_force_tool", None)
        if force_tool:
            sequential_instruction = (
                f"\n\n=== IMPORTANT: SEQUENTIAL TOOL EXECUTION REQUIRED ===\n"
                f"You MUST call the '{force_tool}' tool FIRST and ONLY this tool.\n"
                f"DO NOT call multiple tools at once.\n"
                f"Call ONE tool, wait for the result, then call the next tool.\n"
                f"This is a WORKFLOW - each step depends on the previous step's result.\n"
                f"=== END INSTRUCTION ===\n"
            )
            system_prompt += sequential_instruction
            self.logger.info(
                f"[TOOL INSTRUCTIONS] Added sequential execution instruction for force_tool='{force_tool}'"
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

        if not has_tool_results:
            return system_prompt

        # Check for ERROR responses from tools - these MUST be handled first
        tool_messages = [m for m in trimmed_messages if m.__class__.__name__ == "ToolMessage"]
        error_results = []
        for tm in tool_messages:
            content = str(getattr(tm, 'content', ''))
            # Check if tool returned an error
            if content.startswith('ERROR:') or content.startswith('Error:'):
                error_results.append(content)
        
        if error_results:
            # Critical: Tool returned an error - the model MUST NOT claim success
            error_instruction = (
                "\n\n=== CRITICAL: TOOL RETURNED AN ERROR - YOU MUST CALL A TOOL ===\n"
                "The previous tool call FAILED. Read the error message carefully.\n\n"
                "**ERROR MESSAGE:**\n"
                f"{error_results[-1][:800]}\n\n"
                "**YOU MUST DO ONE OF THESE:**\n"
                "1. Call the tool suggested in the error message (e.g., transition_phase, add_todo_item, start_todo_item)\n"
                "2. Follow the workflow steps exactly as described in the error\n\n"
                "**DO NOT:**\n"
                "- Claim the file was created (IT WAS NOT)\n"
                "- Skip workflow steps\n"
                "- Respond with text saying you completed the task\n"
                "- Give the user any output without first fixing the workflow state\n\n"
                "**NEXT ACTION:** Call one of these workflow tools:\n"
                "- transition_phase('planning', 'reason') - to move to next phase\n"
                "- add_todo_item('title', 'description') - to create a task\n"
                "- start_todo_item('todo_1') - to begin working on a task\n\n"
                "Call a tool NOW. Do not respond with text."
            )
            system_prompt += error_instruction
            self.logger.info(
                f"[POST-TOOL] Tool returned ERROR - injecting error handling instructions"
            )
            return system_prompt

        tool_calling_mode = getattr(
            self._chat_model, "tool_calling_mode", "react"
        )

        # Check if response format is explicitly set
        response_format = getattr(self, "_response_format", None)
        
        # Check if we're in research/agentic mode (force_tool was set)
        force_tool = getattr(self, "_force_tool", None)
        is_research_mode = force_tool == "search_web"
        
        # Count how many tool calls have been made to determine research phase
        tool_call_count = len([
            m for m in trimmed_messages 
            if hasattr(m, 'tool_calls') and m.tool_calls
        ])
        
        # Count scrape ATTEMPTS vs SUCCESSES
        scrape_attempts = sum(
            1 for m in trimmed_messages 
            if hasattr(m, 'tool_calls') and m.tool_calls
            for tc in m.tool_calls if tc.get('name') == 'scrape_website'
        )
        
        # Check for SUCCESSFUL scrapes by examining ToolMessage name and content
        successful_scrapes = 0
        failed_scrapes = 0
        tool_messages = [m for m in trimmed_messages if m.__class__.__name__ == "ToolMessage"]
        for tm in tool_messages:
            # Check if this is a scrape result by looking at the name attribute
            tool_name = getattr(tm, 'name', None)
            if tool_name == 'scrape_website':
                content = str(getattr(tm, 'content', ''))
                # Consider it successful if content is substantial and no error indicators
                is_error = (
                    'error' in content.lower()[:100] or 
                    'failed' in content.lower()[:100] or
                    'could not' in content.lower()[:100] or
                    len(content) < 200
                )
                if is_error:
                    failed_scrapes += 1
                else:
                    successful_scrapes += 1
        
        # Extract URLs from search results for reference
        search_urls = []
        for tm in tool_messages:
            content = str(getattr(tm, 'content', ''))
            if 'http' in content and 'search' in content.lower():
                # Extract URLs from search results
                import re
                urls = re.findall(r'https?://[^\s\]"<>]+', content)
                search_urls.extend(urls[:5])  # Keep top 5
        
        has_document = any(
            'create_research_document' in str(getattr(m, 'tool_calls', []))
            for m in trimmed_messages
        )
        
        self.logger.info(
            f"[POST-TOOL] response_format={response_format}, tool_calling_mode={tool_calling_mode}, "
            f"force_tool={force_tool}, is_research_mode={is_research_mode}, "
            f"tool_calls={tool_call_count}, scrape_attempts={scrape_attempts}, "
            f"successful_scrapes={successful_scrapes}, failed_scrapes={failed_scrapes}, "
            f"has_doc={has_document}, search_urls={len(search_urls)}"
        )

        # Build instruction based on mode
        if is_research_mode:
            # Research mode: provide explicit workflow instructions based on phase
            
            # Build URL suggestions if we have them
            url_hint = ""
            if search_urls:
                url_hint = "\n\n**URLS FROM YOUR SEARCH RESULTS (use these!):**\n"
                for url in search_urls[:3]:
                    url_hint += f"- {url}\n"
            
            if scrape_attempts == 0 and tool_call_count <= 2:
                # Phase 1: Just searched, need to scrape
                instruction = (
                    "\n\n=== DEEP RESEARCH WORKFLOW - PHASE 1: SCRAPE SOURCES ===\n"
                    "You've completed initial searches. Now you MUST scrape the most relevant URLs.\n\n"
                    "**YOUR NEXT ACTION:**\n"
                    "Call `scrape_website` on 2-3 URLs from your search results above.\n"
                    "IMPORTANT: Only use URLs that appeared in your search results!"
                    f"{url_hint}\n"
                    "**DO NOT** write a response yet. You need more detailed content first."
                )
            elif scrape_attempts > 0 and successful_scrapes == 0 and failed_scrapes > 0:
                # Phase 1b: Scrapes failed, try different URLs
                instruction = (
                    "\n\n=== DEEP RESEARCH WORKFLOW - SCRAPE ERROR RECOVERY ===\n"
                    "Your previous scrape attempt failed. This is normal - some sites block scraping.\n\n"
                    "**YOUR NEXT ACTION:**\n"
                    "Try scraping DIFFERENT URLs from your search results.\n"
                    "Choose URLs from different domains than the ones that failed."
                    f"{url_hint}\n"
                    "**DO NOT** give up. Try 2-3 more URLs before proceeding."
                )
            elif successful_scrapes > 0 and not has_document:
                # Phase 2: Have successful scrapes, need to create document
                instruction = (
                    "\n\n=== DEEP RESEARCH WORKFLOW - PHASE 2: CREATE RESEARCH DOCUMENT ===\n"
                    f"You've successfully scraped {successful_scrapes} source(s). Now create your document.\n\n"
                    "**YOUR NEXT ACTION:**\n"
                    "1. Call `create_research_document` with a title for your research paper\n"
                    "2. Then call `append_to_document` to add your synthesized findings\n\n"
                    "**DO NOT** respond to the user yet. Create the document first."
                )
            elif has_document and tool_call_count < 8:
                # Phase 3: Document exists, continue writing/editing
                instruction = (
                    "\n\n=== DEEP RESEARCH WORKFLOW - PHASE 3: WRITE & REVIEW ===\n"
                    "Your research document exists. Continue building it.\n\n"
                    "**YOUR NEXT ACTIONS:**\n"
                    "1. Use `append_to_document` to add more sections (introduction, analysis, conclusion)\n"
                    "2. Review what you've written for accuracy\n"
                    "3. If you find issues, use `append_to_document` to add corrections\n\n"
                    "**WHEN COMPLETE:** Once your research paper has:\n"
                    "- Introduction\n"
                    "- Main findings with citations\n"
                    "- Conclusion\n\n"
                    "Then provide a summary response to the user with the document path."
                )
            else:
                # Phase 4: Research complete or max iterations, summarize
                instruction = (
                    "\n\n=== DEEP RESEARCH WORKFLOW - PHASE 4: COMPLETE ===\n"
                    "Your research is complete. Provide a summary to the user.\n\n"
                    "**YOUR RESPONSE SHOULD INCLUDE:**\n"
                    "1. Key findings from your research\n"
                    "2. The path to the research document you created (if any)\n"
                    "3. A brief summary of your sources\n\n"
                    "**DO NOT** call more tools. Respond with your findings."
                )
        elif response_format == "json":
            # Force JSON response even after tools
            instruction = (
                "\n\n=== CRITICAL RESPONSE FORMAT REQUIREMENT ===\n"
                "You have tool results in the conversation above. "
                "Now answer the user's question using that information.\n"
                "YOU MUST respond ONLY with valid JSON in the EXACT format specified in the system prompt above.\n"
                "Do NOT write conversational text. Do NOT explain or narrate. ONLY output the JSON object.\n"
                "Your entire response must be parseable JSON - nothing else."
            )
        elif response_format is not None and response_format != "conversational":
            # Custom format specified
            instruction = (
                f"\n\n=== CRITICAL: USE TOOL RESULTS ===\n"
                f"You have tool results in the conversation above. "
                f"Answer the user's question using that information. "
                f"Respond in {response_format} format."
            )
        else:
            # Check if the last tool was a "task-completing" tool
            # These tools produce output that should be presented to the user,
            # NOT followed by more tool calls
            TASK_COMPLETING_TOOLS = {
                "create_code_file",  # Code was written - present it to user
                "write_file",        # File was written - present result
                "execute_python",    # Code was executed - present output
                "complete_todo_item",  # Workflow item completed
            }
            
            # Get last AI message to check what tool was called
            ai_messages = [m for m in trimmed_messages if hasattr(m, 'tool_calls') and m.tool_calls]
            last_tool_name = None
            if ai_messages:
                last_ai = ai_messages[-1]
                if last_ai.tool_calls:
                    last_tool_name = last_ai.tool_calls[-1].get("name")
            
            # Check if the tool result indicates success
            tool_succeeded = False
            if tool_messages:
                last_tool_content = str(getattr(tool_messages[-1], 'content', ''))
                # Success indicators
                if any(indicator in last_tool_content.lower() for indicator in 
                       ['created', 'successfully', 'written', '✓', 'complete', 'done']):
                    tool_succeeded = True
            
            if last_tool_name in TASK_COMPLETING_TOOLS and tool_succeeded:
                # Task-completing tool succeeded - tell model to respond, not call more tools
                instruction = (
                    "\n\n=== TASK COMPLETED - RESPOND TO USER ===\n"
                    "The requested task has been completed successfully!\n\n"
                    "**YOUR NEXT ACTION:** Respond to the user with a summary.\n"
                    "- Tell them what was accomplished\n"
                    "- Include the file path or result from the tool output\n"
                    "- Keep it brief and friendly\n\n"
                    "**DO NOT:**\n"
                    "- Call more tools (the task is DONE)\n"
                    "- Start a new task without being asked\n"
                    "- Give a generic greeting\n\n"
                    "Example response: 'Done! I created hello_world.py with your function.'"
                )
                self.logger.info(
                    f"[POST-TOOL] Task-completing tool '{last_tool_name}' succeeded - "
                    "instructing model to respond (not call more tools)"
                )
            else:
                # Default behavior - conversational (for both react and json mode)
                instruction = (
                    "\n\n=== CRITICAL: USE TOOL RESULTS ===\n"
                    "Tool results are available in the conversation above.\n"
                    "IMPORTANT: You MUST use these tool results to answer the user's question.\n"
                    "Do NOT ignore the tool results. Do NOT give a generic greeting.\n"
                    "Synthesize the information from the tool results into a helpful, conversational response.\n"
                    "If the tool returned search results, summarize the key information for the user."
                )

        system_prompt += instruction
        self.logger.info(
            f"[POST-TOOL] Full instruction text:\n{instruction}"
        )

        # Log tool results for debugging
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

    def _is_tool_call_json(self, text: str) -> bool:
        """Check if text looks like a JSON tool call definition.
        
        Args:
            text: Text to check
            
        Returns:
            True if text appears to be a tool call JSON
        """
        stripped = text.strip()
        # Check for JSON tool call patterns
        if stripped.startswith('{') and ('"name"' in stripped or '"tool"' in stripped):
            # Looks like start of a tool call JSON
            return True
        if '"arguments"' in stripped or '"query"' in stripped:
            # Contains argument-like content
            return True
        return False

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
        
        # Track thinking state for <think>...</think> (Qwen3) or [THINK]...[/THINK] (Ministral3) blocks
        in_thinking_block = False
        thinking_started = False  # Track if we've already seen an opening tag
        thinking_tag_format = ""  # "angle" or "brackets" - set when opening tag detected
        thinking_content = []
        final_thinking_content = None  # Store completed thinking content for DB persistence
        
        # Track <tool_call> tag buffering - don't stream tool call tags to GUI
        tool_call_tag_buffer = []
        in_tool_call_tag = False
        
        # Track JSON tool call buffering - don't stream tool call JSON to GUI
        json_buffer = []
        in_json_tool_call = False
        json_brace_depth = 0
        
        # Track if we've streamed any content yet (for trimming leading whitespace)
        has_streamed_content = False
        
        has_emitter = hasattr(self, "_signal_emitter") and self._signal_emitter is not None
        # self.logger.debug(f"[THINKING] Starting streaming response generation (has_signal_emitter={has_emitter})")

        try:
            self.logger.info(f"[STREAM] Starting stream from chat_model type: {type(self._chat_model).__name__}")
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
                # self.logger.debug(f"[THINKING] Chunk received: '{text[:50]}...' (in_thinking={in_thinking_block})")
                
                # Detect thinking block boundaries using format-agnostic helpers
                # Supports both <think>...</think> (Qwen3) and [THINK]...[/THINK] (Ministral 3)
                found_open, tag_format, _, after_think = detect_thinking_open_tag(text)
                if found_open and not thinking_started:
                    in_thinking_block = True
                    thinking_started = True
                    thinking_tag_format = tag_format
                    # self.logger.debug(f"[THINKING] Detected {tag_format} opening tag - starting thinking block")
                    # Emit thinking started signal
                    if hasattr(self, "_signal_emitter") and self._signal_emitter:
                        self._signal_emitter.emit_signal(
                            SignalCode.LLM_THINKING_SIGNAL,
                            {"status": "started", "content": ""}
                        )
                    
                    # Check if closing tag is also in this chunk (entire thinking block in one chunk)
                    found_close, before_close, after_close = detect_thinking_close_tag(after_think, tag_format)
                    if found_close:
                        # Both tags in same chunk - extract thinking and remaining content
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
                        # self.logger.debug(f"[THINKING] Complete thinking block in single chunk, content len={len(final_thinking_content)}")
                        
                        if hasattr(self, "_signal_emitter") and self._signal_emitter:
                            self._signal_emitter.emit_signal(
                                SignalCode.LLM_THINKING_SIGNAL,
                                {"status": "completed", "content": final_thinking_content}
                            )
                        thinking_content = []
                        
                        # Stream any content after closing tag to the main callback
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
                        # Only opening tag in this chunk, stream content to thinking
                        thinking_content.append(after_think)
                        if hasattr(self, "_signal_emitter") and self._signal_emitter:
                            self._signal_emitter.emit_signal(
                                SignalCode.LLM_THINKING_SIGNAL,
                                {"status": "streaming", "content": after_think}
                            )
                    continue  # Skip normal processing for this chunk
                
                # If we're in a thinking block, emit thinking content
                if in_thinking_block:
                    # Check for closing tag using the same format as the opening tag
                    found_close, before_close, after_close = detect_thinking_close_tag(text, thinking_tag_format)
                    if found_close:
                        if before_close:
                            thinking_content.append(before_close)
                            if hasattr(self, "_signal_emitter") and self._signal_emitter:
                                self._signal_emitter.emit_signal(
                                    SignalCode.LLM_THINKING_SIGNAL,
                                    {"status": "streaming", "content": before_close}
                                )
                        
                        # Mark thinking as complete
                        in_thinking_block = False
                        # self.logger.debug(f"[THINKING] Detected closing tag - ending thinking block, content len={len(''.join(thinking_content))}")
                        
                        # Save thinking content for DB persistence BEFORE clearing the list
                        final_thinking_content = "".join(thinking_content)
                        
                        if hasattr(self, "_signal_emitter") and self._signal_emitter:
                            self._signal_emitter.emit_signal(
                                SignalCode.LLM_THINKING_SIGNAL,
                                {"status": "completed", "content": final_thinking_content}
                            )
                        thinking_content = []
                        
                        # Stream any content after closing tag to the main callback
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
                
                # Detect <tool_call> tags and buffer them instead of streaming
                # This prevents tool call markup from appearing in the chat UI
                text_to_stream = text
                
                # Check if we're starting a <tool_call> tag
                if not in_tool_call_tag and '<tool_call>' in text:
                    in_tool_call_tag = True
                    # Stream any text before the tag
                    before_tag = text.split('<tool_call>', 1)[0]
                    if before_tag.strip():
                        text_to_stream = before_tag
                    else:
                        text_to_stream = ""
                    # Start buffering from the tag onwards
                    tool_call_tag_buffer.append(text.split('<tool_call>', 1)[1] if '<tool_call>' in text else "")
                    continue
                
                # If we're in a <tool_call> tag, buffer it
                if in_tool_call_tag:
                    if '</tool_call>' in text:
                        # End of tool call tag - buffer content before closing tag
                        before_close = text.split('</tool_call>', 1)[0]
                        tool_call_tag_buffer.append(before_close)
                        in_tool_call_tag = False
                        # Stream any content after </tool_call>
                        after_close = text.split('</tool_call>', 1)[1] if '</tool_call>' in text else ""
                        if after_close.strip():
                            text_to_stream = after_close
                        else:
                            text_to_stream = ""
                        tool_call_tag_buffer = []
                    else:
                        # Still inside the tag, buffer everything
                        tool_call_tag_buffer.append(text)
                        text_to_stream = ""
                    if not text_to_stream:
                        continue
                
                # Detect JSON tool call patterns and buffer them instead of streaming
                # This prevents tool call JSON from appearing in the chat UI
                
                # Check if we're starting a JSON tool call
                if not in_json_tool_call and '{' in text:
                    # Check if this looks like a tool call JSON
                    remaining = text[text.index('{'):]
                    if self._is_tool_call_json(remaining) or ('"name"' in text and '"arguments"' in text):
                        in_json_tool_call = True
                        # Stream any text before the '{'
                        before_json = text[:text.index('{')]
                        if before_json.strip():
                            text_to_stream = before_json
                        else:
                            text_to_stream = ""
                        # Start buffering the JSON part
                        json_buffer.append(text[text.index('{'):])
                        json_brace_depth = text.count('{') - text.count('}')
                
                # If we're in a JSON tool call, buffer it
                if in_json_tool_call and text_to_stream == text:
                    json_buffer.append(text)
                    json_brace_depth += text.count('{') - text.count('}')
                    text_to_stream = ""
                    
                    # Check if JSON is complete
                    if json_brace_depth <= 0:
                        in_json_tool_call = False
                        # Check if there's text after the closing brace
                        buffered = "".join(json_buffer)
                        if '}' in buffered:
                            last_brace = buffered.rfind('}')
                            after_json = buffered[last_brace + 1:]
                            if after_json.strip():
                                text_to_stream = after_json
                        json_buffer = []
                        json_brace_depth = 0
                
                # Stream non-JSON content to GUI immediately
                # Skip whitespace-only content to prevent creating empty assistant messages
                if text_to_stream and self._token_callback:
                    try:
                        # Keep stripping leading whitespace until we find non-blank content
                        # This handles cases where multiple chunks contain only whitespace
                        if not has_streamed_content:
                            text_to_stream = text_to_stream.lstrip()
                            # Only mark as streamed if we have actual content after stripping
                            if text_to_stream:
                                has_streamed_content = True
                        
                        # Only call callback if we have content to stream
                        if text_to_stream:
                            self._token_callback(text_to_stream)
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

        response_message = AIMessage(
            content=complete_content,
            additional_kwargs=additional_kwargs,
            tool_calls=tool_calls or [],
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
