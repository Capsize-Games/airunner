"""
Unit tests for FLUX Model Manager.

Tests the FLUX model manager implementation including:
- Pipeline selection
- Memory optimizations
- VRAM detection and optimization application
- Property accessors
- Model loading/unloading
"""

import pytest
import torch
from unittest.mock import Mock, patch, MagicMock

from airunner.components.art.managers.stablediffusion.flux_model_manager import (
    FluxModelManager,
)
from diffusers import FluxPipeline, FluxImg2ImgPipeline, FluxInpaintPipeline


class TestFluxModelManager:
    """Test suite for FluxModelManager."""

    def test_img2img_pipelines(self):
        """Test img2img pipeline property returns correct classes."""
        manager = FluxModelManager()
        pipelines = manager.img2img_pipelines

        assert isinstance(pipelines, tuple)
        assert FluxImg2ImgPipeline in pipelines
        assert len(pipelines) == 1

    def test_txt2img_pipelines(self):
        """Test txt2img pipeline property returns correct classes."""
        manager = FluxModelManager()
        pipelines = manager.txt2img_pipelines

        assert isinstance(pipelines, tuple)
        assert FluxPipeline in pipelines
        assert len(pipelines) == 1

    def test_controlnet_pipelines_empty(self):
        """Test ControlNet pipelines returns empty tuple."""
        manager = FluxModelManager()
        pipelines = manager.controlnet_pipelines

        assert isinstance(pipelines, tuple)
        assert len(pipelines) == 0

    def test_outpaint_pipelines(self):
        """Test outpaint pipeline property returns correct classes."""
        manager = FluxModelManager()
        pipelines = manager.outpaint_pipelines

        assert isinstance(pipelines, tuple)
        assert FluxInpaintPipeline in pipelines
        assert len(pipelines) == 1

    def test_pipeline_map(self):
        """Test pipeline map contains all operation types."""
        manager = FluxModelManager()
        pipeline_map = manager.pipeline_map

        assert isinstance(pipeline_map, dict)
        assert "txt2img" in pipeline_map
        assert "img2img" in pipeline_map
        assert "inpaint" in pipeline_map
        assert "outpaint" in pipeline_map
        assert pipeline_map["txt2img"] == FluxPipeline
        assert pipeline_map["img2img"] == FluxImg2ImgPipeline
        assert pipeline_map["inpaint"] == FluxInpaintPipeline
        assert pipeline_map["outpaint"] == FluxInpaintPipeline

    def test_pipeline_class_txt2img(self):
        """Test _pipeline_class returns txt2img for default operation."""
        manager = FluxModelManager()
        manager.is_img2img = False
        manager.is_inpaint = False
        manager.is_outpaint = False

        pipeline_class = manager._pipeline_class
        assert pipeline_class == FluxPipeline

    def test_pipeline_class_img2img(self):
        """Test _pipeline_class returns img2img when is_img2img is True."""
        manager = FluxModelManager()
        manager.is_img2img = True
        manager.is_inpaint = False
        manager.is_outpaint = False

        pipeline_class = manager._pipeline_class
        assert pipeline_class == FluxImg2ImgPipeline

    def test_pipeline_class_inpaint(self):
        """Test _pipeline_class returns inpaint when is_inpaint is True."""
        manager = FluxModelManager()
        manager.is_img2img = False
        manager.is_inpaint = True
        manager.is_outpaint = False

        pipeline_class = manager._pipeline_class
        assert pipeline_class == FluxInpaintPipeline

    def test_pipeline_class_outpaint(self):
        """Test _pipeline_class returns outpaint when is_outpaint is True."""
        manager = FluxModelManager()
        manager.is_img2img = False
        manager.is_inpaint = False
        manager.is_outpaint = True

        pipeline_class = manager._pipeline_class
        assert pipeline_class == FluxInpaintPipeline

    def test_use_from_single_file_false(self):
        """Test FLUX uses from_pretrained, not from_single_file."""
        manager = FluxModelManager()
        assert manager.use_from_single_file is False

    def test_use_compel_disabled(self):
        """Test Compel is disabled for FLUX (uses T5, not CLIP)."""
        manager = FluxModelManager()
        assert manager.use_compel is False

    def test_compel_tokenizer_with_pipe(self):
        """Test compel_tokenizer returns tokenizer when pipe has it."""
        manager = FluxModelManager()
        mock_pipe = Mock()
        mock_pipe.tokenizer = Mock()
        manager._pipe = mock_pipe

        assert manager.compel_tokenizer == mock_pipe.tokenizer

    def test_compel_tokenizer_without_pipe(self):
        """Test compel_tokenizer returns None when no pipe."""
        manager = FluxModelManager()
        manager._pipe = None

        assert manager.compel_tokenizer is None

    def test_compel_text_encoder_with_pipe(self):
        """Test compel_text_encoder returns text encoder when pipe has it."""
        manager = FluxModelManager()
        mock_pipe = Mock()
        mock_pipe.text_encoder = Mock()
        manager._pipe = mock_pipe

        assert manager.compel_text_encoder == mock_pipe.text_encoder

    def test_compel_text_encoder_without_pipe(self):
        """Test compel_text_encoder returns None when no pipe."""
        manager = FluxModelManager()
        manager._pipe = None

        assert manager.compel_text_encoder is None

    @patch(
        "airunner.components.art.managers.stablediffusion.flux_model_manager.torch"
    )
    def test_prepare_pipe_data_sets_bfloat16(self, mock_torch):
        """Test _prepare_pipe_data sets bfloat16 dtype."""
        manager = FluxModelManager()
        mock_torch.bfloat16 = torch.bfloat16

        with patch.object(
            manager, "_prepare_pipe_data", wraps=manager._prepare_pipe_data
        ) as mock_method:
            # Mock parent's _prepare_pipe_data to return base data
            with patch.object(
                FluxModelManager.__bases__[0],
                "_prepare_pipe_data",
                return_value={"test": "data"},
            ):
                data = manager._prepare_pipe_data()

        assert "torch_dtype" in data
        assert data["torch_dtype"] == torch.bfloat16
        assert "safety_checker" not in data
        assert "feature_extractor" not in data

    @patch(
        "airunner.components.art.managers.stablediffusion.flux_model_manager.torch.cuda"
    )
    def test_make_memory_efficient_high_vram(self, mock_cuda):
        """Test memory optimizations for high VRAM (≥24GB)."""
        manager = FluxModelManager()
        mock_pipe = MagicMock()
        manager._pipe = mock_pipe
        manager._device = "cuda:0"
        manager.logger = Mock()

        # Mock CUDA device with 24GB VRAM
        mock_cuda.is_available.return_value = True
        mock_props = Mock()
        mock_props.total_memory = 24 * 1024**3  # 24GB
        mock_cuda.get_device_properties.return_value = mock_props

        manager._make_memory_efficient()

        # Should load full model to GPU for 24GB+
        mock_pipe.to.assert_called_once_with("cuda:0")
        # Should not enable CPU offload
        mock_pipe.enable_model_cpu_offload.assert_not_called()

    @patch(
        "airunner.components.art.managers.stablediffusion.flux_model_manager.torch.cuda"
    )
    def test_make_memory_efficient_medium_vram(self, mock_cuda):
        """Test memory optimizations for medium VRAM (16-24GB) - RTX 5080."""
        manager = FluxModelManager()
        mock_pipe = MagicMock()
        manager._pipe = mock_pipe
        manager.logger = Mock()

        # Mock CUDA device with 16GB VRAM (RTX 5080)
        mock_cuda.is_available.return_value = True
        mock_props = Mock()
        mock_props.total_memory = 16 * 1024**3  # 16GB
        mock_cuda.get_device_properties.return_value = mock_props

        manager._make_memory_efficient()

        # Should enable CPU offload for 16GB
        mock_pipe.enable_model_cpu_offload.assert_called_once()
        # Should enable VAE slicing
        mock_pipe.enable_vae_slicing.assert_called_once()
        # Should enable attention slicing
        mock_pipe.enable_attention_slicing.assert_called_once_with("auto")

    @patch(
        "airunner.components.art.managers.stablediffusion.flux_model_manager.torch.cuda"
    )
    def test_make_memory_efficient_low_vram(self, mock_cuda):
        """Test memory optimizations for low VRAM (<16GB)."""
        manager = FluxModelManager()
        mock_pipe = MagicMock()
        manager._pipe = mock_pipe
        manager.logger = Mock()

        # Mock CUDA device with 12GB VRAM
        mock_cuda.is_available.return_value = True
        mock_props = Mock()
        mock_props.total_memory = 12 * 1024**3  # 12GB
        mock_cuda.get_device_properties.return_value = mock_props

        manager._make_memory_efficient()

        # Should enable both CPU offload methods for <16GB
        mock_pipe.enable_model_cpu_offload.assert_called_once()
        mock_pipe.enable_sequential_cpu_offload.assert_called_once()

    @patch(
        "airunner.components.art.managers.stablediffusion.flux_model_manager.torch.cuda"
    )
    def test_make_memory_efficient_no_cuda(self, mock_cuda):
        """Test memory optimizations when CUDA is not available."""
        manager = FluxModelManager()
        mock_pipe = MagicMock()
        manager._pipe = mock_pipe
        manager.logger = Mock()

        # Mock no CUDA
        mock_cuda.is_available.return_value = False

        manager._make_memory_efficient()

        # Should log warning
        manager.logger.warning.assert_called_once()

    def test_load_prompt_embeds(self):
        """Test _load_prompt_embeds for FLUX (no pre-computation)."""
        manager = FluxModelManager()
        manager.logger = Mock()
        manager.prompt = "test prompt"
        manager.negative_prompt = "test negative"

        manager._load_prompt_embeds()

        # Should store prompts but not compute embeddings
        assert manager._current_prompt == "test prompt"
        assert manager._current_negative_prompt == "test negative"

    def test_clear_memory_efficient_settings(self):
        """Test clearing memory efficient settings."""
        manager = FluxModelManager()
        mock_pipe = MagicMock()
        manager._pipe = mock_pipe

        manager._clear_memory_efficient_settings()

        # Should disable VAE and attention slicing
        mock_pipe.disable_vae_slicing.assert_called_once()
        mock_pipe.disable_attention_slicing.assert_called_once()

    def test_load_model_interface(self):
        """Test load_model interface method."""
        manager = FluxModelManager()

        with patch.object(manager, "_load_model") as mock_load:
            manager.load_model("arg1", kwarg1="value1")
            mock_load.assert_called_once_with("arg1", kwarg1="value1")

    def test_unload_model_interface(self):
        """Test unload_model interface method."""
        manager = FluxModelManager()

        with patch.object(manager, "_unload_model") as mock_unload:
            manager.unload_model("arg1", kwarg1="value1")
            mock_unload.assert_called_once_with("arg1", kwarg1="value1")

    def test_load_model_calls_load(self):
        """Test _load_model calls load method."""
        manager = FluxModelManager()

        with patch.object(manager, "load") as mock_load:
            manager._load_model()
            mock_load.assert_called_once()

    def test_unload_model_calls_unload(self):
        """Test _unload_model calls unload method."""
        manager = FluxModelManager()

        with patch.object(manager, "unload") as mock_unload:
            manager._unload_model()
            mock_unload.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
