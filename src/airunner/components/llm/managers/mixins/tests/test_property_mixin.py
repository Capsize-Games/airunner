"""Unit tests for PropertyMixin."""

from unittest.mock import Mock, patch
import pytest

from airunner.components.llm.managers.mixins.property_mixin import (
    PropertyMixin,
)


class TestablePropertyMixin(PropertyMixin):
    """Testable version of PropertyMixin."""

    def __init__(self):
        """Initialize with mock dependencies."""
        self.logger = Mock()
        self._current_model_path = "/path/to/model"
        self._chat_model = Mock()
        self._tool_manager = Mock()
        self.llm_generator_settings = Mock()
        self.llm_generator_settings.model_path = "/path/to/model"
        self.llm_generator_settings.override_parameters = False
        self.llm_generator_settings.use_cache = True
        self.llm_generator_settings.model_version = "v1.0"
        self.chatbot = Mock()
        self.chatbot.use_cache = False
        self.chatbot.model_version = "v2.0"


@pytest.fixture
def mixin():
    """Create a testable PropertyMixin instance."""
    return TestablePropertyMixin()


class TestSupportsFunctionCalling:
    """Tests for supports_function_calling property."""

    @patch(
        "airunner.components.llm.managers.mixins.property_mixin."
        "LLMProviderConfig"
    )
    def test_returns_true_when_model_supports_function_calling(
        self, mock_config, mixin
    ):
        """Should return True for models with function calling support."""
        mock_config.LOCAL_MODELS = {
            "test_model": {
                "name": "test_model",
                "function_calling": True,
            }
        }
        mixin.llm_generator_settings.model_path = "/path/to/test_model"

        assert mixin.supports_function_calling is True

    @patch(
        "airunner.components.llm.managers.mixins.property_mixin."
        "LLMProviderConfig"
    )
    def test_returns_false_when_model_lacks_function_calling(
        self, mock_config, mixin
    ):
        """Should return False for models without function calling."""
        mock_config.LOCAL_MODELS = {
            "test_model": {
                "name": "test_model",
                "function_calling": False,
            }
        }
        mixin.llm_generator_settings.model_path = "/path/to/test_model"

        assert mixin.supports_function_calling is False

    @patch(
        "airunner.components.llm.managers.mixins.property_mixin."
        "LLMProviderConfig"
    )
    def test_returns_false_when_model_path_not_found(self, mock_config, mixin):
        """Should return False when model not in config."""
        mock_config.LOCAL_MODELS = {}
        mixin.llm_generator_settings.model_path = "/path/to/unknown_model"

        assert mixin.supports_function_calling is False

    def test_returns_false_when_no_model_path(self, mixin):
        """Should return False when model_path is None."""
        mixin.llm_generator_settings.model_path = None

        assert mixin.supports_function_calling is False

    @patch(
        "airunner.components.llm.managers.mixins.property_mixin."
        "LLMProviderConfig"
    )
    def test_handles_exceptions_gracefully(self, mock_config, mixin):
        """Should return False and log warning on exceptions."""
        mock_config.LOCAL_MODELS = Mock(side_effect=Exception("Config error"))

        assert mixin.supports_function_calling is False
        mixin.logger.warning.assert_called_once()


class TestTools:
    """Tests for tools property."""

    def test_returns_tools_from_tool_manager(self, mixin):
        """Should return tools from tool manager when available."""
        expected_tools = [Mock(), Mock()]
        mixin._tool_manager.get_all_tools.return_value = expected_tools

        assert mixin.tools == expected_tools
        mixin._tool_manager.get_all_tools.assert_called_once()

    def test_returns_empty_list_when_no_tool_manager(self, mixin):
        """Should return empty list when tool manager is None."""
        mixin._tool_manager = None

        assert mixin.tools == []


class TestIsMistral:
    """Tests for is_mistral property."""

    def test_returns_true_for_mistral_model(self, mixin):
        """Should return True when model path contains 'mistral'."""
        mixin._current_model_path = "/path/to/mistral-7b"

        assert mixin.is_mistral is True

    def test_returns_true_for_uppercase_mistral(self, mixin):
        """Should handle case-insensitive matching."""
        mixin._current_model_path = "/path/to/Mistral-7B"

        assert mixin.is_mistral is True

    def test_returns_false_for_non_mistral_model(self, mixin):
        """Should return False for non-Mistral models."""
        mixin._current_model_path = "/path/to/llama-2-7b"

        assert mixin.is_mistral is False

    def test_returns_false_when_no_model_path(self, mixin):
        """Should return False when model path is None."""
        mixin._current_model_path = None

        assert mixin.is_mistral is False


class TestIsLlamaInstruct:
    """Tests for is_llama_instruct property."""

    def test_returns_true_for_llama_instruct_model(self, mixin):
        """Should return True when path contains both 'llama' and 'instruct'."""
        mixin._current_model_path = "/path/to/llama-2-7b-instruct"

        assert mixin.is_llama_instruct is True

    def test_returns_true_for_uppercase_llama_instruct(self, mixin):
        """Should handle case-insensitive matching."""
        mixin._current_model_path = "/path/to/LLAMA-2-7B-INSTRUCT"

        assert mixin.is_llama_instruct is True

    def test_returns_false_for_llama_without_instruct(self, mixin):
        """Should return False for non-instruct LLaMA models."""
        mixin._current_model_path = "/path/to/llama-2-7b-chat"

        assert mixin.is_llama_instruct is False

    def test_returns_false_for_instruct_without_llama(self, mixin):
        """Should return False for non-LLaMA instruct models."""
        mixin._current_model_path = "/path/to/mistral-instruct"

        assert mixin.is_llama_instruct is False

    def test_returns_false_when_no_model_path(self, mixin):
        """Should return False when model path is None."""
        mixin._current_model_path = None

        assert mixin.is_llama_instruct is False


class TestGetAvailableVramGb:
    """Tests for _get_available_vram_gb method."""

    @patch(
        "airunner.components.llm.managers.mixins.property_mixin."
        "HardwareProfiler"
    )
    def test_creates_hardware_profiler_first_time(
        self, mock_profiler_class, mixin
    ):
        """Should create HardwareProfiler on first call."""
        mock_instance = Mock()
        mock_instance._get_available_vram_gb.return_value = 8.0
        mock_profiler_class.return_value = mock_instance

        # Remove _hw_profiler if exists
        if hasattr(mixin, "_hw_profiler"):
            delattr(mixin, "_hw_profiler")

        result = mixin._get_available_vram_gb()

        assert result == 8.0
        mock_profiler_class.assert_called_once()

    @patch(
        "airunner.components.llm.managers.mixins.property_mixin."
        "HardwareProfiler"
    )
    def test_reuses_hardware_profiler_on_subsequent_calls(
        self, mock_profiler_class, mixin
    ):
        """Should reuse existing HardwareProfiler instance."""
        mock_instance = Mock()
        mock_instance._get_available_vram_gb.return_value = 8.0
        mixin._hw_profiler = mock_instance

        result = mixin._get_available_vram_gb()

        assert result == 8.0
        mock_profiler_class.assert_not_called()


class TestUseCache:
    """Tests for use_cache property."""

    def test_returns_llm_generator_setting_when_override_enabled(self, mixin):
        """Should use llm_generator_settings when override is True."""
        mixin.llm_generator_settings.override_parameters = True
        mixin.llm_generator_settings.use_cache = True
        mixin.chatbot.use_cache = False

        assert mixin.use_cache is True

    def test_returns_chatbot_setting_when_override_disabled(self, mixin):
        """Should use chatbot setting when override is False."""
        mixin.llm_generator_settings.override_parameters = False
        mixin.llm_generator_settings.use_cache = True
        mixin.chatbot.use_cache = False

        assert mixin.use_cache is False


class TestModelVersion:
    """Tests for model_version property."""

    def test_returns_llm_generator_version_when_override_enabled(self, mixin):
        """Should use llm_generator_settings when override is True."""
        mixin.llm_generator_settings.override_parameters = True
        mixin.llm_generator_settings.model_version = "v1.0"
        mixin.chatbot.model_version = "v2.0"

        assert mixin.model_version == "v1.0"

    def test_returns_chatbot_version_when_override_disabled(self, mixin):
        """Should use chatbot version when override is False."""
        mixin.llm_generator_settings.override_parameters = False
        mixin.llm_generator_settings.model_version = "v1.0"
        mixin.chatbot.model_version = "v2.0"

        assert mixin.model_version == "v2.0"


class TestModelName:
    """Tests for model_name property."""

    def test_extracts_model_name_from_path(self, mixin):
        """Should return basename of model path."""
        mixin.llm_generator_settings.model_path = "/path/to/mistral-7b"

        assert mixin.model_name == "mistral-7b"

    def test_handles_path_with_trailing_slash(self, mixin):
        """Should normalize path with trailing slash."""
        mixin.llm_generator_settings.model_path = "/path/to/mistral-7b/"

        assert mixin.model_name == "mistral-7b"

    def test_raises_error_when_no_model_path(self, mixin):
        """Should raise ValueError when model path is not configured."""
        mixin.llm_generator_settings.model_path = None

        with pytest.raises(ValueError, match="No model path configured"):
            _ = mixin.model_name


class TestLlm:
    """Tests for llm property."""

    def test_returns_chat_model(self, mixin):
        """Should return the _chat_model instance."""
        expected_model = Mock()
        mixin._chat_model = expected_model

        assert mixin.llm == expected_model

    def test_returns_none_when_chat_model_not_loaded(self, mixin):
        """Should return None when chat model hasn't been loaded."""
        mixin._chat_model = None

        assert mixin.llm is None


class TestModelPath:
    """Tests for model_path property."""

    def test_returns_expanded_model_path(self, mixin):
        """Should return expanded absolute path from settings."""
        mixin.llm_generator_settings.model_path = "/path/to/model"

        assert mixin.model_path == "/path/to/model"

    def test_expands_tilde_in_path(self, mixin):
        """Should expand ~ to user home directory."""
        mixin.llm_generator_settings.model_path = "~/models/mistral-7b"

        result = mixin.model_path

        # Should not contain ~ after expansion
        assert "~" not in result
        assert "models/mistral-7b" in result

    def test_raises_error_when_no_model_path(self, mixin):
        """Should raise ValueError when model path is not configured."""
        mixin.llm_generator_settings.model_path = None

        with pytest.raises(ValueError, match="No model path configured"):
            _ = mixin.model_path
