"""Tests for local LLM execution ownership boundaries."""

from unittest.mock import Mock, patch

from airunner.components.llm.managers.mixins.component_loader_mixin import (
    ComponentLoaderMixin,
)
from airunner.components.llm.managers.mixins.status_management_mixin import (
    StatusManagementMixin,
)
from airunner.components.llm.managers.mixins.validation_mixin import (
    ValidationMixin,
)


class LocalExecutionHarness(
    ComponentLoaderMixin,
    ValidationMixin,
    StatusManagementMixin,
):
    """Minimal harness for local execution ownership tests."""

    def __init__(self):
        self.logger = Mock()
        self.llm_settings = Mock(use_local_llm=True, use_api=False)
        self._model = None
        self._tokenizer = None
        self._chat_model = None
        self._tool_manager = None
        self._workflow_manager = None
        self._current_model_path = "/tmp/model"
        self.chatbot = None
        self.api = Mock()
        self.emit_signal = Mock()
        self.change_model_status = Mock()
        self.load_conversation = Mock()
        self._pending_conversation_message = None

    def _is_gguf_quantization_selected(self):
        return False

    def _is_mistral3_model(self):
        return False


def test_component_loader_releases_manager_owned_local_components():
    """Local execution ownership should move into the chat adapter."""
    harness = LocalExecutionHarness()
    harness._model = Mock(name="transformers_model")
    harness._tokenizer = Mock(name="transformers_tokenizer")
    chat_model = Mock(model=harness._model, tokenizer=harness._tokenizer)

    with patch(
        "airunner.components.llm.managers.mixins.component_loader_mixin.ChatModelFactory.create_from_settings",
        return_value=chat_model,
    ):
        harness._load_chat_model()

    assert harness._chat_model is chat_model
    assert harness._model is None
    assert harness._tokenizer is None


def test_validation_accepts_chat_model_owned_local_components():
    """Local loaded checks should accept adapter-owned model components."""
    harness = LocalExecutionHarness()
    harness._chat_model = Mock(model=Mock(), tokenizer=Mock())
    harness._workflow_manager = Mock()

    assert harness._check_components_loaded_for_local() is True


def test_status_logging_skips_backend_failures_when_adapter_owns_them():
    """Status logging should not report missing backend components spuriously."""
    harness = LocalExecutionHarness()
    harness._chat_model = Mock(model=Mock(), tokenizer=Mock())
    harness._workflow_manager = Mock()

    harness._log_component_failures()

    logged_errors = [call.args[0] for call in harness.logger.error.call_args_list]
    assert "Model failed to load" not in logged_errors
    assert "Tokenizer failed to load" not in logged_errors