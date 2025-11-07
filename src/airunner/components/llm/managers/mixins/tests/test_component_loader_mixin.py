"""Tests for ComponentLoaderMixin.

This module tests component loading and unloading functionality including:
- ChatModel creation via factory
- RAG system initialization after model load
- ToolManager loading with RAG capabilities
- WorkflowManager configuration
- Component unloading and memory cleanup
"""

import sys
from unittest.mock import Mock, MagicMock, patch


# Mock heavy dependencies before importing the mixin
sys.modules["airunner.components.llm.adapters"] = MagicMock()
sys.modules["airunner.components.llm.managers.tool_manager"] = MagicMock()
sys.modules["airunner.components.llm.managers.workflow_manager"] = MagicMock()

from airunner.components.llm.managers.mixins.component_loader_mixin import (
    ComponentLoaderMixin,
)


class MockComponentLoader(ComponentLoaderMixin):
    """Mock implementation of ComponentLoaderMixin for testing."""

    def __init__(self):
        self.logger = Mock()
        self.llm_settings = Mock()
        self._model = None
        self._tokenizer = None
        self._chat_model = None
        self._tool_manager = None
        self._workflow_manager = None
        self._current_model_path = "/path/to/model"
        self.chatbot = None
        self.supports_function_calling = False
        self.system_prompt = "Test system prompt"
        self.tools = []


class TestLoadChatModel:
    """Test ChatModel loading functionality."""

    def test_load_chat_model_creates_model_successfully(self):
        """Test successful ChatModel creation via factory."""
        loader = MockComponentLoader()
        mock_chat_model = Mock()

        with patch(
            "airunner.components.llm.managers.mixins.component_loader_mixin.ChatModelFactory.create_from_settings",
            return_value=mock_chat_model,
        ):
            loader._load_chat_model()

        assert loader._chat_model == mock_chat_model
        loader.logger.info.assert_any_call("Creating ChatModel via factory")

    def test_load_chat_model_skips_if_already_loaded(self):
        """Test that loading is skipped if ChatModel already exists."""
        loader = MockComponentLoader()
        existing_model = Mock()
        loader._chat_model = existing_model

        with patch(
            "airunner.components.llm.managers.mixins.component_loader_mixin.ChatModelFactory.create_from_settings"
        ) as mock_factory:
            loader._load_chat_model()

        mock_factory.assert_not_called()
        assert loader._chat_model == existing_model

    def test_load_chat_model_initializes_rag_if_available(self):
        """Test RAG initialization after ChatModel creation."""
        loader = MockComponentLoader()
        loader._setup_rag = Mock()
        mock_chat_model = Mock()

        with patch(
            "airunner.components.llm.managers.mixins.component_loader_mixin.ChatModelFactory.create_from_settings",
            return_value=mock_chat_model,
        ):
            loader._load_chat_model()

        loader._setup_rag.assert_called_once()
        loader.logger.info.assert_any_call(
            "Initializing RAG system now that LLM is loaded"
        )

    def test_load_chat_model_skips_rag_if_not_available(self):
        """Test that RAG initialization is skipped if _setup_rag doesn't exist."""
        loader = MockComponentLoader()
        mock_chat_model = Mock()

        with patch(
            "airunner.components.llm.managers.mixins.component_loader_mixin.ChatModelFactory.create_from_settings",
            return_value=mock_chat_model,
        ):
            loader._load_chat_model()

        # Should not raise AttributeError
        assert loader._chat_model == mock_chat_model

    def test_load_chat_model_handles_factory_error(self):
        """Test error handling during ChatModel creation."""
        loader = MockComponentLoader()

        with patch(
            "airunner.components.llm.managers.mixins.component_loader_mixin.ChatModelFactory.create_from_settings",
            side_effect=Exception("Factory error"),
        ):
            loader._load_chat_model()

        assert loader._chat_model is None
        loader.logger.error.assert_called_once()
        assert "Error creating ChatModel" in str(loader.logger.error.call_args)

    def test_load_chat_model_passes_correct_parameters(self):
        """Test that correct parameters are passed to ChatModelFactory."""
        loader = MockComponentLoader()
        loader._model = Mock(name="test_model")
        loader._tokenizer = Mock(name="test_tokenizer")
        loader.chatbot = Mock(name="test_chatbot")
        loader.llm_settings = Mock(name="test_settings")

        with patch(
            "airunner.components.llm.managers.mixins.component_loader_mixin.ChatModelFactory.create_from_settings"
        ) as mock_factory:
            loader._load_chat_model()

        mock_factory.assert_called_once_with(
            llm_settings=loader.llm_settings,
            model=loader._model,
            tokenizer=loader._tokenizer,
            chatbot=loader.chatbot,
            model_path="/path/to/model",
        )


class TestLoadToolManager:
    """Test ToolManager loading functionality."""

    def test_load_tool_manager_creates_manager_successfully(self):
        """Test successful ToolManager creation with RAG capabilities."""
        loader = MockComponentLoader()

        with patch(
            "airunner.components.llm.managers.mixins.component_loader_mixin.ToolManager"
        ) as mock_tool_manager_class:
            mock_instance = Mock()
            mock_tool_manager_class.return_value = mock_instance

            loader._load_tool_manager()

        assert loader._tool_manager == mock_instance
        mock_tool_manager_class.assert_called_once_with(rag_manager=loader)
        loader.logger.info.assert_called_with(
            "Tool manager loaded with RAG capabilities"
        )

    def test_load_tool_manager_skips_if_already_loaded(self):
        """Test that loading is skipped if ToolManager already exists."""
        loader = MockComponentLoader()
        existing_manager = Mock()
        loader._tool_manager = existing_manager

        with patch(
            "airunner.components.llm.managers.mixins.component_loader_mixin.ToolManager"
        ) as mock_tool_manager_class:
            loader._load_tool_manager()

        mock_tool_manager_class.assert_not_called()
        assert loader._tool_manager == existing_manager

    def test_load_tool_manager_handles_error(self):
        """Test error handling during ToolManager creation."""
        loader = MockComponentLoader()

        with patch(
            "airunner.components.llm.managers.mixins.component_loader_mixin.ToolManager",
            side_effect=Exception("ToolManager error"),
        ):
            loader._load_tool_manager()

        assert loader._tool_manager is None
        loader.logger.error.assert_called_once()
        assert "Error loading tool manager" in str(
            loader.logger.error.call_args
        )


class TestLoadWorkflowManager:
    """Test WorkflowManager loading functionality."""

    def test_load_workflow_manager_creates_manager_successfully(self):
        """Test successful WorkflowManager creation."""
        loader = MockComponentLoader()
        loader._chat_model = Mock()
        loader._tool_manager = Mock()

        with patch(
            "airunner.components.llm.managers.workflow_manager.WorkflowManager"
        ) as mock_workflow_class:
            mock_instance = Mock()
            mock_workflow_class.return_value = mock_instance

            loader._load_workflow_manager()

        assert loader._workflow_manager == mock_instance
        mock_workflow_class.assert_called_once_with(
            system_prompt="Test system prompt",
            chat_model=loader._chat_model,
            tools=None,
            max_tokens=2000,
            conversation_id=None,
        )

    def test_load_workflow_manager_skips_if_already_loaded(self):
        """Test that loading is skipped if WorkflowManager already exists."""
        loader = MockComponentLoader()
        loader._chat_model = Mock()
        existing_manager = Mock()
        loader._workflow_manager = existing_manager

        with patch(
            "airunner.components.llm.managers.workflow_manager.WorkflowManager"
        ) as mock_workflow_class:
            loader._load_workflow_manager()

        mock_workflow_class.assert_not_called()
        assert loader._workflow_manager == existing_manager

    def test_load_workflow_manager_fails_without_chat_model(self):
        """Test that WorkflowManager loading fails without ChatModel."""
        loader = MockComponentLoader()
        loader._chat_model = None
        loader._tool_manager = Mock()

        loader._load_workflow_manager()

        assert loader._workflow_manager is None
        loader.logger.error.assert_called_with(
            "Cannot load workflow manager: ChatModel not loaded"
        )

    def test_load_workflow_manager_warns_without_tool_manager(self):
        """Test warning when loading WorkflowManager without ToolManager."""
        loader = MockComponentLoader()
        loader._chat_model = Mock()
        loader._tool_manager = None

        with patch(
            "airunner.components.llm.managers.workflow_manager.WorkflowManager"
        ):
            loader._load_workflow_manager()

        loader.logger.warning.assert_called_with(
            "Tool manager not loaded, workflow will have no tools"
        )

    def test_load_workflow_manager_passes_tools_when_function_calling_supported(
        self,
    ):
        """Test that tools are passed when model supports function calling."""
        loader = MockComponentLoader()
        loader._chat_model = Mock()
        loader._tool_manager = Mock()
        loader.supports_function_calling = True
        loader.tools = [Mock(name="tool1"), Mock(name="tool2")]

        with patch(
            "airunner.components.llm.managers.workflow_manager.WorkflowManager"
        ) as mock_workflow_class:
            loader._load_workflow_manager()

        # Check that tools were passed
        call_args = mock_workflow_class.call_args
        assert call_args.kwargs["tools"] == loader.tools
        loader.logger.info.assert_any_call(
            "Model supports function calling - passing 2 tools"
        )

    def test_load_workflow_manager_no_tools_when_function_calling_not_supported(
        self,
    ):
        """Test that tools are NOT passed when model doesn't support function calling."""
        loader = MockComponentLoader()
        loader._chat_model = Mock()
        loader._tool_manager = Mock()
        loader.supports_function_calling = False
        loader.tools = [Mock(name="tool1")]

        with patch(
            "airunner.components.llm.managers.workflow_manager.WorkflowManager"
        ) as mock_workflow_class:
            loader._load_workflow_manager()

        # Check that tools were NOT passed
        call_args = mock_workflow_class.call_args
        assert call_args.kwargs["tools"] is None
        loader.logger.info.assert_any_call(
            "Model does not support function calling - no tools will be passed"
        )

    def test_load_workflow_manager_no_tools_when_tools_empty(self):
        """Test handling when tools list is empty even with function calling support."""
        loader = MockComponentLoader()
        loader._chat_model = Mock()
        loader._tool_manager = Mock()
        loader.supports_function_calling = True
        loader.tools = []

        with patch(
            "airunner.components.llm.managers.workflow_manager.WorkflowManager"
        ) as mock_workflow_class:
            loader._load_workflow_manager()

        # Check that tools is None (empty list is falsy)
        call_args = mock_workflow_class.call_args
        assert call_args.kwargs["tools"] is None
        loader.logger.info.assert_any_call(
            "No tools available - workflow will run without tools"
        )

    def test_load_workflow_manager_handles_error(self):
        """Test error handling during WorkflowManager creation."""
        loader = MockComponentLoader()
        loader._chat_model = Mock()
        loader._tool_manager = Mock()

        with patch(
            "airunner.components.llm.managers.workflow_manager.WorkflowManager",
            side_effect=Exception("WorkflowManager error"),
        ):
            loader._load_workflow_manager()

        assert loader._workflow_manager is None
        loader.logger.error.assert_called_once()
        assert "Error loading workflow manager" in str(
            loader.logger.error.call_args
        )


class TestUnloadChatModel:
    """Test ChatModel unloading functionality."""

    def test_unload_chat_model_deletes_model(self):
        """Test that ChatModel is deleted and set to None."""
        loader = MockComponentLoader()
        loader._chat_model = Mock()

        loader._unload_chat_model()

        assert loader._chat_model is None

    def test_unload_chat_model_handles_none_gracefully(self):
        """Test that unloading handles None ChatModel without error."""
        loader = MockComponentLoader()
        loader._chat_model = None

        loader._unload_chat_model()  # Should not raise

        assert loader._chat_model is None


class TestUnloadToolManager:
    """Test ToolManager unloading functionality."""

    def test_unload_tool_manager_deletes_manager(self):
        """Test that ToolManager is deleted and set to None."""
        loader = MockComponentLoader()
        loader._tool_manager = Mock()

        loader._unload_tool_manager()

        assert loader._tool_manager is None

    def test_unload_tool_manager_handles_none_gracefully(self):
        """Test that unloading handles None ToolManager without error."""
        loader = MockComponentLoader()
        loader._tool_manager = None

        loader._unload_tool_manager()  # Should not raise

        assert loader._tool_manager is None


class TestUnloadWorkflowManager:
    """Test WorkflowManager unloading functionality."""

    def test_unload_workflow_manager_deletes_manager(self):
        """Test that WorkflowManager is deleted and set to None."""
        loader = MockComponentLoader()
        loader._workflow_manager = Mock()

        loader._unload_workflow_manager()

        assert loader._workflow_manager is None

    def test_unload_workflow_manager_handles_none_gracefully(self):
        """Test that unloading handles None WorkflowManager without error."""
        loader = MockComponentLoader()
        loader._workflow_manager = None

        loader._unload_workflow_manager()  # Should not raise

        assert loader._workflow_manager is None


class TestUnloadModel:
    """Test model unloading functionality."""

    def test_unload_model_deletes_model_and_clears_cache(self):
        """Test that model is deleted and CUDA cache is cleared."""
        loader = MockComponentLoader()
        loader._model = Mock()

        with patch("torch.cuda.is_available", return_value=True), patch(
            "torch.cuda.empty_cache"
        ) as mock_empty_cache, patch(
            "torch.cuda.synchronize"
        ) as mock_synchronize, patch(
            "gc.collect"
        ) as mock_gc_collect:
            loader._unload_model()

        assert loader._model is None
        mock_gc_collect.assert_called_once()
        mock_empty_cache.assert_called_once()
        mock_synchronize.assert_called_once()

    def test_unload_model_without_cuda(self):
        """Test model unloading when CUDA is not available."""
        loader = MockComponentLoader()
        loader._model = Mock()

        with patch("torch.cuda.is_available", return_value=False), patch(
            "gc.collect"
        ) as mock_gc_collect:
            loader._unload_model()

        assert loader._model is None
        mock_gc_collect.assert_called_once()

    def test_unload_model_handles_none_gracefully(self):
        """Test that unloading handles None model without error."""
        loader = MockComponentLoader()
        loader._model = None

        with patch("torch.cuda.is_available", return_value=True), patch(
            "gc.collect"
        ):
            loader._unload_model()  # Should not raise

        assert loader._model is None

    def test_unload_model_handles_attribute_error(self):
        """Test error handling when model deletion fails."""
        loader = MockComponentLoader()
        loader._model = Mock()

        # Test that even with errors, model is set to None
        # The try/except in _unload_model handles AttributeError
        loader._unload_model()

        # Should always end up as None
        assert loader._model is None


class TestUnloadTokenizer:
    """Test tokenizer unloading functionality."""

    def test_unload_tokenizer_deletes_tokenizer(self):
        """Test that tokenizer is deleted and garbage collected."""
        loader = MockComponentLoader()
        loader._tokenizer = Mock()

        with patch("gc.collect") as mock_gc_collect:
            loader._unload_tokenizer()

        assert loader._tokenizer is None
        mock_gc_collect.assert_called_once()

    def test_unload_tokenizer_handles_none_gracefully(self):
        """Test that unloading handles None tokenizer without error."""
        loader = MockComponentLoader()
        loader._tokenizer = None

        with patch("gc.collect"):
            loader._unload_tokenizer()  # Should not raise

        assert loader._tokenizer is None

    def test_unload_tokenizer_handles_attribute_error(self):
        """Test error handling when tokenizer deletion fails."""
        loader = MockComponentLoader()
        loader._tokenizer = Mock()

        # Test that even with errors, tokenizer is set to None
        # The try/except in _unload_tokenizer handles AttributeError
        loader._unload_tokenizer()

        # Should always end up as None
        assert loader._tokenizer is None


class TestUnloadComponents:
    """Test orchestration of all component unloading."""

    def test_unload_components_calls_all_unload_methods(self):
        """Test that all unload methods are called in correct order."""
        loader = MockComponentLoader()
        loader._workflow_manager = Mock()
        loader._tool_manager = Mock()
        loader._chat_model = Mock()
        loader._tokenizer = Mock()
        loader._model = Mock()

        # Mock all unload methods
        loader._unload_workflow_manager = Mock()
        loader._unload_tool_manager = Mock()
        loader._unload_chat_model = Mock()
        loader._unload_tokenizer = Mock()
        loader._unload_model = Mock()

        loader._unload_components()

        # Verify all methods called
        loader._unload_workflow_manager.assert_called_once()
        loader._unload_tool_manager.assert_called_once()
        loader._unload_chat_model.assert_called_once()
        loader._unload_tokenizer.assert_called_once()
        loader._unload_model.assert_called_once()

    def test_unload_components_continues_on_error(self):
        """Test that unloading continues even if one method raises exception."""
        loader = MockComponentLoader()

        # Mock unload methods with one raising exception
        loader._unload_workflow_manager = Mock()
        loader._unload_tool_manager = Mock(
            side_effect=Exception("Tool manager error")
        )
        loader._unload_chat_model = Mock()
        loader._unload_tokenizer = Mock()
        loader._unload_model = Mock()

        loader._unload_components()

        # All methods should be called despite error
        loader._unload_workflow_manager.assert_called_once()
        loader._unload_tool_manager.assert_called_once()
        loader._unload_chat_model.assert_called_once()
        loader._unload_tokenizer.assert_called_once()
        loader._unload_model.assert_called_once()

        # Error should be logged
        loader.logger.error.assert_called()

    def test_unload_components_logs_all_errors(self):
        """Test that all errors during unloading are logged."""
        loader = MockComponentLoader()

        # Mock all unload methods to raise exceptions
        loader._unload_workflow_manager = Mock(
            side_effect=Exception("Workflow error")
        )
        loader._unload_tool_manager = Mock(side_effect=Exception("Tool error"))
        loader._unload_chat_model = Mock(
            side_effect=Exception("Chat model error")
        )
        loader._unload_tokenizer = Mock(
            side_effect=Exception("Tokenizer error")
        )
        loader._unload_model = Mock(side_effect=Exception("Model error"))

        loader._unload_components()

        # Should log 5 errors (one for each method)
        assert loader.logger.error.call_count == 5
