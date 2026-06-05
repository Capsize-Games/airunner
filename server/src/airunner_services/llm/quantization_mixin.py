"""Service-owned LLM quantization helpers."""

import os
from typing import Optional, Union

import torch
from transformers import AutoModelForCausalLM
from transformers.utils.quantization_config import (
    BitsAndBytesConfig,
    GPTQConfig,
)

from airunner_services.settings import AIRUNNER_LOCAL_FILES_ONLY
from airunner_services.llm.quantization_policy import (
    create_bitsandbytes_config,
    resolve_quantization_dtype,
)
from airunner_services.model_management.hardware_profiler import (
    HardwareProfiler,
)
from airunner_services.utils.application.enum_resolver import signal_code_proxy
from airunner_services.utils.memory.clear_memory import clear_memory

SignalCode = signal_code_proxy(
    {
        "LLM_QUANTIZATION_PROGRESS": "llm_quantization_progress",
        "LLM_QUANTIZATION_FAILED": "llm_quantization_failed",
    }
)


class QuantizationMixin:
    """Mixin for LLM model quantization functionality."""

    @property
    def _hardware_profiler(self) -> HardwareProfiler:
        """Lazily initialize the hardware profiler."""
        if not hasattr(self, "_hw_profiler_instance"):
            self._hw_profiler_instance = HardwareProfiler()
        return self._hw_profiler_instance

    def _get_available_vram_gb(self) -> float:
        """Return the currently available VRAM in gigabytes."""
        return self._hardware_profiler._get_available_vram_gb()

    def _auto_select_quantization(self) -> str:
        """Select a quantization level based on available VRAM."""
        available_vram = self._get_available_vram_gb()
        self.logger.info(f"Available VRAM: {available_vram:.2f} GB")

        if available_vram >= 28:
            return "32bit"
        if available_vram >= 14:
            return "8bit"
        return "8bit"

    def _get_quantization_info(self, vram_gb: float) -> dict:
        """Return human-readable quantization details for one VRAM level."""
        if vram_gb >= 28:
            return {
                "level": "32-bit",
                "description": "Full precision",
                "config": None,
            }
        if vram_gb >= 14:
            return {
                "level": "8-bit",
                "description": "High quality, moderate speed",
                "config": "BitsAndBytesConfig",
            }
        if vram_gb >= 7:
            return {
                "level": "4-bit",
                "description": "Good quality, faster inference",
                "config": "BitsAndBytesConfig",
            }
        return {
            "level": "2-bit",
            "description": "Maximum speed, lower quality",
            "config": "GPTQConfig",
        }

    def _get_quantized_model_path(self, base_path: str, bits: str) -> str:
        """Return the target directory for one quantized model variant."""
        base_dir = os.path.dirname(base_path)
        model_name = os.path.basename(base_path)
        return os.path.join(base_dir, f"{model_name}-{bits}")

    def _check_quantized_model_exists(self, quant_path: str) -> bool:
        """Return whether one quantized model directory appears valid."""
        if not os.path.exists(quant_path):
            return False

        try:
            required_files = ["config.json"]
            has_model = any(
                file_name.endswith((".safetensors", ".bin"))
                for file_name in os.listdir(quant_path)
            )
            has_config = all(
                os.path.exists(os.path.join(quant_path, file_name))
                for file_name in required_files
            )
            return has_model and has_config
        except Exception as error:
            self.logger.warning(f"Error checking quantized model: {error}")
            return False

    def _save_quantized_model(self, dtype: str, original_path: str) -> None:
        """Persist a BitsAndBytes quantized model when supported."""
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
                original_path,
                dtype,
                current=1,
                total=1,
            )
        except Exception as error:
            self.logger.error(f"Failed to save quantized model: {error}")
            raise

    def _ensure_quantized_models(self, base_model_path: str) -> None:
        """Skip pre-quantization because BitsAndBytes is runtime only."""
        del base_model_path
        self.logger.info(
            "Skipping pre-quantization - BitsAndBytes uses runtime "
            "quantization"
        )

    def _create_8bit_config(self) -> BitsAndBytesConfig:
        """Create an 8-bit BitsAndBytes quantization config."""
        config = create_bitsandbytes_config("8bit")
        if config is None:
            raise RuntimeError("Failed to build 8-bit quantization config")
        return config

    def _create_4bit_config(self) -> BitsAndBytesConfig:
        """Create a 4-bit BitsAndBytes quantization config."""
        config = create_bitsandbytes_config(
            "4bit",
            four_bit_compute_dtype=torch.float16,
        )
        if config is None:
            raise RuntimeError("Failed to build 4-bit quantization config")
        return config

    def _create_2bit_config(self) -> GPTQConfig:
        """Create a 2-bit GPTQ quantization config."""
        return GPTQConfig(bits=2, dataset="c4", tokenizer=self._tokenizer)

    def _create_quantized_model(
        self,
        base_path: str,
        bits: str,
        current: int = 1,
        total: int = 1,
    ) -> None:
        """Create one quantized version of the current model."""
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
                base_path,
                quant_path,
                quant_config,
                bits,
                current,
                total,
            )
        except Exception as error:
            self._handle_quantization_error(error, bits, quant_path)
            raise

    def _get_quantization_config_for_creation(
        self,
        bits: str,
    ) -> Optional[Union[BitsAndBytesConfig, GPTQConfig]]:
        """Return the quantization config used for persistent creation."""
        if bits == "8bit":
            return self._create_8bit_config()
        if bits == "4bit":
            return self._create_4bit_config()

        self.logger.warning(
            "2bit quantization requires GPTQ - skipping for now"
        )
        self._emit_quantization_progress(
            f"Skipping {bits} (requires GPTQ)",
            100,
            bits,
            1,
            1,
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
        """Load one quantized model and save it to disk."""
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
        """Load a model using one quantization configuration."""
        model_kwargs = {
            "local_files_only": AIRUNNER_LOCAL_FILES_ONLY,
            "trust_remote_code": True,
            "quantization_config": quant_config,
            "device_map": "auto",
        }

        return AutoModelForCausalLM.from_pretrained(
            base_path,
            **model_kwargs,
        )

    def _save_model_and_config_files(
        self,
        model: AutoModelForCausalLM,
        base_path: str,
        quant_path: str,
    ) -> None:
        """Save a quantized model and copy its auxiliary config files."""
        import shutil

        self.logger.info(f"Saving quantized model to {quant_path}")
        model.save_pretrained(quant_path, safe_serialization=True)

        config_files = [
            "generation_config.json",
            "tokenizer_config.json",
        ]

        for file_name in config_files:
            source = os.path.join(base_path, file_name)
            if os.path.exists(source):
                shutil.copy2(source, os.path.join(quant_path, file_name))

    def _emit_quantization_progress(
        self,
        stage: str,
        progress: int,
        bits: str,
        current: int,
        total: int,
    ) -> None:
        """Emit a quantization progress signal."""
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
        self,
        bits: str,
        current: int,
        total: int,
    ) -> None:
        """Emit one quantization completion event."""
        self._emit_quantization_progress(
            f"Completed {bits} quantization ({current}/{total})",
            int((current / total) * 100),
            bits,
            current,
            total,
        )
        self.logger.info(f"✓ {bits} quantization complete")

    def _handle_quantization_error(
        self,
        error: Exception,
        bits: str,
        quant_path: str,
    ) -> None:
        """Emit one failure event for a quantization error."""
        import traceback

        self.logger.error(f"Failed to create {bits} quantized model: {error}")
        self.logger.error(traceback.format_exc())
        self.emit_signal(
            SignalCode.LLM_QUANTIZATION_FAILED,
            {
                "error": str(error),
                "bits": bits,
                "output_path": quant_path,
            },
        )

    @property
    def _quantization_config(
        self,
    ) -> Optional[Union[BitsAndBytesConfig, GPTQConfig]]:
        """Return the quantization config for the current dtype setting."""
        dtype = self.llm_dtype
        self.logger.info(f"Current dtype setting: {dtype}")

        dtype, auto_selected = resolve_quantization_dtype(
            dtype,
            self._auto_select_quantization,
        )
        if auto_selected:
            self.logger.info(f"Auto-selected quantization: {dtype}")
            self.llm_generator_settings.dtype = dtype

        self.logger.info(f"Creating quantization config for dtype: {dtype}")
        return self._create_quantization_config_by_dtype(dtype)

    def _create_quantization_config_by_dtype(
        self,
        dtype: str,
    ) -> Optional[Union[BitsAndBytesConfig, GPTQConfig]]:
        """Create the quantization config matching one dtype string."""
        if dtype == "8bit":
            self.logger.info(
                "Created 8-bit quantization config with CPU offload"
            )
            return self._create_8bit_config()
        if dtype == "4bit":
            self.logger.info("Created 4-bit quantization config")
            return self._create_4bit_config()
        if dtype == "2bit":
            self.logger.info("Created 2-bit GPTQ config")
            return self._create_2bit_config()

        self.logger.warning(
            f"No quantization for dtype={dtype} (using full precision)"
        )
        return None


__all__ = ["QuantizationMixin"]
