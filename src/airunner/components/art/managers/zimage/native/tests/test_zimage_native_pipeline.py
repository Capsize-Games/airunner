"""Unit tests for the native Z-Image pipeline.

Tests the complete generation pipeline.
"""

import pytest
import torch
from types import SimpleNamespace
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

    def test_load_text_encoder_uses_cpu_execution_on_low_free_vram(self) -> None:
        """Test text encoder falls back to CPU execution on low VRAM."""
        pipeline = ZImageNativePipeline(device=torch.device("cuda"))
        encoder = MagicMock()
        encoder.tokenizer = MagicMock()

        with patch(
            "airunner.components.art.managers.zimage.native.zimage_native_pipeline.torch.cuda.is_available",
            return_value=True,
        ), patch(
            "airunner.components.art.managers.zimage.native.zimage_native_pipeline.torch.cuda.mem_get_info",
            return_value=(int(2.25 * 1024**3), int(15.47 * 1024**3)),
        ), patch(
            "airunner.components.art.managers.zimage.native.zimage_native_pipeline.torch.cuda.get_device_properties",
            return_value=SimpleNamespace(total_memory=int(15.47 * 1024**3)),
        ), patch(
            "airunner.components.art.managers.zimage.native.zimage_native_pipeline.ZImageTextEncoder",
            return_value=encoder,
        ) as mock_encoder:
            pipeline.load_text_encoder(model_path="/tmp/text_encoder")

        kwargs = mock_encoder.call_args.kwargs
        assert kwargs["quantization"] is None
        assert kwargs["device"] == torch.device("cpu")
        assert kwargs["enable_cpu_offload"] is False
        assert kwargs["max_memory"] is None

    def test_load_text_encoder_keeps_4bit_when_free_vram_is_sufficient(self) -> None:
        """Test text encoder stays 4-bit when there is enough free VRAM."""
        pipeline = ZImageNativePipeline(device=torch.device("cuda"))
        encoder = MagicMock()
        encoder.tokenizer = MagicMock()

        with patch(
            "airunner.components.art.managers.zimage.native.zimage_native_pipeline.torch.cuda.is_available",
            return_value=True,
        ), patch(
            "airunner.components.art.managers.zimage.native.zimage_native_pipeline.torch.cuda.mem_get_info",
            return_value=(int(9.0 * 1024**3), int(15.47 * 1024**3)),
        ), patch(
            "airunner.components.art.managers.zimage.native.zimage_native_pipeline.torch.cuda.get_device_properties",
            return_value=SimpleNamespace(total_memory=int(15.47 * 1024**3)),
        ), patch(
            "airunner.components.art.managers.zimage.native.zimage_native_pipeline.ZImageTextEncoder",
            return_value=encoder,
        ) as mock_encoder:
            pipeline.load_text_encoder(model_path="/tmp/text_encoder")

        kwargs = mock_encoder.call_args.kwargs
        assert kwargs["quantization"] == "4bit"
        assert kwargs["device"] == torch.device("cuda")
        assert kwargs["enable_cpu_offload"] is False
        assert kwargs["max_memory"] == {0: "7GiB", "cpu": "32GiB"}

    def test_prepare_text_encoder_keeps_cpu_encoder_on_cpu(self) -> None:
        """Test CPU fallback text encoders are not moved back to GPU."""
        pipeline = ZImageNativePipeline(device=torch.device("cuda"))
        model = MagicMock()
        model.parameters.return_value = iter([
            torch.nn.Parameter(torch.zeros(1))
        ])
        pipeline.text_encoder = SimpleNamespace(
            model=model,
            model_path="/tmp/text_encoder",
            prefer_cpu_execution=True,
            uses_accelerate_offload=False,
        )

        pipeline._prepare_text_encoder_for_encoding()

        model.to.assert_not_called()

    def test_move_prompt_conditioning_to_device(self) -> None:
        """Test prompt embeddings are moved to the transformer device."""
        pipeline = ZImageNativePipeline(
            device=torch.device("cpu"),
            dtype=torch.bfloat16,
        )
        prompt_embeds = torch.randn(1, 2, 3, dtype=torch.float32)
        negative_embeds = torch.randn(1, 2, 3, dtype=torch.float32)
        attention_mask = torch.ones(1, 2, dtype=torch.long)

        moved_prompt, moved_negative, moved_mask = (
            pipeline._move_prompt_conditioning_to_device(
                prompt_embeds,
                negative_embeds,
                attention_mask,
            )
        )

        assert moved_prompt.dtype == torch.bfloat16
        assert moved_negative is not None
        assert moved_negative.dtype == torch.bfloat16
        assert moved_mask is not None
        assert moved_mask.dtype == torch.long

    def test_load_vae_ignores_cpu_text_encoder_fallback(self) -> None:
        """Test VAE loading still runs when text encoding stays on CPU."""
        pipeline = ZImageNativePipeline(device=torch.device("cpu"))
        pipeline.text_encoder = SimpleNamespace(prefer_cpu_execution=True)
        fake_vae = MagicMock()
        fake_vae.to.return_value = fake_vae
        fake_vae.config = SimpleNamespace(block_out_channels=[1, 2, 4, 8])

        with patch(
            "airunner.components.art.managers.zimage.native.zimage_native_pipeline.AutoencoderKL.from_pretrained",
            return_value=fake_vae,
        ) as mock_from_pretrained:
            pipeline.load_vae(vae_path="/tmp/vae")

        mock_from_pretrained.assert_called_once_with(
            "/tmp/vae",
            torch_dtype=torch.bfloat16,
        )
        assert pipeline.vae is fake_vae


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
