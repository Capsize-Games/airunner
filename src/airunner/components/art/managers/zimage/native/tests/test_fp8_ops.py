"""Unit tests for FP8 operations module.

Tests QuantizedTensor and TensorCoreFP8Layout functionality for ComfyUI-compatible
FP8 quantized weight handling.
"""

import pytest
import torch

from airunner.components.art.managers.zimage.native.fp8_ops import (
    QuantizedTensor,
    TensorCoreFP8Layout,
)


class TestTensorCoreFP8Layout:
    """Tests for TensorCoreFP8Layout class."""

    def test_quantize_basic(self) -> None:
        """Test basic quantization to FP8."""
        tensor = torch.randn(64, 128, dtype=torch.float32)
        scale = torch.tensor([0.5], dtype=torch.float32)
        
        qdata, params = TensorCoreFP8Layout.quantize(tensor, scale=scale)
        
        assert qdata.dtype == torch.float8_e4m3fn
        assert qdata.shape == (64, 128)
        assert 'scale' in params
        assert params['scale'].dtype == torch.float32

    def test_quantize_recalculate_scale(self) -> None:
        """Test quantization with auto-calculated scale."""
        tensor = torch.randn(32, 64, dtype=torch.float32)
        
        qdata, params = TensorCoreFP8Layout.quantize(tensor, scale="recalculate")
        
        assert qdata.dtype == torch.float8_e4m3fn
        assert params['scale'] is not None

    def test_dequantize_produces_float(self) -> None:
        """Test that dequantize produces float32 output."""
        original = torch.randn(32, 64, dtype=torch.float32)
        scale = torch.tensor([2.0], dtype=torch.float32)
        
        qdata, params = TensorCoreFP8Layout.quantize(original, scale=scale)
        
        # Dequantize
        dequantized = TensorCoreFP8Layout.dequantize(
            qdata, params['scale'], params['orig_dtype']
        )
        
        assert dequantized.dtype == torch.float32
        assert dequantized.shape == original.shape

    def test_dequantize_to_bfloat16(self) -> None:
        """Test dequantizing to bfloat16."""
        original = torch.randn(16, 32, dtype=torch.bfloat16)
        scale = torch.tensor([1.5], dtype=torch.float32)
        
        # Quantize from bfloat16
        qdata, params = TensorCoreFP8Layout.quantize(original, scale=scale)
        
        # Dequantize back
        dequantized = TensorCoreFP8Layout.dequantize(
            qdata, params['scale'], params['orig_dtype']
        )
        
        # Should preserve original dtype
        assert dequantized.dtype == torch.bfloat16

    def test_roundtrip_accuracy(self) -> None:
        """Test quantize/dequantize roundtrip maintains approximate values."""
        original = torch.randn(16, 16, dtype=torch.float32)
        
        qdata, params = TensorCoreFP8Layout.quantize(original, scale="recalculate")
        restored = TensorCoreFP8Layout.dequantize(
            qdata, params['scale'], params['orig_dtype']
        )
        
        # FP8 has limited precision, but should be relatively close
        assert torch.allclose(original, restored, atol=0.5)


class TestQuantizedTensor:
    """Tests for QuantizedTensor class."""

    def test_creation_from_float(self) -> None:
        """Test creating QuantizedTensor from regular tensor."""
        tensor = torch.randn(32, 64, dtype=torch.float32)
        
        qtensor = QuantizedTensor.from_float(tensor, "TensorCoreFP8Layout", scale="recalculate")
        
        assert isinstance(qtensor, QuantizedTensor)
        assert qtensor.shape == (32, 64)

    def test_from_fp8_with_scale(self) -> None:
        """Test creating QuantizedTensor from FP8 data with scale."""
        fp8_data = torch.randn(16, 32, dtype=torch.float32).to(torch.float8_e4m3fn)
        scale = torch.tensor([0.5], dtype=torch.float32)
        
        qtensor = QuantizedTensor.from_fp8_with_scale(fp8_data, scale)
        
        assert isinstance(qtensor, QuantizedTensor)
        assert qtensor.shape == (16, 32)

    def test_dequantize(self) -> None:
        """Test dequantizing QuantizedTensor."""
        tensor = torch.randn(16, 32, dtype=torch.float32)
        qtensor = QuantizedTensor.from_float(tensor, "TensorCoreFP8Layout", scale="recalculate")
        
        # Dequantize back
        dequantized = qtensor.dequantize()
        
        assert dequantized.dtype == torch.float32
        assert dequantized.shape == tensor.shape

    def test_device_movement(self) -> None:
        """Test moving QuantizedTensor to device."""
        tensor = torch.randn(8, 16, dtype=torch.float32)
        qtensor = QuantizedTensor.from_float(tensor, "TensorCoreFP8Layout", scale="recalculate")
        
        # Move to CPU (should work regardless of CUDA availability)
        moved = qtensor.to(device="cpu")
        
        assert moved.device.type == "cpu"

    @pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA required")
    def test_cuda_device_movement(self) -> None:
        """Test moving QuantizedTensor to CUDA."""
        tensor = torch.randn(8, 16, dtype=torch.float32)
        qtensor = QuantizedTensor.from_float(tensor, "TensorCoreFP8Layout", scale="recalculate")
        
        moved = qtensor.to(device="cuda:0")
        
        assert moved.device.type == "cuda"

    def test_shape_preserved(self) -> None:
        """Test that shape is preserved through quantization."""
        shapes = [(8,), (8, 16), (2, 8, 16), (2, 4, 8, 16)]
        
        for shape in shapes:
            tensor = torch.randn(*shape, dtype=torch.float32)
            qtensor = QuantizedTensor.from_float(tensor, "TensorCoreFP8Layout", scale="recalculate")
            assert qtensor.shape == shape
