"""Tests for ModelLoaderMixin.

Tests GPU memory management, Mistral3 detection, model loading workflows,
quantization configuration, and error handling.
"""

import pytest
from unittest.mock import Mock, patch
from transformers import AutoConfig, BitsAndBytesConfig
import torch

from airunner.components.llm.managers.mixins.model_loader_mixin import (
    ModelLoaderMixin,
)
from airunner.components.llm.config.provider_config import LLMProviderConfig


class MockLLMManager(ModelLoaderMixin):
    """Mock LLM manager for testing ModelLoaderMixin."""

    def __init__(self):
        self.logger = Mock()
        self._model = None
        self.model_path = "/path/to/model"
        self.attn_implementation = "flash_attention_2"
        self.use_cache = True
        self.torch_dtype = torch.float16
        self.device = "cuda:0"

        # Add methods that ModelLoaderMixin depends on
        self._select_dtype = Mock(return_value="4bit")
        self._get_quantized_model_path = Mock(
            return_value="/path/to/quantized"
        )
        self._check_quantized_model_exists = Mock(return_value=False)
        self._create_bitsandbytes_config = Mock(
            return_value=BitsAndBytesConfig()
        )
        self._configure_quantization_memory = Mock(return_value={"0": "20GB"})
        self._load_adapters = Mock()
        self._save_loaded_model_quantized = Mock()

        # Context/Yarn settings
        self.llm_generator_settings = Mock(model_id=None)
        self.llm_settings = Mock(use_yarn=False)


@pytest.fixture
def manager():
    """Create mock manager instance."""
    return MockLLMManager()


# GPU Memory Management Tests


@patch(
    "airunner.components.llm.managers.mixins.model_loader_mixin.torch.cuda.is_available"
)
@patch(
    "airunner.components.llm.managers.mixins.model_loader_mixin.clear_memory"
)
@patch(
    "airunner.components.llm.managers.mixins.model_loader_mixin.gpu_memory_stats"
)
def test_log_gpu_memory_status_cuda_available(
    mock_gpu_stats, mock_clear, mock_cuda_available, manager
):
    """Test GPU memory logging when CUDA is available."""
    mock_cuda_available.return_value = True
    mock_gpu_stats.return_value = {
        "total": 24.0,
        "allocated": 10.0,
        "free": 14.0,
    }

    manager._log_gpu_memory_status()

    mock_clear.assert_called_once_with(device=0)
    mock_gpu_stats.assert_called_once()
    assert manager.logger.info.called
    log_message = manager.logger.info.call_args[0][0]
    assert "14.00GB free" in log_message
    assert "24.00GB total" in log_message


@patch(
    "airunner.components.llm.managers.mixins.model_loader_mixin.torch.cuda.is_available"
)
def test_log_gpu_memory_status_no_cuda(mock_cuda_available, manager):
    """Test GPU memory logging when CUDA is not available."""
    mock_cuda_available.return_value = False

    manager._log_gpu_memory_status()

    assert not manager.logger.info.called


# Mistral3 Detection Tests


def test_detect_mistral3_model_by_type(manager):
    """Test Mistral3 detection via model_type attribute."""
    config = Mock(spec=AutoConfig)
    config.model_type = "mistral3"
    config.architectures = None

    result = manager._detect_mistral3_model(config)

    assert result is True


def test_detect_mistral3_model_by_architecture(manager):
    """Test Mistral3 detection via architectures list."""
    config = Mock(spec=AutoConfig)
    config.model_type = "other"
    config.architectures = ["Mistral3ForConditionalGeneration"]

    result = manager._detect_mistral3_model(config)

    assert result is True


def test_detect_mistral3_model_partial_architecture_match(manager):
    """Test Mistral3 detection with partial architecture name match."""
    config = Mock(spec=AutoConfig)
    config.model_type = "other"
    config.architectures = ["SomeMistral3Model"]

    result = manager._detect_mistral3_model(config)

    assert result is True


def test_detect_mistral3_model_not_mistral3(manager):
    """Test Mistral3 detection returns False for non-Mistral3 models."""
    config = Mock(spec=AutoConfig)
    config.model_type = "llama"
    config.architectures = ["LlamaForCausalLM"]

    result = manager._detect_mistral3_model(config)

    assert result is False


def test_detect_mistral3_model_no_architectures(manager):
    """Test Mistral3 detection with None architectures."""
    config = Mock(spec=AutoConfig)
    config.model_type = "llama"
    config.architectures = None

    result = manager._detect_mistral3_model(config)

    assert result is False


# Base Model Kwargs Preparation Tests


def test_prepare_base_model_kwargs_non_mistral3(manager):
    """Test base kwargs preparation for non-Mistral3 models."""
    result = manager._prepare_base_model_kwargs(is_mistral3=False)

    assert result["local_files_only"] is True
    assert result["trust_remote_code"] is True
    assert result["attn_implementation"] == "flash_attention_2"
    assert result["use_cache"] is True


def test_prepare_base_model_kwargs_mistral3(manager):
    """Test base kwargs preparation for Mistral3 models (no use_cache)."""
    result = manager._prepare_base_model_kwargs(is_mistral3=True)

    assert result["local_files_only"] is True
    assert result["trust_remote_code"] is True
    assert result["attn_implementation"] == "flash_attention_2"
    assert "use_cache" not in result


# Quantization Kwargs Application Tests


def test_apply_quantization_to_kwargs_full_precision(manager):
    """Test applying full precision kwargs when no quantization config."""
    model_kwargs = {}

    manager._apply_quantization_to_kwargs(model_kwargs, None, "none")

    assert model_kwargs["torch_dtype"] == torch.float16
    assert model_kwargs["device_map"] == "cuda:0"
    assert manager.logger.warning.called


def test_apply_quantization_to_kwargs_with_config(manager):
    """Test applying quantization kwargs with BitsAndBytes config."""
    model_kwargs = {}
    quantization_config = BitsAndBytesConfig(load_in_4bit=True)

    manager._apply_quantization_to_kwargs(
        model_kwargs, quantization_config, "4bit"
    )

    assert model_kwargs["quantization_config"] == quantization_config
    assert model_kwargs["device_map"] == "auto"
    assert model_kwargs["dtype"] == torch.float16
    assert "max_memory" in model_kwargs


def test_apply_full_precision_kwargs(manager):
    """Test applying full precision configuration."""
    model_kwargs = {}

    manager._apply_full_precision_kwargs(model_kwargs)

    assert model_kwargs["torch_dtype"] == torch.float16
    assert model_kwargs["device_map"] == "cuda:0"
    assert manager.logger.warning.called


def test_apply_quantized_kwargs(manager):
    """Test applying quantized configuration."""
    model_kwargs = {}
    quantization_config = BitsAndBytesConfig(load_in_8bit=True)

    manager._apply_quantized_kwargs(model_kwargs, quantization_config, "8bit")

    assert model_kwargs["quantization_config"] == quantization_config
    assert model_kwargs["device_map"] == "auto"
    assert model_kwargs["max_memory"] == {"0": "20GB"}


def test_apply_quantized_kwargs_no_max_memory(manager):
    """Test applying quantized kwargs when no max_memory configured."""
    manager._configure_quantization_memory.return_value = None
    model_kwargs = {}
    quantization_config = BitsAndBytesConfig(load_in_4bit=True)

    manager._apply_quantized_kwargs(model_kwargs, quantization_config, "4bit")

    assert "max_memory" not in model_kwargs


def test_apply_context_settings_with_yarn(manager):
    """Should apply YaRN rope scaling when supported and enabled."""
    # Avoid creating AutoConfig() directly (requires network). Use a minimal dummy config.
    class DummyConfig:
        pass

    config = DummyConfig()
    config.max_position_embeddings = 32768

    manager.llm_generator_settings.model_id = "qwen3-8b"
    manager.llm_settings.use_yarn = True

    with patch.object(
        LLMProviderConfig,
        "get_model_info",
        return_value={
            "native_context_length": 32768,
            "yarn_max_context_length": 131072,
            "supports_yarn": True,
        },
    ):
        result = manager._apply_context_settings(config)

    assert config.rope_scaling["type"] == "yarn"
    assert config.rope_scaling["original_max_position_embeddings"] == 32768
    assert config.max_position_embeddings == 131072
    assert result["use_yarn"] is True
    assert result["target_context_length"] == 131072


def test_apply_context_settings_without_yarn(manager):
    """Should leave config unchanged when YaRN disabled."""
    class DummyConfig:
        pass

    config = DummyConfig()
    config.max_position_embeddings = 32768

    manager.llm_generator_settings.model_id = "qwen3-8b"
    manager.llm_settings.use_yarn = False

    with patch.object(
        LLMProviderConfig,
        "get_model_info",
        return_value={
            "native_context_length": 32768,
            "yarn_max_context_length": 131072,
            "supports_yarn": True,
        },
    ):
        result = manager._apply_context_settings(config)

    assert not hasattr(config, "rope_scaling") or not config.rope_scaling
    assert config.max_position_embeddings == 32768
    assert result["use_yarn"] is False
    assert result["target_context_length"] == 32768


# Model Loading Tests


@patch(
    "airunner.components.llm.managers.mixins.model_loader_mixin.AutoModelForCausalLM"
)
def test_load_standard_model_success(mock_auto_model, manager):
    """Test loading standard causal LM model successfully."""
    mock_model = Mock()
    mock_auto_model.from_pretrained.return_value = mock_model
    model_kwargs = {"device_map": "auto"}

    manager._load_standard_model("/path/to/model", model_kwargs)

    assert manager._model == mock_model
    mock_auto_model.from_pretrained.assert_called_once_with(
        "/path/to/model", **model_kwargs
    )


@patch("airunner.components.llm.managers.mixins.model_loader_mixin.AutoModel")
@patch(
    "airunner.components.llm.managers.mixins.model_loader_mixin.AutoModelForCausalLM"
)
def test_load_standard_model_unrecognized_architecture(
    mock_causal_lm, mock_auto_model, manager
):
    """Test fallback to AutoModel for unrecognized architecture."""
    mock_causal_lm.from_pretrained.side_effect = ValueError(
        "Unrecognized configuration class <class 'CustomConfig'>"
    )
    mock_model = Mock()
    mock_auto_model.from_pretrained.return_value = mock_model
    model_kwargs = {"device_map": "auto"}

    manager._load_standard_model("/path/to/model", model_kwargs)

    assert manager._model == mock_model
    assert manager.logger.warning.called
    assert manager.logger.info.called
    mock_auto_model.from_pretrained.assert_called_once_with(
        "/path/to/model", **model_kwargs
    )


@patch(
    "airunner.components.llm.managers.mixins.model_loader_mixin.AutoModelForCausalLM"
)
def test_load_standard_model_other_value_error(mock_auto_model, manager):
    """Test that non-architecture errors are re-raised."""
    mock_auto_model.from_pretrained.side_effect = ValueError(
        "Some other error"
    )

    with pytest.raises(ValueError, match="Some other error"):
        manager._load_standard_model("/path/to/model", {})


@patch(
    "airunner.components.llm.managers.mixins.model_loader_mixin.Mistral3ForConditionalGeneration"
)
def test_load_mistral3_model_success(mock_mistral3, manager):
    """Test loading Mistral3 model successfully."""
    mock_model = Mock()
    mock_mistral3.from_pretrained.return_value = mock_model
    model_kwargs = {"device_map": "auto"}

    manager._load_mistral3_model("/path/to/model", model_kwargs)

    assert manager._model == mock_model
    assert manager.logger.info.call_count == 2  # Loading + success messages


@patch(
    "airunner.components.llm.managers.mixins.model_loader_mixin.Mistral3ForConditionalGeneration",
    None,
)
def test_load_mistral3_model_not_available(manager):
    """Test loading Mistral3 model when class not available."""
    with pytest.raises(
        ImportError, match="Mistral3ForConditionalGeneration not available"
    ):
        manager._load_mistral3_model("/path/to/model", {})


def test_load_model_from_pretrained_mistral3(manager):
    """Test loading from pretrained delegates to Mistral3 loader."""
    manager._load_mistral3_model = Mock()
    model_kwargs = {"device_map": "auto"}

    manager._load_model_from_pretrained("/path/to/model", True, model_kwargs)

    manager._load_mistral3_model.assert_called_once_with(
        "/path/to/model", model_kwargs
    )


def test_load_model_from_pretrained_standard(manager):
    """Test loading from pretrained delegates to standard loader."""
    manager._load_standard_model = Mock()
    model_kwargs = {"device_map": "auto"}

    manager._load_model_from_pretrained("/path/to/model", False, model_kwargs)

    manager._load_standard_model.assert_called_once_with(
        "/path/to/model", model_kwargs
    )


# Pre-quantized Model Loading Tests


def test_should_use_pre_quantized_4bit_exists(manager):
    """Test should use pre-quantized model for 4bit when it exists."""
    manager._check_quantized_model_exists.return_value = True

    result = manager._should_use_pre_quantized("4bit", "/path/to/quantized")

    assert result is True


def test_should_use_pre_quantized_8bit_exists(manager):
    """Test should use pre-quantized model for 8bit when it exists."""
    manager._check_quantized_model_exists.return_value = True

    result = manager._should_use_pre_quantized("8bit", "/path/to/quantized")

    assert result is True


def test_should_use_pre_quantized_not_exists(manager):
    """Test should not use pre-quantized when it doesn't exist."""
    manager._check_quantized_model_exists.return_value = False

    result = manager._should_use_pre_quantized("4bit", "/path/to/quantized")

    assert result is False


def test_should_use_pre_quantized_full_precision(manager):
    """Test should not use pre-quantized for full precision."""
    result = manager._should_use_pre_quantized("none", "/path/to/quantized")

    assert result is False


@patch("airunner.components.llm.managers.mixins.model_loader_mixin.AutoConfig")
def test_load_pre_quantized_model(mock_auto_config, manager):
    """Test loading pre-quantized model from disk."""
    mock_config = Mock(spec=AutoConfig)
    mock_config.model_type = "llama"
    mock_config.architectures = ["LlamaForCausalLM"]
    mock_auto_config.from_pretrained.return_value = mock_config

    manager._load_model_from_pretrained = Mock()

    manager._load_pre_quantized_model("/path/to/quantized", "4bit")

    assert manager.logger.info.call_count == 2
    manager._load_model_from_pretrained.assert_called_once()


@patch("airunner.components.llm.managers.mixins.model_loader_mixin.AutoConfig")
def test_load_quantized_model_config(mock_auto_config, manager):
    """Test loading configuration for pre-quantized model."""
    mock_config = Mock()
    mock_auto_config.from_pretrained.return_value = mock_config

    result = manager._load_quantized_model_config("/path/to/quantized")

    assert result == mock_config
    mock_auto_config.from_pretrained.assert_called_once_with(
        "/path/to/quantized",
        local_files_only=True,
        trust_remote_code=True,
    )


def test_prepare_pre_quantized_kwargs(manager):
    """Test preparing kwargs for pre-quantized model (no quantization_config)."""
    result = manager._prepare_pre_quantized_kwargs(is_mistral3=False)

    assert "quantization_config" not in result
    assert result["device_map"] == "auto"
    assert result["torch_dtype"] == torch.float16


# Runtime Quantization Tests


@patch("airunner.components.llm.managers.mixins.model_loader_mixin.AutoConfig")
def test_load_with_runtime_quantization(mock_auto_config, manager):
    """Test loading model with runtime quantization."""
    mock_config = Mock(spec=AutoConfig)
    mock_config.model_type = "llama"
    mock_config.architectures = ["LlamaForCausalLM"]
    mock_auto_config.from_pretrained.return_value = mock_config

    manager._load_model_from_pretrained = Mock()
    quantization_config = BitsAndBytesConfig(load_in_4bit=True)
    manager._create_bitsandbytes_config.return_value = quantization_config

    manager._load_with_runtime_quantization("4bit")

    manager._load_model_from_pretrained.assert_called_once()
    manager._save_loaded_model_quantized.assert_called_once()


@patch("airunner.components.llm.managers.mixins.model_loader_mixin.AutoConfig")
def test_load_model_config_for_runtime_quantization(mock_auto_config, manager):
    """Test loading model config for runtime quantization."""
    mock_config = Mock()
    mock_auto_config.from_pretrained.return_value = mock_config

    result = manager._load_model_config_for_runtime_quantization()

    assert result == mock_config
    mock_auto_config.from_pretrained.assert_called_once()


def test_prepare_runtime_quantization_kwargs(manager):
    """Test preparing kwargs for runtime quantization."""
    quantization_config = BitsAndBytesConfig(load_in_8bit=True)

    result = manager._prepare_runtime_quantization_kwargs(
        is_mistral3=False,
        quantization_config=quantization_config,
        dtype="8bit",
    )

    assert result["quantization_config"] == quantization_config
    assert result["device_map"] == "auto"


# Save Quantized Model Tests


def test_save_quantized_if_applicable_4bit(manager):
    """Test saving 4bit quantized model after runtime quantization."""
    quantization_config = BitsAndBytesConfig(load_in_4bit=True)

    manager._save_quantized_if_applicable("4bit", quantization_config)

    manager._save_loaded_model_quantized.assert_called_once_with(
        "/path/to/model", "4bit", quantization_config
    )


def test_save_quantized_if_applicable_8bit(manager):
    """Test saving 8bit quantized model after runtime quantization."""
    quantization_config = BitsAndBytesConfig(load_in_8bit=True)

    manager._save_quantized_if_applicable("8bit", quantization_config)

    manager._save_loaded_model_quantized.assert_called_once_with(
        "/path/to/model", "8bit", quantization_config
    )


def test_save_quantized_if_applicable_full_precision(manager):
    """Test no save for full precision models."""
    manager._save_quantized_if_applicable("none", None)

    manager._save_loaded_model_quantized.assert_not_called()


def test_save_quantized_if_applicable_error_handling(manager):
    """Test error handling when save fails."""
    quantization_config = BitsAndBytesConfig(load_in_4bit=True)
    manager._save_loaded_model_quantized.side_effect = RuntimeError(
        "Disk full"
    )

    manager._save_quantized_if_applicable("4bit", quantization_config)

    assert manager.logger.warning.called


# Main Load Method Tests


@patch(
    "airunner.components.llm.managers.mixins.model_loader_mixin.torch.cuda.is_available"
)
def test_load_model_already_loaded(mock_cuda, manager):
    """Test load_model returns early if model already loaded."""
    manager._model = Mock()  # Model already loaded
    manager._execute_model_loading = Mock()

    manager._load_model()

    manager._execute_model_loading.assert_not_called()


@patch(
    "airunner.components.llm.managers.mixins.model_loader_mixin.torch.cuda.is_available"
)
def test_load_model_executes_loading(mock_cuda, manager):
    """Test load_model executes loading when model is None."""
    mock_cuda.return_value = False
    manager._execute_model_loading = Mock()

    manager._load_model()

    manager._execute_model_loading.assert_called_once()


@patch(
    "airunner.components.llm.managers.mixins.model_loader_mixin.torch.cuda.is_available"
)
def test_load_model_handles_errors(mock_cuda, manager):
    """Test load_model handles exceptions during loading."""
    mock_cuda.return_value = False
    manager._execute_model_loading = Mock(
        side_effect=RuntimeError("CUDA out of memory")
    )

    manager._load_model()

    assert manager._model is None
    assert manager.logger.error.called


def test_execute_model_loading_uses_pre_quantized(manager):
    """Test execute_model_loading uses pre-quantized when available."""
    manager._select_dtype.return_value = "4bit"
    manager._check_quantized_model_exists.return_value = True
    manager._load_pre_quantized_model = Mock()

    manager._execute_model_loading()

    manager._load_pre_quantized_model.assert_called_once()


def test_execute_model_loading_uses_runtime_quantization(manager):
    """Test execute_model_loading uses runtime quantization when needed."""
    manager._select_dtype.return_value = "4bit"
    manager._check_quantized_model_exists.return_value = False
    manager._load_with_runtime_quantization = Mock()

    manager._execute_model_loading()

    manager._load_with_runtime_quantization.assert_called_once()
    assert manager.logger.info.called


def test_execute_model_loading_loads_adapters(manager):
    """Test execute_model_loading loads adapters after model."""
    manager._select_dtype.return_value = "none"
    manager._load_with_runtime_quantization = Mock()

    manager._execute_model_loading()

    manager._load_adapters.assert_called_once()


def test_load_with_runtime_or_full_precision_quantized(manager):
    """Test loading with runtime quantization for quantized dtypes."""
    manager._load_with_runtime_quantization = Mock()

    manager._load_with_runtime_or_full_precision("4bit")

    assert manager.logger.info.called
    manager._load_with_runtime_quantization.assert_called_once_with("4bit")


def test_load_with_runtime_or_full_precision_full(manager):
    """Test loading with full precision for non-quantized dtypes."""
    manager._load_with_runtime_quantization = Mock()

    manager._load_with_runtime_or_full_precision("none")

    manager._load_with_runtime_quantization.assert_called_once_with("none")


def test_handle_model_loading_error(manager):
    """Test error handling logs traceback and sets model to None."""
    error = ValueError("Invalid model path")

    manager._handle_model_loading_error(error)

    assert manager._model is None
    assert manager.logger.error.call_count == 2  # Error + traceback
