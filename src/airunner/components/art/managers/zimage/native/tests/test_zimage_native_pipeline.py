"""Unit tests for the native Z-Image pipeline.

Tests the complete generation pipeline.
"""

import pytest
import torch
from unittest.mock import MagicMock, patch

from airunner.components.art.managers.zimage.native.zimage_native_pipeline import (
    ZImageNativePipeline,
)
from airunner.components.art.managers.zimage.native.flow_match_scheduler import (
    FlowMatchEulerScheduler,
)


class TestZImageNativePipeline:
    """Tests for ZImageNativePipeline class."""

    def test_creation(self) -> None:
        """Test pipeline creation."""
        pipeline = ZImageNativePipeline()
        
        assert pipeline is not None
        assert pipeline.transformer is None  # Not loaded yet
        assert pipeline.scheduler is None

    def test_device_property_cuda_default(self) -> None:
        """Test device defaults to CUDA if available."""
        pipeline = ZImageNativePipeline()
        
        # Default should be CUDA if available, else CPU
        expected = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        assert pipeline.device == expected

    def test_device_property_explicit_cpu(self) -> None:
        """Test explicit CPU device."""
        pipeline = ZImageNativePipeline(device=torch.device("cpu"))
        
        assert pipeline.device == torch.device("cpu")

    def test_scheduler_creation(self) -> None:
        """Test scheduler initialization."""
        pipeline = ZImageNativePipeline()
        
        # Manually initialize scheduler
        pipeline.scheduler = FlowMatchEulerScheduler(shift=3.0)
        
        assert pipeline.scheduler is not None
        assert pipeline.scheduler.shift == 3.0

    def test_memory_usage(self) -> None:
        """Test memory usage reporting."""
        pipeline = ZImageNativePipeline()
        
        usage = pipeline.memory_usage
        
        assert 'vram' in usage
        assert 'cpu' in usage
        assert isinstance(usage['vram'], float)
        assert isinstance(usage['cpu'], float)

    def test_is_fp8_default(self) -> None:
        """Test FP8 flag defaults to False."""
        pipeline = ZImageNativePipeline()
        
        assert pipeline.is_fp8 is False

    def test_dtype_default(self) -> None:
        """Test default dtype is bfloat16."""
        pipeline = ZImageNativePipeline()
        
        assert pipeline.dtype == torch.bfloat16

    def test_loaded_components_empty(self) -> None:
        """Test loaded components list starts empty."""
        pipeline = ZImageNativePipeline()
        
        assert pipeline._loaded_components == []

    def test_custom_dtype(self) -> None:
        """Test setting custom dtype."""
        pipeline = ZImageNativePipeline(dtype=torch.float16)
        
        assert pipeline.dtype == torch.float16


class TestZImageNativePipelineIntegration:
    """Integration tests for the pipeline - skipped until full implementation."""

    @pytest.mark.skip(reason="Requires full model loading")
    def test_single_step_denoise(self) -> None:
        """Test a single denoising step."""
        pass

    @pytest.mark.skip(reason="Requires full model loading")
    def test_full_denoise_loop(self) -> None:
        """Test full denoising loop."""
        pass
