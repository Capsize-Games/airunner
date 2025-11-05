"""Tests for AdapterLoaderMixin.

Tests adapter name retrieval from settings, adapter querying from database,
PEFT adapter application, and comprehensive adapter loading workflows.
"""

import pytest
from unittest.mock import Mock, patch

from airunner.components.llm.managers.mixins.adapter_loader_mixin import (
    AdapterLoaderMixin,
)
from airunner.components.llm.data.fine_tuned_model import FineTunedModel


class MockLLMManager(AdapterLoaderMixin):
    """Mock LLM manager for testing AdapterLoaderMixin."""

    def __init__(self):
        self.logger = Mock()
        self._model = Mock()


@pytest.fixture
def manager():
    """Create mock manager instance."""
    return MockLLMManager()


@pytest.fixture
def mock_adapter():
    """Create mock FineTunedModel instance."""
    adapter = Mock(spec=FineTunedModel)
    adapter.name = "test-adapter"
    adapter.adapter_path = "/path/to/adapter"
    return adapter


# Settings Retrieval Tests


@patch(
    "airunner.components.llm.managers.mixins.adapter_loader_mixin.get_qsettings"
)
def test_get_enabled_adapter_names_success(mock_qsettings, manager):
    """Test retrieving enabled adapter names from QSettings."""
    mock_qs = Mock()
    mock_qs.value.return_value = '["adapter1", "adapter2"]'
    mock_qsettings.return_value = mock_qs

    result = manager._get_enabled_adapter_names()

    assert result == ["adapter1", "adapter2"]
    mock_qs.value.assert_called_once_with(
        "llm_settings/enabled_adapters", "[]"
    )


@patch(
    "airunner.components.llm.managers.mixins.adapter_loader_mixin.get_qsettings"
)
def test_get_enabled_adapter_names_empty(mock_qsettings, manager):
    """Test retrieving empty adapter list from QSettings."""
    mock_qs = Mock()
    mock_qs.value.return_value = "[]"
    mock_qsettings.return_value = mock_qs

    result = manager._get_enabled_adapter_names()

    assert result == []


@patch(
    "airunner.components.llm.managers.mixins.adapter_loader_mixin.get_qsettings"
)
def test_get_enabled_adapter_names_json_decode_error(mock_qsettings, manager):
    """Test handling of invalid JSON in adapter settings."""
    mock_qs = Mock()
    mock_qs.value.return_value = "invalid json"
    mock_qsettings.return_value = mock_qs

    result = manager._get_enabled_adapter_names()

    assert result == []
    assert manager.logger.error.called


# Database Query Tests


def test_get_enabled_adapters_empty_names(manager):
    """Test querying adapters with empty names list."""
    result = manager._get_enabled_adapters([])

    assert result == []


@patch(
    "airunner.components.llm.managers.mixins.adapter_loader_mixin.FineTunedModel"
)
def test_get_enabled_adapters_success(mock_model_class, manager, mock_adapter):
    """Test successfully querying adapters from database."""
    adapter2 = Mock(spec=FineTunedModel)
    adapter2.name = "other-adapter"

    mock_model_class.objects.all.return_value = [mock_adapter, adapter2]

    result = manager._get_enabled_adapters(["test-adapter"])

    assert len(result) == 1
    assert result[0].name == "test-adapter"


@patch(
    "airunner.components.llm.managers.mixins.adapter_loader_mixin.FineTunedModel"
)
def test_get_enabled_adapters_multiple_matches(mock_model_class, manager):
    """Test querying multiple matching adapters."""
    adapter1 = Mock(spec=FineTunedModel)
    adapter1.name = "adapter-1"
    adapter2 = Mock(spec=FineTunedModel)
    adapter2.name = "adapter-2"
    adapter3 = Mock(spec=FineTunedModel)
    adapter3.name = "adapter-3"

    mock_model_class.objects.all.return_value = [adapter1, adapter2, adapter3]

    result = manager._get_enabled_adapters(["adapter-1", "adapter-3"])

    assert len(result) == 2
    assert adapter1 in result
    assert adapter3 in result
    assert adapter2 not in result


@patch(
    "airunner.components.llm.managers.mixins.adapter_loader_mixin.FineTunedModel"
)
def test_get_enabled_adapters_database_error(mock_model_class, manager):
    """Test handling database query errors (table not exists)."""
    mock_model_class.objects.all.side_effect = Exception(
        "Table does not exist"
    )

    result = manager._get_enabled_adapters(["adapter1"])

    assert result == []
    assert manager.logger.error.called


# Adapter Application Tests


@patch(
    "airunner.components.llm.managers.mixins.adapter_loader_mixin.PeftModel"
)
@patch(
    "airunner.components.llm.managers.mixins.adapter_loader_mixin.os.path.exists"
)
def test_apply_adapter_success(mock_exists, mock_peft, manager, mock_adapter):
    """Test successfully applying PEFT adapter to model."""
    mock_exists.return_value = True
    mock_peft_model = Mock()
    mock_peft.from_pretrained.return_value = mock_peft_model

    result = manager._apply_adapter(mock_adapter)

    assert result is True
    assert manager._model == mock_peft_model
    mock_peft_model.eval.assert_called_once()
    # Verify from_pretrained was called with the adapter path
    assert mock_peft.from_pretrained.called
    call_args = mock_peft.from_pretrained.call_args
    assert call_args[0][1] == "/path/to/adapter"


@patch(
    "airunner.components.llm.managers.mixins.adapter_loader_mixin.os.path.exists"
)
def test_apply_adapter_no_path(mock_exists, manager, mock_adapter):
    """Test adapter application fails when adapter_path is None."""
    mock_adapter.adapter_path = None

    result = manager._apply_adapter(mock_adapter)

    assert result is False
    assert manager.logger.warning.called


@patch(
    "airunner.components.llm.managers.mixins.adapter_loader_mixin.os.path.exists"
)
def test_apply_adapter_path_not_exists(mock_exists, manager, mock_adapter):
    """Test adapter application fails when path doesn't exist."""
    mock_exists.return_value = False

    result = manager._apply_adapter(mock_adapter)

    assert result is False
    mock_exists.assert_called_once_with("/path/to/adapter")
    assert manager.logger.warning.called


@patch(
    "airunner.components.llm.managers.mixins.adapter_loader_mixin.PeftModel"
)
@patch(
    "airunner.components.llm.managers.mixins.adapter_loader_mixin.os.path.exists"
)
def test_apply_adapter_loading_error(
    mock_exists, mock_peft, manager, mock_adapter
):
    """Test handling errors during adapter loading."""
    mock_exists.return_value = True
    mock_peft.from_pretrained.side_effect = RuntimeError("CUDA out of memory")

    result = manager._apply_adapter(mock_adapter)

    assert result is False
    assert manager.logger.error.called


# Full Adapter Loading Workflow Tests


@patch(
    "airunner.components.llm.managers.mixins.adapter_loader_mixin.PeftModel",
    None,
)
def test_load_adapters_peft_not_available(manager):
    """Test load_adapters returns early when PeftModel not installed."""
    manager._get_enabled_adapter_names = Mock()

    manager._load_adapters()

    manager._get_enabled_adapter_names.assert_not_called()


@patch(
    "airunner.components.llm.managers.mixins.adapter_loader_mixin.PeftModel"
)
def test_load_adapters_no_enabled_adapters(mock_peft, manager):
    """Test load_adapters returns early when no adapters enabled."""
    manager._get_enabled_adapter_names = Mock(return_value=[])
    manager._get_enabled_adapters = Mock()

    manager._load_adapters()

    manager._get_enabled_adapters.assert_not_called()


@patch(
    "airunner.components.llm.managers.mixins.adapter_loader_mixin.PeftModel"
)
def test_load_adapters_success_single(mock_peft, manager, mock_adapter):
    """Test successfully loading single adapter."""
    manager._get_enabled_adapter_names = Mock(return_value=["test-adapter"])
    manager._get_enabled_adapters = Mock(return_value=[mock_adapter])
    manager._apply_adapter = Mock(return_value=True)

    manager._load_adapters()

    manager._apply_adapter.assert_called_once_with(mock_adapter)
    assert manager.logger.info.called
    log_message = manager.logger.info.call_args[0][0]
    assert "1 adapter(s)" in log_message


@patch(
    "airunner.components.llm.managers.mixins.adapter_loader_mixin.PeftModel"
)
def test_load_adapters_success_multiple(mock_peft, manager):
    """Test successfully loading multiple adapters."""
    adapter1 = Mock(spec=FineTunedModel)
    adapter1.name = "adapter-1"
    adapter2 = Mock(spec=FineTunedModel)
    adapter2.name = "adapter-2"

    manager._get_enabled_adapter_names = Mock(
        return_value=["adapter-1", "adapter-2"]
    )
    manager._get_enabled_adapters = Mock(return_value=[adapter1, adapter2])
    manager._apply_adapter = Mock(return_value=True)

    manager._load_adapters()

    assert manager._apply_adapter.call_count == 2
    assert manager.logger.info.called
    log_message = manager.logger.info.call_args[0][0]
    assert "2 adapter(s)" in log_message


@patch(
    "airunner.components.llm.managers.mixins.adapter_loader_mixin.PeftModel"
)
def test_load_adapters_partial_success(mock_peft, manager):
    """Test loading adapters when some fail."""
    adapter1 = Mock(spec=FineTunedModel)
    adapter1.name = "adapter-1"
    adapter2 = Mock(spec=FineTunedModel)
    adapter2.name = "adapter-2"

    manager._get_enabled_adapter_names = Mock(
        return_value=["adapter-1", "adapter-2"]
    )
    manager._get_enabled_adapters = Mock(return_value=[adapter1, adapter2])
    manager._apply_adapter = Mock(side_effect=[True, False])

    manager._load_adapters()

    assert manager.logger.info.called
    log_message = manager.logger.info.call_args[0][0]
    assert "1 adapter(s)" in log_message  # Only 1 succeeded


@patch(
    "airunner.components.llm.managers.mixins.adapter_loader_mixin.PeftModel"
)
def test_load_adapters_all_fail(mock_peft, manager):
    """Test loading adapters when all fail."""
    adapter1 = Mock(spec=FineTunedModel)

    manager._get_enabled_adapter_names = Mock(return_value=["adapter-1"])
    manager._get_enabled_adapters = Mock(return_value=[adapter1])
    manager._apply_adapter = Mock(return_value=False)

    manager._load_adapters()

    # No success message logged when loaded_count is 0
    assert not manager.logger.info.called


@patch(
    "airunner.components.llm.managers.mixins.adapter_loader_mixin.PeftModel"
)
def test_load_adapters_exception_handling(mock_peft, manager):
    """Test handling exceptions during adapter loading workflow."""
    manager._get_enabled_adapter_names = Mock(
        side_effect=RuntimeError("Settings error")
    )

    manager._load_adapters()

    assert manager.logger.error.called
