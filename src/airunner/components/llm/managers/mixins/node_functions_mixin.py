"""Node functions mixin for WorkflowManager.

Handles LangGraph node implementations (_call_model, _force_response_node,
_route_after_model). These are broken into focused helper methods for
maintainability.
"""

from typing import Any, Dict, List, TYPE_CHECKING

from langchain_core.messages import AIMessage, BaseMessage, trim_messages

from airunner.components.llm.managers.mixins.node_functions import (
    ConsciousnessIntegrationMixin,
    DocumentConversationalFollowupMixin,
    DocumentResponsePolicyMixin,
    ForcedResponseMixin,
    InternalStageGenerationMixin,
    MessageStateMixin,
    PostToolInstructionsMixin,
    PromptAssemblyMixin,
    ResponseClassifierMixin,
    ResponseGenerationMixin,
    ResponseNormalizationMixin,
    ResponseRecoveryMixin,
    RoutingDecisionMixin,
    SearchResultsPromptMixin,
    StreamingControlMixin,
    StreamingResponseMixin,
    ToolResponseHelpersMixin,
)

if TYPE_CHECKING:
    from airunner.components.llm.managers.workflow_manager import WorkflowState


class NodeFunctionsMixin(
    ConsciousnessIntegrationMixin,
    DocumentConversationalFollowupMixin,
    DocumentResponsePolicyMixin,
    ForcedResponseMixin,
    InternalStageGenerationMixin,
    MessageStateMixin,
    PostToolInstructionsMixin,
    PromptAssemblyMixin,
    ResponseClassifierMixin,
    ResponseGenerationMixin,
    ResponseNormalizationMixin,
    ResponseRecoveryMixin,
    RoutingDecisionMixin,
    SearchResultsPromptMixin,
    StreamingControlMixin,
    StreamingResponseMixin,
    ToolResponseHelpersMixin,
):
    """Implements LangGraph node functions for the workflow."""

    WORKFLOW_TOOLS = {
        "start_workflow",
        "transition_phase",
        "add_todo_item",
        "start_todo_item",
        "complete_todo_item",
        "get_workflow_status",
    }

    def _maybe_consciousness_pre_llm(self, messages: List[Any]) -> None:
        """Call the pre-LLM consciousness hook when enabled."""
        self._run_consciousness_hook("on_pre_llm", messages=messages)

    def _maybe_consciousness_post_llm(
        self,
        ai_message: Any,
        messages: List[Any],
    ) -> None:
        """Call the post-LLM consciousness hook when enabled."""
        self._run_consciousness_hook(
            "on_post_llm",
            ai_message,
            messages=messages,
        )

    def _call_model(self, state: "WorkflowState") -> Dict[str, Any]:
        """Call the model with trimmed message history."""
        messages = list(state.get("messages") or [])
        self.logger.info(
            "[CALL MODEL DEBUG] Total messages in state: %s",
            len(messages),
        )
        for index, message in enumerate(messages[-5:]):
            msg_type = type(message).__name__
            content_preview = (
                str(message.content)[:100]
                if hasattr(message, "content")
                else "No content"
            )
            self.logger.info(
                "[CALL MODEL DEBUG] Message %s: %s - %s",
                index,
                msg_type,
                content_preview,
            )

        generation_kwargs = state.get("generation_kwargs", {})
        try:
            self._maybe_consciousness_pre_llm(messages)
        except Exception:
            pass

        chat_model = getattr(self, "_chat_model", None)
        if chat_model and getattr(chat_model, "is_vision_model", False):
            trimmed_messages = messages
        else:
            trimmed_messages = self._trim_messages(messages)

        disable_tools_for_followup = self._should_disable_tools_for_followup(
            trimmed_messages
        )
        chat_model_overrides = {}
        tools_backup = getattr(self, "_tools", None)
        followup_prompt_backup = None

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
                followup_prompt_backup = (
                    self._apply_document_followup_system_prompt()
                )

            prompt = self._build_prompt(trimmed_messages)
            response_message = self._generate_response(
                prompt,
                generation_kwargs,
            )
        finally:
            if followup_prompt_backup is not None:
                self._restore_document_followup_system_prompt(
                    followup_prompt_backup
                )
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

        if response_message is None:
            self.logger.error(
                "[CALL MODEL DEBUG] Model returned no message; emitting "
                "fallback AIMessage"
            )
            response_message = AIMessage(
                content="",
                additional_kwargs={"error": "no_message_generated"},
                tool_calls=[],
            )

        try:
            self._maybe_consciousness_post_llm(response_message, messages)
        except Exception:
            pass

        return {"messages": [response_message]}

    def _trim_messages(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        """Trim message history to fit the context window."""
        return trim_messages(
            messages,
            max_tokens=self._max_history_tokens,
            strategy="last",
            token_counter=self._token_counter,
            include_system=True,
            allow_partial=False,
            start_on="human",
        )

