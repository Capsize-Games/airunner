"""
Phase Execution Mixin - Handles phase execution loops with tool calls.

This mixin provides phase execution functionality for the Deep Research Agent:
- Phase execution loops
- Tool call retry logic
- Tool requirement extraction
"""

from typing import Any, Dict, List
from langchain_core.messages import HumanMessage
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


class PhaseExecutionMixin:
    """Mixin for phase execution with tool loops in Deep Research Agent."""

    def _extract_required_tools(self, task_prompt: str) -> List[str]:
        """Infer which tools the task prompt explicitly asked the model to call."""
        if not task_prompt:
            return []

        task_lower = task_prompt.lower()
        available_names = [
            tool.name
            for tool in self._tools
            if hasattr(tool, "name") and tool.name
        ]

        required = [
            name
            for name in available_names
            if any(
                pattern in task_lower
                for pattern in [
                    f"call {name.lower()}",
                    f"{name.lower()}(",
                    f"{name.lower()}:",
                ]
            )
        ]

        return list(dict.fromkeys(required))

    def _build_tool_retry_prompt(
        self, topic: str, required_tools: List[str]
    ) -> str:
        """Construct a direct instruction reminding the model to emit a tool call."""
        tool_hint = (
            "Call one of these tools immediately: " + ", ".join(required_tools)
            if required_tools
            else "Call one of the allowed tools provided in the system instructions."
        )

        topic_hint = (
            f"Use the exact research topic: {topic}."
            if topic
            else "Use the exact topic from the task prompt."
        )

        return (
            "You failed to call a tool. Respond NOW with a single JSON object.\n"
            '{"tool": "tool_name", "arguments": { ... }}\n'
            f"{tool_hint}\n"
            f"{topic_hint}\n"
            "Do not write prose or mention any other subject."
        )

    def _handle_missing_tool_calls(
        self,
        phase_name: str,
        iterations: int,
        topic: str,
        required_tools: List[str],
        messages: list,
    ) -> bool:
        """Handle case where model didn't return tool calls.

        Returns:
            True if should retry, False if should break
        """
        if iterations >= 5:
            logger.warning(
                f"[{phase_name}] No tool calls after {iterations} attempts"
            )
            return False

        logger.warning(
            f"[{phase_name}] Model response lacked tool calls (attempt {iterations}); "
            "reinforcing instructions"
        )
        retry_prompt = self._build_tool_retry_prompt(
            topic=topic, required_tools=required_tools
        )
        messages.append(HumanMessage(content=retry_prompt))
        return True

    def _execute_tool_calls_iteration(
        self,
        response: Any,
        phase_name: str,
        state: dict,
        state_updates: dict,
        messages: list,
        iterations: int,
    ) -> None:
        """Execute all tool calls from model response."""
        logger.info(
            f"[{phase_name}] Iteration {iterations}: "
            f"Executing {len(response.tool_calls)} tool call(s)"
        )

        tool_results = [
            self._execute_single_tool(
                tool_call, phase_name, state, state_updates
            )
            for tool_call in response.tool_calls
        ]
        messages.extend(tool_results)

    def _execute_phase_with_tools(
        self,
        phase_name: str,
        task_prompt: str,
        state: dict,
        max_tool_calls: int = 5,
    ) -> dict:
        """Execute a phase by calling the model and handling tool calls internally."""
        self._emit_progress(phase_name, "Starting phase execution")

        state_updates: Dict[str, Any] = {}
        required_tools = self._extract_required_tools(task_prompt)
        topic = state.get("research_topic", "")
        messages = self._initialize_phase_messages(topic)
        iterations = 0

        while iterations < max_tool_calls:
            iterations += 1

            response = self._invoke_model_with_tools(
                phase_name, task_prompt, messages, iterations
            )
            messages.append(response)

            if not hasattr(response, "tool_calls") or not response.tool_calls:
                if not self._handle_missing_tool_calls(
                    phase_name, iterations, topic, required_tools, messages
                ):
                    break
                continue

            self._execute_tool_calls_iteration(
                response,
                phase_name,
                state,
                state_updates,
                messages,
                iterations,
            )

        if iterations >= max_tool_calls:
            logger.warning(
                f"[{phase_name}] Reached max tool call limit ({max_tool_calls})"
            )

        self._emit_progress(
            phase_name, f"Completed after {iterations} iteration(s)"
        )

        return {"messages": messages, "state_updates": state_updates}
