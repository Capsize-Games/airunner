"""Quantization configuration management for LLM models.

This mixin handles:
- Automatic dtype selection
- BitsAndBytes quantization configuration
- Memory limits for quantized models
- Saving quantized models to disk
"""

import json
import os
import shutil
from typing import Any, Dict, Optional, TYPE_CHECKING

import torch
from transformers import BitsAndBytesConfig

if TYPE_CHECKING:
    pass


class QuantizationConfigMixin:
    """Mixin for LLM quantization configuration and management."""

    def _select_dtype(self) -> str:
        """Select and configure quantization dtype.

        Auto-selects quantization if dtype is "auto", otherwise uses
        the configured dtype setting.

        Returns:
            Selected dtype string (e.g., "4bit", "8bit", "float16")
        """
        dtype = self.llm_dtype
        self.logger.info(f"Current dtype setting: {dtype}")

        if not dtype or dtype == "auto":
            dtype = self._auto_select_quantization()
            self.llm_generator_settings.dtype = dtype
            self.logger.info(f"✓ Auto-selected quantization: {dtype}")
        else:
            self.logger.info(f"Using configured dtype: {dtype}")

        return dtype

    def _create_bitsandbytes_config(
        self, dtype: str
    ) -> Optional[BitsAndBytesConfig]:
        """Create BitsAndBytes quantization configuration.

        Args:
            dtype: Quantization type ("8bit", "4bit", "2bit", or full precision)

        Returns:
            BitsAndBytesConfig if quantization requested, None for full precision
        """
        if dtype not in ["8bit", "4bit", "2bit"]:
            self.logger.info(
                f"Loading full precision model (no quantization) - dtype={dtype}"
            )
            return None

        self.logger.info(f"Using BitsAndBytes runtime {dtype} quantization")

        if dtype == "8bit":
            return self._create_8bit_config()

        if dtype in ["4bit", "2bit"]:
            return self._create_4bit_config(dtype)

        return None

    def _create_8bit_config(self) -> BitsAndBytesConfig:
        """Create 8-bit quantization configuration.

        Returns:
            BitsAndBytesConfig for 8-bit quantization with CPU offload
        """
        config = BitsAndBytesConfig(
            load_in_8bit=True,
            llm_int8_threshold=6.0,
            llm_int8_has_fp16_weight=False,
            llm_int8_enable_fp32_cpu_offload=True,
        )
        self.logger.info("Created 8-bit BitsAndBytes config with CPU offload")
        return config

    def _create_4bit_config(self, dtype: str) -> BitsAndBytesConfig:
        """Create 4-bit quantization configuration.

        Args:
            dtype: Requested dtype ("4bit" or "2bit")

        Returns:
            BitsAndBytesConfig for 4-bit quantization (2-bit falls back to 4-bit)
        """
        if dtype == "2bit":
            self.logger.warning(
                "2-bit quantization requires GPTQ/AWQ with calibration dataset"
            )
            self.logger.warning("Falling back to 4-bit BitsAndBytes")

        config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.bfloat16,  # bfloat16 is faster and more stable than float16
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
        )
        self.logger.info("Created 4-bit BitsAndBytes config with bfloat16 compute")
        return config

    def _configure_quantization_memory(self, dtype: str) -> Dict[str, Any]:
        """Configure memory limits for quantization.

        Different quantization levels need different memory allocations:
        - 8-bit: 13GB GPU + 18GB CPU (with CPU offload)
        - 4-bit: 14GB GPU only (reserves 1.5GB for activations)
        - Other: Auto allocation

        Args:
            dtype: Quantization type

        Returns:
            Dictionary with max_memory configuration for device_map
        """
        if not torch.cuda.is_available():
            return self._configure_cpu_memory(dtype)

        if dtype == "8bit":
            return self._configure_8bit_memory()

        if dtype == "4bit":
            return self._configure_4bit_memory()

        return self._configure_auto_memory(dtype)

    def _configure_cpu_memory(self, dtype: str) -> Dict[str, Any]:
        """Configure memory for CPU-only quantization.

        Args:
            dtype: Quantization type

        Returns:
            Empty dict for auto allocation
        """
        self.logger.info(f"✓ Applying {dtype} quantization (no CUDA)")
        self.logger.info(
            f"  Using device_map='auto', dtype={self.torch_dtype}"
        )
        return {}

    def _configure_auto_memory(self, dtype: str) -> Dict[str, Any]:
        """Configure automatic memory allocation.

        Args:
            dtype: Quantization type

        Returns:
            Empty dict for auto allocation
        """
        self.logger.info(f"✓ Applying {dtype} quantization")
        self.logger.info(
            f"  Using device_map='auto', dtype={self.torch_dtype}"
        )
        return {}

    def _configure_8bit_memory(self) -> Dict[str, Any]:
        """Configure memory limits for 8-bit quantization.

        Returns:
            Max memory dict with 13GB GPU + 18GB CPU
        """
        self.logger.info("✓ Applying 8-bit quantization with CPU offload")
        self.logger.info(
            f"  Using device_map='auto', dtype={self.torch_dtype}, "
            "max_memory=13GB GPU + 18GB CPU"
        )
        return {0: "13GB", "cpu": "18GB"}

    def _configure_4bit_memory(self) -> Dict[str, Any]:
        """Configure memory limits for 4-bit quantization.

        Returns:
            Max memory dict with 14GB GPU (reserves 1.5GB for activations)
        """
        self.logger.info("✓ Applying 4-bit quantization (GPU-only)")
        self.logger.info(
            f"  Using device_map='auto', dtype={self.torch_dtype}, "
            "max_memory=14GB GPU (reserves 1.5GB for activations)"
        )
        return {0: "14GB"}

    def _save_loaded_model_quantized(
        self,
        original_path: str,
        dtype: str,
        quantization_config: "BitsAndBytesConfig",
    ) -> None:
        """Save the currently loaded BitsAndBytes quantized model to disk.

        Manually injects quantization_config into config.json because
        transformers doesn't always preserve it automatically.

        Args:
            original_path: Path to original unquantized model
            dtype: Quantization type ("4bit" or "8bit")
            quantization_config: BitsAndBytes configuration used
        """
        quantized_path = self._get_quantized_model_path(original_path, dtype)

        if self._check_quantized_model_exists(quantized_path):
            self.logger.info(
                f"Quantized model already exists at {quantized_path}"
            )
            return

        self._save_quantized_model_files(quantized_path, dtype, original_path)

    def _save_quantized_model_files(
        self, quantized_path: str, dtype: str, original_path: str
    ) -> None:
        """Save quantized model files and configuration.

        Args:
            quantized_path: Destination path for quantized model
            dtype: Quantization type
            original_path: Source path for tokenizer files
        """
        try:
            os.makedirs(quantized_path, exist_ok=True)
            self.logger.info(
                f"Saving BitsAndBytes {dtype} quantized model to "
                f"{quantized_path}"
            )

            self._save_model_weights(quantized_path)
            self._inject_quantization_config(quantized_path, dtype)
            self._copy_tokenizer_files(original_path, quantized_path)

            self.logger.info(
                f"✓ BitsAndBytes {dtype} quantized model saved successfully. "
                "Future loads will use this saved version "
                "(no re-quantization needed)."
            )
        except Exception as e:
            self._handle_save_error(e, quantized_path)

    def _save_model_weights(self, quantized_path: str) -> None:
        """Save model weights with BitsAndBytes quantization preserved.

        Args:
            quantized_path: Destination path
        """
        self._model.save_pretrained(
            quantized_path, safe_serialization=True, max_shard_size="5GB"
        )

    def _inject_quantization_config(
        self, quantized_path: str, dtype: str
    ) -> None:
        """Inject quantization_config into config.json.

        This is critical - transformers doesn't always save it automatically.

        Args:
            quantized_path: Path to quantized model directory
            dtype: Quantization type
        """
        config_path = os.path.join(quantized_path, "config.json")
        with open(config_path, "r") as f:
            config = json.load(f)

        config["quantization_config"] = self._build_quantization_config_dict(
            dtype
        )

        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)

        self.logger.info(f"✓ Injected quantization_config into {config_path}")

    def _build_quantization_config_dict(self, dtype: str) -> Dict[str, Any]:
        """Build quantization configuration dictionary for config.json.

        Args:
            dtype: Quantization type ("4bit" or "8bit")

        Returns:
            Dictionary with quantization configuration
        """
        return {
            "load_in_4bit": dtype == "4bit",
            "load_in_8bit": dtype == "8bit",
            "llm_int8_threshold": 6.0,
            "llm_int8_has_fp16_weight": False,
            "bnb_4bit_compute_dtype": "float16",
            "bnb_4bit_use_double_quant": True,
            "bnb_4bit_quant_type": "nf4",
            "quant_method": "bitsandbytes",
        }

    def _copy_tokenizer_files(
        self, original_path: str, quantized_path: str
    ) -> None:
        """Copy tokenizer files from original model to quantized version.

        Args:
            original_path: Source directory
            quantized_path: Destination directory
        """
        config_files = [
            "generation_config.json",
            "tokenizer_config.json",
            "tokenizer.json",
            "special_tokens_map.json",
        ]

        if self._is_mistral3_model():
            config_files.append("tekken.json")

        for file in config_files:
            src = os.path.join(original_path, file)
            if os.path.exists(src):
                dst = os.path.join(quantized_path, file)
                shutil.copy2(src, dst)

    def _handle_save_error(
        self, error: Exception, quantized_path: str
    ) -> None:
        """Handle errors during quantized model save.

        Args:
            error: Exception that occurred
            quantized_path: Path to clean up
        """
        self.logger.error(f"Failed to save quantized model: {error}")
        if os.path.exists(quantized_path):
            try:
                shutil.rmtree(quantized_path)
            except Exception as cleanup_error:
                self.logger.error(
                    f"Failed to clean up partial save: {cleanup_error}"
                )
