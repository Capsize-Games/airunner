import os
import torch
from typing import Optional, Union
from transformers import AutoConfig, AutoModelForCausalLM
from transformers.utils.quantization_config import (
    BitsAndBytesConfig,
    GPTQConfig,
)

from airunner.enums import SignalCode
from airunner.settings import AIRUNNER_LOCAL_FILES_ONLY
from airunner.utils.memory import clear_memory
from airunner.components.model_management.hardware_profiler import (
    HardwareProfiler,
)


class QuantizationMixin:
    """Mixin for LLM model quantization functionality."""

    @property
    def _hardware_profiler(self) -> HardwareProfiler:
        """Lazy initialization of hardware profiler."""
        if not hasattr(self, "_hw_profiler_instance"):
            self._hw_profiler_instance = HardwareProfiler()
        return self._hw_profiler_instance

    def _get_available_vram_gb(self) -> float:
        """Get available VRAM in gigabytes."""
        return self._hardware_profiler._get_available_vram_gb()

    def _auto_select_quantization(self) -> str:
        """Automatically select quantization level based on available VRAM."""
        available_vram = self._get_available_vram_gb()
        self.logger.info(f"Available VRAM: {available_vram:.2f} GB")

        if available_vram >= 28:
            return "32bit"
        elif available_vram >= 14:
            return "8bit"
        else:
            return "8bit"

    def _get_quantization_info(self, vram_gb: float) -> dict:
        """
        Get human-readable quantization information.

        Args:
            vram_gb: Available VRAM in gigabytes

        Returns:
            dict: Quantization details with level, description, and config type
        """
        if vram_gb >= 28:
            return {
                "level": "32-bit",
                "description": "Full precision",
                "config": None,
            }
        elif vram_gb >= 14:
            return {
                "level": "8-bit",
                "description": "High quality, moderate speed",
                "config": "BitsAndBytesConfig",
            }
        elif vram_gb >= 7:
            return {
                "level": "4-bit",
                "description": "Good quality, faster inference",
                "config": "BitsAndBytesConfig",
            }
        else:
            return {
                "level": "2-bit",
                "description": "Maximum speed, lower quality",
                "config": "GPTQConfig",
            }

    def _get_quantized_model_path(self, base_path: str, bits: str) -> str:
        """
        Get the path for a BitsAndBytes quantized model.

        Args:
            base_path: Base model path
            bits: Quantization level ("4bit", "8bit")

        Returns:
            str: Path to quantized model directory (e.g., model-4bit/)
        """
        base_dir = os.path.dirname(base_path)
        model_name = os.path.basename(base_path)
        return os.path.join(base_dir, f"{model_name}-{bits}")

    def _check_quantized_model_exists(self, quant_path: str) -> bool:
        """
        Check if a BitsAndBytes quantized model exists and is valid.

        Args:
            quant_path: Path to quantized model

        Returns:
            bool: True if quantized model exists and appears valid
        """
        if not os.path.exists(quant_path):
            return False

        try:
            required_files = ["config.json"]
            has_model = any(
                f.endswith((".safetensors", ".bin"))
                for f in os.listdir(quant_path)
            )
            has_config = all(
                os.path.exists(os.path.join(quant_path, f))
                for f in required_files
            )
            return has_model and has_config
        except Exception as e:
            self.logger.warning(f"Error checking quantized model: {e}")
            return False

    def _is_mistral3_model(self) -> bool:
        """Check if the current model is a Mistral3 model."""
        try:
            config = AutoConfig.from_pretrained(
                self.model_path,
                local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
                trust_remote_code=True,
            )
            is_mistral3_type = (
                hasattr(config, "model_type")
                and config.model_type == "mistral3"
            )
            is_mistral3_arch = hasattr(config, "architectures") and any(
                "Mistral3" in arch for arch in (config.architectures or [])
            )
            return is_mistral3_type or is_mistral3_arch
        except Exception:
            return False

    def _save_quantized_model(self, dtype: str, original_path: str) -> None:
        """
        Save a BitsAndBytes quantized model to disk.

        Since BitsAndBytes PR#753 (merged Nov 2023), 4-bit/8-bit models CAN be
        saved and loaded using save_pretrained/from_pretrained. This creates a
        persistent quantized model that loads much faster than runtime quantization.

        Args:
            dtype: Quantization level ("4bit", "8bit", etc.)
            original_path: Original model path that was loaded
        """
        if not self._model or not dtype or dtype == "none":
            return

        if dtype not in ["4bit", "8bit"]:
            self.logger.info(
                f"Quantization saving not supported for dtype={dtype}"
            )
            return

        quantized_path = self._get_quantized_model_path(original_path, dtype)

        if self._check_quantized_model_exists(quantized_path):
            self.logger.info(
                f"Quantized model already exists at {quantized_path}"
            )
            return

        self.logger.info(
            f"Saving BitsAndBytes {dtype} quantized model to {quantized_path}"
        )

        try:
            self._create_quantized_model(
                original_path, dtype, current=1, total=1
            )
        except Exception as e:
            self.logger.error(f"Failed to save quantized model: {e}")
            raise

    def _ensure_quantized_models(self, base_model_path: str) -> None:
        """
        DEPRECATED: Pre-quantization is not supported with BitsAndBytes.

        BitsAndBytes performs runtime quantization during model loading.

        Args:
            base_model_path: Path to the full precision model
        """
        self.logger.info(
            "Skipping pre-quantization - BitsAndBytes uses runtime quantization"
        )

    def _create_8bit_config(self) -> BitsAndBytesConfig:
        """Create 8-bit BitsAndBytes quantization config."""
        return BitsAndBytesConfig(
            load_in_8bit=True,
            llm_int8_threshold=6.0,
            llm_int8_has_fp16_weight=False,
            llm_int8_enable_fp32_cpu_offload=True,
        )

    def _create_4bit_config(self) -> BitsAndBytesConfig:
        """Create 4-bit BitsAndBytes quantization config."""
        return BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
        )

    def _create_2bit_config(self) -> GPTQConfig:
        """Create 2-bit GPTQ quantization config."""
        return GPTQConfig(bits=2, dataset="c4", tokenizer=self._tokenizer)

    def _create_quantized_model(
        self, base_path: str, bits: str, current: int = 1, total: int = 1
    ) -> None:
        """
        Create a quantized version of the model.

        Args:
            base_path: Path to full precision model
            bits: Quantization level ("2bit", "4bit", "8bit")
            current: Current quantization number (for progress)
            total: Total number of quantizations to create
        """
        quant_path = self._get_quantized_model_path(base_path, bits)
        os.makedirs(quant_path, exist_ok=True)
        self.logger.info(f"Creating {bits} quantized model at {quant_path}")

        self._emit_quantization_progress(
            f"Creating {bits} quantized model ({current}/{total})",
            int(((current - 1) / total) * 100),
            bits,
            current,
            total,
        )

        try:
            quant_config = self._get_quantization_config_for_creation(bits)
            if quant_config is None:
                return

            self._load_and_save_quantized_model(
                base_path, quant_path, quant_config, bits, current, total
            )
        except Exception as e:
            self._handle_quantization_error(e, bits, quant_path)
            raise

    def _get_quantization_config_for_creation(
        self, bits: str
    ) -> Optional[Union[BitsAndBytesConfig, GPTQConfig]]:
        """Get quantization config for model creation."""
        if bits == "8bit":
            return self._create_8bit_config()
        elif bits == "4bit":
            return self._create_4bit_config()
        else:
            self.logger.warning(
                "2bit quantization requires GPTQ - skipping for now"
            )
            self._emit_quantization_progress(
                f"Skipping {bits} (requires GPTQ)", 100, bits, 1, 1
            )
            return None

    def _load_and_save_quantized_model(
        self,
        base_path: str,
        quant_path: str,
        quant_config: Union[BitsAndBytesConfig, GPTQConfig],
        bits: str,
        current: int,
        total: int,
    ) -> None:
        """Load model with quantization and save to disk."""
        self._emit_quantization_progress(
            f"Loading {bits} model with quantization",
            int(((current - 0.7) / total) * 100),
            bits,
            current,
            total,
        )

        model = self._load_quantized_model_from_path(base_path, quant_config)

        self._emit_quantization_progress(
            f"Saving {bits} quantized model to disk",
            int(((current - 0.3) / total) * 100),
            bits,
            current,
            total,
        )

        self._save_model_and_config_files(model, base_path, quant_path)
        self._emit_quantization_complete(bits, current, total)

        del model
        clear_memory()

    def _load_quantized_model_from_path(
        self,
        base_path: str,
        quant_config: Union[BitsAndBytesConfig, GPTQConfig],
    ) -> AutoModelForCausalLM:
        """Load model with quantization configuration."""
        model_kwargs = {
            "local_files_only": AIRUNNER_LOCAL_FILES_ONLY,
            "trust_remote_code": True,
            "quantization_config": quant_config,
            "device_map": "auto",
        }

        if self._is_mistral3_model():
            from transformers.models.mistral3 import (
                Mistral3ForConditionalGeneration,
            )

            return Mistral3ForConditionalGeneration.from_pretrained(
                base_path, **model_kwargs
            )
        else:
            return AutoModelForCausalLM.from_pretrained(
                base_path, **model_kwargs
            )

    def _save_model_and_config_files(
        self, model: AutoModelForCausalLM, base_path: str, quant_path: str
    ) -> None:
        """Save quantized model and copy configuration files.
        
        Note: We do NOT copy config.json because model.save_pretrained() already
        saves it with the quantization_config included. Copying from base_path
        would overwrite the quantization settings needed for reloading.
        """
        import shutil

        self.logger.info(f"Saving quantized model to {quant_path}")
        model.save_pretrained(quant_path, safe_serialization=True)

        # Copy tokenizer and generation config files (but NOT config.json)
        config_files = [
            "generation_config.json",
            "tokenizer_config.json",
        ]
        if self._is_mistral3_model():
            config_files.append("tekken.json")

        for file in config_files:
            src = os.path.join(base_path, file)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(quant_path, file))

    def _emit_quantization_progress(
        self, stage: str, progress: int, bits: str, current: int, total: int
    ) -> None:
        """Emit quantization progress signal."""
        self.emit_signal(
            SignalCode.LLM_QUANTIZATION_PROGRESS,
            {
                "stage": stage,
                "progress": progress,
                "bits": bits,
                "total": total,
                "current": current,
            },
        )

    def _emit_quantization_complete(
        self, bits: str, current: int, total: int
    ) -> None:
        """Emit quantization completion signal."""
        self._emit_quantization_progress(
            f"Completed {bits} quantization ({current}/{total})",
            int((current / total) * 100),
            bits,
            current,
            total,
        )
        self.logger.info(f"✓ {bits} quantization complete")

    def _handle_quantization_error(
        self, error: Exception, bits: str, quant_path: str
    ) -> None:
        """Handle quantization error and emit failure signal."""
        import traceback

        self.logger.error(f"Failed to create {bits} quantized model: {error}")
        self.logger.error(traceback.format_exc())
        self.emit_signal(
            SignalCode.LLM_QUANTIZATION_FAILED,
            {"error": str(error), "bits": bits, "output_path": quant_path},
        )

    @property
    def _quantization_config(
        self,
    ) -> Optional[Union[BitsAndBytesConfig, GPTQConfig]]:
        """
        Get the appropriate quantization configuration based on dtype settings.

        Returns:
            Optional[Union[BitsAndBytesConfig, GPTQConfig]]: Configuration for model quantization
        """
        dtype = self.llm_dtype
        self.logger.info(f"Current dtype setting: {dtype}")

        if not dtype or dtype == "auto":
            dtype = self._auto_select_quantization()
            self.logger.info(f"Auto-selected quantization: {dtype}")
            self.llm_generator_settings.dtype = dtype

        self.logger.info(f"Creating quantization config for dtype: {dtype}")
        return self._create_quantization_config_by_dtype(dtype)

    def _create_quantization_config_by_dtype(
        self, dtype: str
    ) -> Optional[Union[BitsAndBytesConfig, GPTQConfig]]:
        """Create quantization config based on dtype string."""
        if dtype == "8bit":
            self.logger.info(
                "Created 8-bit quantization config with CPU offload"
            )
            return self._create_8bit_config()
        elif dtype == "4bit":
            self.logger.info("Created 4-bit quantization config")
            return self._create_4bit_config()
        elif dtype == "2bit":
            self.logger.info("Created 2-bit GPTQ config")
            return self._create_2bit_config()
        else:
            self.logger.warning(
                f"No quantization for dtype={dtype} (using full precision)"
            )
            return None
