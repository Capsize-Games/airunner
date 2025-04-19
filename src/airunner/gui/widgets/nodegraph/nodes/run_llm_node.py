import time
from typing import Dict, Optional

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
        super().__init__()

        # Input port for the LLMRequest
        self.add_input("llm_request", display_name=True)
        self.add_input("prompt", display_name=True)

        # Output port for the LLMResponse
        self.add_output("llm_response")

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
            # Generate a mock response for testing
            response = self._generate_mock_response(prompt, llm_request)
        else:
            # Try to use the actual LLM
            response = self._call_llm(
                prompt, system_prompt, llm_request, model_type, model_name
            )

        return {"llm_response": response}

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
        return LLMResponse(
            text=response_text,
            tokens_generated=len(response_text.split()),
            tokens_processed=len(prompt.split()),
            total_time=time.time() - start_time,
            metadata={"mock": True},
        )

    def _call_llm(
        self,
        prompt: str,
        system_prompt: str,
        llm_request: LLMRequest,
        model_type: str,
        model_name: str,
    ) -> LLMResponse:
        """
        Call the LLM with the given request parameters.

        Args:
            prompt: The input prompt text.
            system_prompt: The system context prompt.
            llm_request: The LLMRequest object.
            model_type: Type of model to use (Local, OpenAI, etc.)
            model_name: Name or path of the model.

        Returns:
            LLMResponse: The model's response.
        """
        start_time = time.time()

        # In a real implementation, this would call the appropriate LLM handler
        # For now, we'll return a placeholder response
        try:
            # Placeholder for actual LLM call
            # In a real implementation, you would route to the appropriate
            # handler based on model_type and model_name
            response_text = (
                f"This would be a response from {model_type} using {model_name}.\n"
                f"Currently this is a placeholder as the actual LLM integration "
                f"would need to be implemented in a real application."
            )

            return LLMResponse(
                text=response_text,
                tokens_generated=len(response_text.split()),
                tokens_processed=len(prompt.split()),
                total_time=time.time() - start_time,
                metadata={
                    "model_type": model_type,
                    "model_name": model_name,
                    "placeholder": True,
                },
            )
        except Exception as e:
            # Return an error response
            error_text = f"Error calling LLM: {str(e)}"
            return LLMResponse(
                text=error_text,
                tokens_generated=0,
                tokens_processed=len(prompt.split()),
                total_time=time.time() - start_time,
                metadata={"error": str(e)},
            )
