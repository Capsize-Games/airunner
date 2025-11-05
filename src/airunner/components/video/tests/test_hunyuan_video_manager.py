"""
Unit tests for HunyuanVideoManager.

Tests model loading, unloading, parameter validation, and cancellation.
"""

import os
import pytest
import torch
import numpy as np
from PIL import Image
from unittest.mock import patch, MagicMock

from airunner.components.video.managers.hunyuan_video_manager import (
    HunyuanVideoManager,
)
from airunner.enums import SignalCode, ModelType


@pytest.fixture
def manager():
    """Create a HunyuanVideoManager instance for testing."""
    with patch("torch.cuda.is_available", return_value=True):
        return HunyuanVideoManager()


@pytest.fixture
def test_image():
    """Create a test input image."""
    return Image.fromarray(
        np.random.randint(0, 255, (384, 640, 3), dtype=np.uint8)
    )


class TestHunyuanVideoManager:
    """Tests for HunyuanVideoManager class."""

    def test_initialization(self, manager):
        """Test manager initializes with correct defaults."""
        assert manager.model_type == ModelType.HUNYUAN_VIDEO
        assert manager.text_encoder is None
        assert manager.text_encoder_2 is None
        assert manager.vae is None
        assert manager.transformer is None
        assert manager.image_encoder is None
        assert manager._cancel_requested is False

    def test_config_override(self):
        """Test configuration can be overridden."""
        config = {
            "num_inference_steps": 100,
            "guidance_scale": 10.0,
            "use_teacache": False,
        }
        with patch("torch.cuda.is_available", return_value=True):
            manager = HunyuanVideoManager(config=config)
            assert manager.num_inference_steps == 100
            assert manager.guidance_scale == 10.0
            assert manager.use_teacache is False

    @patch(
        "airunner.components.video.managers.hunyuan_video_manager.LlamaModel"
    )
    @patch(
        "airunner.components.video.managers.hunyuan_video_manager.CLIPTextModel"
    )
    @patch(
        "airunner.components.video.managers.hunyuan_video_manager.AutoencoderKLHunyuanVideo"
    )
    @patch(
        "airunner.components.video.managers.hunyuan_video_manager.HunyuanVideoTransformer3DModelPacked"
    )
    @patch(
        "airunner.components.video.managers.hunyuan_video_manager.SiglipVisionModel"
    )
    @patch("torch.cuda.is_available", return_value=True)
    def test_load_model_success(
        self,
        mock_cuda,
        mock_siglip,
        mock_transformer,
        mock_vae,
        mock_clip,
        mock_llama,
        manager,
    ):
        """Test successful model loading."""
        # Setup mocks
        mock_llama.from_pretrained.return_value = MagicMock()
        mock_clip.from_pretrained.return_value = MagicMock()
        mock_vae.from_pretrained.return_value = MagicMock()
        mock_transformer.from_pretrained.return_value = MagicMock()
        mock_siglip.from_pretrained.return_value = MagicMock()

        # Load model
        manager._load_model()

        # Verify models were loaded
        assert manager.text_encoder is not None
        assert manager.text_encoder_2 is not None
        assert manager.vae is not None
        assert manager.transformer is not None
        assert manager.image_encoder is not None

    def test_unload_model(self, manager):
        """Test model unloading clears all references."""
        # Set some mock models
        manager.text_encoder = MagicMock()
        manager.text_encoder_2 = MagicMock()
        manager.vae = MagicMock()
        manager.transformer = MagicMock()
        manager.image_encoder = MagicMock()

        # Unload
        with patch("torch.cuda.empty_cache"):
            manager._unload_model()

        # Verify all cleared
        assert manager.text_encoder is None
        assert manager.text_encoder_2 is None
        assert manager.vae is None
        assert manager.transformer is None
        assert manager.image_encoder is None

    def test_generate_video_validates_prompt(self, manager, test_image):
        """Test generate_video rejects empty prompt."""
        with pytest.raises(ValueError, match="Prompt cannot be empty"):
            manager.generate_video(
                prompt="",
                init_image=test_image,
                num_frames=65,
            )

    def test_generate_video_validates_image(self, manager):
        """Test generate_video rejects missing image."""
        with pytest.raises(ValueError, match="Input image is required"):
            manager.generate_video(
                prompt="test prompt",
                init_image=None,
                num_frames=65,
            )

    def test_generate_video_validates_num_frames(self, manager, test_image):
        """Test generate_video validates frame count."""
        with pytest.raises(ValueError, match="num_frames must be at least 1"):
            manager.generate_video(
                prompt="test prompt",
                init_image=test_image,
                num_frames=0,
            )

    def test_generate_video_validates_fps(self, manager, test_image):
        """Test generate_video validates fps."""
        with pytest.raises(ValueError, match="fps must be greater than 0"):
            manager.generate_video(
                prompt="test prompt",
                init_image=test_image,
                num_frames=65,
                fps=0,
            )

    def test_cancel_generation(self, manager):
        """Test generation cancellation flag."""
        assert manager._cancel_requested is False

        manager.cancel_generation()

        assert manager._cancel_requested is True

    def test_emit_progress(self, manager):
        """Test progress signal emission."""
        callback_data = None

        def callback(data):
            nonlocal callback_data
            callback_data = data

        manager.register(SignalCode.VIDEO_PROGRESS_SIGNAL, callback)

        manager._emit_progress(50, "Test message")

        assert callback_data is not None
        assert callback_data["progress"] == 50
        assert callback_data["message"] == "Test message"

    @patch(
        "airunner.components.video.managers.hunyuan_video_manager.sample_hunyuan"
    )
    @patch("airunner.components.video.managers.hunyuan_video_manager.hunyuan")
    @patch("torch.cuda.is_available", return_value=True)
    def test_generate_video_emits_signals(
        self, mock_cuda, mock_hunyuan, mock_sample, manager, test_image
    ):
        """Test that generate_video emits appropriate signals."""
        # Setup mocks
        manager.text_encoder = MagicMock()
        manager.text_encoder_2 = MagicMock()
        manager.tokenizer = MagicMock()
        manager.tokenizer_2 = MagicMock()
        manager.vae = MagicMock()
        manager.transformer = MagicMock()
        manager.transformer.dtype = torch.float16
        manager.image_encoder = MagicMock()
        manager.feature_extractor = MagicMock()

        # Setup encode_prompt_conds mock
        mock_hunyuan.encode_prompt_conds.return_value = (
            torch.zeros(1, 256, 4096),
            torch.zeros(1, 768),
        )

        # Setup VAE encode mock
        mock_hunyuan.vae_encode.return_value = torch.zeros(1, 16, 1, 48, 80)

        # Setup sample_hunyuan mock
        mock_sample.return_value = torch.zeros(1, 16, 9, 48, 80)

        # Setup VAE decode mock
        mock_hunyuan.vae_decode.return_value = torch.zeros(1, 3, 33, 384, 640)

        # Track progress signals
        progress_signals = []

        def track_progress(data):
            progress_signals.append(data)

        manager.register(SignalCode.VIDEO_PROGRESS_SIGNAL, track_progress)

        # Generate (should emit multiple progress signals)
        with patch(
            "airunner.components.video.managers.hunyuan_video_manager.save_bcthw_as_mp4"
        ):
            with patch(
                "airunner.components.video.managers.hunyuan_video_manager.clip_vision"
            ):
                result = manager.generate_video(
                    prompt="test",
                    init_image=test_image,
                    num_frames=65,
                    steps=10,
                )

        # Should have emitted progress signals
        assert len(progress_signals) > 0
        assert any(d["progress"] == 100 for d in progress_signals)

    def test_high_vram_mode(self):
        """Test high VRAM mode detection."""
        with patch("torch.cuda.is_available", return_value=True):
            with patch("torch.cuda.get_device_properties") as mock_props:
                # Test high VRAM (>60GB)
                mock_props.return_value.total_memory = 70 * 1024**3
                manager = HunyuanVideoManager()
                assert manager.high_vram is True

                # Test low VRAM (<60GB)
                mock_props.return_value.total_memory = 40 * 1024**3
                manager = HunyuanVideoManager()
                assert manager.high_vram is False

    def test_outputs_folder_creation(self, manager):
        """Test outputs folder is created."""
        assert manager.outputs_folder.endswith("hunyuanvideo")
        assert os.path.exists(manager.outputs_folder)


class TestHunyuanVideoManagerIntegration:
    """Integration tests requiring actual model loading."""

    @pytest.mark.slow
    @pytest.mark.gpu
    def test_full_generation_pipeline(self, test_image):
        """Test complete generation pipeline (requires GPU and models)."""
        manager = HunyuanVideoManager()

        try:
            # Load models
            manager._load_model()

            # Generate short video
            output = manager.generate_video(
                prompt="A beautiful landscape",
                negative_prompt="blurry",
                init_image=test_image,
                num_frames=65,
                steps=10,
                seed=42,
            )

            # Verify output
            assert output is not None
            assert output.endswith(".mp4")

        finally:
            manager._unload_model()
