"""Forced-response helpers for node functions."""

from typing import Any, Dict, List, Optional, Tuple

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from airunner.components.llm.config.generation_presets import (
    WorkflowGenerationStage,
)


class ForcedResponseMixin:
    """Handle forced responses generated from tool results."""

    def _force_response_node(self, state: Any) -> Dict[str, Any]:
        """Generate a forced response when duplicate tool routing occurs."""
        messages = list(state.get("messages") or [])
        ai_message_with_tools = self._get_last_tool_calling_ai_message(
            messages
        )
        if not ai_message_with_tools:
            self.logger.error(
                "Force response node called but no AIMessage with tool_calls "
                "found"
            )
            return {"messages": []}

        tool_name = ai_message_with_tools.tool_calls[0].get("name")
        tool_messages = self._get_current_turn_tool_messages(messages)
        all_tool_content = self._combine_tool_results(tool_messages)
        user_question = self._get_user_question(messages)
        generation_kwargs = state.get("generation_kwargs", {})

        if tool_name in self.WORKFLOW_TOOLS:
            self.logger.info(
                "Force response node: Duplicate workflow tool '%s' - adding "
                "continuation instructions and routing back to model",
                tool_name,
            )
            continuation_msg = self._create_workflow_continuation_message(
                all_tool_content,
                tool_name,
                user_question,
            )
            self.logger.info(
                "Force response node: Added continuation message, routing "
                "to model"
            )
            return {
                "messages": [continuation_msg],
                "workflow_continuation": True,
            }

        if self._should_return_tool_direct(tool_name):
            self.logger.info(
                "Force response node: returning direct tool result for '%s'",
                tool_name,
            )
            return {
                "messages": [
                    self._create_direct_tool_response_message(
                        tool_messages,
                        tool_name,
                    )
                ],
                "workflow_continuation": False,
            }

        self.logger.info(
            "Force response node: Generating answer from %s chars across %s "
            "tool result(s)",
            len(all_tool_content),
            len(tool_messages),
        )
        forced_message = self._generate_forced_response_message(
            all_tool_content,
            tool_name,
            user_question,
            generation_kwargs,
            message_history=messages,
        )
        self.logger.info(
            "Force response node: Generated %s char response",
            len(forced_message.content) if forced_message.content else 0,
        )
        return {
            "messages": [forced_message],
            "workflow_continuation": False,
        }

    def _generate_forced_response_message(
        self,
        tool_content: str,
        tool_name: str,
        user_question: str,
        generation_kwargs: Optional[Dict] = None,
        message_history: Optional[List[BaseMessage]] = None,
    ) -> AIMessage:
        """Generate one full AIMessage from tool results."""
        try:
            response_message = self._generate_response_message_from_results(
                tool_content,
                tool_name,
                user_question,
                generation_kwargs,
                message_history=message_history,
            )
            if response_message:
                return response_message
        except Exception as error:
            self.logger.error(
                "Failed to generate forced response: %s",
                error,
            )

        fallback = (
            "I found some information but encountered an issue generating "
            "a complete response."
        )
        if self._token_callback:
            self._token_callback(fallback)
        return AIMessage(content=fallback, tool_calls=[])

    def _create_workflow_continuation_message(
        self,
        tool_content: str,
        tool_name: str,
        user_question: str,
    ) -> HumanMessage:
        """Create a HumanMessage with workflow continuation instructions."""
        self.logger.info(
            "Creating workflow continuation message for duplicate '%s' call",
            tool_name,
        )
        next_action = ""
        if "YOUR NEXT TOOL CALL:" in tool_content:
            for line in tool_content.split("\n"):
                if "YOUR NEXT TOOL CALL:" in line:
                    next_action = line.split(
                        "YOUR NEXT TOOL CALL:",
                        1,
                    )[1].strip()
                    break
        elif "IMMEDIATE NEXT ACTION" in tool_content:
            lines = tool_content.split("\n")
            for index, line in enumerate(lines):
                if "Call this tool NOW:" in line and index + 1 < len(lines):
                    next_action = lines[index + 1].strip()
                    break

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
        """Generate one response that continues the workflow."""
        self.logger.info(
            "Generating workflow continuation for duplicate '%s' call",
            tool_name,
        )
        next_action = ""
        if "YOUR NEXT TOOL CALL:" in tool_content:
            for line in tool_content.split("\n"):
                if "YOUR NEXT TOOL CALL:" in line:
                    next_action = line.split(
                        "YOUR NEXT TOOL CALL:",
                        1,
                    )[1].strip()
                    break
        elif "IMMEDIATE NEXT ACTION" in tool_content:
            lines = tool_content.split("\n")
            for index, line in enumerate(lines):
                if "Call this tool NOW:" in line and index + 1 < len(lines):
                    next_action = lines[index + 1].strip()
                    break

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
            response_message = self._stream_model_response(
                [HumanMessage(content=prompt_text)],
                generation_kwargs,
            )
            if response_message:
                return AIMessage(
                    content=response_message.content or "",
                    additional_kwargs=getattr(
                        response_message,
                        "additional_kwargs",
                        {},
                    ),
                    tool_calls=getattr(response_message, "tool_calls", []),
                )
        except Exception as error:
            self.logger.error(
                "Failed to generate workflow continuation: %s",
                error,
            )

        fallback = (
            "The workflow has been started but I'm having trouble "
            "continuing. The next step should be to call transition_phase "
            "to move to the planning phase."
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
        """Generate one conversational response from tool results."""
        try:
            return self._generate_response_from_results(
                tool_content,
                tool_name,
                user_question,
                generation_kwargs,
            )
        except Exception as error:
            self.logger.error(
                "Failed to generate forced response: %s",
                error,
            )
            fallback = (
                "I found some information but encountered an issue "
                "generating a complete response."
            )
            if self._token_callback:
                self._token_callback(fallback)
            return fallback

    def _generate_response_message_from_results(
        self,
        all_tool_content: str,
        tool_name: str,
        user_question: str = "",
        generation_kwargs: Optional[Dict] = None,
        message_history: Optional[List[BaseMessage]] = None,
    ) -> Optional[AIMessage]:
        """Generate one full AIMessage from tool results."""
        self.logger.info(
            "Forcing model to answer based on %s results "
            "(preserving thinking)...",
            tool_name,
        )
        try:
            document_intent = self._get_document_query_intent(user_question)
            document_tool = self._is_document_result_tool(tool_name)
            deterministic_response = (
                self._build_deterministic_document_response(
                    all_tool_content,
                    tool_name,
                    user_question,
                )
            )
            if deterministic_response:
                grounded_message = AIMessage(
                    content=deterministic_response,
                    additional_kwargs={},
                    tool_calls=[],
                )
                if (
                    message_history
                    and self._should_run_document_conversational_pass(
                        tool_name,
                    )
                ):
                    final_message = self._run_document_conversational_pass(
                        deterministic_response,
                        user_question=user_question,
                        message_history=message_history,
                        generation_kwargs=generation_kwargs,
                        stage_messages=[],
                    )
                    if final_message is not None:
                        self._emit_final_thinking_signal(final_message)
                        return final_message
                if self._token_callback:
                    self._token_callback(deterministic_response)
                return grounded_message

            simple_prompt_text = self._build_search_results_prompt(
                all_tool_content,
                tool_name,
                user_question,
                structured_answer=document_tool,
            )
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
            response_message = self._stream_internal_response(
                simple_prompt,
                internal_generation_kwargs,
                thinking_metadata=thinking_metadata,
                buffer_visible_output=True,
            )
            if response_message is None:
                return None

            reject_structure_only = (
                document_tool and document_intent == "summary"
            )
            drafted_response = self._recover_forced_response_content(
                response_message,
                reject_structure_only=reject_structure_only,
            )
            stage_messages: List[Tuple[str, Optional[AIMessage]]] = [
                ("document_synthesis", response_message),
            ]
            if self._should_verify_document_response(tool_name, user_question):
                verified_message = self._run_document_verification_pass(
                    all_tool_content,
                    tool_name,
                    user_question,
                    drafted_response,
                    generation_kwargs,
                )
                if verified_message is not None:
                    stage_messages.append(
                        ("document_verification", verified_message)
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
                fallback_identity = self._build_document_identity_response(
                    all_tool_content
                )
                if fallback_identity and not visible_content:
                    visible_content = fallback_identity
            if document_tool and document_intent == "structure":
                fallback_structure = self._build_document_structure_response(
                    all_tool_content
                )
                if fallback_structure and not visible_content:
                    visible_content = fallback_structure

            grounded_message = AIMessage(
                content=visible_content,
                additional_kwargs=getattr(
                    response_message,
                    "additional_kwargs",
                    {},
                ),
                tool_calls=[],
            )
            if (
                message_history
                and self._should_run_document_conversational_pass(tool_name)
            ):
                final_message = self._run_document_conversational_pass(
                    visible_content,
                    user_question=user_question,
                    message_history=message_history,
                    generation_kwargs=generation_kwargs,
                    stage_messages=stage_messages,
                    reject_structure_only=reject_structure_only,
                )
                if final_message is not None:
                    return final_message
            if document_tool:
                return self._merge_document_stage_thinking(
                    grounded_message,
                    stage_messages=stage_messages,
                )
            return grounded_message

        except Exception as error:
            self.logger.error(
                "Failed to generate forced response message: %s",
                error,
            )
            return None

    def _generate_response_from_results(
        self,
        all_tool_content: str,
        tool_name: str,
        user_question: str = "",
        generation_kwargs: Optional[Dict] = None,
    ) -> str:
        """Generate visible response text from tool results."""
        self.logger.info(
            "Forcing model to answer based on %s results...",
            tool_name,
        )
        try:
            response_message = self._generate_response_message_from_results(
                all_tool_content,
                tool_name,
                user_question,
                generation_kwargs,
            )
            if response_message is None:
                raise RuntimeError("no forced response message generated")

            document_intent = self._get_document_query_intent(user_question)
            document_tool = self._is_document_result_tool(tool_name)
            reject_structure_only = (
                document_tool and document_intent == "summary"
            )
            response_content = self._recover_forced_response_content(
                response_message,
                reject_structure_only=reject_structure_only,
            )
            if self._looks_like_instruction_reflection(response_content):
                response_content = ""
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
                "Model streamed %s char answer",
                len(response_content),
            )
            return response_content

        except Exception as error:
            self.logger.error(
                "Failed to generate forced response: %s",
                error,
            )
            fallback = (
                "I found some information but encountered an issue generating "
                "a complete response. Let me try to help with what I found."
            )
            if self._token_callback:
                self._token_callback(fallback)
            return fallback

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
                structured_answer=self._is_document_result_tool(tool_name),
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