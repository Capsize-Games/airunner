"""Unit tests for the native pipeline wrapper.

Tests the wrapper that provides diffusers-compatible interface.
"""

import pytest
import torch

from airunner.components.art.managers.zimage.native.zimage_native_pipeline import (
    ZImageNativePipeline,
)
from airunner.components.art.managers.zimage.native.zimage_native_wrapper import (
    NativePipelineWrapper,
    PipelineOutput,
)
from airunner.components.art.managers.zimage.native.flow_match_scheduler import (
    FlowMatchEulerScheduler,
)


class TestNativePipelineWrapper:
    """Tests for NativePipelineWrapper class."""

    def test_creation(self) -> None:
        """Test wrapper creation."""
        native = ZImageNativePipeline()
        wrapper = NativePipelineWrapper(native)
        
        assert wrapper is not None
        assert wrapper.is_native_fp8 is True

    def test_device_property(self) -> None:
        """Test device property."""
        native = ZImageNativePipeline(device=torch.device("cpu"))
        wrapper = NativePipelineWrapper(native)
        
        assert wrapper.device == torch.device("cpu")

    def test_dtype_property(self) -> None:
        """Test dtype property."""
        native = ZImageNativePipeline(dtype=torch.float16)
        wrapper = NativePipelineWrapper(native)
        
        assert wrapper.dtype == torch.float16

    def test_scheduler_property(self) -> None:
        """Test scheduler getter/setter."""
        native = ZImageNativePipeline()
        wrapper = NativePipelineWrapper(native)
        
        scheduler = FlowMatchEulerScheduler()
        wrapper.scheduler = scheduler
        
        assert wrapper.scheduler is scheduler

    def test_to_method(self) -> None:
        """Test to() method for device movement."""
        native = ZImageNativePipeline(device=torch.device("cpu"))
        wrapper = NativePipelineWrapper(native)
        
        result = wrapper.to("cpu")
        
        # Should return self for chaining
        assert result is wrapper
        assert wrapper.device == torch.device("cpu")


class TestPipelineOutput:
    """Tests for PipelineOutput class."""

    def test_creation(self) -> None:
        """Test output creation."""
        from PIL import Image
        
        images = [Image.new("RGB", (64, 64))]
        output = PipelineOutput(images)
        
        assert output.images == images
        assert len(output.images) == 1
