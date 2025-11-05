"""Tests for QuantizationConfigMixin."""

from unittest.mock import Mock, patch, mock_open

import torch
from transformers import BitsAndBytesConfig


class TestableQuantizationMixin:
    """Test harness for QuantizationConfigMixin."""

    def __init__(self):
        """Initialize test harness with mock attributes."""
        from airunner.components.llm.managers.mixins.quantization_config_mixin import (
            QuantizationConfigMixin,
        )

        # Apply mixin
        self.__class__ = type(
            "TestableQuantization",
            (QuantizationConfigMixin,),
            dict(self.__class__.__dict__),
        )

        # Mock attributes expected by mixin
        self.logger = Mock()
        self.llm_dtype = None
        self.llm_generator_settings = Mock()
        self.torch_dtype = torch.float16
        self._model = Mock()

        # Mock methods used by mixin
        self._auto_select_quantization = Mock(return_value="4bit")
        self._get_quantized_model_path = Mock(
            return_value="/path/to/quantized"
        )
        self._check_quantized_model_exists = Mock(return_value=False)
        self._is_mistral3_model = Mock(return_value=False)


class TestSelectDtype:
    """Tests for _select_dtype method."""

    def test_uses_configured_dtype_when_set(self):
        """Should use configured dtype when not auto."""
        mixin = TestableQuantizationMixin()
        mixin.llm_dtype = "4bit"

        result = mixin._select_dtype()

        assert result == "4bit"
        mixin.logger.info.assert_any_call("Using configured dtype: 4bit")
        mixin._auto_select_quantization.assert_not_called()

    def test_auto_selects_when_dtype_is_auto(self):
        """Should auto-select quantization when dtype is 'auto'."""
        mixin = TestableQuantizationMixin()
        mixin.llm_dtype = "auto"
        mixin._auto_select_quantization.return_value = "8bit"

        result = mixin._select_dtype()

        assert result == "8bit"
        mixin._auto_select_quantization.assert_called_once()
        assert mixin.llm_generator_settings.dtype == "8bit"

    def test_auto_selects_when_dtype_is_none(self):
        """Should auto-select quantization when dtype is None."""
        mixin = TestableQuantizationMixin()
        mixin.llm_dtype = None

        result = mixin._select_dtype()

        assert result == "4bit"  # Mock default
        mixin._auto_select_quantization.assert_called_once()


class TestCreate8bitConfig:
    """Tests for _create_8bit_config method."""

    def test_creates_8bit_config_with_correct_params(self):
        """Should create 8-bit config with CPU offload enabled."""
        mixin = TestableQuantizationMixin()

        config = mixin._create_8bit_config()

        assert isinstance(config, BitsAndBytesConfig)
        assert config.load_in_8bit is True
        assert config.llm_int8_threshold == 6.0
        assert config.llm_int8_has_fp16_weight is False
        assert config.llm_int8_enable_fp32_cpu_offload is True
        mixin.logger.info.assert_called_with(
            "Created 8-bit BitsAndBytes config with CPU offload"
        )


class TestCreate4bitConfig:
    """Tests for _create_4bit_config method."""

    def test_creates_4bit_config_with_correct_params(self):
        """Should create 4-bit config with double quantization."""
        mixin = TestableQuantizationMixin()

        config = mixin._create_4bit_config("4bit")

        assert isinstance(config, BitsAndBytesConfig)
        assert config.load_in_4bit is True
        assert config.bnb_4bit_compute_dtype == torch.float16
        assert config.bnb_4bit_use_double_quant is True
        assert config.bnb_4bit_quant_type == "nf4"

    def test_warns_when_2bit_requested(self):
        """Should warn when 2-bit is requested and fall back to 4-bit."""
        mixin = TestableQuantizationMixin()

        config = mixin._create_4bit_config("2bit")

        assert config.load_in_4bit is True
        mixin.logger.warning.assert_any_call(
            "2-bit quantization requires GPTQ/AWQ with calibration dataset"
        )
        mixin.logger.warning.assert_any_call(
            "Falling back to 4-bit BitsAndBytes"
        )


class TestCreateBitsandbytesConfig:
    """Tests for _create_bitsandbytes_config method."""

    def test_returns_none_for_full_precision(self):
        """Should return None when dtype is not quantized."""
        mixin = TestableQuantizationMixin()

        config = mixin._create_bitsandbytes_config("float16")

        assert config is None
        mixin.logger.info.assert_any_call(
            "Loading full precision model (no quantization) - dtype=float16"
        )

    def test_creates_8bit_config(self):
        """Should create 8-bit config when dtype is '8bit'."""
        mixin = TestableQuantizationMixin()

        config = mixin._create_bitsandbytes_config("8bit")

        assert isinstance(config, BitsAndBytesConfig)
        assert config.load_in_8bit is True

    def test_creates_4bit_config(self):
        """Should create 4-bit config when dtype is '4bit'."""
        mixin = TestableQuantizationMixin()

        config = mixin._create_bitsandbytes_config("4bit")

        assert isinstance(config, BitsAndBytesConfig)
        assert config.load_in_4bit is True

    def test_handles_2bit_request(self):
        """Should handle 2-bit request and fall back to 4-bit."""
        mixin = TestableQuantizationMixin()

        config = mixin._create_bitsandbytes_config("2bit")

        assert isinstance(config, BitsAndBytesConfig)
        assert config.load_in_4bit is True


class TestConfigureCpuMemory:
    """Tests for _configure_cpu_memory method."""

    def test_returns_empty_dict_for_cpu_quantization(self):
        """Should return empty dict for CPU-only quantization."""
        mixin = TestableQuantizationMixin()

        result = mixin._configure_cpu_memory("4bit")

        assert result == {}
        mixin.logger.info.assert_any_call(
            "✓ Applying 4bit quantization (no CUDA)"
        )


class TestConfigureAutoMemory:
    """Tests for _configure_auto_memory method."""

    def test_returns_empty_dict_for_auto_allocation(self):
        """Should return empty dict for automatic memory allocation."""
        mixin = TestableQuantizationMixin()

        result = mixin._configure_auto_memory("float16")

        assert result == {}
        mixin.logger.info.assert_any_call("✓ Applying float16 quantization")


class TestConfigure8bitMemory:
    """Tests for _configure_8bit_memory method."""

    def test_configures_13gb_gpu_18gb_cpu(self):
        """Should configure 13GB GPU + 18GB CPU for 8-bit."""
        mixin = TestableQuantizationMixin()

        result = mixin._configure_8bit_memory()

        assert result == {0: "13GB", "cpu": "18GB"}
        mixin.logger.info.assert_any_call(
            "✓ Applying 8-bit quantization with CPU offload"
        )


class TestConfigure4bitMemory:
    """Tests for _configure_4bit_memory method."""

    def test_configures_14gb_gpu_only(self):
        """Should configure 14GB GPU only for 4-bit."""
        mixin = TestableQuantizationMixin()

        result = mixin._configure_4bit_memory()

        assert result == {0: "14GB"}
        mixin.logger.info.assert_any_call(
            "✓ Applying 4-bit quantization (GPU-only)"
        )


class TestConfigureQuantizationMemory:
    """Tests for _configure_quantization_memory method."""

    @patch("torch.cuda.is_available", return_value=False)
    def test_uses_cpu_config_when_no_cuda(self, mock_cuda):
        """Should use CPU config when CUDA not available."""
        mixin = TestableQuantizationMixin()

        result = mixin._configure_quantization_memory("4bit")

        assert result == {}

    @patch("torch.cuda.is_available", return_value=True)
    def test_uses_8bit_config_for_8bit_dtype(self, mock_cuda):
        """Should use 8-bit memory config when dtype is '8bit'."""
        mixin = TestableQuantizationMixin()

        result = mixin._configure_quantization_memory("8bit")

        assert result == {0: "13GB", "cpu": "18GB"}

    @patch("torch.cuda.is_available", return_value=True)
    def test_uses_4bit_config_for_4bit_dtype(self, mock_cuda):
        """Should use 4-bit memory config when dtype is '4bit'."""
        mixin = TestableQuantizationMixin()

        result = mixin._configure_quantization_memory("4bit")

        assert result == {0: "14GB"}

    @patch("torch.cuda.is_available", return_value=True)
    def test_uses_auto_config_for_other_dtype(self, mock_cuda):
        """Should use auto memory config for other dtypes."""
        mixin = TestableQuantizationMixin()

        result = mixin._configure_quantization_memory("float16")

        assert result == {}


class TestBuildQuantizationConfigDict:
    """Tests for _build_quantization_config_dict method."""

    def test_builds_4bit_config_dict(self):
        """Should build correct config dict for 4-bit."""
        mixin = TestableQuantizationMixin()

        config = mixin._build_quantization_config_dict("4bit")

        assert config["load_in_4bit"] is True
        assert config["load_in_8bit"] is False
        assert config["quant_method"] == "bitsandbytes"
        assert config["bnb_4bit_quant_type"] == "nf4"

    def test_builds_8bit_config_dict(self):
        """Should build correct config dict for 8-bit."""
        mixin = TestableQuantizationMixin()

        config = mixin._build_quantization_config_dict("8bit")

        assert config["load_in_8bit"] is True
        assert config["load_in_4bit"] is False
        assert config["llm_int8_threshold"] == 6.0


class TestSaveModelWeights:
    """Tests for _save_model_weights method."""

    def test_calls_save_pretrained_with_correct_params(self):
        """Should call save_pretrained with safe serialization."""
        mixin = TestableQuantizationMixin()
        mixin._model = Mock()

        mixin._save_model_weights("/path/to/save")

        mixin._model.save_pretrained.assert_called_once_with(
            "/path/to/save", safe_serialization=True, max_shard_size="5GB"
        )


class TestInjectQuantizationConfig:
    """Tests for _inject_quantization_config method."""

    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"model_type": "llama"}',
    )
    @patch("json.load")
    @patch("json.dump")
    def test_injects_config_into_json(self, mock_dump, mock_load, mock_file):
        """Should inject quantization config into config.json."""
        mixin = TestableQuantizationMixin()
        mock_load.return_value = {"model_type": "llama"}

        mixin._inject_quantization_config("/path/to/model", "4bit")

        # Verify json.load was called
        assert mock_load.called
        # Verify json.dump was called with updated config
        assert mock_dump.called
        dumped_config = mock_dump.call_args[0][0]
        assert "quantization_config" in dumped_config
        assert dumped_config["quantization_config"]["load_in_4bit"] is True


class TestCopyTokenizerFiles:
    """Tests for _copy_tokenizer_files method."""

    @patch("os.path.exists")
    @patch("shutil.copy2")
    def test_copies_standard_tokenizer_files(self, mock_copy, mock_exists):
        """Should copy standard tokenizer files when they exist."""
        mixin = TestableQuantizationMixin()
        mixin._is_mistral3_model.return_value = False
        mock_exists.return_value = True

        mixin._copy_tokenizer_files("/original", "/quantized")

        # Should copy 4 standard files
        assert mock_copy.call_count == 4

    @patch("os.path.exists")
    @patch("shutil.copy2")
    def test_copies_tekken_for_mistral3(self, mock_copy, mock_exists):
        """Should copy tekken.json for Mistral3 models."""
        mixin = TestableQuantizationMixin()
        mixin._is_mistral3_model.return_value = True
        mock_exists.return_value = True

        mixin._copy_tokenizer_files("/original", "/quantized")

        # Should copy 5 files (4 standard + tekken.json)
        assert mock_copy.call_count == 5

    @patch("os.path.exists")
    @patch("shutil.copy2")
    def test_skips_missing_files(self, mock_copy, mock_exists):
        """Should skip files that don't exist."""
        mixin = TestableQuantizationMixin()
        mixin._is_mistral3_model.return_value = False
        mock_exists.return_value = False

        mixin._copy_tokenizer_files("/original", "/quantized")

        # Should not copy any files if none exist
        mock_copy.assert_not_called()


class TestHandleSaveError:
    """Tests for _handle_save_error method."""

    @patch("os.path.exists", return_value=True)
    @patch("shutil.rmtree")
    def test_cleans_up_partial_save_on_error(self, mock_rmtree, mock_exists):
        """Should clean up partial save directory on error."""
        mixin = TestableQuantizationMixin()
        error = Exception("Save failed")

        mixin._handle_save_error(error, "/path/to/partial")

        mixin.logger.error.assert_called_with(
            "Failed to save quantized model: Save failed"
        )
        mock_rmtree.assert_called_once_with("/path/to/partial")

    @patch("os.path.exists", return_value=True)
    @patch("shutil.rmtree", side_effect=Exception("Cleanup failed"))
    def test_handles_cleanup_failure(self, mock_rmtree, mock_exists):
        """Should handle cleanup failures gracefully."""
        mixin = TestableQuantizationMixin()
        error = Exception("Save failed")

        mixin._handle_save_error(error, "/path/to/partial")

        # Should log both errors
        assert mixin.logger.error.call_count == 2

    @patch("os.path.exists", return_value=False)
    @patch("shutil.rmtree")
    def test_skips_cleanup_if_path_does_not_exist(
        self, mock_rmtree, mock_exists
    ):
        """Should skip cleanup if path doesn't exist."""
        mixin = TestableQuantizationMixin()
        error = Exception("Save failed")

        mixin._handle_save_error(error, "/path/to/nonexistent")

        mock_rmtree.assert_not_called()


class TestSaveQuantizedModelFiles:
    """Tests for _save_quantized_model_files method."""

    @patch("os.makedirs")
    def test_creates_directory_structure(self, mock_makedirs):
        """Should create quantized model directory."""
        mixin = TestableQuantizationMixin()
        mixin._save_model_weights = Mock()
        mixin._inject_quantization_config = Mock()
        mixin._copy_tokenizer_files = Mock()

        mixin._save_quantized_model_files("/quantized", "4bit", "/original")

        mock_makedirs.assert_called_once_with("/quantized", exist_ok=True)

    @patch("os.makedirs")
    def test_calls_all_save_steps(self, mock_makedirs):
        """Should call all save steps in order."""
        mixin = TestableQuantizationMixin()
        mixin._save_model_weights = Mock()
        mixin._inject_quantization_config = Mock()
        mixin._copy_tokenizer_files = Mock()

        mixin._save_quantized_model_files("/quantized", "4bit", "/original")

        mixin._save_model_weights.assert_called_once_with("/quantized")
        mixin._inject_quantization_config.assert_called_once_with(
            "/quantized", "4bit"
        )
        mixin._copy_tokenizer_files.assert_called_once_with(
            "/original", "/quantized"
        )

    @patch("os.makedirs", side_effect=Exception("Permission denied"))
    def test_handles_errors_during_save(self, mock_makedirs):
        """Should handle errors during save process."""
        mixin = TestableQuantizationMixin()
        mixin._handle_save_error = Mock()

        mixin._save_quantized_model_files("/quantized", "4bit", "/original")

        mixin._handle_save_error.assert_called_once()


class TestSaveLoadedModelQuantized:
    """Tests for _save_loaded_model_quantized method."""

    def test_skips_save_if_already_exists(self):
        """Should skip save if quantized model already exists."""
        mixin = TestableQuantizationMixin()
        mixin._check_quantized_model_exists.return_value = True
        mixin._save_quantized_model_files = Mock()

        mixin._save_loaded_model_quantized("/original", "4bit", Mock())

        mixin._save_quantized_model_files.assert_not_called()

    def test_saves_new_quantized_model(self):
        """Should save quantized model when it doesn't exist."""
        mixin = TestableQuantizationMixin()
        mixin._check_quantized_model_exists.return_value = False
        mixin._save_quantized_model_files = Mock()

        config = Mock()
        mixin._save_loaded_model_quantized("/original", "4bit", config)

        mixin._save_quantized_model_files.assert_called_once()
