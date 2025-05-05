import time
from typing import Dict, Optional

from NodeGraphQt.constants import NodePropWidgetEnum

from airunner.enums import LLMActionType, SignalCode
from airunner.gui.widgets.nodegraph.nodes.llm.base_llm_node import (
    BaseLLMNode,
)
from airunner.handlers.llm.llm_request import LLMRequest
from airunner.handlers.llm.llm_response import LLMResponse


class RunLLMNode(BaseLLMNode):
    """
    A node that executes an LLMRequest and returns an LLMResponse.

    This node takes an LLMRequest as input, executes it against a language model,
    and returns the resulting LLMResponse.
    """

    NODE_NAME = "Run LLM"
    _input_ports = [
        dict(name="llm_request", display_name="LLM Request"),
        dict(name="prompt", display_name="Prompt"),
    ]
    _output_ports = [
        dict(name="llm_response", display_name="LLM Response"),
        dict(name="llm_message", display_name="LLM Message"),
    ]

    def __init__(self):
        self.signal_handlers = {
            SignalCode.LLM_TEXT_STREAMED_SIGNAL: self._on_llm_text_streamed,
        }
        super().__init__()
        self._accumulated_response_text = ""
        self._current_llm_response = None

        # Add settings for LLM execution
        self.add_combo_menu(
            name="model_type",
            label="Model Type",
            items=["Local Model", "OpenAI", "Anthropic", "OpenRouter"],
            tooltip="Select which model provider to use",
            tab="settings",
        )

        self.add_text_input(
            name="model_name",
            label="Model Name",
            text="",
            placeholder_text="Model name or path",
            tooltip="Name or path of the model to use",
            tab="settings",
        )

        self.add_text_input(
            name="system_prompt",
            label="System Prompt",
            text="You are a helpful assistant.",
            placeholder_text="Enter system prompt here",
            tooltip="System prompt to provide context for the model",
            tab="settings",
        )

        self.add_checkbox(
            name="use_mock",
            label="Mock Mode",
            text="Use mock generation (for testing)",
            state=False,
            tooltip="Generate mock responses instead of calling the model",
            tab="settings",
        )

        self.create_property(
            "prompt",
            "",
            widget_type=NodePropWidgetEnum.QLINE_EDIT.value,
            tab="basic",
        )

    def execute(self, input_data: Dict):
        """
        Execute the node to process an LLMRequest and return an LLMResponse.

        Args:
            input_data: Dictionary containing input values, including an LLMRequest.

        Returns:
            dict: A dictionary with the key 'llm_response' containing an LLMResponse.
        """
        # Reset accumulator and response state for this execution
        self._accumulated_response_text = ""
        self._current_llm_response = None

        # Get the LLMRequest from input or create a default one
        llm_request = input_data.get("llm_request", LLMRequest())

        # Ensure we have a valid LLMRequest object
        if not isinstance(llm_request, LLMRequest):
            llm_request = LLMRequest()

        # Get the prompt text if provided
        prompt = input_data.get("prompt", self.get_property("prompt"))

        # Get settings
        model_type = self.get_property("model_type")
        model_name = self.get_property("model_name")
        system_prompt = self.get_property("system_prompt")
        self._call_llm(
            prompt, system_prompt, llm_request, model_type, model_name
        )
        return None

    def _generate_mock_response(
        self, prompt: str, llm_request: LLMRequest
    ) -> LLMResponse:
        """
        Generate a mock LLM response for testing purposes.

        Args:
            prompt: The input prompt text.
            llm_request: The LLMRequest object.

        Returns:
            LLMResponse: A mock response.
        """
        start_time = time.time()

        # Simple mock response that echoes the prompt and settings
        response_text = (
            f"MOCK RESPONSE\n\n"
            f"I received your prompt: '{prompt}'\n\n"
            f"Using settings:\n"
            f"- Temperature: {llm_request.temperature}\n"
            f"- Max tokens: {llm_request.max_new_tokens}\n"
            f"- Top p: {llm_request.top_p}\n\n"
            f"This is a simulated response for testing purposes."
        )

        # Create a mock response
        mock_response = LLMResponse(
            text=response_text,
            tokens_generated=len(response_text.split()),
            tokens_processed=len(prompt.split()),
            total_time=time.time() - start_time,
            metadata={"mock": True},
        )
        # Simulate the streaming completion for mock
        self._current_llm_response = mock_response
        return mock_response

    def _call_llm(
        self,
        prompt: str,
        system_prompt: str,
        llm_request: LLMRequest,
        model_type: str,
        model_name: str,
    ):  # Removed -> LLMResponse return type hint
        """
        Call the LLM with the given request parameters.

        Args:
            prompt: The input prompt text.
            system_prompt: The system context prompt.
            llm_request: The LLMRequest object.
            model_type: Type of model to use (Local, OpenAI, etc.)
            model_name: Name or path of the model.
        """
        try:
            llm_request.node_id = self.id
            print("CALLING LLM TEXT GENERATE REQUEST SIGNAL WITH ", prompt)
            self.api.llm.send_request(
                prompt=prompt,
                llm_request=llm_request,
                action=LLMActionType.CHAT,
                do_tts_reply=True,
                node_id=self.id,
            )
        except Exception as e:
            print(f"Error emitting LLM request signal for node {self.id}: {e}")
            error_response = LLMResponse(
                text=f"Error starting LLM call: {str(e)}",
                metadata={"error": str(e)},
            )
            self._current_llm_response = error_response
            self._accumulated_response_text = error_response.message

    def _on_llm_text_streamed(self, data: Dict):
        llm_response: Optional[LLMResponse] = data.get("response", None)

        if not llm_response or llm_response.node_id != self.id:
            return

        # Reset accumulator if this is the first message chunk
        if llm_response.is_first_message:
            self._accumulated_response_text = ""

        # Append the new message chunk to the accumulator
        self._accumulated_response_text += llm_response.message

        # Store the latest response object (might be useful for metadata)
        self._current_llm_response = llm_response

        # Propagate the *accumulated* text to connected output ports
        self._propagate_outputs_to_downstream_nodes()

        # If this is the end of the message, maybe log or finalize something
        if llm_response.is_end_of_message:
            # Optionally, you could store the final complete response object if needed
            # self._final_complete_response = llm_response # If LLMResponse structure supports final state
            self.api.nodegraph.node_executed(
                node_id=self.id,
                result=self.output_ports()[0].name(),
                data={
                    "llm_response": llm_response,
                    "llm_message": self._accumulated_response_text,
                },
            )

    def _propagate_outputs_to_downstream_nodes(self):
        """
        Propagate current outputs to all connected downstream nodes.
        This is called when an asynchronous response is received to update downstream nodes.
        """
        if not self._current_llm_response:
            return

        # Get the output data that would be returned by execute()
        output_data = {
            "llm_response": self._current_llm_response,
            "llm_message": self._accumulated_response_text,
        }

        # For each output port, find all connected ports and update their nodes
        for port_name, output_port in self.outputs().items():
            if port_name not in output_data:
                continue

            # Get the data for this port
            port_data = output_data[port_name]

            # For each connected port, update its node with our data
            for connected_port in output_port.connected_ports():
                downstream_node = connected_port.node()
                downstream_port_name = connected_port.name()

                # If the downstream node has a 'set_property' method, use it.
                # This is the primary way to update nodes like TextboxNode.
                if hasattr(downstream_node, "set_property"):
                    # Check if the port name matches what TextboxNode expects (e.g., 'prompt')
                    # or if the downstream node can handle the specific port_name directly.
                    # Assuming TextboxNode's input is 'prompt' and we connect 'llm_message' to it.
                    if port_name == "llm_message":
                        # Use the name of the *connected input port* on the downstream node
                        downstream_node.set_property(
                            downstream_port_name, port_data
                        )
                        print(
                            f"Updated {downstream_node.name()} property '{downstream_port_name}' via set_property"
                        )
                    # Handle other potential output ports if necessary
                    elif port_name == "llm_response":
                        # Example: Propagate the full response object if needed
                        # downstream_node.set_property(downstream_port_name, port_data)
                        pass  # Adjust as needed for llm_response propagation
