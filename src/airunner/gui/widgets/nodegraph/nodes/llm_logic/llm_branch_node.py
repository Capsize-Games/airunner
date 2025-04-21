import time
from typing import Dict, Optional

from NodeGraphQt.constants import NodePropWidgetEnum

from airunner.enums import LLMActionType, SignalCode
from airunner.gui.widgets.nodegraph.nodes.base_workflow_node import (
    BaseWorkflowNode,
)
from airunner.handlers.llm.llm_request import LLMRequest
from airunner.handlers.llm.llm_response import LLMResponse


class LLMBranchNode(BaseWorkflowNode):
    """
    A node that evaluates a logical condition using an LLM and routes execution flow
    based on whether the condition is true or false.

    This node uses an LLM to evaluate a text condition and then triggers either
    the TRUE or FALSE output execution port.
    """

    NODE_NAME = "Branch"
    __identifier__ = "airunner.workflow.nodes.LLMBranchNode"
    type_ = "airunner.workflow.nodes.LLMBranchNode"

    EXEC_TRUE_PORT_NAME = "True"  # Internal name
    EXEC_FALSE_PORT_NAME = "False"  # Internal name

    has_exec_out_port = False

    def __init__(self):
        self.signal_handlers = {
            SignalCode.LLM_TEXT_STREAMED_SIGNAL: self._on_llm_text_streamed,
        }
        super().__init__()

        self.model._graph_item = self
        self.add_input("condition", display_name=True)
        self.add_input("llm_request", display_name=True)
        self.add_input("llm_prompt", display_name=True)
        self.add_output(
            self.EXEC_TRUE_PORT_NAME,  # Internal name used for code reference
            multi_output=False,  # Only one connection allowed
            display_name=True,  # Show the name
            painter_func=self._draw_exec_port,  # Use execution port style
        )
        self.add_output(
            name=self.EXEC_FALSE_PORT_NAME,  # Internal name used for code reference
            multi_output=False,  # Only one connection allowed
            display_name=True,  # Show the name
            painter_func=self._draw_exec_port,  # Use execution port style
        )

        # State variables for async LLM evaluation
        self._current_response = None
        self._accumulated_response_text = ""
        self._condition_result = None
        self._execution_pending = False

        self.create_property(
            "condition",
            value="Check if the following is true: the sky is blue.",
            widget_type=NodePropWidgetEnum.QTEXT_EDIT.value,
            tab="condition",
        )

        self.create_property(
            "system_prompt",
            value="You are a logical assistant. Your task is to evaluate a condition and respond ONLY with 'TRUE' or 'FALSE'. Nothing else.",
            widget_type=NodePropWidgetEnum.QTEXT_EDIT.value,
            tab="settings",
        )

        self.create_property(
            "model_type",
            value="Local Model",
            items=["Local Model", "OpenAI", "Anthropic", "OpenRouter"],
            widget_type=NodePropWidgetEnum.QCOMBO_BOX.value,
            tab="settings",
        )

        self.create_property(
            "model_name",
            value="",
            widget_type=NodePropWidgetEnum.QLINE_EDIT.value,
            tab="settings",
        )

        self.create_property(
            "use_mock",
            value=False,
            widget_type=NodePropWidgetEnum.QCHECK_BOX.value,
            tab="settings",
        )

        self.create_property(
            "timeout_seconds",
            value=5,
            widget_type=NodePropWidgetEnum.INT.value,
            tab="settings",
        )

    # Ensure this node's properties are shown when it's selected
    def on_selected(self):
        """Called when the node is selected."""
        super().on_selected()
        self.graph.property_bin().set_node(self)

    def execute(self, input_data: Dict):
        """
        Execute the node to evaluate a condition using an LLM and route execution flow.

        Args:
            input_data: Dictionary containing input values, including a condition and LLMRequest.

        Returns:
            dict: A dictionary with the _exec_triggered key pointing to either TRUE or FALSE output.
        """
        # Reset state for this execution
        self._accumulated_response_text = ""
        self._current_response = None
        self._condition_result = None
        self._execution_pending = True

        llm_prompt = self._get_value(input_data, "llm_prompt", str)
        if llm_prompt:
            # If llm_prompt is provided, use it as the system prompt
            self.set_property("condition", llm_prompt)

        # Get the condition from input or use property
        condition = self._get_value(input_data, "condition", str)

        # Get the LLMRequest from input or create a default one
        llm_request = input_data.get("llm_request", LLMRequest())

        # Ensure we have a valid LLMRequest object
        if not isinstance(llm_request, LLMRequest):
            llm_request = LLMRequest()

        # Add our node ID to the request
        llm_request.node_id = self.id

        # Get settings
        model_type = self.get_property("model_type")
        model_name = self.get_property("model_name")
        system_prompt = self.get_property("system_prompt")
        use_mock = self.get_property("use_mock")
        timeout = self.get_property("timeout_seconds")

        if use_mock:
            # Generate a mock response for testing (synchronous)
            result = self._generate_mock_condition_result(condition)
            return {
                "_exec_triggered": (
                    self.EXEC_TRUE_PORT_NAME
                    if result
                    else self.EXEC_FALSE_PORT_NAME
                )
            }
        else:
            # Start the LLM call to evaluate the condition
            self._call_llm_for_condition(
                condition, system_prompt, llm_request, model_type, model_name
            )

            # Wait for the result with a timeout
            start_time = time.time()
            while (
                self._condition_result is None
                and time.time() - start_time < timeout
            ):
                time.sleep(0.1)  # Small wait to avoid tight loop

            # If we got a result, return it; otherwise default to FALSE
            if self._condition_result is not None:
                return {
                    "_exec_triggered": (
                        self.EXEC_TRUE_PORT_NAME
                        if self._condition_result
                        else self.EXEC_FALSE_PORT_NAME
                    )
                }
            else:
                print(
                    f"LLM condition evaluation timed out after {timeout} seconds. Defaulting to FALSE."
                )
                return {"_exec_triggered": self.EXEC_FALSE_PORT_NAME}

    def _generate_mock_condition_result(self, condition: str) -> bool:
        """
        Generate a mock result for testing purposes.

        This simple implementation just checks if the string contains "true" or "false".
        In a real application, you might want a more sophisticated mock.

        Args:
            condition: The condition string to evaluate.

        Returns:
            bool: The mock evaluation result.
        """
        condition_lower = condition.lower()

        # Very basic heuristic for demo purposes
        contains_true = "true" in condition_lower
        contains_false = "false" in condition_lower

        # If it has both "true" and "false", the outcome depends on which comes last
        if contains_true and contains_false:
            last_true_pos = condition_lower.rfind("true")
            last_false_pos = condition_lower.rfind("false")
            return last_true_pos > last_false_pos

        # Otherwise return based on just containing "true"
        return contains_true

    def _call_llm_for_condition(
        self,
        condition: str,
        system_prompt: str,
        llm_request: LLMRequest,
        model_type: str,
        model_name: str,
    ):
        """
        Call the LLM to evaluate the condition.

        Args:
            condition: The condition to evaluate.
            system_prompt: The system prompt to guide the LLM.
            llm_request: The LLMRequest object with generation parameters.
            model_type: Type of model to use.
            model_name: Name or path of the model.
        """
        try:
            # Prepare a clear prompt that will yield a TRUE/FALSE response
            prompt = f"""Please evaluate the following condition and respond ONLY with either "TRUE" or "FALSE" (all caps). 

No other text, no explanation:

CONDITION: {condition}"""

            self.emit_signal(
                SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL,
                {
                    "llm_request": True,
                    "node_id": self.id,  # Include node ID for routing response
                    "request_data": {
                        "action": LLMActionType.CHAT,
                        "prompt": prompt,
                        "system_prompt": system_prompt,
                        "model_type": model_type,
                        "model_name": model_name,
                        "llm_request": llm_request,
                    },
                },
            )
        except Exception as e:
            print(
                f"Error emitting LLM request signal for condition evaluation in node {self.id}: {e}"
            )
            # Default to FALSE on error
            self._condition_result = False
            self._execution_pending = False

    def _on_llm_text_streamed(self, data: Dict):
        """
        Handle the streamed text from the LLM response.

        Args:
            data: Dictionary containing the LLM response.
        """
        llm_response: Optional[LLMResponse] = data.get("response", None)

        if not llm_response or llm_response.node_id != self.id:
            return

        # Reset accumulator if this is the first message chunk
        if llm_response.is_first_message:
            self._accumulated_response_text = ""

        # Append the new message chunk to the accumulator
        self._accumulated_response_text += llm_response.message

        # Store the latest response object
        self._current_response = llm_response

        # If this is the end of the message, evaluate the result
        if llm_response.is_end_of_message:
            self._evaluate_condition_result()
            self._execution_pending = False

    def _evaluate_condition_result(self):
        """
        Evaluate the final text to determine if the condition is TRUE or FALSE.
        """
        if not self._accumulated_response_text:
            self._condition_result = False
            return

        # Normalize the response text and check for TRUE
        normalized_response = self._accumulated_response_text.strip().upper()

        # Check if the response is TRUE
        is_true = (
            "TRUE" in normalized_response
            and "FALSE" not in normalized_response
        )

        # Set the condition result
        self._condition_result = is_true

        print(
            f"Condition evaluated as: {self._condition_result} based on response: '{self._accumulated_response_text}'"
        )

    def _get_value(self, input_data, name, expected_type):
        """
        Get a value from input data or fall back to the node property.

        Args:
            input_data: Dictionary containing input values.
            name: Name of the parameter.
            expected_type: Type to convert the value to.

        Returns:
            The value converted to the expected type.
        """
        if name in input_data and input_data[name] is not None:
            value = input_data[name]
            if expected_type == bool:
                return bool(value)
            elif expected_type == int:
                return int(value)
            elif expected_type == float:
                return float(value)
            return value
        else:
            # Get from node property
            value = self.get_property(name)
            if expected_type == bool:
                return bool(value)
            elif expected_type == int:
                return int(value)
            elif expected_type == float:
                return float(value)
            return value
