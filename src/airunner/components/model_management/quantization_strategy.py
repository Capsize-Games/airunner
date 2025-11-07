from dataclasses import dataclass
from enum import Enum
from typing import Optional

from airunner.components.model_management.hardware_profiler import (
    HardwareProfile,
)
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger


class QuantizationLevel(Enum):
    """Available quantization levels."""

    NONE = "none"
    FLOAT16 = "fp16"
    BFLOAT16 = "bf16"
    INT8 = "8bit"
    INT4 = "4bit"
    INT2 = "2bit"


@dataclass
class QuantizationConfig:
    """Quantization configuration for model loading."""

    level: QuantizationLevel
    description: str
    estimated_memory_gb: float
    requires_calibration: bool = False


class QuantizationStrategy:
    """Selects optimal quantization based on model size and available memory."""

    def __init__(self):
        self.logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)

    def select_quantization(
        self,
        model_size_gb: float,
        hardware: HardwareProfile,
        preferred_level: Optional[QuantizationLevel] = None,
    ) -> QuantizationConfig:
        """Select optimal quantization level."""
        if preferred_level:
            return self._get_config_for_level(preferred_level, model_size_gb)

        return self._auto_select_quantization(model_size_gb, hardware)

    def _auto_select_quantization(
        self, model_size_gb: float, hardware: HardwareProfile
    ) -> QuantizationConfig:
        """Automatically select quantization based on available resources."""
        vram_gb = hardware.available_vram_gb

        if vram_gb >= model_size_gb * 1.5:
            return self._get_config_for_level(
                QuantizationLevel.FLOAT16, model_size_gb
            )
        elif vram_gb >= model_size_gb * 0.8:
            return self._get_config_for_level(
                QuantizationLevel.INT8, model_size_gb
            )
        elif vram_gb >= model_size_gb * 0.5:
            return self._get_config_for_level(
                QuantizationLevel.INT4, model_size_gb
            )
        else:
            return self._get_config_for_level(
                QuantizationLevel.INT4, model_size_gb
            )

    def _get_config_for_level(
        self, level: QuantizationLevel, model_size_gb: float
    ) -> QuantizationConfig:
        """Get configuration for specific quantization level."""
        configs = {
            QuantizationLevel.NONE: QuantizationConfig(
                level=level,
                description="Full precision (FP32)",
                estimated_memory_gb=model_size_gb * 4.0,
            ),
            QuantizationLevel.FLOAT16: QuantizationConfig(
                level=level,
                description="Half precision (FP16)",
                estimated_memory_gb=model_size_gb * 2.0,
            ),
            QuantizationLevel.BFLOAT16: QuantizationConfig(
                level=level,
                description="Brain float 16 (BF16)",
                estimated_memory_gb=model_size_gb * 2.0,
            ),
            QuantizationLevel.INT8: QuantizationConfig(
                level=level,
                description="8-bit quantization",
                estimated_memory_gb=model_size_gb * 1.0,
            ),
            QuantizationLevel.INT4: QuantizationConfig(
                level=level,
                description="4-bit quantization",
                estimated_memory_gb=model_size_gb * 0.5,
            ),
            QuantizationLevel.INT2: QuantizationConfig(
                level=level,
                description="2-bit quantization (requires calibration)",
                estimated_memory_gb=model_size_gb * 0.25,
                requires_calibration=True,
            ),
        }
        return configs.get(level, configs[QuantizationLevel.INT4])
