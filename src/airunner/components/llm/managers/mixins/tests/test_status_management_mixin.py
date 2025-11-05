"""Tests for StatusManagementMixin.

Tests the status management mixin functionality including status updates,
success/error messaging, and component state logging.
"""

from unittest.mock import Mock

from airunner.components.llm.managers.mixins.status_management_mixin import (
    StatusManagementMixin,
)
from airunner.components.llm.managers.llm_response import LLMResponse
from airunner.enums import SignalCode, ModelType, ModelStatus


class TestableStatusMixin(StatusManagementMixin):
    """Testable version of StatusManagementMixin."""

    def __init__(self):
        self.api = Mock()
        self.api.llm = Mock()
        self.emit_signal = Mock()
        self.logger = Mock()
        self.llm_settings = Mock()
        self.model_status = {ModelType.LLM: ModelStatus.UNLOADED}
        self.change_model_status = Mock()
        self._chat_model = None
        self._workflow_manager = None
        self._model = None
        self._tokenizer = None
        self._pending_conversation_message = None
        self.load_conversation = Mock()
        self._get_available_vram_gb = Mock(return_value=8.0)
        self._get_quantization_info = Mock(
            return_value={"level": "4-bit", "description": "Good balance"}
        )
        self._is_mistral3_model = Mock(return_value=False)
        self._check_components_loaded_for_api = Mock(return_value=False)
        self._check_components_loaded_for_local = Mock(return_value=False)


class TestSendErrorResponse:
    """Tests for _send_error_response method."""

    def test_sends_via_api_when_available(self):
        """Test error response sent via API when available."""
        mixin = TestableStatusMixin()

        mixin._send_error_response("Test error")

        mixin.api.llm.send_llm_text_streamed_signal.assert_called_once()
        call_args = mixin.api.llm.send_llm_text_streamed_signal.call_args[0][0]
        assert isinstance(call_args, LLMResponse)
        assert call_args.message == "Test error"
        assert call_args.is_end_of_message is True

    def test_falls_back_to_signal_on_api_error(self):
        """Test falls back to signal emission when API fails."""
        mixin = TestableStatusMixin()
        mixin.api.llm.send_llm_text_streamed_signal.side_effect = Exception()

        mixin._send_error_response("Test error")

        mixin.emit_signal.assert_called_once()
        assert (
            mixin.emit_signal.call_args[0][0]
            == SignalCode.LLM_TEXT_STREAMED_SIGNAL
        )


class TestSendSuccessMessage:
    """Tests for _send_success_message method."""

    def test_sends_api_mode_message(self):
        """Test sends API mode success message."""
        mixin = TestableStatusMixin()

        mixin._send_success_message(is_api=True)

        call_args = mixin.api.llm.send_llm_text_streamed_signal.call_args[0][0]
        assert "API mode" in call_args.message

    def test_sends_local_mode_message(self):
        """Test sends local mode success message."""
        mixin = TestableStatusMixin()

        mixin._send_success_message(is_api=False)

        call_args = mixin.api.llm.send_llm_text_streamed_signal.call_args[0][0]
        assert "ready for chat" in call_args.message


class TestSendQuantizationInfo:
    """Tests for _send_quantization_info method."""

    def test_sends_quantization_info(self):
        """Test sends quantization selection info."""
        mixin = TestableStatusMixin()

        mixin._send_quantization_info()

        mixin._get_available_vram_gb.assert_called_once()
        mixin._get_quantization_info.assert_called_once_with(8.0)
        mixin.emit_signal.assert_called_once()

        signal_data = mixin.emit_signal.call_args[0][1]
        assert "4-bit" in signal_data["response"].message
        assert "8.0GB" in signal_data["response"].message


class TestHandlePendingConversation:
    """Tests for _handle_pending_conversation method."""

    def test_does_nothing_when_no_pending_conversation(self):
        """Test does nothing when no pending conversation."""
        mixin = TestableStatusMixin()

        mixin._handle_pending_conversation()

        mixin.load_conversation.assert_not_called()

    def test_loads_pending_conversation(self):
        """Test loads pending conversation when present."""
        mixin = TestableStatusMixin()
        pending_msg = {"conversation_id": 123}
        mixin._pending_conversation_message = pending_msg

        mixin._handle_pending_conversation()

        mixin.load_conversation.assert_called_once_with(pending_msg)
        assert mixin._pending_conversation_message is None


class TestLogComponentFailures:
    """Tests for _log_component_failures method."""

    def test_logs_chat_model_failure(self):
        """Test logs when chat model not loaded."""
        mixin = TestableStatusMixin()

        mixin._log_component_failures()

        mixin.logger.error.assert_any_call("ChatModel failed to load")

    def test_logs_workflow_manager_failure(self):
        """Test logs when workflow manager not loaded."""
        mixin = TestableStatusMixin()

        mixin._log_component_failures()

        mixin.logger.error.assert_any_call("Workflow manager failed to load")

    def test_logs_model_failure_for_local(self):
        """Test logs model failure for local LLM."""
        mixin = TestableStatusMixin()
        mixin.llm_settings.use_local_llm = True

        mixin._log_component_failures()

        mixin.logger.error.assert_any_call("Model failed to load")

    def test_logs_tokenizer_failure_non_mistral(self):
        """Test logs tokenizer failure for non-Mistral models."""
        mixin = TestableStatusMixin()
        mixin.llm_settings.use_local_llm = True

        mixin._log_component_failures()

        mixin.logger.error.assert_any_call("Tokenizer failed to load")


class TestUpdateModelStatus:
    """Tests for _update_model_status method."""

    def test_marks_loaded_for_api_mode(self):
        """Test marks model as loaded for API mode."""
        mixin = TestableStatusMixin()
        mixin.llm_settings.use_api = True
        mixin._check_components_loaded_for_api.return_value = True

        mixin._update_model_status()

        mixin.change_model_status.assert_called_with(
            ModelType.LLM, ModelStatus.LOADED
        )

    def test_marks_loaded_for_local_mode(self):
        """Test marks model as loaded for local mode."""
        mixin = TestableStatusMixin()
        mixin.llm_settings.use_api = False
        mixin._check_components_loaded_for_local.return_value = True

        mixin._update_model_status()

        mixin.change_model_status.assert_called_with(
            ModelType.LLM, ModelStatus.LOADED
        )

    def test_marks_failed_when_components_not_loaded(self):
        """Test marks model as failed when components not loaded."""
        mixin = TestableStatusMixin()
        mixin.llm_settings.use_api = False

        mixin._update_model_status()

        mixin.change_model_status.assert_called_with(
            ModelType.LLM, ModelStatus.FAILED
        )


class TestMarkModelLoadedApi:
    """Tests for _mark_model_loaded_api method."""

    def test_updates_status_and_sends_message(self):
        """Test updates status and sends success message."""
        mixin = TestableStatusMixin()

        mixin._mark_model_loaded_api()

        mixin.change_model_status.assert_called_once_with(
            ModelType.LLM, ModelStatus.LOADED
        )
        mixin.emit_signal.assert_called_once_with(
            SignalCode.TOGGLE_LLM_SIGNAL, {"enabled": True}
        )


class TestMarkModelLoadedLocal:
    """Tests for _mark_model_loaded_local method."""

    def test_updates_status_and_handles_pending(self):
        """Test updates status and handles pending conversation."""
        mixin = TestableStatusMixin()
        mixin._pending_conversation_message = {"conversation_id": 1}

        mixin._mark_model_loaded_local()

        mixin.change_model_status.assert_called_once_with(
            ModelType.LLM, ModelStatus.LOADED
        )
        mixin.load_conversation.assert_called_once()


class TestMarkModelFailed:
    """Tests for _mark_model_failed method."""

    def test_logs_failures_and_updates_status(self):
        """Test logs component failures and marks as failed."""
        mixin = TestableStatusMixin()

        mixin._mark_model_failed()

        # Should have logged errors for all missing components
        assert mixin.logger.error.call_count >= 2
        mixin.change_model_status.assert_called_once_with(
            ModelType.LLM, ModelStatus.FAILED
        )
