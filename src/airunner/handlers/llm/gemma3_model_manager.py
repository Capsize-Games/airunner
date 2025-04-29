import os
import torch
from typing import Dict, Optional, Any, List, Union

from transformers import Gemma3ForConditionalGeneration, AutoProcessor
from llama_index.core.chat_engine.types import AgentChatResponse

from airunner.handlers.llm.llm_model_manager import LLMModelManager
from airunner.handlers.llm.llm_request import LLMRequest
from airunner.settings import AIRUNNER_LOCAL_FILES_ONLY
from airunner.enums import LLMActionType, ModelType, ModelStatus


class Gemma3Manager(LLMModelManager):
    """
    Handler for Google's Gemma 3 multimodal model operations in AI Runner.

    This class extends LLMModelManager to provide specialized handling for
    Gemma 3 models, which support both text and image inputs.
    """

    _processor = None  # Replaces tokenizer for Gemma 3
    _model = None  # Gemma3ForConditionalGeneration instance

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger.debug("Initializing Gemma3Manager")

    @property
    def model_path(self) -> str:
        """
        Get the path to the Gemma 3 model based on settings or use default.

        Returns:
            str: Path to the model directory
        """
        model_version = self.model_version
        # If not specifically set, use the default Gemma 3 model
        if not model_version or "gemma-3" not in model_version.lower():
            model_version = "google/gemma-3-4b-it"

        # Check if it's a local path or Hugging Face model ID
        if os.path.exists(os.path.expanduser(model_version)):
            return os.path.expanduser(model_version)

        # Return as is for Hugging Face model IDs
        return model_version

    @property
    def supports_vision(self) -> bool:
        """
        Check if the current model supports vision inputs.

        Returns:
            bool: True if the model supports vision inputs
        """
        # All Gemma 3 models support vision
        return True

    def _load_tokenizer(self) -> None:
        """
        Load the AutoProcessor for Gemma 3 model instead of tokenizer.

        Gemma 3 uses AutoProcessor which handles both text and image inputs.
        """
        if self._processor is not None:
            return

        self.logger.debug(f"Loading Gemma3 processor from {self.model_path}")
        try:
            self._processor = AutoProcessor.from_pretrained(
                self.model_path,
                local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
                trust_remote_code=True,
            )
            self._tokenizer = (
                self._processor
            )  # For compatibility with parent class
            self.logger.debug("Gemma3 processor loaded successfully")
        except Exception as e:
            self.logger.error(f"Error loading Gemma3 processor: {e}")
            self._processor = None
            self._tokenizer = None

    def _load_model(self) -> None:
        """
        Load the Gemma3ForConditionalGeneration model.
        """
        if self._model is not None:
            return

        self.logger.debug(f"Loading Gemma3 model from {self.model_path}")
        try:
            self._model = Gemma3ForConditionalGeneration.from_pretrained(
                self.model_path,
                local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
                trust_remote_code=True,
                device_map="auto",
                torch_dtype=torch.bfloat16,
            ).eval()
            self.logger.debug("Gemma3 model loaded successfully")
        except Exception as e:
            self.logger.error(f"Error loading Gemma3 model: {e}")
            self._model = None

    def _do_generate(
        self,
        prompt: str = "",
        action: LLMActionType = LLMActionType.CHAT,
        system_prompt: Optional[str] = None,
        rag_system_prompt: Optional[str] = None,
        llm_request: Optional[LLMRequest] = None,
        do_tts_reply: bool = True,
        image_data: Optional[Union[str, bytes]] = None,
        messages: Optional[List[Dict[str, Any]]] = None,
    ) -> AgentChatResponse:
        """
        Generate a response using the Gemma 3 model.

        This method supports both text-only and multimodal inputs, and can
        accept either a prompt + image or a pre-formatted message array.

        Args:
            prompt: The text prompt for generation.
            action: The type of action to perform.
            system_prompt: Optional system prompt to override defaults.
            rag_system_prompt: Optional system prompt for RAG operations.
            llm_request: Optional request configuration.
            do_tts_reply: Whether to convert the reply to speech.
            image_data: Optional image data (URL, file path, or bytes) to include in the prompt.
            messages: Optional pre-formatted message array in Gemma 3 format.

        Returns:
            AgentChatResponse: The generated response.
        """
        self.logger.debug("Generating response with Gemma3")

        # Load model if needed
        if self._current_model_path != self.model_path:
            self.unload()
            self.load()

        # Use provided messages or create from scratch
        if not messages:
            # Prepare system message
            system_message = system_prompt or "You are a helpful assistant."

            # Prepare messages in Gemma 3 format
            messages = [
                {
                    "role": "system",
                    "content": [{"type": "text", "text": system_message}],
                }
            ]

            # Add user message with text and optional image
            user_content = []

            # Add image if provided
            if image_data:
                user_content.append({"type": "image", "image": image_data})

            # Add text prompt if provided
            if prompt:
                user_content.append({"type": "text", "text": prompt})

            # Add user message if we have content
            if user_content:
                messages.append({"role": "user", "content": user_content})

        # Process through Gemma 3 model
        llm_request = llm_request or LLMRequest.from_default()
        max_new_tokens = llm_request.max_new_tokens

        try:
            # Apply chat template and prepare inputs
            inputs = self._processor.apply_chat_template(
                messages,
                add_generation_prompt=True,
                tokenize=True,
                return_dict=True,
                return_tensors="pt",
            ).to(self._model.device, dtype=torch.bfloat16)

            input_len = inputs["input_ids"].shape[-1]

            # Generate response
            with torch.inference_mode():
                generation = self._model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    do_sample=llm_request.do_sample,
                    temperature=(
                        llm_request.temperature / 1000
                        if llm_request.temperature > 1
                        else llm_request.temperature
                    ),
                    top_p=(
                        llm_request.top_p / 1000
                        if llm_request.top_p > 1
                        else llm_request.top_p
                    ),
                    top_k=llm_request.top_k,
                    repetition_penalty=(
                        llm_request.repetition_penalty / 100
                        if llm_request.repetition_penalty > 1
                        else llm_request.repetition_penalty
                    ),
                )
                generation = generation[0][input_len:]

            # Decode response
            decoded = self._processor.decode(
                generation, skip_special_tokens=True
            )

            print(decoded)

            # Create response object
            response = AgentChatResponse(response=decoded)

            # Send final message signal
            if action is LLMActionType.CHAT:
                self._send_final_message(llm_request)

            return response

        except Exception as e:
            self.logger.error(f"Error generating with Gemma3: {e}")
            return AgentChatResponse(
                response=f"Error generating response: {str(e)}"
            )

    def _load_agent(self) -> None:
        """
        No need for a separate agent for Gemma 3 models.

        The Gemma3Manager handles text generation directly.
        """
        self._chat_agent = self  # Use self as the chat agent

    def unload(self) -> None:
        """
        Unload all Gemma 3 model components from memory.
        """
        if self.model_status[ModelType.LLM] in (
            ModelStatus.LOADING,
            ModelStatus.UNLOADED,
        ):
            return

        self.logger.debug("Unloading Gemma3 model")
        self.change_model_status(ModelType.LLM, ModelStatus.LOADING)

        # Unload model
        try:
            if self._model is not None:
                del self._model
                self._model = None
        except Exception as e:
            self.logger.warning(f"Error unloading Gemma3 model: {e}")

        # Unload processor
        try:
            if self._processor is not None:
                del self._processor
                self._processor = None
                self._tokenizer = None
        except Exception as e:
            self.logger.warning(f"Error unloading Gemma3 processor: {e}")

        torch.cuda.empty_cache()

        self.change_model_status(ModelType.LLM, ModelStatus.UNLOADED)

    def _update_model_status(self):
        """
        Update the model status based on loading results.
        """
        if self._model is not None and self._processor is not None:
            self.change_model_status(ModelType.LLM, ModelStatus.LOADED)
        else:
            self.logger.error("Gemma3 model or processor failed to load")
            self.change_model_status(ModelType.LLM, ModelStatus.FAILED)

    def chat(self, prompt: str, **kwargs) -> AgentChatResponse:
        """
        Chat method to be compatible with the chat_agent interface.

        Args:
            prompt: The text prompt for generation.
            **kwargs: Additional arguments for generation.

        Returns:
            AgentChatResponse: The generated response.
        """
        action = kwargs.get("action", LLMActionType.CHAT)
        system_prompt = kwargs.get("system_prompt")
        rag_system_prompt = kwargs.get("rag_system_prompt")
        llm_request = kwargs.get("llm_request")
        messages = kwargs.get("messages")
        image_data = kwargs.get("image_data")

        return self._do_generate(
            prompt=prompt,
            action=action,
            system_prompt=system_prompt,
            rag_system_prompt=rag_system_prompt,
            llm_request=llm_request,
            image_data=image_data,
            messages=messages,
        )

    def clear_history(self, data: Optional[Dict] = None) -> None:
        """
        Clear conversation history.

        Gemma3 doesn't maintain internal history, so this is a no-op.

        Args:
            data: Optional data with history clearing parameters.
        """
        # No history to clear
        pass

    @property
    def context_window(self) -> int:
        """
        Get the context window size of the model.

        Returns:
            int: The approximate context window size
        """
        # Gemma 3 models have an 8k context window
        return 8192
