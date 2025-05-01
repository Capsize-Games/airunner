from typing import Dict, Any
from NodeGraphQt.constants import NodePropWidgetEnum
from airunner.gui.widgets.nodegraph.nodes.llm.base_llm_node import BaseLLMNode
from airunner.handlers.llm.gemma3_model_manager import Gemma3Manager
from airunner.enums import SignalCode, LLMActionType
from airunner.handlers.llm.llm_request import LLMRequest
from PIL import Image
import base64
import io


class Gemma3Node(BaseLLMNode):
    NODE_NAME = "Gemma3"
    __identifier__ = "LLM.Gemma3Node"
    has_exec_in_port = True
    has_exec_out_port = True
    _input_ports = [
        dict(name="messages", display_name="Messages"),
        dict(name="prompt", display_name="Prompt"),
        dict(name="system_prompt", display_name="System Prompt"),
        dict(name="image", display_name="Image"),
        dict(name="llm_request", display_name="LLM Request"),
    ]
    _output_ports = [
        dict(name="response", display_name="Response"),
        dict(name="model_info", display_name="Model Info"),
    ]
    _properties = [
        dict(
            name="max_new_tokens",
            value=100,
            widget_type=NodePropWidgetEnum.INT,
            range=(1, 2048),
            tab="generation",
        ),
        dict(
            name="model_id",
            value="google/gemma-3-4b-it",
            widget_type=NodePropWidgetEnum.QLINE_EDIT,
            tab="model",
        ),
        dict(
            name="temperature",
            value=0.7,
            widget_type=NodePropWidgetEnum.FLOAT,
            range=(0.0, 2.0),
            tab="generation",
        ),
        dict(
            name="repetition_penalty",
            value=1.1,
            widget_type=NodePropWidgetEnum.FLOAT,
            range=(1.0, 2.0),
            tab="generation",
        ),
    ]

    def __init__(self):
        self.signal_handlers = {
            SignalCode.LLM_TEXT_STREAMED_SIGNAL: self._on_llm_text_streamed,
        }
        super().__init__()
        self._accumulated_response_text = ""
        self._current_llm_response = None
        self._model_manager = None

    def _get_model_manager(self) -> Gemma3Manager:
        """
        Get or create the Gemma3Manager instance.

        Returns:
            Gemma3Manager: The model manager instance
        """
        if self._model_manager is None:
            self._model_manager = Gemma3Manager()
        return self._model_manager

    def _on_llm_text_streamed(self, data: Dict):
        """
        Handle streaming text responses from the LLM.

        Args:
            data: Response data from the LLM
        """
        llm_response = data.get("response")
        if not llm_response or llm_response.node_id != self.id:
            return

        # Reset accumulator if this is the first message chunk
        if llm_response.is_first_message:
            self._accumulated_response_text = ""

        # Append the new message chunk to the accumulator
        if isinstance(llm_response.message, str):
            self._accumulated_response_text += llm_response.message

        # Store the latest response object
        self._current_llm_response = llm_response

    def execute(self, input_data: Dict[str, Any]):
        """
        Execute the node with the provided input data.

        Args:
            input_data: Dictionary containing input values

        Returns:
            Dict: Output values including the response text
        """
        # Get messages or create from individual components
        messages = input_data.get("messages")
        model_id = self.get_property("model_id")
        max_new_tokens = self.get_property("max_new_tokens")
        temperature = self.get_property("temperature")
        repetition_penalty = self.get_property("repetition_penalty")

        # If no messages provided, build from individual components
        if not messages:
            messages = []

            # Get system prompt
            system_prompt = input_data.get(
                "system_prompt", "You are a helpful assistant."
            )
            if system_prompt:
                messages.append(
                    {
                        "role": "system",
                        "content": [{"type": "text", "text": system_prompt}],
                    }
                )

            # Get prompt and image
            prompt = input_data.get("prompt", "")
            image = input_data.get("image")

            # Build content list for user message
            content = []

            # Add image if provided
            if image:
                if isinstance(image, str):
                    # Assume it's a URL or base64 string
                    content.append({"type": "image", "image": image})
                elif isinstance(image, Image.Image):
                    # Convert PIL image to base64
                    buffer = io.BytesIO()
                    image.save(buffer, format="PNG")
                    img_str = base64.b64encode(buffer.getvalue()).decode(
                        "utf-8"
                    )
                    content.append(
                        {
                            "type": "image",
                            "image": f"data:image/png;base64,{img_str}",
                        }
                    )

            # Add text prompt if provided
            if prompt:
                content.append({"type": "text", "text": prompt})

            # Add user message if we have content
            if content:
                messages.append({"role": "user", "content": content})

        # Get or create LLMRequest
        llm_request = input_data.get("llm_request", LLMRequest())
        if not isinstance(llm_request, LLMRequest):
            llm_request = LLMRequest()

        # Set node_id for routing responses
        llm_request.node_id = self.id

        # Override LLMRequest parameters if specified in the node
        if max_new_tokens:
            llm_request.max_new_tokens = max_new_tokens

        # Set temperature (convert to the expected scale)
        if temperature is not None:
            llm_request.temperature = float(temperature)

        # Set repetition penalty (convert to the expected scale)
        if repetition_penalty is not None:
            llm_request.repetition_penalty = float(repetition_penalty)

        # Get the model manager
        model_manager = self._get_model_manager()

        # Set model version
        model_manager.llm_generator_settings.model_version = model_id

        # Load the model
        model_manager.load()

        # Generate response by directly passing messages to the manager
        response = model_manager.chat(
            prompt="",  # Empty since we're using messages
            action=LLMActionType.CHAT,
            llm_request=llm_request,
            messages=messages,
        )

        # Return response and model information
        model_info = {
            "model_id": model_id,
            "context_window": model_manager.context_window,
            "supports_vision": model_manager.supports_vision,
        }

        return {
            "response": response,
            "model_info": model_info,
            "_exec_triggered": self.EXEC_OUT_PORT_NAME,
        }
