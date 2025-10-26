"""LLM Call Node for LangGraph workflows.

This node makes LLM calls within a LangGraph workflow.
"""

from typing import List
from airunner.vendor.nodegraphqt.constants import NodePropWidgetEnum
from airunner.components.nodegraph.gui.widgets.nodes.langgraph.base_langgraph_node import (
    BaseLangGraphNode,
)


class LLMCallNode(BaseLangGraphNode):
    """Call an LLM within a LangGraph workflow.

    This node takes messages from state, calls an LLM,
    and stores the response back in state.
    """

    NODE_NAME = "LLM Call"
    state_key = "messages"

    _input_ports = [
        dict(name="prompt", display_name="Prompt"),
        dict(name="system_prompt", display_name="System Prompt"),
    ]

    _output_ports = [
        dict(name="response", display_name="Response"),
    ]

    _properties = [
        dict(
            name="model",
            value="gpt-4",
            widget_type=NodePropWidgetEnum.QLINE_EDIT,
            tab="model",
        ),
        dict(
            name="temperature",
            value=0.7,
            widget_type=NodePropWidgetEnum.QDOUBLESPIN_BOX,
            range=(0.0, 2.0),
            tab="parameters",
        ),
        dict(
            name="max_tokens",
            value=1000,
            widget_type=NodePropWidgetEnum.QSPIN_BOX,
            range=(1, 4096),
            tab="parameters",
        ),
        dict(
            name="system_prompt",
            value="You are a helpful assistant.",
            widget_type=NodePropWidgetEnum.QTEXT_EDIT,
            tab="prompts",
        ),
        dict(
            name="message_key",
            value="messages",
            widget_type=NodePropWidgetEnum.QLINE_EDIT,
            tab="state",
        ),
        dict(
            name="response_key",
            value="response",
            widget_type=NodePropWidgetEnum.QLINE_EDIT,
            tab="state",
        ),
    ]

    def get_node_type(self) -> str:
        """Get node type identifier."""
        return "llm"

    def get_description(self) -> str:
        """Get node description."""
        model = self.get_property("model")
        return f"Call LLM ({model})"

    def to_langgraph_code(self) -> str:
        """Generate Python code for LLM call.

        Returns:
            Python code string
        """
        model = self.get_property("model")
        temperature = self.get_property("temperature")
        max_tokens = self.get_property("max_tokens")
        system_prompt = self.get_property("system_prompt")
        message_key = self.get_property("message_key")
        response_key = self.get_property("response_key")

        func_name = self._sanitize_name(self.name())

        code = f'''def {func_name}(state: AgentState) -> AgentState:
    """{self.get_description()}"""
    from langchain_anthropic import ChatAnthropic
    
    llm = ChatAnthropic(
        model="{model}",
        temperature={temperature},
        max_tokens={max_tokens},
    )
    
    # Get messages from state
    messages = state.get("{message_key}", [])
    if not messages:
        logger.warning("No messages in state")
        return state
    
    # Prepare prompt
    user_message = messages[-1] if isinstance(messages, list) else messages
    full_prompt = f"{system_prompt}\\n\\nUser: {{user_message}}"
    
    # Call LLM
    try:
        response = llm.invoke(full_prompt)
        state["{response_key}"] = str(response.content)
        state["{message_key}"].append(str(response.content))
        logger.info("LLM call completed")
    except Exception as e:
        logger.error(f"LLM call error: {{e}}")
        state["error"] = str(e)
    
    return state'''

        return code

    def get_input_state_keys(self) -> List[str]:
        """Get state keys this node reads from."""
        return [self.get_property("message_key")]

    def get_output_state_keys(self) -> List[str]:
        """Get state keys this node writes to."""
        return [
            self.get_property("message_key"),
            self.get_property("response_key"),
        ]

    @staticmethod
    def _sanitize_name(name: str) -> str:
        """Sanitize node name to valid Python identifier."""
        sanitized = "".join(
            c if c.isalnum() or c == "_" else "_" for c in name
        )
        if sanitized and sanitized[0].isdigit():
            sanitized = f"node_{sanitized}"
        return sanitized or "llm_node"
