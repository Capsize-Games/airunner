"""Node functions mixin for WorkflowManager."""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from langchain_core.messages import BaseMessage
from airunner_services.llm.managers.response_synthesizer import (
    ResponseSynthesizer,
)
from airunner_services.llm.managers.mixins.node_response_generation_helper import (
    NodeResponseGenerationHelper,
)
from airunner_services.llm.managers.mixins.node_post_tool_instructions_helper import (
    NodePostToolInstructionsHelper,
)
from airunner_services.llm.managers.mixins.node_prompt_assembly_helper import (
    NodePromptAssemblyHelper,
)
from airunner_services.llm.managers.mixins.node_forced_response_helper import (
    NodeForcedResponseHelper,
)
from airunner_services.llm.managers.mixins.node_routing_debug_helper import (
    NodeRoutingDebugHelper,
)
from airunner_services.llm.managers.mixins.node_streaming_response_helper import (
    NodeStreamingResponseHelper,
)
from airunner_services.llm.managers.route_policy import RoutePolicy

if TYPE_CHECKING:
    from airunner_services.llm.workflow_manager import WorkflowState


class NodeFunctionsMixin:
    """Implements LangGraph node functions for the workflow."""

    WORKFLOW_TOOLS = {
        "start_workflow",
        "transition_phase",
        "add_todo_item",
        "start_todo_item",
        "complete_todo_item",
        "get_workflow_status",
    }

    def _get_route_policy(self) -> RoutePolicy:
        """Return the cached route-policy helper."""
        helper = getattr(self, "_route_policy_helper", None)
        if helper is None:
            helper = RoutePolicy(self)
            self._route_policy_helper = helper
        return helper

    def _get_response_synthesizer(self) -> ResponseSynthesizer:
        """Return the cached response-synthesis helper."""
        helper = getattr(self, "_response_synthesizer", None)
        if helper is None:
            helper = ResponseSynthesizer(self)
            self._response_synthesizer = helper
        return helper

    def _get_response_generation_helper(self) -> NodeResponseGenerationHelper:
        """Return the cached response-generation helper."""
        helper = getattr(self, "_response_generation_helper", None)
        if helper is None:
            helper = NodeResponseGenerationHelper(self)
            self._response_generation_helper = helper
        return helper

    def _get_streaming_response_helper(self) -> NodeStreamingResponseHelper:
        """Return the cached streaming-response helper."""
        helper = getattr(self, "_streaming_response_helper", None)
        if helper is None:
            helper = NodeStreamingResponseHelper(self)
            self._streaming_response_helper = helper
        return helper

    def _get_prompt_assembly_helper(self) -> NodePromptAssemblyHelper:
        """Return the cached prompt-assembly helper."""
        helper = getattr(self, "_prompt_assembly_helper", None)
        if helper is None:
            helper = NodePromptAssemblyHelper(self)
            self._prompt_assembly_helper = helper
        return helper

    def _get_post_tool_instructions_helper(
        self,
    ) -> NodePostToolInstructionsHelper:
        """Return the cached post-tool instruction helper."""
        helper = getattr(self, "_post_tool_instructions_helper", None)
        if helper is None:
            helper = NodePostToolInstructionsHelper(self)
            self._post_tool_instructions_helper = helper
        return helper

    def _get_forced_response_helper(self) -> NodeForcedResponseHelper:
        """Return the cached forced-response helper."""
        helper = getattr(self, "_forced_response_helper", None)
        if helper is None:
            helper = NodeForcedResponseHelper(self)
            self._forced_response_helper = helper
        return helper

    def _get_routing_debug_helper(self) -> NodeRoutingDebugHelper:
        """Return the cached routing-debug helper."""
        helper = getattr(self, "_routing_debug_helper", None)
        if helper is None:
            helper = NodeRoutingDebugHelper(self)
            self._routing_debug_helper = helper
        return helper

    def _force_response_node(self, state: "WorkflowState") -> Dict[str, Any]:
        """Generate one forced response when redundancy is detected."""
        return self._get_forced_response_helper().force_response_node(state)

    def _has_tool_calls(self, message: BaseMessage) -> bool:
        """Return whether one message contains tool calls."""
        return self._get_forced_response_helper().has_tool_calls(message)

    def _get_tool_messages(self, messages: List[BaseMessage]) -> List[Any]:
        """Return the tool messages from one message list."""
        return self._get_forced_response_helper().get_tool_messages(messages)

    def _should_return_tool_direct(self, tool_name: str) -> bool:
        """Return whether one bound tool should bypass the model pass."""
        return self._get_forced_response_helper().should_return_tool_direct(tool_name)

    def _stream_model_response(
        self,
        prompt: List[BaseMessage],
        generation_kwargs: Optional[Dict] = None,
    ) -> str:
        """Stream one model response and preserve response metadata."""
        return self._get_response_generation_helper().stream_model_response(
            prompt,
            generation_kwargs,
        )

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
        return self._get_route_policy().after_model(state)

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
        return self._get_route_policy().after_tools(state)

    def _log_routing_debug(
        self, last_message: BaseMessage, messages: List[BaseMessage]
    ):
        """Log routing debug information for one workflow turn."""
        self._get_routing_debug_helper().log_routing_debug(last_message, messages)

    def _is_duplicate_tool_call(
        self, last_message: BaseMessage, messages: List[BaseMessage]
    ) -> bool:
        """Return whether the latest tool call duplicates a recent one."""
        return self._get_routing_debug_helper().is_duplicate_tool_call(
            last_message,
            messages,
        )

    def _log_tool_call_info(
        self, last_message: BaseMessage, messages: List[BaseMessage]
    ):
        """Log the requested tool calls and previous tool result preview."""
        self._get_routing_debug_helper().log_tool_call_info(
            last_message,
            messages,
        )

    def _call_model(self, state: "WorkflowState") -> Dict[str, Any]:
        """Call the model with trimmed message history."""
        return self._get_prompt_assembly_helper().call_model(state)
