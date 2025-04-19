import time
from typing import Dict, Optional

from airunner.enums import LLMActionType, SignalCode
from airunner.gui.widgets.nodegraph.nodes.base_workflow_node import (
    BaseWorkflowNode,
)
from airunner.handlers.llm.llm_request import LLMRequest
from airunner.handlers.llm.llm_response import LLMResponse


class RunLLMNode(BaseWorkflowNode):
    """
    A node that executes an LLMRequest and returns an LLMResponse.

    This node takes an LLMRequest as input, executes it against a language model,
    and returns the resulting LLMResponse.
    """

    NODE_NAME = "Run LLM"

    def __init__(self):
        self.signal_handlers = {
            SignalCode.LLM_TEXT_STREAMED_SIGNAL: self._on_llm_text_streamed,
        }
        super().__init__()
        self._accumulated_response_text = ""  # Add accumulator for text
        self._current_llm_response = None  # Store the final response object

        # Input port for the LLMRequest
        self.add_input("llm_request", display_name=True)
        self.add_input("prompt", display_name=True)

        # Output port for the LLMResponse
        self.llm_response_port = self.add_output("llm_response")
        self.llm_message_port = self.add_output("llm_message")

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
        prompt = input_data.get("prompt", "")
        if not prompt:
            prompt = "Hello, how are you today?"

        # Get settings
        model_type = self.get_property("model_type")
        model_name = self.get_property("model_name")
        system_prompt = self.get_property("system_prompt")
        use_mock = self.get_property("use_mock")

        # Process the LLM request
        if use_mock:
            # Generate a mock response for testing (synchronous)
            response = self._generate_mock_response(prompt, llm_request)
            # Store the mock response for later use
            self._current_llm_response = response
            self._accumulated_response_text = response.message
            # Return mock response immediately
            return {
                "llm_response": response,
                "llm_message": response.message,
            }
        else:
            # Start the actual LLM call (asynchronous)
            self._call_llm(
                prompt, system_prompt, llm_request, model_type, model_name
            )

            # Here we need to check if we have received a response from the LLM
            # If we have, return it; otherwise, return None
            if self._current_llm_response:
                return {
                    "llm_response": self._current_llm_response,
                    "llm_message": self._accumulated_response_text,
                }
            else:
                # Return None initially, the result will be updated when the response arrives
                return {"llm_response": None, "llm_message": None}

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
            self.emit_signal(
                SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL,
                {
                    "llm_request": True,
                    "graph_request": True,  # Flag this request as originating from the graph
                    "node_id": self.id,  # Include node ID for routing response
                    "request_data": {
                        "action": LLMActionType.CHAT,
                        "prompt": prompt,
                        "system_prompt": system_prompt,  # Pass system prompt
                        "model_type": model_type,  # Pass model info
                        "model_name": model_name,  # Pass model info
                        "llm_request": llm_request,  # Pass the LLMRequest object directly, not as dict
                    },
                },
            )
        except Exception as e:
            # Handle error during signal emission if necessary
            print(f"Error emitting LLM request signal for node {self.id}: {e}")
            # Create an error response and store it in our instance variables
            error_response = LLMResponse(
                text=f"Error starting LLM call: {str(e)}",
                metadata={"error": str(e)},
            )
            self._current_llm_response = error_response
            self._accumulated_response_text = error_response.message

    def _on_llm_text_streamed(self, data: Dict):
        # Assuming the signal sends the final LLMResponse object upon completion
        # If it sends text chunks, accumulation logic would be needed here.
        llm_response: Optional[LLMResponse] = data.get("response", None)

        if llm_response.node_id != self.id:
            print(
                "stream failed",
                self.id,
            )
            return

        if llm_response:
            self._current_llm_response = llm_response
            # Store the response in instance variables instead of trying to set port values directly
            self._accumulated_response_text = llm_response.message
            # The output will be returned by the execute method
        else:
            # Handle potential errors or empty responses from the signal if needed
            # Create a default error response
            self._current_llm_response = LLMResponse(
                text="Error: No response received from LLM.",
                metadata={"error": "Missing response object in signal data"},
            )
            self._accumulated_response_text = (
                self._current_llm_response.message
            )
