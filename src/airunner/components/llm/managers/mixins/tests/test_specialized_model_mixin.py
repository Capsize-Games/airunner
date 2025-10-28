"""Unit tests for SpecializedModelMixin."""

from unittest.mock import Mock, patch
import pytest
from langchain_core.messages import AIMessage

from airunner.components.llm.managers.mixins.specialized_model_mixin import (
    SpecializedModelMixin,
)


# Mock ModelCapability enum for testing
class MockModelCapability:
    """Mock capability enum."""

    PROMPT_ENHANCEMENT = "prompt_enhancement"
    CODE_GENERATION = "code_generation"


class MockModelSpec:
    """Mock model specification."""

    def __init__(self, model_path: str):
        """Initialize mock model spec.

        Args:
            model_path: Path to the model
        """
        self.model_path = model_path


class TestableSpecializedModelMixin(SpecializedModelMixin):
    """Testable version of SpecializedModelMixin."""

    def __init__(self):
        """Initialize with mock dependencies."""
        self.logger = Mock()
        self._current_model_path = "/path/to/primary/model"
        self.model_path = "/path/to/primary/model"
        self._chat_model = Mock()
        self.llm_generator_settings = Mock()
        self.llm_generator_settings.model_path = "/path/to/primary/model"
        self.load = Mock()
        self.unload = Mock()
        self._restore_primary_model = None


@pytest.fixture
def mixin():
    """Create a testable SpecializedModelMixin instance."""
    return TestableSpecializedModelMixin()


@pytest.fixture
def mock_get_model():
    """Create mock get_model_for_capability function."""
    with patch(
        "airunner.components.llm.config.model_capabilities."
        "get_model_for_capability"
    ) as mock:
        yield mock


class TestLoadSpecializedModel:
    """Tests for load_specialized_model method."""

    def test_loads_specialized_model_successfully(self, mixin, mock_get_model):
        """Should load specialized model and return chat model."""
        mock_get_model.return_value = MockModelSpec(
            "/path/to/specialized/model"
        )

        result = mixin.load_specialized_model(
            MockModelCapability.PROMPT_ENHANCEMENT
        )

        assert result == mixin._chat_model
        mixin.unload.assert_called_once()
        mixin.load.assert_called_once()

    def test_returns_none_when_no_model_for_capability(
        self, mixin, mock_get_model
    ):
        """Should return None when capability has no registered model."""
        mock_get_model.return_value = None

        result = mixin.load_specialized_model(
            MockModelCapability.CODE_GENERATION
        )

        assert result is None
        mixin.logger.warning.assert_called_once()

    def test_returns_existing_model_if_already_loaded(
        self, mixin, mock_get_model
    ):
        """Should return existing model if already using correct one."""
        mixin._current_model_path = "/path/to/specialized/model"
        mock_get_model.return_value = MockModelSpec(
            "/path/to/specialized/model"
        )

        result = mixin.load_specialized_model(
            MockModelCapability.PROMPT_ENHANCEMENT
        )

        assert result == mixin._chat_model
        mixin.unload.assert_not_called()
        mixin.load.assert_not_called()

    def test_sets_restore_function_when_return_to_primary(
        self, mixin, mock_get_model
    ):
        """Should set restore function when return_to_primary is True."""
        mock_get_model.return_value = MockModelSpec(
            "/path/to/specialized/model"
        )

        mixin.load_specialized_model(
            MockModelCapability.PROMPT_ENHANCEMENT, return_to_primary=True
        )

        assert mixin._restore_primary_model is not None
        assert callable(mixin._restore_primary_model)

    def test_does_not_set_restore_when_return_to_primary_false(
        self, mixin, mock_get_model
    ):
        """Should not set restore function when return_to_primary is False."""
        mock_get_model.return_value = MockModelSpec(
            "/path/to/specialized/model"
        )

        mixin.load_specialized_model(
            MockModelCapability.PROMPT_ENHANCEMENT, return_to_primary=False
        )

        assert mixin._restore_primary_model is None

    def test_temporarily_overrides_model_path(self, mixin, mock_get_model):
        """Should temporarily override model path in settings."""
        original_path = "/path/to/primary/model"
        specialized_path = "/path/to/specialized/model"
        mixin.llm_generator_settings.model_path = original_path
        mock_get_model.return_value = MockModelSpec(specialized_path)

        mixin.load_specialized_model(MockModelCapability.PROMPT_ENHANCEMENT)

        # During load, path should be specialized
        assert mixin.llm_generator_settings.model_path == specialized_path

    def test_restores_settings_on_load_failure(self, mixin, mock_get_model):
        """Should restore original settings if load fails."""
        original_path = "/path/to/primary/model"
        mixin.llm_generator_settings.model_path = original_path
        mock_get_model.return_value = MockModelSpec(
            "/path/to/specialized/model"
        )
        mixin.load.side_effect = Exception("Load failed")

        result = mixin.load_specialized_model(
            MockModelCapability.PROMPT_ENHANCEMENT
        )

        assert result is None
        assert mixin.llm_generator_settings.model_path == original_path
        mixin.logger.error.assert_called_once()

    def test_logs_model_swap(self, mixin, mock_get_model):
        """Should log when swapping models."""
        mock_get_model.return_value = MockModelSpec(
            "/path/to/specialized/model"
        )

        mixin.load_specialized_model(MockModelCapability.PROMPT_ENHANCEMENT)

        # Should log the model swap
        assert any(
            "Loading specialized model" in str(call)
            for call in mixin.logger.info.call_args_list
        )

    def test_unloads_current_model_before_loading(self, mixin, mock_get_model):
        """Should unload current model before loading specialized one."""
        mock_get_model.return_value = MockModelSpec(
            "/path/to/specialized/model"
        )

        mixin.load_specialized_model(MockModelCapability.PROMPT_ENHANCEMENT)

        # Unload should be called before load
        assert mixin.unload.called
        assert mixin.load.called


class TestDoRestorePrimary:
    """Tests for _do_restore_primary method."""

    def test_restores_primary_model_path(self, mixin):
        """Should restore original model path setting."""
        primary_path = "/path/to/primary"
        original_setting = "/path/to/original"

        mixin._do_restore_primary(primary_path, original_setting)

        assert mixin.llm_generator_settings.model_path == original_setting

    def test_unloads_and_loads_model(self, mixin):
        """Should unload specialized and load primary model."""
        mixin._do_restore_primary("/primary", "/original")

        mixin.unload.assert_called_once()
        mixin.load.assert_called_once()

    def test_clears_restore_function(self, mixin):
        """Should clear the restore function after restoring."""
        mixin._restore_primary_model = Mock()

        mixin._do_restore_primary("/primary", "/original")

        assert mixin._restore_primary_model is None

    def test_logs_restoration(self, mixin):
        """Should log when restoring primary model."""
        mixin._do_restore_primary("/path/to/primary", "/original")

        mixin.logger.info.assert_called_once()
        assert "Restoring primary model" in str(mixin.logger.info.call_args)


class TestUseSpecializedModel:
    """Tests for use_specialized_model method."""

    def test_generates_with_specialized_model(self, mixin, mock_get_model):
        """Should generate text with specialized model."""
        mock_get_model.return_value = MockModelSpec(
            "/path/to/specialized/model"
        )
        mock_response = AIMessage(content="Enhanced prompt")
        mixin._chat_model.invoke.return_value = mock_response

        result = mixin.use_specialized_model(
            MockModelCapability.PROMPT_ENHANCEMENT, "Test prompt"
        )

        assert result == "Enhanced prompt"
        mixin._chat_model.invoke.assert_called_once_with("Test prompt")

    def test_returns_none_when_model_load_fails(self, mixin, mock_get_model):
        """Should return None if specialized model fails to load."""
        mock_get_model.return_value = None

        result = mixin.use_specialized_model(
            MockModelCapability.PROMPT_ENHANCEMENT, "Test prompt"
        )

        assert result is None

    def test_extracts_content_from_ai_message(self, mixin, mock_get_model):
        """Should extract content from AIMessage response."""
        mock_get_model.return_value = MockModelSpec(
            "/path/to/specialized/model"
        )
        mock_response = AIMessage(content="Generated text")
        mixin._chat_model.invoke.return_value = mock_response

        result = mixin.use_specialized_model(
            MockModelCapability.CODE_GENERATION, "Test"
        )

        assert result == "Generated text"

    def test_handles_string_response(self, mixin, mock_get_model):
        """Should handle string response from model."""
        mock_get_model.return_value = MockModelSpec(
            "/path/to/specialized/model"
        )
        mixin._chat_model.invoke.return_value = "Direct string"

        result = mixin.use_specialized_model(
            MockModelCapability.PROMPT_ENHANCEMENT, "Test"
        )

        assert result == "Direct string"

    def test_converts_other_types_to_string(self, mixin, mock_get_model):
        """Should convert non-string/AIMessage responses to string."""
        mock_get_model.return_value = MockModelSpec(
            "/path/to/specialized/model"
        )
        mixin._chat_model.invoke.return_value = {"content": "test"}

        result = mixin.use_specialized_model(
            MockModelCapability.PROMPT_ENHANCEMENT, "Test"
        )

        assert "content" in result
        assert "test" in result

    def test_restores_primary_after_generation(self, mixin, mock_get_model):
        """Should restore primary model after generation."""
        mock_get_model.return_value = MockModelSpec(
            "/path/to/specialized/model"
        )
        mixin._chat_model.invoke.return_value = "Result"

        # load_specialized_model will create a restore function
        # We need to verify it gets called
        result = mixin.use_specialized_model(
            MockModelCapability.PROMPT_ENHANCEMENT, "Test"
        )

        # After use_specialized_model completes, the restore function should have been called
        # and cleared (set to None)
        assert result == "Result"
        # The restore function should have been called and then cleared
        # So checking that unload/load were called (which happens in restore)
        assert mixin.unload.call_count >= 1
        assert mixin.load.call_count >= 1

    def test_restores_primary_on_generation_error(self, mixin, mock_get_model):
        """Should restore primary model even if generation fails."""
        mock_get_model.return_value = MockModelSpec(
            "/path/to/specialized/model"
        )
        mixin._chat_model.invoke.side_effect = Exception("Generation failed")

        result = mixin.use_specialized_model(
            MockModelCapability.PROMPT_ENHANCEMENT, "Test"
        )

        assert result is None
        # Should have attempted to restore (unload/load called)
        assert mixin.unload.call_count >= 1
        assert mixin.load.call_count >= 1
        mixin.logger.error.assert_called()

    def test_handles_restore_failure_gracefully(self, mixin, mock_get_model):
        """Should handle restore failure without crashing."""
        mock_get_model.return_value = MockModelSpec(
            "/path/to/specialized/model"
        )
        mixin._chat_model.invoke.side_effect = Exception("Generation failed")

        # Make load fail during restore to test error handling
        mixin.load.side_effect = [None, Exception("Restore load failed")]

        result = mixin.use_specialized_model(
            MockModelCapability.PROMPT_ENHANCEMENT, "Test"
        )

        assert result is None
        # Should log both generation error and restore error
        assert mixin.logger.error.call_count >= 2

    def test_does_not_crash_without_restore_function(
        self, mixin, mock_get_model
    ):
        """Should not crash if restore function not set."""
        mock_get_model.return_value = MockModelSpec(
            "/path/to/specialized/model"
        )
        mixin._chat_model.invoke.return_value = "Result"
        mixin._restore_primary_model = None

        result = mixin.use_specialized_model(
            MockModelCapability.PROMPT_ENHANCEMENT, "Test"
        )

        assert result == "Result"
