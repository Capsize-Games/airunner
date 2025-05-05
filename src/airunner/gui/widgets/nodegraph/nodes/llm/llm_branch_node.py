import time
from typing import Dict, Optional

from NodeGraphQt.constants import NodePropWidgetEnum

from airunner.enums import LLMActionType, SignalCode
from airunner.gui.widgets.nodegraph.nodes.llm.base_llm_node import (
    BaseLLMNode,
)
from airunner.handlers.llm.llm_request import LLMRequest
from airunner.handlers.llm.llm_response import LLMResponse


class LLMBranchNode(BaseLLMNode):
    """
    A node that evaluates a logical condition using an LLM and routes execution flow
    based on whether the condition is true or false.

    This node uses an LLM to evaluate a text condition and then triggers either
    the TRUE or FALSE output execution port.
    """

    NODE_NAME = "Branch"
    EXEC_TRUE_PORT_NAME = "True"  # Internal name
    EXEC_FALSE_PORT_NAME = "False"  # Internal name
    has_exec_out_port = False
    has_exec_in_port = True
    _input_ports = [
        dict(name="condition", display_name="Condition"),
        dict(name="llm_request", display_name="LLM Request"),
        dict(name="llm_prompt", display_name="LLM Prompt"),
    ]
    _output_ports = [
        dict(name=EXEC_TRUE_PORT_NAME, display_name="True"),
        dict(name=EXEC_FALSE_PORT_NAME, display_name="False"),
    ]
    _properties = [
        dict(
            name="condition",
            value="Check if the following is true: the sky is blue.",
            widget_type=NodePropWidgetEnum.QTEXT_EDIT,
            tab="condition",
        ),
        dict(
            name="system_prompt",
            value="You are a logical assistant. Your task is to evaluate a condition and respond ONLY with 'TRUE' or 'FALSE'. Nothing else.",
            widget_type=NodePropWidgetEnum.QTEXT_EDIT,
            tab="settings",
        ),
        dict(
            name="model_type",
            value="Local Model",
            items=["Local Model", "OpenAI", "Anthropic", "OpenRouter"],
            widget_type=NodePropWidgetEnum.QCOMBO_BOX,
            tab="settings",
        ),
        dict(
            name="model_name",
            value="",
            widget_type=NodePropWidgetEnum.QLINE_EDIT,
            tab="settings",
        ),
        dict(
            name="use_mock",
            value=False,
            widget_type=NodePropWidgetEnum.QCHECK_BOX,
            tab="settings",
        ),
        dict(
            name="timeout_seconds",
            value=5,
            widget_type=NodePropWidgetEnum.INT,
            tab="settings",
        ),
    ]

    def __init__(self):
        self.signal_handlers = {
            SignalCode.LLM_TEXT_STREAMED_SIGNAL: self._on_llm_text_streamed,
        }
        super().__init__()
        self.model._graph_item = self
        self._current_response = None
        self._accumulated_response_text = ""
        self._condition_result = None
        self._execution_pending = False
        self._waiting_for_llm = False
        self._exec_data = {}

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
            dict: A dictionary with data outputs, but no execution flow triggering.
                  The execution flow will be triggered by signals when the LLM evaluation completes.
        """
        # Reset state for this execution
        self._accumulated_response_text = ""
        self._current_response = None
        self._condition_result = None

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
            # Immediately emit the completion signal
            self.api.nodegraph.node_executed(
                node_id=self.id,
                result=(
                    self.EXEC_TRUE_PORT_NAME
                    if result
                    else self.EXEC_FALSE_PORT_NAME
                ),
                data={"condition": condition, "result": result},
            )
        else:
            print(f"Starting LLM evaluation for condition: {condition}")

            # Store execution data for later use when the response comes back
            self._exec_data = {
                "condition": condition,
                "timeout": timeout,
                "start_time": time.time(),
            }

            # Start the LLM call to evaluate the condition
            self._call_llm_for_condition(
                condition, system_prompt, llm_request, model_type, model_name
            )

            # Start timeout timer
            self._start_timeout_timer(timeout)

        # Return empty dict - execution will continue via signals instead of return value
        return {}

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
            prompt = f"""Evaluate the following condition and respond ONLY with either "TRUE" or "FALSE" (all caps). 

No other text, no explanation:

CONDITION: {condition}"""

            self.api.llm.send_request(
                prompt=prompt,
                llm_request=llm_request,
                action=LLMActionType.CHAT,
                do_tts_reply=False,
                node_id=self.id,
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
        if type(llm_response.message) is str:
            self._accumulated_response_text += llm_response.message

        # Store the latest response object
        self._current_response = llm_response

        # If this is the end of the message, evaluate the result
        if llm_response.is_end_of_message:
            print("End of LLM message received")
            self._evaluate_condition_result()
            self._waiting_for_llm = False  # Mark that we're done waiting
            self._execution_pending = False

            # Trigger the next execution step
            self._trigger_next_execution()

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

    def _trigger_next_execution(self):
        """
        Trigger the next execution step based on the condition result.
        """
        # Get execution data
        condition = self._exec_data.get("condition")
        timeout = self._exec_data.get("timeout")
        start_time = self._exec_data.get("start_time")

        # Check if we have no more execution data (already processed)
        if not self._exec_data:
            return

        current_time = time.time()
        elapsed_time = current_time - start_time if start_time else 0

        print(f"Condition evaluated in {elapsed_time:.2f} seconds")

        # Check if we got a result
        if self._condition_result is not None:
            # We have a result, determine the appropriate execution path name
            output_port_name = (
                self.EXEC_TRUE_PORT_NAME
                if self._condition_result
                else self.EXEC_FALSE_PORT_NAME
            )
            self._exec_data = {}  # Clear execution data

            # Emit signal indicating completion and which port to trigger next
            self.api.nodegraph.node_executed(
                node_id=self.id, result=output_port_name
            )

        elif elapsed_time >= timeout:
            # We timed out, default to FALSE
            print(
                f"LLM condition evaluation timed out after {timeout} seconds. Defaulting to FALSE."
            )
            self._exec_data = {}  # Clear execution data

            # Emit signal indicating completion and trigger the FALSE port
            self.api.nodegraph.node_executed(
                node_id=self.id,
                result=self.EXEC_FALSE_PORT_NAME,
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

    def _start_timeout_timer(self, timeout_seconds):
        """
        Start a timer to handle the LLM timeout.
        After the specified timeout period, if no response was received,
        the execution will default to the FALSE path.

        Args:
            timeout_seconds: Number of seconds to wait before timing out
        """
        # Import QTimer here to avoid making the entire file dependent on Qt
        from PySide6.QtCore import QTimer

        if not hasattr(self, "_timeout_timer"):
            self._timeout_timer = QTimer()
            self._timeout_timer.setSingleShot(True)
            self._timeout_timer.timeout.connect(self._on_timeout)

        # Ensure any previous timer is stopped
        self._timeout_timer.stop()

        # Start the timer with the specified timeout in milliseconds
        self._timeout_timer.start(timeout_seconds * 1000)
        print(f"Started timeout timer for {timeout_seconds} seconds")

    def _on_timeout(self):
        """Handle timeout when LLM doesn't respond in time"""
        # Only handle the timeout if we're still waiting for the LLM
        if self._exec_data and not self._condition_result:
            print("LLM evaluation timed out")

            # Default to FALSE on timeout
            self._condition_result = False
            self._waiting_for_llm = False
            self._execution_pending = False

            # Emit signal to continue execution with FALSE path
            self.api.nodegraph.node_executed(
                node_id=self.id,
                result=self.EXEC_FALSE_PORT_NAME,
            )

            # Clear execution data
            self._exec_data = {}
