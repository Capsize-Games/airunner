"""Status management mixin for LLM model manager.

This mixin handles status updates, success/error messaging, and component
state logging for the LLM model manager.
"""

from typing import TYPE_CHECKING

from airunner.enums import SignalCode, ModelType, ModelStatus, LLMActionType
from airunner.components.llm.managers.llm_response import LLMResponse

if TYPE_CHECKING:
    from airunner.components.llm.managers.llm_model_manager import (
        LLMModelManager,
    )


class StatusManagementMixin:
    """Mixin for managing model loading status and user notifications.

    Handles sending status messages to the GUI and logging component
    loading failures.
    """

    def _send_error_response(self: "LLMModelManager", message: str) -> None:
        """Send error message to GUI via API or signal.

        Args:
            message: Error message to display to user.
        """
        response = LLMResponse(message=message, is_end_of_message=True, is_system_message=True)

        try:
            self.api.llm.send_llm_text_streamed_signal(response)
        except Exception:
            self.emit_signal(
                SignalCode.LLM_TEXT_STREAMED_SIGNAL,
                {"response": response},
            )

    def _send_success_message(self: "LLMModelManager", is_api: bool) -> None:
        """Send model loaded success message to GUI.

        Args:
            is_api: True if model loaded in API mode, False for local mode.
        """
        message = (
            "✅ Model loaded successfully (API mode)\n"
            if is_api
            else "✅ Model loaded and ready for chat\n"
        )

        response = LLMResponse(message=message, is_end_of_message=False, is_system_message=True)

        try:
            self.api.llm.send_llm_text_streamed_signal(response)
        except Exception:
            self.emit_signal(
                SignalCode.LLM_TEXT_STREAMED_SIGNAL,
                {"response": response},
            )

    def _send_quantization_info(self: "LLMModelManager") -> None:
        """Send auto-selected quantization information to GUI.

        Displays which quantization level was automatically selected based
        on available VRAM.
        """
        vram_gb = self._get_available_vram_gb()
        quant_info = self._get_quantization_info(vram_gb)

        message = (
            f"🔧 Auto-selecting quantization: {quant_info['level']} "
            f"({quant_info['description']}) "
            f"based on {vram_gb:.1f}GB available VRAM\n"
        )

        response = LLMResponse(
            message=message,
            is_end_of_message=False,
            action=LLMActionType.CHAT,
            is_system_message=True,
        )

        self.emit_signal(
            SignalCode.LLM_TEXT_STREAMED_SIGNAL,
            {"response": response},
        )

    def _handle_pending_conversation(self: "LLMModelManager") -> None:
        """Process pending conversation load if one exists.

        Called after model loading to load a conversation that was
        requested before the model was ready.
        """
        pending_msg = getattr(self, "_pending_conversation_message", None)

        if pending_msg is None:
            return

        self.logger.info("Processing pending conversation after model loaded")
        self.load_conversation(pending_msg)
        self._pending_conversation_message = None

    def _log_component_failures(self: "LLMModelManager") -> None:
        """Log which model components failed to load.

        Helps diagnose loading issues by reporting which specific
        components (model, tokenizer, chat model, workflow) failed.
        For GGUF models, model and tokenizer are not required.
        """
        if not self._chat_model:
            self.logger.error("ChatModel failed to load")

        if not self._workflow_manager:
            self.logger.error("Workflow manager failed to load")

        if self.llm_settings.use_local_llm:
            # For GGUF models, _model and _tokenizer are not used
            # Check if GGUF is selected via the validation mixin method
            is_gguf = getattr(self, '_is_gguf_quantization_selected', lambda: False)()
            
            if not is_gguf:
                if not self._model:
                    self.logger.error("Model failed to load")

                is_mistral3 = self._is_mistral3_model()
                if not self._tokenizer and not is_mistral3:
                    self.logger.error("Tokenizer failed to load")

    def _update_model_status(self: "LLMModelManager") -> None:
        """Update model loading status based on loaded components.

        Checks if all required components are loaded (API or local mode),
        emits status signals, and sends success/failure messages to GUI.
        """
        is_api = self.llm_settings.use_api

        # Check API mode components loaded
        if is_api and self._check_components_loaded_for_api():
            self._mark_model_loaded_api()
            return

        # Check local mode components loaded
        if not is_api and self._check_components_loaded_for_local():
            self._mark_model_loaded_local()
            return

        # Loading failed
        self._mark_model_failed()

    def _mark_model_loaded_api(self: "LLMModelManager") -> None:
        """Mark model as successfully loaded in API mode."""
        self.change_model_status(ModelType.LLM, ModelStatus.LOADED)
        self.emit_signal(SignalCode.TOGGLE_LLM_SIGNAL, {"enabled": True})
        self._send_success_message(is_api=True)

    def _mark_model_loaded_local(self: "LLMModelManager") -> None:
        """Mark model as successfully loaded in local mode."""
        self.change_model_status(ModelType.LLM, ModelStatus.LOADED)
        self.emit_signal(SignalCode.TOGGLE_LLM_SIGNAL, {"enabled": True})
        self._send_success_message(is_api=False)
        self._handle_pending_conversation()

    def _mark_model_failed(self: "LLMModelManager") -> None:
        """Mark model loading as failed and log details."""
        self._log_component_failures()
        self.change_model_status(ModelType.LLM, ModelStatus.FAILED)
