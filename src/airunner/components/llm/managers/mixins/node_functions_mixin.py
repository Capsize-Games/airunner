"""Node functions mixin for WorkflowManager.

Handles LangGraph node implementations (_call_model, _force_response_node, _route_after_model).
These are broken into focused helper methods for maintainability.
"""

import os
import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    BaseMessage,
    trim_messages,
)

from langchain_core.messages import SystemMessage
from airunner.components.llm.config.generation_presets import (
    WorkflowGenerationStage,
    get_workflow_generation_preset,
)
from airunner.components.llm.config.document_tasks import (
    get_document_task_config,
)
from airunner.components.llm.utils.document_query_routing import (
    route_document_query,
)
from airunner.components.llm.utils.thinking_parser import (
    strip_thinking_tags,
    detect_thinking_open_tag,
    detect_thinking_close_tag,
)
from airunner.components.llm.utils.stream_text import combine_stream_chunks
from airunner.components.llm.managers.llm_response import LLMResponse
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

    @dataclass
    class _ConsciousnessCtx:
        conversation_id: Optional[int]
        thread_id: Any
        messages: Optional[List[Any]]

    def _get_consciousness_engine(self):
        """Best-effort loader for the optional consciousness extension."""
        try:
            from airunner_extensions.consciousness import get_engine

            return get_engine()
        except Exception:
            return None

    @staticmethod
    def _is_consciousness_enabled(value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "y", "on"}
        return bool(value)

    def _consciousness_enabled_for_request(self) -> bool:
        try:
            data = getattr(self, "data", None) or {}
            return self._is_consciousness_enabled(data.get("enable_consciousness", None))
        except Exception:
            return True

    def _maybe_consciousness_pre_llm(self, messages: List[Any]) -> None:
        if not self._consciousness_enabled_for_request():
            return
        engine = self._get_consciousness_engine()
        if not engine:
            return
        try:
            ctx = self._ConsciousnessCtx(
                conversation_id=getattr(self, "_conversation_id", None),
                thread_id=getattr(self, "_thread_id", "default"),
                messages=messages,
            )
            engine.on_pre_llm(ctx)
        except Exception:
            # Never break generation.
            return

    def _maybe_consciousness_post_llm(self, ai_message: Any, messages: List[Any]) -> None:
        if not self._consciousness_enabled_for_request():
            return
        engine = self._get_consciousness_engine()
        if not engine:
            return
        try:
            ctx = self._ConsciousnessCtx(
                conversation_id=getattr(self, "_conversation_id", None),
                thread_id=getattr(self, "_thread_id", "default"),
                messages=messages,
            )
            engine.on_post_llm(ai_message, ctx)
        except Exception:
            # Never break generation.
            return

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
        ai_message_with_tools = self._get_last_tool_calling_ai_message(
            state["messages"]
        )

        if not ai_message_with_tools:
            self.logger.error(
                "Force response node called but no AIMessage with tool_calls found"
            )
            return {"messages": []}

        # Get tool information
        tool_name = ai_message_with_tools.tool_calls[0].get("name")
        tool_messages = self._get_current_turn_tool_messages(
            state["messages"]
        )
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
            if self._should_return_tool_direct(tool_name):
                self.logger.info(
                    f"Force response node: returning direct tool result for '{tool_name}'"
                )
                return {
                    "messages": [
                        self._create_direct_tool_response_message(
                            tool_messages, tool_name
                        )
                    ],
                    "workflow_continuation": False,
                }

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

    def _get_last_tool_calling_ai_message(
        self, messages: List[BaseMessage]
    ) -> Optional[AIMessage]:
        """Return the most recent AI message that requested tools."""
        for message in reversed(messages):
            if isinstance(message, AIMessage) and self._has_tool_calls(message):
                return message
        return None

    def _get_current_turn_messages(
        self, messages: List[BaseMessage]
    ) -> List[BaseMessage]:
        """Return messages for the most recent user turn only."""
        for index in range(len(messages) - 1, -1, -1):
            if messages[index].__class__.__name__ == "HumanMessage":
                return messages[index:]
        return messages

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

    def _get_current_turn_tool_messages(
        self, messages: List[BaseMessage]
    ) -> List[Any]:
        """Extract tool results produced during the active user turn."""
        return self._get_tool_messages(self._get_current_turn_messages(messages))

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

    def _get_bound_tool(self, tool_name: str) -> Optional[Any]:
        """Return the currently bound tool object by name."""
        for tool in getattr(self, "_tools", []) or []:
            if getattr(tool, "name", None) == tool_name:
                return tool
        return None

    def _should_return_tool_direct(self, tool_name: str) -> bool:
        """Check whether a bound tool should bypass the post-tool model pass."""
        tool = self._get_bound_tool(tool_name)
        return bool(tool and getattr(tool, "return_direct", False))

    def _create_direct_tool_response_message(
        self, tool_messages: List[Any], tool_name: str
    ) -> AIMessage:
        """Create an assistant message directly from tool output."""
        direct_content = ""
        for tool_message in reversed(tool_messages):
            if getattr(tool_message, "name", None) == tool_name and getattr(
                tool_message, "content", None
            ):
                direct_content = str(tool_message.content).strip()
                break

        if not direct_content and tool_messages:
            direct_content = str(getattr(tool_messages[-1], "content", "")).strip()

        return AIMessage(content=direct_content, tool_calls=[])

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

For a structured workflow, the typical sequence is:
1. start_workflow (DONE - you already did this)
2. transition_phase('planning', 'reason') 
3. add_todo_item('title', 'description')
4. transition_phase('execution', 'reason')
5. start_todo_item('todo_id')
6. use the task tools needed for that TODO
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
            document_intent = self._get_document_query_intent(user_question)
            deterministic_response = (
                self._build_deterministic_document_response(
                    all_tool_content,
                    tool_name,
                    user_question,
                )
            )
            if deterministic_response:
                if self._token_callback:
                    self._token_callback(deterministic_response)
                return AIMessage(
                    content=deterministic_response,
                    additional_kwargs={},
                    tool_calls=[],
                )

            simple_prompt_text = self._build_search_results_prompt(
                all_tool_content,
                tool_name,
                user_question,
            )

            # Convert to message format
            simple_prompt = [HumanMessage(content=simple_prompt_text)]
            internal_generation_kwargs = (
                self._prepare_internal_response_generation_kwargs(
                    generation_kwargs,
                    tool_name=tool_name,
                    user_question=user_question,
                    stage=WorkflowGenerationStage.DOCUMENT_SYNTHESIS,
                )
            )
            thinking_metadata = self._build_internal_stage_debug_metadata(
                internal_generation_kwargs,
                tool_name=tool_name,
                user_question=user_question,
                stage=WorkflowGenerationStage.DOCUMENT_SYNTHESIS,
            )

            # Force the synthesis pass to return visible text instead of
            # reasoning/tool scaffolding.
            response_message = self._stream_internal_response(
                simple_prompt,
                internal_generation_kwargs,
                thinking_metadata=thinking_metadata,
                buffer_visible_output=True,
            )

            if response_message:
                document_tool = self._is_document_result_tool(tool_name)
                reject_structure_only = (
                    document_tool and document_intent == "summary"
                )
                drafted_response = self._recover_forced_response_content(
                    response_message,
                    reject_structure_only=reject_structure_only,
                )
                if self._should_verify_document_response(
                    tool_name,
                    user_question,
                ):
                    verified_message = self._run_document_verification_pass(
                        all_tool_content,
                        tool_name,
                        user_question,
                        drafted_response,
                        generation_kwargs,
                    )
                    if self._should_accept_verified_document_response(
                        verified_message,
                        reject_structure_only=reject_structure_only,
                    ):
                        response_message = verified_message

                self._emit_final_thinking_signal(response_message)
                visible_content = self._recover_forced_response_content(
                    response_message,
                    reject_structure_only=reject_structure_only,
                )
                if self._looks_like_instruction_reflection(visible_content):
                    visible_content = ""
                if reject_structure_only and drafted_response and not visible_content:
                    visible_content = drafted_response
                if document_tool and document_intent == "identity":
                    fallback_identity = (
                        self._build_document_identity_response(
                            all_tool_content
                        )
                    )
                    if fallback_identity and not visible_content:
                        visible_content = fallback_identity
                if document_tool and document_intent == "structure":
                    fallback_structure = (
                        self._build_document_structure_response(
                            all_tool_content
                        )
                    )
                    if fallback_structure and not visible_content:
                        visible_content = fallback_structure
                # Ensure tool_calls is empty
                return AIMessage(
                    content=visible_content,
                    additional_kwargs=getattr(response_message, "additional_kwargs", {}),
                    tool_calls=[],
                )

            return None

        except Exception as e:
            self.logger.error(f"Failed to generate forced response message: {e}")
            return None

    def _prepare_internal_response_generation_kwargs(
        self,
        generation_kwargs: Optional[Dict],
        *,
        tool_name: str,
        user_question: str,
        stage: WorkflowGenerationStage = (
            WorkflowGenerationStage.DOCUMENT_SYNTHESIS
        ),
    ) -> Dict:
        """Return generation kwargs tuned for one internal synthesis pass."""
        prepared = dict(generation_kwargs or {})
        if not self._is_document_result_tool(tool_name):
            return prepared
        if self._get_document_query_intent(user_question) != "summary":
            return prepared

        return get_workflow_generation_preset(stage).apply_to_generation_kwargs(
            prepared
        )

    @staticmethod
    def _collect_generation_debug_settings(
        generation_kwargs: Dict,
    ) -> Dict[str, Any]:
        """Return one compact debug view of resolved generation settings."""
        settings = {}
        for key in (
            "max_new_tokens",
            "max_tokens",
            "temperature",
            "top_p",
            "top_k",
            "num_beams",
            "repetition_penalty",
            "no_repeat_ngram_size",
            "reasoning_effort",
        ):
            value = generation_kwargs.get(key)
            if value is not None:
                settings[key] = value
        return settings

    def _build_internal_stage_debug_metadata(
        self,
        generation_kwargs: Dict,
        *,
        tool_name: str,
        user_question: str,
        stage: WorkflowGenerationStage,
    ) -> Optional[Dict[str, Any]]:
        """Return one read-only metadata payload for internal LLM stages."""
        if not self._is_document_result_tool(tool_name):
            return None
        intent = self._get_document_query_intent(user_question)
        metadata = {
            "kind": "llm_stage_settings",
            "title": stage.value.replace("_", " ").title(),
            "stage": stage.value,
            "intent": intent,
            "preset_applied": intent == "summary",
            "settings": self._collect_generation_debug_settings(
                generation_kwargs
            ),
        }
        if metadata["preset_applied"]:
            metadata["preset_id"] = stage.value
        return metadata

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
            deterministic_response = (
                self._build_deterministic_document_response(
                    all_tool_content,
                    tool_name,
                    user_question,
                )
            )
            if deterministic_response:
                if self._token_callback:
                    self._token_callback(deterministic_response)
                return deterministic_response

            simple_prompt_text = self._build_search_results_prompt(
                all_tool_content,
                tool_name,
                user_question,
            )

            # Convert to message format
            simple_prompt = [HumanMessage(content=simple_prompt_text)]
            internal_generation_kwargs = (
                self._prepare_internal_response_generation_kwargs(
                    generation_kwargs,
                    tool_name=tool_name,
                    user_question=user_question,
                    stage=WorkflowGenerationStage.DOCUMENT_SYNTHESIS,
                )
            )
            thinking_metadata = self._build_internal_stage_debug_metadata(
                internal_generation_kwargs,
                tool_name=tool_name,
                user_question=user_question,
                stage=WorkflowGenerationStage.DOCUMENT_SYNTHESIS,
            )

            # Stream a plain answer without tool bindings or hidden thinking.
            response_message = self._stream_internal_response(
                simple_prompt,
                internal_generation_kwargs,
                thinking_metadata=thinking_metadata,
                buffer_visible_output=True,
            )

            # Extract content from the response message
            document_intent = self._get_document_query_intent(user_question)
            document_tool = self._is_document_result_tool(tool_name)
            reject_structure_only = (
                document_tool and document_intent == "summary"
            )
            drafted_response = self._recover_forced_response_content(
                response_message,
                reject_structure_only=reject_structure_only,
            )
            if self._should_verify_document_response(tool_name, user_question):
                verified_message = self._run_document_verification_pass(
                    all_tool_content,
                    tool_name,
                    user_question,
                    drafted_response,
                    generation_kwargs,
                )
                if self._should_accept_verified_document_response(
                    verified_message,
                    reject_structure_only=reject_structure_only,
                ):
                    response_message = verified_message

            self._emit_final_thinking_signal(response_message)
            response_content = self._recover_forced_response_content(
                response_message,
                reject_structure_only=reject_structure_only,
            )
            if self._looks_like_instruction_reflection(response_content):
                response_content = ""
            if reject_structure_only and drafted_response and not response_content:
                response_content = drafted_response
            if document_tool and document_intent == "identity":
                fallback_identity = self._build_document_identity_response(
                    all_tool_content
                )
                if fallback_identity and not response_content:
                    response_content = fallback_identity
            if document_tool and document_intent == "structure":
                fallback_structure = self._build_document_structure_response(
                    all_tool_content
                )
                if fallback_structure and not response_content:
                    response_content = fallback_structure

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

    def _should_verify_document_response(
        self,
        tool_name: str,
        user_question: str,
    ) -> bool:
        """Return whether a synthesized document answer needs verification."""
        if not self._is_document_result_tool(tool_name):
            return False
        return self._get_document_query_intent(user_question) not in {
            "identity",
            "structure",
        }

    def _run_document_verification_pass(
        self,
        all_tool_content: str,
        tool_name: str,
        user_question: str,
        drafted_response: str,
        generation_kwargs: Optional[Dict],
    ) -> Optional[AIMessage]:
        """Run one bounded verification pass for a document answer."""
        verification_prompt_text = (
            self._build_search_results_verification_prompt(
                all_tool_content,
                tool_name,
                user_question,
                drafted_response,
            )
        )
        self.logger.info(
            "Running verification pass for synthesized document response"
        )
        verification_generation_kwargs = (
            self._prepare_internal_response_generation_kwargs(
                generation_kwargs,
                tool_name=tool_name,
                user_question=user_question,
                stage=WorkflowGenerationStage.DOCUMENT_VERIFICATION,
            )
        )
        thinking_metadata = self._build_internal_stage_debug_metadata(
            verification_generation_kwargs,
            tool_name=tool_name,
            user_question=user_question,
            stage=WorkflowGenerationStage.DOCUMENT_VERIFICATION,
        )
        return self._stream_internal_response(
            [HumanMessage(content=verification_prompt_text)],
            verification_generation_kwargs,
            thinking_metadata=thinking_metadata,
            buffer_visible_output=True,
        )

    def _should_accept_verified_document_response(
        self,
        verified_message: Optional[AIMessage],
        *,
        reject_structure_only: bool,
    ) -> bool:
        """Return whether the verifier produced one user-facing answer."""
        if verified_message is None:
            return False
        verified_content = self._recover_forced_response_content(
            verified_message,
            reject_structure_only=reject_structure_only,
        )
        return bool(verified_content.strip())

    def _build_search_results_prompt(
        self,
        all_tool_content: str,
        tool_name: str,
        user_question: str = "",
    ) -> str:
        """Build one no-tool synthesis prompt for search results."""
        question_context = (
            f"User's question: {user_question}\n\n"
            if user_question
            else ""
        )
        rag_guidance = ""
        response_style = "Avoid repetition and be concise."
        prompt_results = all_tool_content
        prompt_results_label = "Search results"
        document_tool = self._is_document_result_tool(tool_name)
        document_intent = self._get_document_query_intent(user_question)
        if document_tool:
            if document_intent == "identity":
                rag_guidance = (
                    "If the user is asking what the document is, answer "
                    "directly and briefly by naming the document and, "
                    "when available, its title, author, or file type. "
                    "Do not mention search results or instructions.\n\n"
                )
            elif document_intent == "structure":
                rag_guidance = (
                    "If the user is asking for chapters, sections, or the "
                    "document structure, answer with the section names only. "
                    "Do not restate the document title, author, file type, "
                    "stored path, or any broader summary unless the user "
                    "explicitly asks for them.\n\n"
                )
            elif document_intent == "summary":
                prompt_results = self._build_document_summary_prompt_results(
                    all_tool_content
                )
                if prompt_results != all_tool_content:
                    prompt_results_label = "Evidence excerpts"
                summary_guidance = (
                    "If the user is asking for a summary of the document, "
                    "synthesize the evidence below into a substantive "
                    "overview. Explain the central worldview, argument, or "
                    "subject first, then cover the most important supporting "
                    "ideas, claims, practices, or concrete details that "
                    "appear in the excerpts. Merge overlapping evidence into "
                    "one coherent answer instead of repeating it. Prefer "
                    "specific details over vague labels. Keep isolated "
                    "front-matter anecdotes or biographical trivia secondary "
                    "unless the same idea recurs elsewhere in the evidence. "
                    "Stay anchored to what the excerpts explicitly say. Do "
                    "not infer genre, series, trilogy, collection, or "
                    "bibliographic relationships unless the evidence states "
                    "them directly. Treat uncanny, dreamlike, or eerie "
                    "atmosphere as mood unless the excerpts explicitly "
                    "confirm literal supernatural events. Do "
                    "not infer divine, supernatural, or hidden-authority "
                    "beliefs unless the evidence states them directly. "
                    "The evidence below already comes from the currently "
                    "loaded document the user is asking about. Do not ask "
                    "the user to identify which book, story, document, "
                    "title, or author they mean when that evidence is "
                    "already present. "
                    "Write 7 to 10 sentences in 2 to 4 short paragraphs. Do "
                    "not repeat the document title, author, or structure "
                    "unless the user asked for them. Do not answer with "
                    "bare category labels such as 'Setting, Premise, "
                    "Conflict, Characters.' Write full sentences only. Do "
                    "not mention file "
                    "names, stored paths, excerpt numbers, search results, "
                    "or internal instructions. Do not use bullet points, "
                    "numbered lists, or excerpt inventories.\n\n"
                )
                if self._is_document_about_question(user_question):
                    rag_guidance = (
                        "If the user is asking what the book, story, or "
                        "document is about, lead with the premise, setting, "
                        "central conflict, and the most important character "
                        "relationships first. Treat isolated later scenes, "
                        "one-off travel stops, and stray dialogue fragments "
                        "as secondary unless the evidence clearly shows they "
                        "define the work as a whole. Prefer the inciting "
                        "incident, victim, investigator, and case setup over "
                        "static character descriptions or travel anecdotes. If the excerpts describe "
                        "a corpse, a supposedly dead figure, studio illusions, "
                        "or eerie atmosphere, prefer a grounded mystery or noir "
                        "framing unless the evidence explicitly confirms literal "
                        "supernatural events. Do not describe literal "
                        "resurrection, a supernatural world, or magical cities "
                        "unless the evidence states that directly. Do not "
                        "attribute criticism, accusations, or quoted dialogue "
                        "to the apparently dead figure unless the excerpt "
                        "explicitly identifies that speaker. Treat later "
                        "arguments and recollections as secondary to the "
                        "inciting mystery.\n\n"
                        + summary_guidance
                    )
                    response_style = (
                        "Lead with premise, setting, and central conflict. "
                        "Keep stray scene details secondary and favor a "
                        "grounded mystery framing unless the excerpts say otherwise. "
                        "Prioritize the case setup over static character profiles."
                    )
                else:
                    rag_guidance = summary_guidance
                    response_style = (
                        "Start with the central themes, not opening trivia. "
                        "Synthesize across excerpts and avoid repetition."
                    )
            elif document_intent == "compare":
                rag_guidance = (
                    "If the user is asking for a comparison, compare only "
                    "the people, sections, claims, or results that the "
                    "document evidence actually supports. Separate the most "
                    "important similarities from the most important "
                    "differences when helpful. If the evidence only covers "
                    "one side of the requested comparison, say so briefly "
                    "instead of filling gaps.\n\n"
                )
                response_style = (
                    "Keep the comparison structured, direct, and grounded in "
                    "the excerpts."
                )
            elif document_intent == "extract":
                rag_guidance = (
                    "If the user is asking you to extract or pull out "
                    "specific information, return only the supported names, "
                    "dates, values, measurements, labels, or facts that the "
                    "document states. Preserve exact wording for concrete "
                    "values when possible. If a requested field is missing, "
                    "say it is not stated instead of guessing.\n\n"
                )
                response_style = (
                    "Use labeled lines or a short list when that makes the "
                    "extracted information easier to read."
                )
            elif document_intent == "list":
                rag_guidance = (
                    "If the user is asking for a list or enumeration, "
                    "extract only the items the document supports. "
                    "Deduplicate overlapping items, keep them concise, and "
                    "preserve exact wording for names, dates, headings, or "
                    "values when useful.\n\n"
                )
                response_style = (
                    "Prefer a compact, readable list if that best matches the "
                    "user's request."
                )
            elif document_intent == "transform":
                rag_guidance = (
                    "If the user is asking you to organize or reformat "
                    "document information, follow the requested structure as "
                    "closely as the evidence allows. Keep the answer factual, "
                    "clear, and readable. If the requested layout is more "
                    "specific than the evidence supports, provide the closest "
                    "clear structure without inventing missing data.\n\n"
                )
                response_style = (
                    "Follow the requested structure while keeping every field "
                    "grounded in the excerpts."
                )
            else:
                rag_guidance = (
                    "Use document identity fields only when they help "
                    "answer the user's question. Do not repeat the document "
                    "title, author, file type, stored path, or document "
                    "structure unless they are needed for the answer.\n\n"
                )

        prompt_intro = (
            "You are answering a question about a currently loaded "
            "document using document evidence. Respond naturally and "
            "conversationally.\n\n"
            if document_tool
            else "You are answering a question based on search results. "
            "Respond naturally and conversationally.\n\n"
        )
        response_instruction = (
            "Based on the document evidence above, provide a clear, "
            "conversational answer to the user's question about that "
            "document. Use ONLY the information from the document "
            "evidence. The excerpts already belong to the loaded document "
            "the user is asking about, so do not ask which book, story, "
            "or document they mean unless no document evidence is "
            "present. Do not call any tools, do not use JSON, and do not "
            "prefix the reply with labels like Draft:, Answer:, or "
            "Response:. Just write a natural response."
            if document_tool
            else "Based on the search results above, provide a clear, "
            "conversational answer to the user's question. Use ONLY the "
            "information from the search results. Do not call any tools, "
            "do not use JSON, and do not prefix the reply with labels "
            "like Draft:, Answer:, or Response:. Just write a natural "
            "response."
        )

        return (
            f"{prompt_intro}"
            f"{question_context}"
            f"{rag_guidance}"
            f"{prompt_results_label}:\n"
            f"{prompt_results}\n\n"
            f"{response_instruction} {response_style}"
        )

    def _build_search_results_verification_prompt(
        self,
        all_tool_content: str,
        tool_name: str,
        user_question: str,
        drafted_response: str,
    ) -> str:
        """Build a verification prompt for the final document answer."""
        prompt_results = all_tool_content
        prompt_results_label = "Search results"
        document_intent = self._get_document_query_intent(user_question)
        if (
            self._is_document_result_tool(tool_name)
            and document_intent == "summary"
        ):
            prompt_results = self._build_document_summary_prompt_results(
                all_tool_content
            )
            if prompt_results != all_tool_content:
                prompt_results_label = "Evidence excerpts"

        draft_block = drafted_response.strip()
        if draft_block:
            draft_instruction = (
                "Draft answer to verify:\n"
                f"{draft_block}\n\n"
            )
        else:
            draft_instruction = (
                "Draft answer to verify:\n"
                "The initial draft was empty or unusable. Rebuild the final "
                "answer directly from the evidence below.\n\n"
            )

        response_style = (
            "Write 7 to 10 sentences in 2 to 4 short paragraphs."
            if document_intent == "summary"
            else "Return the extracted information in a clear structure."
            if document_intent == "extract"
            else "Return a clear, readable list when the user asked for one."
            if document_intent == "list"
            else "Return the requested structure as clearly as the evidence allows."
            if document_intent == "transform"
            else "Answer directly in one or two concise paragraphs."
        )
        verification_focus = (
            "Lead with the premise, setting, central conflict, and major "
            "relationships that the excerpts support. Prefer recurring core "
            "details over isolated late-scene events."
            if document_intent == "summary"
            else "Keep exact supported values and remove guessed or merged fields."
            if document_intent == "extract"
            else "Keep only supported items, remove duplicates, and do not pad the list with inferences."
            if document_intent == "list"
            else "Compare only supported similarities and differences, and remove unsupported contrasts."
            if document_intent == "compare"
            else "Follow the requested structure, but drop fields the evidence does not support."
            if document_intent == "transform"
            else "Prefer the clearest directly supported claims and remove "
            "anything the evidence does not clearly support."
        )
        clarification_guidance = (
            "The evidence below already belongs to the currently loaded "
            "document the user is asking about. Do not respond with a "
            "clarification request about which book, story, or document "
            "they mean, and do not ask for the title or author, when that "
            "document evidence is already present.\n"
            if self._is_document_result_tool(tool_name)
            else ""
        )

        return (
            "You are verifying and finalizing a document-grounded answer.\n\n"
            f"User question: {user_question}\n\n"
            f"{draft_instruction}"
            f"{prompt_results_label}:\n{prompt_results}\n\n"
            f"{clarification_guidance}"
            "Check the draft against the evidence and keep only supported "
            "claims. Rewrite or remove unsupported details, instruction "
            "leakage, or stray scene fragments. If the draft is weak, ignore "
            "it and answer directly from the evidence. If the evidence is "
            "incomplete, say so briefly instead of guessing.\n"
            "Do not answer with claim-by-claim verdicts such as Supported, "
            "Not supported, or Partially supported.\n"
            "Do not answer with bare category labels such as 'Setting, "
            "Premise, Conflict, Characters.' Write complete sentences only.\n"
            f"{verification_focus}\n"
            f"{response_style}\n"
            "Do not mention search results, verification, instructions, file "
            "names, stored paths, excerpt numbers, labels like Draft:, "
            "Verified:, Answer:, or Response:, or any internal reasoning "
            "steps. Return only the final user-facing answer."
        )

    @staticmethod
    def _extract_rag_excerpt_bodies(all_tool_content: str) -> list[str]:
        """Return cleaned excerpt bodies from one formatted RAG result."""
        excerpt_pattern = re.compile(
            r"\[Excerpt \d+ from [^\]]+\]\n(.*?)(?=\n\n\[Excerpt \d+ from [^\]]+\]\n|\Z)",
            flags=re.DOTALL,
        )
        excerpts: list[str] = []
        for match in excerpt_pattern.finditer(str(all_tool_content or "")):
            excerpt = " ".join(match.group(1).split())
            if excerpt and excerpt not in excerpts:
                excerpts.append(excerpt)
        return excerpts

    @staticmethod
    def _extract_primary_document_label(all_tool_content: str) -> str:
        """Return the first matched-document label when available."""
        for line in str(all_tool_content or "").splitlines():
            stripped = line.strip()
            if stripped.startswith("Document 1: "):
                return stripped.removeprefix("Document 1: ").strip()
        return ""

    def _build_document_summary_prompt_results(
        self,
        all_tool_content: str,
    ) -> str:
        """Return excerpt-focused synthesis input for document summaries."""
        excerpts = self._extract_rag_excerpt_bodies(all_tool_content)
        document_label = self._extract_primary_document_label(all_tool_content)
        sections: list[str] = []
        if document_label:
            sections.append(f"Current document: {document_label}")
        if not excerpts:
            if sections:
                sections.append(all_tool_content)
                return "\n\n".join(sections)
            return all_tool_content
        sections.extend(excerpts)
        return "\n\n".join(sections)

    def _build_deterministic_document_response(
        self,
        all_tool_content: str,
        tool_name: str,
        user_question: str,
    ) -> str:
        """Return one direct document answer when synthesis is unnecessary."""
        if not self._is_document_result_tool(tool_name):
            return ""

        if self._get_document_answer_mode() not in (None, "deterministic"):
            return ""

        document_intent = self._get_document_query_intent(user_question)
        if document_intent == "identity":
            return self._build_document_identity_response(all_tool_content)
        if document_intent == "structure":
            return self._build_document_structure_response(all_tool_content)
        return ""

    @staticmethod
    def _is_document_result_tool(tool_name: str) -> bool:
        """Return whether one tool is part of the document QA pipeline."""
        return tool_name in {"inspect_loaded_documents", "rag_search"}

    def _should_force_document_tool_response(self, tool_name: str) -> bool:
        """Return whether one document tool should bypass replanning."""
        if tool_name == "inspect_loaded_documents":
            return True
        if self._get_document_answer_mode() == "synthesized":
            return False
        llm_request = getattr(self, "llm_request", None)
        primary_tool = getattr(llm_request, "document_primary_tool", None)
        if isinstance(primary_tool, str) and primary_tool:
            return tool_name == primary_tool
        route = getattr(self, "_current_document_query_route", None)
        return tool_name == "rag_search" and route is not None

    def _should_disable_tools_for_followup(
        self,
        messages: List[BaseMessage],
    ) -> bool:
        """Return whether the next model turn should answer without tools."""
        if self._get_document_answer_mode() != "synthesized":
            return False
        current_turn_messages = self._get_current_turn_messages(messages)
        last_ai_msg = self._get_last_tool_calling_ai_message(
            current_turn_messages
        )
        if not last_ai_msg or not getattr(last_ai_msg, "tool_calls", None):
            return False
        return any(
            self._is_document_result_tool(
                str(tool_call.get("name") or "")
            )
            for tool_call in last_ai_msg.tool_calls
        )

    def _get_document_query_intent(self, user_question: str) -> str | None:
        """Return the request-scoped document intent when available."""
        llm_request = getattr(self, "llm_request", None)
        intent = getattr(llm_request, "document_query_intent", None)
        if isinstance(intent, str) and intent:
            return intent
        route = getattr(self, "_current_document_query_route", None)
        intent = getattr(route, "intent", None)
        if isinstance(intent, str) and intent:
            return intent
        routed = route_document_query(
            user_question,
            assume_document_mode=True,
        )
        if routed is not None:
            return routed.intent
        if self._is_document_about_question(user_question):
            return "summary"
        if self._is_document_structure_question(user_question):
            return "structure"
        if self._is_document_summary_question(user_question):
            return "summary"
        if self._is_document_identity_question(user_question):
            return "identity"
        return None

    def _get_document_answer_mode(self) -> str | None:
        """Return the request-scoped document answer mode when available."""
        llm_request = getattr(self, "llm_request", None)
        mode = getattr(llm_request, "document_answer_mode", None)
        if isinstance(mode, str) and mode:
            return mode
        route = getattr(self, "_current_document_query_route", None)
        mode = getattr(route, "answer_mode", None)
        if isinstance(mode, str) and mode:
            return mode
        return None

    @staticmethod
    def _is_document_identity_question(user_question: str) -> bool:
        """Return whether the user is asking to identify a document."""
        normalized = " ".join(str(user_question or "").lower().split())
        if not normalized:
            return False

        identity_phrases = (
            "what is this document",
            "what document is this",
            "tell me what this document is",
            "what is this file",
            "what file is this",
            "which document is this",
            "which file is this",
            "identify this document",
            "identify the document",
            "identify this file",
        )
        if any(phrase in normalized for phrase in identity_phrases):
            return True

        asks_identity = any(
            phrase in normalized
            for phrase in ("what is this", "which is this", "identify")
        )
        mentions_document = "document" in normalized or "file" in normalized
        return asks_identity and mentions_document

    @staticmethod
    def _is_document_structure_question(user_question: str) -> bool:
        """Return whether the user is asking for document structure."""
        normalized = " ".join(str(user_question or "").lower().split())
        if not normalized:
            return False

        structure_phrases = (
            "table of contents",
            "what chapters are",
            "what are the chapters",
            "chapter titles",
            "what sections are",
            "list the sections",
            "document structure",
        )
        return any(phrase in normalized for phrase in structure_phrases)

    @staticmethod
    def _is_document_summary_question(user_question: str) -> bool:
        """Return whether the user is asking for a document summary."""
        normalized = " ".join(str(user_question or "").lower().split())
        if not normalized:
            return False

        summary_phrases = (
            "summarize this document",
            "summarize the document",
            "summary of this document",
            "summary of the document",
            "give me a summary",
            "summarize it",
        )
        return any(phrase in normalized for phrase in summary_phrases)

    @staticmethod
    def _is_document_about_question(user_question: str) -> bool:
        """Return whether the user is asking what a document/book is about."""
        normalized = " ".join(str(user_question or "").lower().split())
        if not normalized:
            return False

        patterns = (
            r"\bwhat(?:'s| is)\s+(?:this|the)\s+(?:book|novel|story|document|file)\s+about\b",
            r"\bwhat\s+is\s+the\s+(?:book|novel|story|document|file)\s+about\b",
            r"\btell\s+me\s+about\s+(?:this|the)\s+(?:book|novel|story|document|file)\b",
        )
        return any(re.search(pattern, normalized) for pattern in patterns)

    @staticmethod
    def _build_document_identity_response(all_tool_content: str) -> str:
        """Return one direct document identity answer from tool results."""
        label = title = author = file_type = stored_path = ""
        for line in all_tool_content.splitlines():
            stripped = line.strip()
            if stripped.startswith("Document 1: ") and not label:
                label = stripped.removeprefix("Document 1: ").strip()
            elif stripped.startswith("Inferred title from filename: "):
                title = stripped.removeprefix(
                    "Inferred title from filename: "
                ).strip()
            elif stripped.startswith("Inferred author from filename: "):
                author = stripped.removeprefix(
                    "Inferred author from filename: "
                ).strip()
            elif stripped.startswith("File type: "):
                file_type = stripped.removeprefix("File type: ").strip()
            elif stripped.startswith("Stored path: "):
                stored_path = stripped.removeprefix("Stored path: ").strip()

        type_label = file_type.lstrip(".").upper()
        if title and author:
            descriptor = f"a {type_label} document" if type_label else "a document"
            return f"This document is {descriptor} titled '{title}' by {author}."
        if title:
            descriptor = f"a {type_label} document" if type_label else "a document"
            return f"This document is {descriptor} titled '{title}'."
        if label:
            descriptor = f"the {type_label} file" if type_label else "the file"
            return f"This document is {descriptor} '{label}'."
        if stored_path:
            return f"This document is stored at '{stored_path}'."
        return ""

    @staticmethod
    def _build_document_structure_response(all_tool_content: str) -> str:
        """Return one direct structure answer from tool results."""
        headings: list[str] = []
        capture_structure = False

        for line in str(all_tool_content or "").splitlines():
            stripped = line.strip()
            if stripped == "Document structure:":
                capture_structure = True
                continue
            if not capture_structure or not stripped:
                continue
            if stripped.startswith("--- Tool Result"):
                break

            match = re.match(r"^\d+\.\s+(.+)$", stripped)
            if not match:
                if headings:
                    break
                continue

            headings.append(match.group(1).strip())

        return "\n".join(headings)

    @staticmethod
    def _strip_forced_response_label(text: str) -> str:
        """Remove one synthetic response label from visible text."""
        cleaned = str(text or "").strip()
        if not cleaned:
            return ""

        patterns = (
            r"^(?:\*\*)?draft(?:\*\*)?\s*:\s*(.+)$",
            r"^(?:\*\*)?answer(?:\*\*)?\s*:\s*(.+)$",
            r"^(?:\*\*)?response(?:\*\*)?\s*:\s*(.+)$",
            r"^(?:\*\*)?final answer(?:\*\*)?\s*:\s*(.+)$",
            r"^(?:\*\*)?final response(?:\*\*)?\s*:\s*(.+)$",
        )
        for pattern in patterns:
            match = re.match(
                pattern,
                cleaned,
                flags=re.IGNORECASE | re.DOTALL,
            )
            if match:
                return match.group(1).strip()

        return cleaned

    @staticmethod
    def _looks_like_instruction_reflection(text: str) -> bool:
        """Return True for meta self-corrections, not user-facing answers."""
        lowered = " ".join(str(text or "").lower().split())
        if not lowered:
            return False
        markers = (
            "actually, rereading",
            "rereading:",
            "looking at the instruction",
            "looking at the instructions",
            "do not mention search results or instructions",
            "i should ensure",
            "i should just",
            "strict adherence",
            "this is a specific constraint",
            "respond naturally implies",
            "let's aim for",
            "don't add fluff",
            "just state the facts",
            "this looks like an instruction or a note rather than a full answer",
            "treat it as the starting point",
            "to be verified against search results",
        )
        if any(marker in lowered for marker in markers):
            return True
        return (
            "search results" in lowered
            and any(
                marker in lowered
                for marker in ("verify", "verified", "instruction")
            )
        )

    @staticmethod
    def _looks_like_summary_prompt_echo(text: str) -> bool:
        """Return True when visible text is just our summary guidance echoed back."""
        lowered = " ".join(str(text or "").lower().split())
        if not lowered:
            return False

        markers = (
            "explain the central worldview",
            "explain the central argument",
            "explain the central subject",
            "cover supporting ideas",
            "cover the most important supporting ideas",
            "merge overlapping evidence",
            "prefer specific details",
            "keep isolated front-matter anecdotes",
            "stay anchored to what the excerpts explicitly say",
        )
        return sum(marker in lowered for marker in markers) >= 2

    @staticmethod
    def _looks_like_search_result_preface_response(text: str) -> bool:
        """Return True for search-engine style summaries and offers."""
        lowered = " ".join(str(text or "").lower().split())
        if not lowered:
            return False
        if lowered.startswith("based on the search results"):
            return True
        if lowered.startswith("from the search results"):
            return True
        return any(
            marker in lowered
            for marker in (
                "would you like me to search",
                "i can help you find more information",
                "i can help you find more details",
            )
        )

    @staticmethod
    def _looks_like_summary_direction_response(text: str) -> bool:
        """Return True for imperative summary directions, not answers."""
        lowered = " ".join(str(text or "").lower().split())
        if not lowered:
            return False

        directive_prefixes = (
            "focus on ",
            "focus the summary on ",
            "emphasize ",
            "highlight ",
            "prioritize ",
            "stick to ",
            "lead with ",
        )
        if not lowered.startswith(directive_prefixes):
            return False

        directive_markers = (
            "aspect",
            "aspects",
            "character",
            "characters",
            "clue",
            "clues",
            "conversation",
            "detail",
            "details",
            "murder mystery",
            "premise",
            "setting",
            "snapshot",
            "theme",
        )
        return any(marker in lowered for marker in directive_markers)

    @staticmethod
    def _looks_like_document_summary_clarification_response(text: str) -> bool:
        """Return True for clarification requests replacing a summary."""
        lowered = " ".join(str(text or "").lower().split())
        if not lowered:
            return False

        markers = (
            "which specific book you're referring to",
            "which specific book you are referring to",
            "could you clarify the title or author",
            "which book you're asking about",
            "which book you are asking about",
            "search results only provide a short excerpt",
            "give you a more accurate and detailed summary",
        )
        if any(marker in lowered for marker in markers):
            return True

        return (
            "clarify" in lowered
            and any(
                marker in lowered
                for marker in ("book", "document", "title", "author")
            )
        )

    @staticmethod
    def _looks_like_summary_format_description_response(text: str) -> bool:
        """Return True for meta descriptions of a summary format."""
        lowered = " ".join(str(text or "").lower().split())
        if not lowered:
            return False

        if not lowered.startswith((
            "a bulleted list of ",
            "a bullet list of ",
            "a brief bulleted list of ",
            "a concise bulleted list of ",
            "a list of ",
        )):
            return False

        excerpt_markers = (
            "snippet",
            "excerpt",
            "text",
            "document",
            "key elements",
            "key details",
        )
        label_markers = (
            "setting",
            "topic",
            "characters",
            "action",
            "context",
            "tone",
            "premise",
            "conflict",
            "themes",
        )
        return (
            any(marker in lowered for marker in excerpt_markers)
            and sum(marker in lowered for marker in label_markers) >= 3
        )

    def _emit_final_thinking_signal(
        self,
        response_message: Optional[AIMessage],
    ) -> None:
        """Ensure the live thinking widget receives one final completion."""
        emitter = getattr(self, "_signal_emitter", None)
        request_id = getattr(self, "_current_request_id", None)
        if emitter is None or not request_id or response_message is None:
            return

        additional_kwargs = (
            getattr(response_message, "additional_kwargs", {}) or {}
        )
        thinking_content = (
            additional_kwargs.get("thinking_content")
            or additional_kwargs.get("reasoning_content")
            or ""
        )
        thinking_metadata = additional_kwargs.get("thinking_metadata")
        emitter.emit_signal(
            SignalCode.LLM_THINKING_SIGNAL,
            {
                "status": "completed",
                "content": str(thinking_content),
                "request_id": request_id,
                "metadata": thinking_metadata,
            },
        )

    def _recover_forced_response_content(
        self,
        response_message: Optional[AIMessage],
        *,
        reject_structure_only: bool = False,
    ) -> str:
        """Recover a visible answer from a reasoning-only internal pass."""
        if response_message is None:
            return ""

        rejected_visible = ""
        visible_content = str(getattr(response_message, "content", "") or "")
        if visible_content.strip():
            cleaned_visible = self._strip_forced_response_label(
                visible_content
            )
            if not self._looks_like_instruction_reflection(
                cleaned_visible
            ) and not self._looks_like_reasoning_header(
                cleaned_visible
                ) and not self._looks_like_verification_verdict_response(
                    cleaned_visible
            ) and not self._looks_like_summary_prompt_echo(
                cleaned_visible
            ) and not self._looks_like_search_result_preface_response(
                cleaned_visible
            ) and not self._looks_like_summary_direction_response(
                cleaned_visible
            ) and not self._looks_like_document_summary_clarification_response(
                cleaned_visible
            ) and not self._looks_like_summary_format_description_response(
                cleaned_visible
            ) and not self._looks_like_malformed_forced_response_fragment(
                cleaned_visible
            ) and not (
                reject_structure_only
                and self._looks_like_summary_scaffolding_response(
                    cleaned_visible
                )
            ):
                return cleaned_visible
            rejected_visible = cleaned_visible

        additional_kwargs = (
            getattr(response_message, "additional_kwargs", {}) or {}
        )
        thinking_content = (
            additional_kwargs.get("thinking_content")
            or additional_kwargs.get("reasoning_content")
            or ""
        )
        cleaned_thinking = strip_thinking_tags(str(thinking_content)).strip()
        if not cleaned_thinking:
            return ""

        drafted_response = self._extract_drafted_response_from_thinking(
            cleaned_thinking
        )
        if drafted_response and not (
            reject_structure_only
            and self._looks_like_summary_scaffolding_response(
                drafted_response
            )
        ):
            self.logger.info(
                "Recovered drafted forced response from reasoning-only output"
            )
            return drafted_response

        if reject_structure_only:
            normalized_reasoning_summary = (
                self._normalize_numbered_summary_response(cleaned_thinking)
            )
            if normalized_reasoning_summary:
                self.logger.info(
                    "Recovered summary prose from numbered reasoning output"
                )
                return normalized_reasoning_summary

        paragraphs = [
            paragraph.strip()
            for paragraph in re.split(r"\n\s*\n", cleaned_thinking)
            if paragraph.strip()
        ]
        for paragraph in paragraphs:
            candidate = self._clean_reasoning_candidate(paragraph)
            if reject_structure_only and (
                self._looks_like_summary_scaffolding_response(candidate)
            ):
                continue
            if candidate:
                self.logger.info(
                    "Recovered visible forced response from reasoning-only output"
                )
                return candidate

        if reject_structure_only and rejected_visible:
            normalized_inventory = self._normalize_inventory_summary_response(
                rejected_visible
            )
            if normalized_inventory:
                self.logger.info(
                    "Flattened list-style summary into visible prose"
                )
                return normalized_inventory

        return ""

    @staticmethod
    def _looks_like_malformed_forced_response_fragment(text: str) -> bool:
        """Return True for tiny prompt-tail fragments, not user answers."""
        normalized = " ".join(str(text or "").split())
        if not normalized:
            return False

        lowered = normalized.lower()
        if any(
            marker in lowered for marker in ("draft:", "answer:", "response:")
        ):
            if len(normalized) <= 80:
                return True
            if normalized[:1] in {'"', "'", ",", ".", ")"}:
                return True

        alpha_chars = sum(1 for char in normalized if char.isalpha())
        if len(normalized) <= 24 and alpha_chars < 8:
            if any(char in normalized for char in ('"', "'", "(", ")", ",")):
                return True

        return False

    def _extract_drafted_response_from_thinking(
        self,
        cleaned_thinking: str,
    ) -> str:
        """Extract quoted draft sentences from structured reasoning output."""
        section_headings = [
            "Final Polish",
            "Refine the Response",
            "Refining for Conciseness and Flow",
            "Draft the Response",
            "Drafting the Response",
        ]
        for heading in section_headings:
            section = self._extract_reasoning_section(
                cleaned_thinking,
                heading,
            )
            if not section:
                continue

            preferred_quote = self._extract_preferred_quote_from_section(
                section
            )
            if preferred_quote:
                return preferred_quote

            quotes = self._extract_quoted_response_lines(section)
            if quotes:
                return " ".join(quotes)

            draft_line = self._extract_labelled_draft_line(section)
            if draft_line:
                return draft_line

        labelled_response = self._extract_labelled_reasoning_response(
            cleaned_thinking
        )
        if labelled_response:
            return labelled_response

        numbered_draft = self._extract_numbered_draft_sentences(
            cleaned_thinking
        )
        if numbered_draft:
            return numbered_draft

        return ""

    def _extract_numbered_draft_sentences(
        self,
        cleaned_thinking: str,
    ) -> str:
        """Extract one numbered draft sentence block from reasoning text."""
        capture = False
        current_item = ""
        sentences: list[str] = []

        def flush_current() -> None:
            nonlocal current_item
            candidate = self._clean_reasoning_candidate(current_item)
            if candidate:
                sentences.append(candidate)
            current_item = ""

        for raw_line in cleaned_thinking.splitlines():
            stripped = raw_line.strip()
            lowered = stripped.lower()
            if not capture:
                if "drafting sentences" in lowered:
                    capture = True
                continue

            if current_item and re.match(r"^\d+\.\s+", stripped):
                flush_current()
            if "review against constraints" in lowered:
                break
            match = re.match(r"^\d+\.\s+(.+)$", stripped)
            if match:
                current_item = match.group(1).strip()
                continue
            if current_item and raw_line[:1].isspace() and stripped:
                current_item = f"{current_item} {stripped}"
                continue
            if current_item and not stripped:
                flush_current()

        if current_item:
            flush_current()
        return " ".join(sentences)

    def _extract_labelled_reasoning_response(
        self,
        cleaned_thinking: str,
    ) -> str:
        """Extract one substantive answer from free-form labelled reasoning."""
        labelled_candidates: list[tuple[int, str]] = []

        for raw_line in cleaned_thinking.splitlines():
            parsed = self._parse_reasoning_labelled_line(raw_line)
            if not parsed:
                continue
            label, body = parsed
            candidate = self._clean_reasoning_candidate(body)
            if not candidate or self._looks_like_malformed_forced_response_fragment(
                candidate
            ):
                continue

            lowered_label = label.lower()
            score = 0
            if "final answer" in lowered_label or "final polish" in lowered_label:
                score = 5
            elif "substantive content" in lowered_label:
                score = 4
            elif "summary" in lowered_label or lowered_label == "answer":
                score = 3
            elif "draft" in lowered_label:
                score = 2
            elif "content" in lowered_label:
                score = 1

            if score:
                labelled_candidates.append((score, candidate))

        if not labelled_candidates:
            return ""

        labelled_candidates.sort(
            key=lambda item: (item[0], len(item[1])),
            reverse=True,
        )
        return labelled_candidates[0][1]

    @staticmethod
    def _parse_reasoning_labelled_line(line: str) -> tuple[str, str] | None:
        """Return one `(label, body)` pair from a labelled reasoning line."""
        candidate = line.strip()
        if not candidate:
            return None

        candidate = re.sub(r"^(?:[-*+]\s+)", "", candidate).strip()
        patterns = (
            r'^\*\*([^*]+):\*\*\s*(.+)$',
            r'^\*([^*]+):\*\s*(.+)$',
            r'^\*([^*]+)\*:\s*(.+)$',
            r'^"([^"]+):"\s*(.+)$',
            r'^([^:]{3,80}):\s*(.+)$',
        )
        for pattern in patterns:
            match = re.match(pattern, candidate)
            if not match:
                continue

            label = match.group(1).strip()
            body = match.group(2).strip()
            body_text = re.sub(r"[^A-Za-z0-9]+", "", body)
            if not body_text:
                continue
            lowered_label = label.lower()
            if any(
                marker in lowered_label
                for marker in (
                    "constraint",
                    "refining",
                    "instruction",
                    "self-correction",
                    "review",
                    "check",
                    "prompt says",
                    "do not repeat",
                )
            ):
                return None
            return label, body

        return None

    def _extract_preferred_quote_from_section(self, section: str) -> str:
        """Return one preferred quoted answer from a reasoning section."""
        labelled_quotes: list[tuple[str, str]] = []
        pattern = re.compile(
            r'^\s*\*\s+(?:\*([^*]+):\*\s*)?"(.+?)"\s*$',
            flags=re.MULTILINE,
        )
        for match in pattern.finditer(section):
            label = (match.group(1) or "").strip().lower()
            quote = match.group(2).strip()
            if quote:
                labelled_quotes.append((label, quote))

        if not labelled_quotes:
            return ""

        preferred_labels = {
            "combine for flow",
            "final answer",
            "final polish",
            "draft",
        }
        for label, quote in reversed(labelled_quotes):
            if label in preferred_labels:
                return quote

        if len(labelled_quotes) == 1:
            return labelled_quotes[0][1]
        return ""

    def _extract_quoted_response_lines(self, section: str) -> list[str]:
        """Return quoted response lines from one reasoning section."""
        return [
            match.group(1).strip()
            for match in re.finditer(
                r'^\s*\*\s+(?:\*[^*]+:\*\s*)?"(.+?)"\s*$',
                section,
                flags=re.MULTILINE,
            )
            if match.group(1).strip()
        ]

    def _extract_labelled_draft_line(self, section: str) -> str:
        """Return one unquoted draft line from a reasoning section."""
        patterns = [
            r'^\s*\*Draft:\*\s*(.+)$',
            r'^\s*Draft:\s*(.+)$',
        ]
        for pattern in patterns:
            match = re.search(pattern, section, flags=re.MULTILINE)
            if not match:
                continue
            candidate = self._clean_reasoning_candidate(match.group(1))
            if candidate:
                return candidate
        return ""

    def _extract_reasoning_section(
        self,
        cleaned_thinking: str,
        heading: str,
    ) -> str:
        """Return one numbered reasoning section by heading label."""
        pattern = re.compile(
            rf"\d+\.\s+\*\*{re.escape(heading)}:\*\*(?:[^\n]*)\n(.*?)(?=\n\d+\.\s+\*\*|\Z)",
            flags=re.DOTALL,
        )
        match = pattern.search(cleaned_thinking)
        if not match:
            return ""
        return match.group(1).strip()

    def _clean_reasoning_candidate(self, paragraph: str) -> str:
        """Normalize one fallback reasoning paragraph into visible text."""
        candidate = paragraph.strip()
        if not candidate:
            return ""
        if candidate[:1] == candidate[-1:] and candidate[:1] in {'"', "'"}:
            candidate = candidate[1:-1].strip()
        candidate = self._strip_forced_response_label(candidate)
        section_body_match = re.match(
            r"^\d+\.\s+\*\*[^*]+:\*\*\s*(.+)$",
            candidate,
            flags=re.DOTALL,
        )
        if section_body_match:
            candidate = section_body_match.group(1).strip()
        if self._looks_like_instruction_reflection(candidate):
            return ""
        if self._looks_like_summary_prompt_echo(candidate):
            return ""
        if self._looks_like_search_result_preface_response(candidate):
            return ""
        if self._looks_like_summary_direction_response(candidate):
            return ""
        if self._looks_like_document_summary_clarification_response(candidate):
            return ""
        if self._looks_like_summary_format_description_response(candidate):
            return ""
        if self._looks_like_reasoning_header(candidate):
            return ""
        if self._looks_like_verification_verdict_response(candidate):
            return ""
        return candidate

    @staticmethod
    def _looks_like_verification_verdict_response(text: str) -> bool:
        """Return True when text is a verifier verdict, not a user answer."""
        normalized = " ".join(str(text or "").split())
        if not normalized:
            return False

        normalized_for_split = re.sub(
            r'([.!?])["\'”)]\s+',
            r"\1 ",
            normalized,
        )
        sentences = [
            sentence.strip(' "\'“”')
            for sentence in re.split(
                r"(?<=[.!?])\s+",
                normalized_for_split,
            )
            if sentence.strip()
        ]
        if len(sentences) < 2:
            return False

        verdict = sentences[-1].rstrip(".!?").lower()
        if verdict not in {
            "supported",
            "not supported",
            "partially supported",
            "unsupported",
            "contradicted",
            "inconclusive",
        }:
            return False

        evidence_markers = (
            normalized[:1] in {'"', "'", "“"}
            or any(marker in normalized.lower() for marker in (
                "claim:",
                "evidence:",
                "excerpt:",
                "the claim",
            ))
        )
        return evidence_markers or len(sentences) <= 2

    @staticmethod
    def _looks_like_structure_only_response(text: str) -> bool:
        """Return True for table-of-contents style answers."""
        normalized = " ".join(str(text or "").split())
        if not normalized:
            return False

        upper = normalized.upper()
        marker_hits = sum(
            1
            for marker in (
                "INTRODUCTION",
                "PROLOGUE",
                "THE BOOK OF",
                "BOOK OF",
                "CHAPTER ",
                "PART ",
            )
            if marker in upper
        )
        if marker_hits < 2:
            return False

        alpha_chars = [char for char in normalized if char.isalpha()]
        if not alpha_chars:
            return False
        uppercase_ratio = (
            sum(1 for char in alpha_chars if char.isupper())
            / len(alpha_chars)
        )
        has_sentence_punctuation = any(
            mark in normalized for mark in (".", "!", "?")
        )
        return uppercase_ratio >= 0.6 and not has_sentence_punctuation

    @staticmethod
    def _looks_like_summary_label_inventory_response(text: str) -> bool:
        """Return True for bare summary category labels without prose."""
        normalized = " ".join(str(text or "").split())
        if not normalized:
            return False

        label_markers = {
            "premise",
            "setting",
            "conflict",
            "central conflict",
            "characters",
            "character relationships",
            "relationships",
            "themes",
            "plot",
            "subject",
            "argument",
            "context",
        }
        parts = [
            part.strip(" .:;!?-\t").lower()
            for part in re.split(r"[,;/]", normalized)
            if part.strip(" .:;!?-\t")
        ]
        if len(parts) < 2 or len(parts) > 6:
            return False

        return all(part in label_markers for part in parts)

    @classmethod
    def _looks_like_summary_scaffolding_response(cls, text: str) -> bool:
        """Return True for summary candidates that are structure or inventory."""
        if cls._looks_like_structure_only_response(text):
            return True
        if cls._looks_like_summary_label_inventory_response(text):
            return True

        lines = [
            line.strip()
            for line in str(text or "").splitlines()
            if line.strip()
        ]
        if len(lines) < 2:
            return False

        list_lines = [
            line for line in lines if re.match(r"^(?:[-*+]\s+|\d+\.\s+)", line)
        ]
        if len(list_lines) < 2:
            return False

        excerpt_line_hits = sum(
            1
            for line in list_lines
            if re.search(r"\bexcerpt\s+\d+", line, flags=re.IGNORECASE)
        )
        if excerpt_line_hits >= 2:
            return True

        lowered = "\n".join(lines).lower()
        markers = (
            "document:",
            "excerpt ",
            "matched documents",
            "relevant excerpts",
        )
        return sum(marker in lowered for marker in markers) >= 2

    @staticmethod
    def _normalize_inventory_summary_response(text: str) -> str:
        """Flatten one list-style excerpt inventory into short prose."""
        fragments: list[str] = []
        for raw_line in str(text or "").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            line = re.sub(r"^(?:[-*+]\s+|\d+\.\s+)", "", line).strip()
            if not line:
                continue
            if line.lower().startswith("document:"):
                line = line.split(":", 1)[-1].strip()
            elif ":" in line and line.lower().startswith("excerpt "):
                line = line.split(":", 1)[-1].strip()
            if not line:
                continue
            if line[-1] not in ".!?":
                line = f"{line}."
            if line not in fragments:
                fragments.append(line)

        if not fragments:
            return ""
        return " ".join(fragments)

    @classmethod
    def _normalize_numbered_summary_response(cls, text: str) -> str:
        """Flatten one numbered reasoning list into plain summary prose."""
        fragments: list[str] = []
        for raw_line in str(text or "").splitlines():
            match = re.match(r"^\s*\d+\.\s+(.+)$", raw_line)
            if not match:
                continue
            line = cls._clean_reasoning_candidate(cls, match.group(1).strip())
            if not line:
                continue

            lowered = line.lower()
            if any(
                marker in lowered
                for marker in (
                    "constraint",
                    "instruction",
                    "review against constraints",
                    "do not call another tool",
                    "respond now",
                )
            ):
                continue

            if line[-1] not in ".!?":
                line = f"{line}."
            if line not in fragments:
                fragments.append(line)

        if len(fragments) < 2:
            return ""
        return " ".join(fragments)

    @staticmethod
    def _looks_like_reasoning_header(candidate: str) -> bool:
        """Return True when text is a planning header, not a user answer."""
        lowered = candidate.strip().lower()
        normalized = re.sub(r"[*_`]+", "", lowered)
        normalized = " ".join(normalized.split())
        if normalized in {
            "thinking process:",
            "drafting the response:",
            "refining for conciseness and flow:",
            "final review against constraints:",
            "analyze the request:",
            "analyze the search results:",
            "synthesize the answer:",
        }:
            return True
        scaffolding_labels = (
            "thinking process",
            "analyze the request",
            "analyze the evidence",
            "analyze the search results",
            "draft the response",
            "drafting the response",
            "drafting - step 1",
            "drafting - step 2",
            "mental outline",
            "writing & counting",
            "refine the response",
            "refining for conciseness and flow",
            "final review against constraints",
            "final polish",
            "synthesize the answer",
        )
        if normalized.endswith(":"):
            residual = normalized
            for label in scaffolding_labels:
                residual = residual.replace(label, " ")
            residual = re.sub(r"[\d\W_]+", " ", residual)
            residual_words = [
                word
                for word in residual.split()
                if word not in {"and", "the", "step"}
            ]
            if any(label in normalized for label in scaffolding_labels):
                if len(residual_words) <= 3:
                    return True
        marker_hits = sum(
            label in normalized for label in scaffolding_labels
        )
        if marker_hits >= 2:
            residual = normalized
            for label in scaffolding_labels:
                residual = residual.replace(label, " ")
            residual = re.sub(r"[\d\W_]+", " ", residual)
            residual_words = [
                word
                for word in residual.split()
                if word not in {"and", "the", "step"}
            ]
            if len(residual_words) <= 3:
                return True
        reasoning_markers = (
            "task:",
            "constraint 1:",
            "constraint 2:",
            "constraint 3:",
            "constraint 4:",
            "constraint 5:",
            "constraint 6:",
            "input:",
            "constraints check:",
            "natural/conversational?",
            "identify document first?",
            "only search result info?",
            "no tools/json?",
            "concise?",
            "self-correction",
            "wait, one more check:",
            "review against constraints",
            "4-6 sentences? yes",
            "one or two short paragraphs? yes",
            "no bullet points? yes",
            "conversational? yes",
            "specific details? yes",
        )
        if any(marker in lowered for marker in reasoning_markers):
            return True
        if re.match(r"^\d+\.\s+\*\*.*\*\*$", candidate):
            return True
        if re.match(r"^\d+\.\s+\*\*.*?:\*\*", candidate):
            return True
        return False

    def _stream_model_response(
        self,
        prompt: List[BaseMessage],
        generation_kwargs: Optional[Dict] = None,
        thinking_metadata: Optional[Dict[str, Any]] = None,
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
                prompt,
                generation_kwargs,
                thinking_metadata=thinking_metadata,
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
        elif tool_name == "inspect_loaded_documents":
            response_content = (
                "I inspected the loaded documents but couldn't identify "
                "enough detail to answer that clearly."
            )
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
        tool_messages = self._get_current_turn_tool_messages(
            state["messages"]
        )
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
        Task-completing tools should go to force_response.

        CRITICAL: Check for potential duplicate tool calls BEFORE routing back to model.
        If we detect the model will likely call the same tool again, route to force_response.

        Args:
            state: Workflow state

        Returns:
            Routing decision: "model", "force_response", or "end"
        """
        current_turn_messages = self._get_current_turn_messages(
            state["messages"]
        )
        tool_messages = self._get_tool_messages(current_turn_messages)

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
            "write_file",          # File was written - present result
            "complete_todo_item",  # Workflow item completed
        }
        DIRECT_RESPONSE_TOOLS = set()

        # Check the most recent tool message to see what tool was called
        last_tool_msg = tool_messages[-1]

        # Get the corresponding AI message with tool_calls
        last_ai_msg = self._get_last_tool_calling_ai_message(
            current_turn_messages
        )
        if not last_ai_msg:
            return "end"
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

            if self._should_return_tool_direct(tool_name):
                self.logger.info(
                    f"[ROUTE DEBUG] Tool '{tool_name}' is return_direct - routing to force_response"
                )
                return "force_response"

            if tool_name in DIRECT_RESPONSE_TOOLS:
                self.logger.info(
                    f"[ROUTE DEBUG] Tool '{tool_name}' should be synthesized directly"
                )
                return "force_response"
            
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

            if self._should_force_document_tool_response(tool_name):
                self.logger.info(
                    "[ROUTE DEBUG] Document tool '%s' completed - forcing "
                    "response synthesis",
                    tool_name,
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
        tool_messages = self._get_current_turn_tool_messages(messages)
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
        tool_messages = self._get_current_turn_tool_messages(messages)
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

        # Log previous tool result from the active turn only
        tool_messages = self._get_current_turn_tool_messages(messages)
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

        # Consciousness integration: capture user text + pre-LLM signals.
        # Best-effort only; must not affect model execution.
        try:
            self._maybe_consciousness_pre_llm(state.get("messages") or [])
        except Exception:
            pass

        # Trim messages (skip trimming for vision models to preserve multimodal parts)
        chat_model = getattr(self, "_chat_model", None)
        if chat_model and getattr(chat_model, "is_vision_model", False):
            trimmed_messages = state["messages"]
        else:
            trimmed_messages = self._trim_messages(state["messages"])

        disable_tools_for_followup = self._should_disable_tools_for_followup(
            trimmed_messages
        )
        chat_model_overrides = {}
        tools_backup = getattr(self, "_tools", None)

        try:
            if disable_tools_for_followup:
                self.logger.info(
                    "[CALL MODEL DEBUG] Disabling tools for synthesized "
                    "document follow-up response"
                )
                if hasattr(self, "_tools"):
                    self._tools = []
                for attr_name, override in (
                    ("tools", None),
                    ("tool_choice", None),
                ):
                    if chat_model is None or not hasattr(chat_model, attr_name):
                        continue
                    chat_model_overrides[attr_name] = getattr(
                        chat_model,
                        attr_name,
                    )
                    setattr(chat_model, attr_name, override)

            # Build prompt with tool instructions
            prompt = self._build_prompt(trimmed_messages)

            # Generate response
            response_message = self._generate_response(
                prompt,
                generation_kwargs,
            )
        finally:
            if disable_tools_for_followup and hasattr(self, "_tools"):
                self._tools = tools_backup
            for attr_name, original_value in chat_model_overrides.items():
                try:
                    setattr(chat_model, attr_name, original_value)
                except Exception:
                    self.logger.debug(
                        "Failed to restore chat model attribute %s",
                        attr_name,
                    )

        # Guard against models returning None so LangGraph doesn't try to merge
        # a None entry into the message list (which raises during add_messages).
        if response_message is None:
            self.logger.error(
                "[CALL MODEL DEBUG] Model returned no message; emitting fallback AIMessage"
            )
            response_message = AIMessage(
                content="",
                additional_kwargs={"error": "no_message_generated"},
                tool_calls=[],
            )

        # Consciousness integration: record assistant output + post-LLM signals.
        try:
            self._maybe_consciousness_post_llm(response_message, state.get("messages") or [])
        except Exception:
            pass

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
                "Respond ONLY with the required tool call.\n"
                "Do NOT write any conversational text, explanation, JSON example, or commentary before or after the tool call.\n"
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
        current_turn_messages = self._get_current_turn_messages(
            trimmed_messages
        )
        has_tool_results = any(
            msg.__class__.__name__ == "ToolMessage"
            for msg in current_turn_messages
        )

        if not has_tool_results:
            return system_prompt

        # Check for ERROR responses from tools - these MUST be handled first
        tool_messages = self._get_tool_messages(current_turn_messages)
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
            m for m in current_turn_messages
            if hasattr(m, 'tool_calls') and m.tool_calls
        ])
        
        # Count scrape ATTEMPTS vs SUCCESSES
        scrape_attempts = sum(
            1
            for m in current_turn_messages
            if hasattr(m, 'tool_calls') and m.tool_calls
            for tc in m.tool_calls if tc.get('name') == 'scrape_website'
        )
        
        # Check for SUCCESSFUL scrapes by examining ToolMessage name and content
        successful_scrapes = 0
        failed_scrapes = 0
        tool_messages = self._get_tool_messages(current_turn_messages)
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
        
        self.logger.info(
            f"[POST-TOOL] response_format={response_format}, tool_calling_mode={tool_calling_mode}, "
            f"force_tool={force_tool}, is_research_mode={is_research_mode}, "
            f"tool_calls={tool_call_count}, scrape_attempts={scrape_attempts}, "
            f"successful_scrapes={successful_scrapes}, failed_scrapes={failed_scrapes}, "
            f"search_urls={len(search_urls)}"
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
            elif successful_scrapes < 2 and tool_call_count < 8:
                # Phase 2: Need broader source coverage before summarizing
                instruction = (
                    "\n\n=== DEEP RESEARCH WORKFLOW - PHASE 2: EXPAND SOURCE COVERAGE ===\n"
                    f"You've successfully scraped {successful_scrapes} source(s). Gather at least one or two more high-value sources before summarizing.\n\n"
                    "**YOUR NEXT ACTION:**\n"
                    "1. Call `scrape_website` on additional strong URLs from your search results\n"
                    "2. Prefer sources that add new facts, dates, or perspectives\n\n"
                    "**DO NOT** respond to the user yet. Strengthen the evidence first."
                )
            elif successful_scrapes > 0:
                # Phase 3: Synthesize the answer directly for the user
                instruction = (
                    "\n\n=== DEEP RESEARCH WORKFLOW - PHASE 3: SYNTHESIZE & RESPOND ===\n"
                    "You have enough source material to answer directly.\n\n"
                    "**YOUR RESPONSE SHOULD INCLUDE:**\n"
                    "1. A concise executive summary\n"
                    "2. Key findings with source links or explicit source attribution\n"
                    "3. Any important uncertainty, disagreement, or missing evidence\n"
                    "4. A short conclusion or recommended next step if relevant\n\n"
                    "**DO NOT** mention a generated document path. Respond with findings only."
                )
            else:
                # Phase 4: Research complete or max iterations, summarize
                instruction = (
                    "\n\n=== DEEP RESEARCH WORKFLOW - PHASE 4: COMPLETE ===\n"
                    "Your research is complete. Provide a summary to the user.\n\n"
                    "**YOUR RESPONSE SHOULD INCLUDE:**\n"
                    "1. Key findings from your research\n"
                    "2. A brief summary of your sources\n"
                    "3. Any notable uncertainty or missing evidence\n\n"
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
                "write_file",        # File was written - present result
                "complete_todo_item",  # Workflow item completed
            }
            
            # Get last AI message to check what tool was called
            ai_messages = [
                m for m in current_turn_messages
                if hasattr(m, 'tool_calls') and m.tool_calls
            ]
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
            elif self._is_document_result_tool(last_tool_name or ""):
                user_question = self._get_user_question(current_turn_messages)
                document_intent = self._get_document_query_intent(
                    user_question
                )
                if document_intent == "identity":
                    instruction = (
                        "\n\n=== ANSWER THE DOCUMENT QUESTION NOW ===\n"
                        "Use the current document tool results to answer directly and briefly.\n"
                        "Name the document and, when available, include the title, author, or file type.\n"
                        "Do NOT mention search results, tool usage, or instructions.\n"
                        "Do NOT call another tool. Respond now."
                    )
                elif document_intent == "structure":
                    instruction = (
                        "\n\n=== ANSWER THE DOCUMENT QUESTION NOW ===\n"
                        "Use the current document tool results to answer with the section names only.\n"
                        "Do NOT restate the document title, author, file type, path, or a broader summary.\n"
                        "Do NOT discuss your reasoning or the instructions.\n"
                        "Do NOT call another tool. Respond now."
                    )
                elif document_intent == "summary":
                    instruction = (
                        "\n\n=== ANSWER THE DOCUMENT QUESTION NOW ===\n"
                        "Use the current document tool results to write a fuller multi-sentence summary.\n"
                        "Focus on the document's themes, claims, and notable details from the excerpts.\n"
                        "Treat any structure block as background context, not the main answer.\n"
                        "Do NOT infer a genre, series, trilogy, collection, or bibliography unless the evidence states it directly.\n"
                        "Treat uncanny or dreamlike atmosphere as mood unless the excerpts explicitly confirm literal supernatural events.\n"
                        "Do NOT attribute quoted criticism, accusations, or stray dialogue to the apparently dead figure unless the excerpt explicitly identifies that speaker.\n"
                        "Do NOT repeat the title, author, or chapter list unless the user asked for them.\n"
                        "Do NOT discuss your reasoning or the instructions.\n"
                        "Do NOT call another tool. Respond now."
                    )
                else:
                    instruction = (
                        "\n\n=== ANSWER THE DOCUMENT QUESTION NOW ===\n"
                        "Use the current document tool results to answer the user's question clearly.\n"
                        "Do NOT mention search results, tool usage, or instructions.\n"
                        "Do NOT call another tool. Respond now."
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
            for m in current_turn_messages
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
        if not stripped.startswith('{'):
            return False

        # Be conservative: only treat as tool-call JSON when it strongly matches
        # known tool-call shapes (name/tool + arguments).
        if ('"name"' in stripped or '"tool"' in stripped) and (
            '"arguments"' in stripped or '"args"' in stripped
        ):
            return True
        if '"tool"' in stripped and any(
            key in stripped
            for key in (
                '"query"',
                '"prompt"',
                '"url"',
                '"path"',
                '"text"',
                '"content"',
            )
        ):
            return True
        if '"function"' in stripped and '"arguments"' in stripped:
            return True
        return False

    def _generate_streaming_response(
        self,
        formatted_prompt,
        generation_kwargs: Dict,
        thinking_metadata: Optional[Dict[str, Any]] = None,
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
        using_reasoning_deltas = False
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
        request_id = getattr(self, "_current_request_id", None)
        tool_choice = getattr(self, "_tool_choice", None)
        forced_tool_choice = (
            isinstance(tool_choice, dict)
            and isinstance(tool_choice.get("function"), dict)
            and bool(tool_choice["function"].get("name"))
        )
        hold_visible_output = bool(
            getattr(self, "_force_tool", None) or forced_tool_choice
        )
        pending_visible_chunks: List[str] = []
        headless_thinking_open = False
        emitted_tool_call_keys: set[str] = set()

        def emit_headless_phase_chunk(
            response: LLMResponse,
        ) -> None:
            """Route one typed phase chunk through the headless NDJSON path."""
            if not is_headless or not has_emitter:
                return
            self._signal_emitter.emit_signal(
                SignalCode.LLM_TEXT_STREAMED_SIGNAL,
                {
                    "response": response,
                    "request_id": request_id,
                },
            )

        def emit_headless_thinking_chunk(
            content: str,
            *,
            is_end: bool = False,
        ) -> None:
            """Emit one typed thinking chunk for the daemon stream."""
            nonlocal headless_thinking_open
            if not is_headless or not has_emitter:
                return
            if not headless_thinking_open and not content and not is_end:
                return
            emit_headless_phase_chunk(
                LLMResponse(
                    message="",
                    is_first_message=not headless_thinking_open,
                    is_end_of_message=is_end,
                    request_id=request_id,
                    message_type="thinking",
                    thinking_content=content,
                )
            )
            if not headless_thinking_open:
                headless_thinking_open = True
            if is_end:
                headless_thinking_open = False

        def emit_headless_tool_call_chunk(tool_call: Dict[str, Any]) -> None:
            """Emit one typed tool-call chunk for the daemon stream."""
            if not is_headless or not has_emitter:
                return
            tool_name = str(tool_call.get("name") or "").strip()
            if not tool_name:
                return
            tool_args = tool_call.get("args") or tool_call.get("arguments")
            dedupe_key = json.dumps(
                {
                    "id": tool_call.get("id"),
                    "name": tool_name,
                    "arguments": tool_args,
                },
                sort_keys=True,
                default=str,
            )
            if dedupe_key in emitted_tool_call_keys:
                return
            emitted_tool_call_keys.add(dedupe_key)
            emit_headless_phase_chunk(
                LLMResponse(
                    message="",
                    is_first_message=True,
                    is_end_of_message=True,
                    request_id=request_id,
                    message_type="tool_call",
                    tool_name=tool_name,
                    tool_arguments=(tool_args if isinstance(tool_args, dict) else None),
                    tool_status="completed",
                )
            )

        def emit_thinking_signal(status: str, content: str) -> None:
            """Emit one request-scoped thinking update to the GUI."""
            if not has_emitter:
                return
            self._signal_emitter.emit_signal(
                SignalCode.LLM_THINKING_SIGNAL,
                {
                    "status": status,
                    "content": content,
                    "request_id": request_id,
                    "metadata": thinking_metadata,
                },
            )

        def forward_stream_text(text_to_stream: str) -> None:
            """Forward one raw chunk to the streaming callback."""
            if not self._token_callback or not text_to_stream:
                return
            try:
                self._token_callback(text_to_stream)
            except Exception as callback_error:
                self.logger.error(
                    "Token callback failed: %s",
                    callback_error,
                    exc_info=True,
                )

        def store_visible_text(
            text_to_stream: str,
            *,
            forward_to_callback: bool = True,
        ) -> None:
            """Persist one visible chunk and optionally forward it."""
            nonlocal has_streamed_content
            if not has_streamed_content:
                text_to_stream = text_to_stream.lstrip()
            if not text_to_stream:
                return

            streamed_content.append(text_to_stream)
            has_streamed_content = True
            if hold_visible_output:
                pending_visible_chunks.append(text_to_stream)
                return
            if forward_to_callback:
                forward_stream_text(text_to_stream)
        # In headless/HTTP mode (e.g. legacy /llm/generate NDJSON streaming) we must not
        # suppress/buffer tokens. Some models can emit the *entire* answer inside <think> blocks;
        # suppressing thinking would then swallow all output for NDJSON clients.
        is_headless = os.environ.get("AIRUNNER_HEADLESS", "").strip().lower() in (
            "1",
            "true",
            "yes",
        )
        suppress_thinking_blocks = bool(has_emitter) and not is_headless
        suppress_tool_call_markup = bool(has_emitter) and not is_headless
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
                additional_kwargs = (
                    getattr(chunk_message, "additional_kwargs", {}) or {}
                )
                reasoning_delta = (
                    additional_kwargs.get("thinking_content")
                    or additional_kwargs.get("reasoning_content")
                )

                # Always capture last chunk (might have tool_calls with no content)
                last_chunk_message = chunk_message

                # Collect tool_calls from ANY chunk that has them
                chunk_tool_calls = getattr(chunk_message, "tool_calls", None)
                if chunk_tool_calls:
                    collected_tool_calls.extend(chunk_tool_calls)
                    for tool_call in chunk_tool_calls:
                        if isinstance(tool_call, dict):
                            emit_headless_tool_call_chunk(tool_call)

                # Only skip if content, tool calls, and reasoning are all empty.
                if not text and not chunk_tool_calls and not reasoning_delta:
                    continue

                # Debug: Log every chunk
                # self.logger.debug(f"[THINKING] Chunk received: '{text[:50]}...' (in_thinking={in_thinking_block})")

                if reasoning_delta:
                    if not thinking_started:
                        thinking_started = True
                        using_reasoning_deltas = True
                        emit_thinking_signal("started", "")

                    thinking_content.append(reasoning_delta)
                    emit_thinking_signal("streaming", reasoning_delta)
                    emit_headless_thinking_chunk(reasoning_delta)

                    if not text:
                        continue

                if using_reasoning_deltas and text:
                    using_reasoning_deltas = False
                    final_thinking_content = "".join(thinking_content)
                    emit_thinking_signal(
                        "completed",
                        final_thinking_content,
                    )
                    emit_headless_thinking_chunk("", is_end=True)
                    thinking_content = []

                found_open, tag_format, before_open, after_think = (
                    detect_thinking_open_tag(text)
                )
                if found_open and not thinking_started:
                    if not suppress_thinking_blocks:
                        forward_stream_text(text)
                    in_thinking_block = True
                    thinking_started = True
                    thinking_tag_format = tag_format
                    emit_thinking_signal("started", "")

                    if before_open:
                        store_visible_text(
                            before_open,
                            forward_to_callback=suppress_thinking_blocks,
                        )

                    found_close, before_close, after_close = (
                        detect_thinking_close_tag(after_think, tag_format)
                    )
                    if found_close:
                        if before_close:
                            thinking_content.append(before_close)
                            emit_thinking_signal(
                                "streaming",
                                before_close,
                            )
                            emit_headless_thinking_chunk(before_close)

                        in_thinking_block = False
                        final_thinking_content = "".join(thinking_content)
                        emit_thinking_signal(
                            "completed",
                            final_thinking_content,
                        )
                        emit_headless_thinking_chunk("", is_end=True)
                        thinking_content = []

                        if after_close:
                            store_visible_text(
                                after_close,
                                forward_to_callback=suppress_thinking_blocks,
                            )
                    elif after_think:
                        thinking_content.append(after_think)
                        emit_thinking_signal(
                            "streaming",
                            after_think,
                        )
                        emit_headless_thinking_chunk(after_think)
                    continue

                if in_thinking_block:
                    if not suppress_thinking_blocks:
                        forward_stream_text(text)

                    found_close, before_close, after_close = (
                        detect_thinking_close_tag(text, thinking_tag_format)
                    )
                    if found_close:
                        if before_close:
                            thinking_content.append(before_close)
                            emit_thinking_signal(
                                "streaming",
                                before_close,
                            )
                            emit_headless_thinking_chunk(before_close)

                        in_thinking_block = False
                        final_thinking_content = "".join(thinking_content)
                        emit_thinking_signal(
                            "completed",
                            final_thinking_content,
                        )
                        emit_headless_thinking_chunk("", is_end=True)
                        thinking_content = []

                        if after_close:
                            store_visible_text(
                                after_close,
                                forward_to_callback=suppress_thinking_blocks,
                            )
                    else:
                        emit_thinking_signal("streaming", text)
                        thinking_content.append(text)
                        emit_headless_thinking_chunk(text)
                    continue
                
                text_to_stream = text

                if suppress_tool_call_markup:
                    # Detect <tool_call> tags and buffer them instead of streaming
                    # This prevents tool call markup from appearing in the chat UI
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
                    if not in_json_tool_call and '{' in text:
                        remaining = text[text.index('{'):]
                        if self._is_tool_call_json(remaining):
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
                
                store_visible_text(text_to_stream)

            if using_reasoning_deltas and thinking_content:
                final_thinking_content = "".join(thinking_content)
                emit_thinking_signal(
                    "completed",
                    final_thinking_content,
                )
                emit_headless_thinking_chunk("", is_end=True)

            if hold_visible_output and not collected_tool_calls:
                combined_visible = combine_stream_chunks(pending_visible_chunks)
                if combined_visible:
                    forward_stream_text(combined_visible)
            elif hold_visible_output and collected_tool_calls:
                streamed_content = []

            # Return message if we have content or tool_calls
            if streamed_content or last_chunk_message:
                # Use final_thinking_content if available (from completed thinking block)
                # Otherwise fall back to current thinking_content list (for incomplete thinking)
                thinking_to_save = final_thinking_content or ("".join(thinking_content) if thinking_content else None)
                return self._create_streamed_message(
                    streamed_content,
                    last_chunk_message,
                    collected_tool_calls,
                    thinking_to_save,
                    thinking_metadata,
                )

            # No chunks were produced (likely interrupted before first token)
            self.logger.error("No generation chunks were returned; emitting empty AIMessage")
            if self._token_callback:
                try:
                    self._token_callback("[generation stalled]")
                except Exception as callback_error:
                    self.logger.error(
                        "Token callback failed while reporting stalled generation: %s",
                        callback_error,
                        exc_info=True,
                    )
            return AIMessage(
                content="",
                additional_kwargs={"error": "no_generation_chunks"},
                tool_calls=[],
            )

        except Exception as exc:
            self.logger.error(
                "Error during streamed model call: %s", exc, exc_info=True
            )

        return None

    def _stream_internal_response(
        self,
        formatted_prompt,
        generation_kwargs: Optional[Dict] = None,
        *,
        thinking_metadata: Optional[Dict[str, Any]] = None,
        buffer_visible_output: bool = False,
    ) -> Optional[AIMessage]:
        """Stream one internal model pass with tools and thinking disabled."""
        chat_model = getattr(self, "_chat_model", None)
        token_callback_backup = getattr(self, "_token_callback", None)
        if chat_model is None:
            return self._stream_model_response(
                formatted_prompt,
                generation_kwargs or {},
                thinking_metadata=thinking_metadata,
            )

        original_values = {}
        for attr_name, override in (
            ("enable_thinking", False),
            ("tools", None),
            ("tool_choice", None),
        ):
            if hasattr(chat_model, attr_name):
                original_values[attr_name] = getattr(chat_model, attr_name)
                setattr(chat_model, attr_name, override)

        try:
            if buffer_visible_output:
                self._token_callback = None
            return self._stream_model_response(
                formatted_prompt,
                generation_kwargs or {},
                thinking_metadata=thinking_metadata,
            )
        finally:
            self._token_callback = token_callback_backup
            for attr_name, original_value in original_values.items():
                try:
                    setattr(chat_model, attr_name, original_value)
                except Exception:
                    self.logger.debug(
                        "Failed to restore chat model attribute %s",
                        attr_name,
                    )

    def _build_request_tool_debug_metadata(self) -> Optional[Dict[str, Any]]:
        """Return one read-only request settings snapshot for tool rows."""
        llm_request = getattr(self, "llm_request", None)
        if llm_request is None:
            return None
        build_metadata = getattr(llm_request, "to_debug_metadata", None)
        if not callable(build_metadata):
            return None
        return build_metadata(title="Request Settings")

    def _create_streamed_message(
        self,
        streamed_content: List[str],
        last_chunk_message: Optional[BaseMessage],
        collected_tool_calls: Optional[List] = None,
        thinking_content: Optional[str] = None,
        thinking_metadata: Optional[Dict[str, Any]] = None,
    ) -> AIMessage:
        """Create AIMessage from streamed content.

        Args:
            streamed_content: List of content chunks
            last_chunk_message: Last chunk message
            collected_tool_calls: Tool calls collected from all chunks
            thinking_content: Thinking content from <think> blocks (optional)
            thinking_metadata: Read-only debug metadata for the thinking block

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

        visible_chunks = []
        for chunk in streamed_content:
            cleaned_chunk = strip_thinking_tags(chunk)
            if cleaned_chunk:
                visible_chunks.append(cleaned_chunk)

        complete_content = combine_stream_chunks(visible_chunks)
        
        # Store thinking content in additional_kwargs so it can be saved to DB
        if thinking_content:
            additional_kwargs = dict(additional_kwargs)  # Make a copy to avoid mutating
            additional_kwargs["thinking_content"] = thinking_content
        if thinking_metadata:
            additional_kwargs = dict(additional_kwargs)
            additional_kwargs["thinking_metadata"] = thinking_metadata

        if tool_calls and "tool_status_metadata" not in additional_kwargs:
            tool_status_metadata = self._build_request_tool_debug_metadata()
            if tool_status_metadata:
                additional_kwargs = dict(additional_kwargs)
                additional_kwargs["tool_status_metadata"] = (
                    tool_status_metadata
                )

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

        tool_calls = getattr(response_message, "tool_calls", []) or []
        additional_kwargs = (
            getattr(response_message, "additional_kwargs", {}) or {}
        )
        if tool_calls and "tool_status_metadata" not in additional_kwargs:
            tool_status_metadata = self._build_request_tool_debug_metadata()
            if tool_status_metadata:
                additional_kwargs = dict(additional_kwargs)
                additional_kwargs["tool_status_metadata"] = (
                    tool_status_metadata
                )
                response_message = AIMessage(
                    content=getattr(response_message, "content", "") or "",
                    additional_kwargs=additional_kwargs,
                    tool_calls=tool_calls,
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
