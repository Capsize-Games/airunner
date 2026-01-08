"""Unit tests for GenerationMixin."""

from unittest.mock import Mock, patch
import pytest
from langchain_core.messages import AIMessage

from airunner.components.llm.managers.mixins.generation_mixin import (
    GenerationMixin,
)
from airunner.components.llm.managers.llm_request import LLMRequest
from airunner.components.llm.managers.llm_response import LLMResponse
from airunner.enums import LLMActionType


class TestableGenerationMixin(GenerationMixin):
    """Testable version of GenerationMixin with required dependencies."""

    def __init__(self):
        """Initialize with mock dependencies."""
        self.logger = Mock()
        self.api = Mock()
        self._workflow_manager = Mock()
        self._tool_manager = Mock()
        self._interrupted = False
        self._current_model_path = "/path/to/model"
        self.model_path = "/path/to/model"
        self.llm_generator_settings = Mock()
        self.chatbot = Mock()
        self.load = Mock()
        self.unload = Mock()

    def get_system_prompt_for_action(self, action: LLMActionType) -> str:
        """Mock method for getting system prompt."""
        return "Default system prompt"

    def get_system_prompt_with_context(
        self, action: LLMActionType, tool_categories=None, force_tool=None
    ) -> str:
        """Mock method for getting context-aware system prompt."""
        return "Default system prompt"


@pytest.fixture
def mixin():
    """Create a testable GenerationMixin instance."""
    return TestableGenerationMixin()


@pytest.fixture
def llm_request():
    """Create a test LLM request."""
    return LLMRequest(node_id="test-node")


class TestSetupGenerationWorkflow:
    """Tests for _setup_generation_workflow method."""

    def test_uses_provided_system_prompt(self, mixin):
        """Should use provided system prompt when given."""
        custom_prompt = "Custom system prompt"
        result = mixin._setup_generation_workflow(
            LLMActionType.CHAT, custom_prompt
        )

        assert result == custom_prompt
        mixin._workflow_manager.update_system_prompt.assert_called_once_with(
            custom_prompt
        )

    def test_uses_action_system_prompt_when_none_provided(self, mixin):
        """Should get action prompt when none provided."""
        result = mixin._setup_generation_workflow(LLMActionType.CHAT, None)

        assert result == "Default system prompt"
        mixin._workflow_manager.update_system_prompt.assert_called_once_with(
            "Default system prompt"
        )

    def test_updates_tools_from_tool_manager(self, mixin):
        """Should update workflow tools from tool manager."""
        mock_tools = [Mock(), Mock()]
        mixin._tool_manager.get_tools_for_action.return_value = mock_tools

        mixin._setup_generation_workflow(LLMActionType.CODE, None)

        mixin._tool_manager.get_tools_for_action.assert_called_once_with(
            LLMActionType.CODE
        )
        mixin._workflow_manager.update_tools.assert_called_once_with(
            mock_tools
        )

    def test_handles_missing_workflow_manager(self, mixin):
        """Should handle missing workflow manager gracefully."""
        mixin._workflow_manager = None

        result = mixin._setup_generation_workflow(LLMActionType.CHAT, None)

        assert result == "Default system prompt"

    def test_handles_missing_tool_manager(self, mixin):
        """Should handle missing tool manager gracefully."""
        mixin._tool_manager = None

        result = mixin._setup_generation_workflow(
            LLMActionType.CHAT, "Test prompt"
        )

        assert result == "Test prompt"
        mixin._workflow_manager.update_system_prompt.assert_called_once_with(
            "Test prompt"
        )


class TestCreateStreamingCallback:
    """Tests for _create_streaming_callback method."""

    def test_callback_accumulates_response(self, mixin, llm_request):
        """Should accumulate response text."""
        complete_response = [""]
        sequence_counter = [0]

        callback = mixin._create_streaming_callback(
            llm_request, complete_response, sequence_counter
        )

        callback("Hello")
        callback(" world")

        assert complete_response[0] == "Hello world"

    def test_callback_increments_sequence(self, mixin, llm_request):
        """Should increment sequence counter for each token."""
        complete_response = [""]
        sequence_counter = [0]

        callback = mixin._create_streaming_callback(
            llm_request, complete_response, sequence_counter
        )

        callback("Hello")
        callback(" world")
        callback("!")

        assert sequence_counter[0] == 3

    def test_callback_sends_llm_signals(self, mixin, llm_request):
        """Should send LLM signals for each token."""
        complete_response = [""]
        sequence_counter = [0]

        callback = mixin._create_streaming_callback(
            llm_request, complete_response, sequence_counter
        )

        callback("Hello")

        mixin.api.llm.send_llm_text_streamed_signal.assert_called_once()
        call_args = mixin.api.llm.send_llm_text_streamed_signal.call_args[0][0]
        assert isinstance(call_args, LLMResponse)
        assert call_args.message == "Hello"
        assert call_args.is_end_of_message is False
        assert call_args.is_first_message is True
        assert call_args.sequence_number == 1

    def test_callback_marks_first_message(self, mixin, llm_request):
        """Should mark first message correctly."""
        complete_response = [""]
        sequence_counter = [0]

        callback = mixin._create_streaming_callback(
            llm_request, complete_response, sequence_counter
        )

        callback("First")
        first_call = (
            mixin.api.llm.send_llm_text_streamed_signal.call_args_list[0][0][0]
        )

        callback("Second")
        second_call = (
            mixin.api.llm.send_llm_text_streamed_signal.call_args_list[1][0][0]
        )

        assert first_call.is_first_message is True
        assert second_call.is_first_message is False

    def test_callback_ignores_empty_tokens(self, mixin, llm_request):
        """Should ignore empty token strings."""
        complete_response = [""]
        sequence_counter = [0]

        callback = mixin._create_streaming_callback(
            llm_request, complete_response, sequence_counter
        )

        callback("")

        assert complete_response[0] == ""
        assert sequence_counter[0] == 0
        mixin.api.llm.send_llm_text_streamed_signal.assert_not_called()

    def test_callback_includes_node_id(self, mixin, llm_request):
        """Should include node_id in signals."""
        complete_response = [""]
        sequence_counter = [0]

        callback = mixin._create_streaming_callback(
            llm_request, complete_response, sequence_counter
        )

        callback("Test")

        call_args = mixin.api.llm.send_llm_text_streamed_signal.call_args[0][0]
        assert call_args.node_id == "test-node"

    def test_callback_handles_none_request(self, mixin):
        """Should handle None request gracefully."""
        complete_response = [""]
        sequence_counter = [0]

        callback = mixin._create_streaming_callback(
            None, complete_response, sequence_counter
        )

        callback("Test")

        call_args = mixin.api.llm.send_llm_text_streamed_signal.call_args[0][0]
        assert call_args.node_id is None


class TestHandleInterruptedGeneration:
    """Tests for _handle_interrupted_generation method."""

    def test_logs_interruption(self, mixin, llm_request):
        """Should log interruption message."""
        mixin._handle_interrupted_generation(llm_request, 5)

        mixin.logger.info.assert_called_once_with(
            "Generation interrupted by user"
        )

    def test_returns_empty_string(self, mixin, llm_request):
        """Should return empty string (no visible interrupt message)."""
        result = mixin._handle_interrupted_generation(llm_request, 5)

        assert result == ""

    def test_sends_interrupt_signal(self, mixin, llm_request):
        """Should send interrupt signal with correct parameters."""
        mixin._handle_interrupted_generation(llm_request, 5)

        mixin.api.llm.send_llm_text_streamed_signal.assert_called_once()
        call_args = mixin.api.llm.send_llm_text_streamed_signal.call_args[0][0]
        assert isinstance(call_args, LLMResponse)
        assert call_args.message == ""
        assert call_args.is_end_of_message is True
        assert call_args.sequence_number == 6  # counter + 1

    def test_handles_none_request(self, mixin):
        """Should handle None request gracefully."""
        result = mixin._handle_interrupted_generation(None, 3)

        assert result == ""
        call_args = mixin.api.llm.send_llm_text_streamed_signal.call_args[0][0]
        assert call_args.node_id is None


class TestClampGenerationTokens:
    """Tests for max_new_tokens clamping to target context."""

    def test_clamps_when_over_target(self, mixin):
        mixin._target_context_length = 100
        generation_kwargs = {"max_new_tokens": 200}

        mixin._clamp_generation_tokens(generation_kwargs)

        assert generation_kwargs["max_new_tokens"] == 100
        mixin.logger.info.assert_called()

    def test_no_clamp_when_under_target(self, mixin):
        mixin._target_context_length = 100
        generation_kwargs = {"max_new_tokens": 50}

        mixin._clamp_generation_tokens(generation_kwargs)

        assert generation_kwargs["max_new_tokens"] == 50
        mixin.logger.info.assert_not_called()


class TestHandleGenerationError:
    """Tests for _handle_generation_error method."""

    def test_logs_error(self, mixin, llm_request):
        """Should log error with exc_info."""
        exc = ValueError("Test error")

        mixin._handle_generation_error(exc, llm_request)

        mixin.logger.error.assert_called_once()
        call_args = mixin.logger.error.call_args
        assert "Error during generation: Test error" in str(call_args)
        assert call_args[1]["exc_info"] is True

    def test_returns_error_message(self, mixin, llm_request):
        """Should return formatted error message."""
        exc = ValueError("Test error")

        result = mixin._handle_generation_error(exc, llm_request)

        assert result == "Error: Test error"

    def test_sends_error_signal(self, mixin, llm_request):
        """Should send error signal."""
        exc = ValueError("Test error")

        mixin._handle_generation_error(exc, llm_request)

        mixin.api.llm.send_llm_text_streamed_signal.assert_called_once()
        call_args = mixin.api.llm.send_llm_text_streamed_signal.call_args[0][0]
        assert isinstance(call_args, LLMResponse)
        assert call_args.message == "Error: Test error"
        assert call_args.is_end_of_message is False

    def test_handles_none_request(self, mixin):
        """Should handle None request gracefully."""
        exc = ValueError("Test error")

        result = mixin._handle_generation_error(exc, None)

        assert result == "Error: Test error"
        call_args = mixin.api.llm.send_llm_text_streamed_signal.call_args[0][0]
        assert call_args.node_id is None


class TestExtractFinalResponse:
    """Tests for _extract_final_response method."""

    def test_extracts_content_from_ai_message(self, mixin):
        """Should extract content from last AIMessage."""
        ai_msg = AIMessage(content="Final response")
        result = {"messages": [ai_msg]}

        extracted = mixin._extract_final_response(result)

        assert extracted == "Final response"

    def test_returns_empty_for_no_messages(self, mixin):
        """Should return empty string when no messages."""
        result = {"messages": []}

        extracted = mixin._extract_final_response(result)

        assert extracted == ""

    def test_returns_empty_for_missing_messages_key(self, mixin):
        """Should return empty string when messages key missing."""
        result = {}

        extracted = mixin._extract_final_response(result)

        assert extracted == ""

    def test_returns_empty_for_none_result(self, mixin):
        """Should return empty string for None result."""
        extracted = mixin._extract_final_response(None)

        assert extracted == ""

    def test_uses_last_ai_message(self, mixin):
        """Should use last AIMessage when multiple exist."""
        msg1 = AIMessage(content="First")
        msg2 = AIMessage(content="Second")
        msg3 = AIMessage(content="Third")
        result = {"messages": [msg1, msg2, msg3]}

        extracted = mixin._extract_final_response(result)

        assert extracted == "Third"

    def test_filters_non_ai_messages(self, mixin):
        """Should filter out non-AIMessage types."""
        from langchain_core.messages import HumanMessage

        human = HumanMessage(content="Human message")
        ai = AIMessage(content="AI message")
        result = {"messages": [human, ai, human]}

        extracted = mixin._extract_final_response(result)

        assert extracted == "AI message"

    def test_handles_empty_content(self, mixin):
        """Should return empty for AIMessage with no content."""
        ai_msg = AIMessage(content="")
        result = {"messages": [ai_msg]}

        extracted = mixin._extract_final_response(result)

        assert extracted == ""

    def test_handles_none_content(self, mixin):
        """Should return empty for AIMessage with None content."""
        ai_msg = AIMessage(content="")
        ai_msg.content = None  # Set to None after creation
        result = {"messages": [ai_msg]}

        extracted = mixin._extract_final_response(result)

        assert extracted == ""


class TestDoGenerate:
    """Tests for _do_generate method."""

    @patch("airunner.components.llm.managers.mixins.generation_mixin.torch")
    def test_basic_generation_flow(self, mock_torch, mixin, llm_request):
        """Should execute basic generation successfully."""
        mock_torch.cuda.is_available.return_value = True
        mixin._workflow_manager.stream.return_value = [
            AIMessage(content="Test response")
        ]

        result = mixin._do_generate(
            "Test prompt", LLMActionType.CHAT, llm_request=llm_request
        )

        assert result["response"] == "Test response"

    @patch("airunner.components.llm.managers.mixins.generation_mixin.torch")
    def test_reloads_model_on_path_mismatch(self, mock_torch, mixin):
        """Should reload model when path mismatch detected."""
        mixin._current_model_path = "/old/path"
        mixin.model_path = "/new/path"
        mixin._workflow_manager.stream.return_value = []

        mixin._do_generate("Test", LLMActionType.CHAT)

        mixin.unload.assert_called_once()
        mixin.load.assert_called_once()

    @patch("airunner.components.llm.managers.mixins.generation_mixin.torch")
    def test_creates_default_request_if_none(self, mock_torch, mixin):
        """Should create default LLMRequest if None provided."""
        mixin._workflow_manager.stream.return_value = []

        mixin._do_generate("Test", LLMActionType.CHAT, llm_request=None)

        # Should not raise exception
        assert True

    @patch("airunner.components.llm.managers.mixins.generation_mixin.torch")
    def test_sets_token_callback(self, mock_torch, mixin):
        """Should set and clear token callback."""
        mixin._workflow_manager.stream.return_value = []

        mixin._do_generate("Test", LLMActionType.CHAT)

        # Should be called twice: once to set, once to clear
        assert mixin._workflow_manager.set_token_callback.call_count == 2

    @patch("airunner.components.llm.managers.mixins.generation_mixin.torch")
    def test_resets_interrupted_flag(self, mock_torch, mixin):
        """Should reset interrupted flag before generation."""
        mixin._interrupted = True
        mixin._workflow_manager.stream.return_value = []

        mixin._do_generate("Test", LLMActionType.CHAT)

        assert mixin._interrupted is False

    @patch("airunner.components.llm.managers.mixins.generation_mixin.torch")
    def test_handles_interrupt_during_streaming(self, mock_torch, mixin):
        """Should handle interrupt during streaming."""

        def stream_with_interrupt(*args, **kwargs):
            mixin._interrupted = True
            yield AIMessage(content="Partial")

        mixin._workflow_manager.stream = stream_with_interrupt

        result = mixin._do_generate("Test", LLMActionType.CHAT)

        # Interrupt should end cleanly without adding visible text
        assert result["response"] == ""

    @patch("airunner.components.llm.managers.mixins.generation_mixin.torch")
    def test_handles_generation_error(self, mock_torch, mixin):
        """Should handle generation errors gracefully."""
        mixin._workflow_manager.stream.side_effect = ValueError("Test error")

        result = mixin._do_generate("Test", LLMActionType.CHAT)

        assert result["response"] == "Error: Test error"

    @patch("airunner.components.llm.managers.mixins.generation_mixin.torch")
    def test_clears_cuda_cache(self, mock_torch, mixin):
        """Should clear CUDA cache when available."""
        mock_torch.cuda.is_available.return_value = True
        mixin._workflow_manager.stream.return_value = []

        mixin._do_generate("Test", LLMActionType.CHAT)

        mock_torch.cuda.empty_cache.assert_called_once()
        mock_torch.cuda.synchronize.assert_called_once()

    @patch("airunner.components.llm.managers.mixins.generation_mixin.torch")
    def test_sends_end_of_message_signal(self, mock_torch, mixin, llm_request):
        """Should send end of message signal."""
        mixin._workflow_manager.stream.return_value = []

        mixin._do_generate("Test", LLMActionType.CHAT, llm_request=llm_request)

        # Should send at least one end-of-message signal
        calls = mixin.api.llm.send_llm_text_streamed_signal.call_args_list
        end_calls = [c for c in calls if c[0][0].is_end_of_message is True]
        assert len(end_calls) > 0

    @patch("airunner.components.llm.managers.mixins.generation_mixin.torch")
    def test_returns_error_when_no_workflow_manager(self, mock_torch, mixin):
        """Should return error when workflow manager missing."""
        mixin._workflow_manager = None

        result = mixin._do_generate("Test", LLMActionType.CHAT)

        assert result["response"] == "Error: workflow unavailable"


class TestSendFinalMessage:
    """Tests for _send_final_message method."""

    def test_sends_end_of_message_signal(self, mixin, llm_request):
        """Should send end-of-message signal."""
        mixin._send_final_message(llm_request)

        mixin.api.llm.send_llm_text_streamed_signal.assert_called_once()
        call_args = mixin.api.llm.send_llm_text_streamed_signal.call_args[0][0]
        assert isinstance(call_args, LLMResponse)
        assert call_args.is_end_of_message is True

    def test_includes_node_id(self, mixin, llm_request):
        """Should include node_id in signal."""
        mixin._send_final_message(llm_request)

        call_args = mixin.api.llm.send_llm_text_streamed_signal.call_args[0][0]
        assert call_args.node_id == "test-node"

    def test_handles_none_request(self, mixin):
        """Should handle None request gracefully."""
        mixin._send_final_message(None)

        call_args = mixin.api.llm.send_llm_text_streamed_signal.call_args[0][0]
        assert call_args.node_id is None


class TestDoSetSeed:
    """Tests for _do_set_seed method."""

    @patch("airunner.components.llm.managers.mixins.generation_mixin.random")
    @patch("airunner.components.llm.managers.mixins.generation_mixin.torch")
    def test_uses_override_settings(self, mock_torch, mock_random, mixin):
        """Should use override settings when enabled."""
        mixin.llm_generator_settings.override_parameters = True
        mixin.llm_generator_settings.seed = 42
        mixin.llm_generator_settings.random_seed = False
        mock_torch.cuda.is_available.return_value = True

        mixin._do_set_seed()

        mock_torch.manual_seed.assert_called_once_with(42)
        mock_random.seed.assert_called_once_with(42)

    @patch("airunner.components.llm.managers.mixins.generation_mixin.random")
    @patch("airunner.components.llm.managers.mixins.generation_mixin.torch")
    def test_uses_chatbot_settings(self, mock_torch, mock_random, mixin):
        """Should use chatbot settings when override disabled."""
        mixin.llm_generator_settings.override_parameters = False
        mixin.chatbot.seed = 99
        mixin.chatbot.random_seed = False
        mock_torch.cuda.is_available.return_value = True

        mixin._do_set_seed()

        mock_torch.manual_seed.assert_called_once_with(99)
        mock_random.seed.assert_called_once_with(99)

    @patch("airunner.components.llm.managers.mixins.generation_mixin.random")
    @patch("airunner.components.llm.managers.mixins.generation_mixin.torch")
    def test_sets_cuda_seeds(self, mock_torch, mock_random, mixin):
        """Should set CUDA seeds when CUDA available."""
        mixin.llm_generator_settings.override_parameters = True
        mixin.llm_generator_settings.seed = 42
        mixin.llm_generator_settings.random_seed = False
        mock_torch.cuda.is_available.return_value = True

        mixin._do_set_seed()

        mock_torch.cuda.manual_seed_all.assert_called_once_with(42)

    @patch("airunner.components.llm.managers.mixins.generation_mixin.random")
    @patch("airunner.components.llm.managers.mixins.generation_mixin.torch")
    def test_skips_seed_when_random_enabled(
        self, mock_torch, mock_random, mixin
    ):
        """Should not set seed when random_seed enabled."""
        mixin.llm_generator_settings.override_parameters = True
        mixin.llm_generator_settings.seed = 42
        mixin.llm_generator_settings.random_seed = True
        mock_torch.cuda.is_available.return_value = False

        mixin._do_set_seed()

        # Should not be called with the seed value
        mock_torch.manual_seed.assert_not_called()
        mock_random.seed.assert_not_called()
