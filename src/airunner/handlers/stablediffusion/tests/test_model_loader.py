"""
Unit tests for model_loader.py utility functions in stablediffusion handler.
Covers model, scheduler, controlnet, lora, embeddings, compel, and deep cache loading/unloading logic.
"""

import pytest
from unittest.mock import patch, MagicMock
import airunner.handlers.stablediffusion.model_loader as model_loader


def test_load_model_success():
    # Mock the actual model loading logic
    with patch("airunner.handlers.stablediffusion.model_loader.SomeModelClass") as mock_model:
        mock_model.return_value = MagicMock()
        result = model_loader.load_model("/fake/path/model.safetensors")
        assert result is not None


def test_load_model_failure():
    # Simulate an exception during model loading
    with patch("airunner.handlers.stablediffusion.model_loader.SomeModelClass", side_effect=RuntimeError("fail")):
        with pytest.raises(RuntimeError):
            model_loader.load_model("/bad/path/model.safetensors")


def test_unload_model():
    # Should call the unload logic and not raise
    with patch("airunner.handlers.stablediffusion.model_loader.SomeModelClass") as mock_model:
        instance = mock_model.return_value
        instance.unload.return_value = True
        assert model_loader.unload_model(instance) is True


def test_load_scheduler():
    # Test scheduler loading logic
    with patch("airunner.handlers.stablediffusion.model_loader.SomeSchedulerClass") as mock_sched:
        mock_sched.return_value = MagicMock()
        result = model_loader.load_scheduler("DPMSolverMultistepScheduler")
        assert result is not None


def test_load_controlnet():
    # Test controlnet loading logic
    with patch("airunner.handlers.stablediffusion.model_loader.SomeControlNetClass") as mock_ctrl:
        mock_ctrl.return_value = MagicMock()
        result = model_loader.load_controlnet("/fake/path/controlnet.pt")
        assert result is not None


def test_load_lora():
    # Test lora loading logic
    with patch("airunner.handlers.stablediffusion.model_loader.SomeLoraClass") as mock_lora:
        mock_lora.return_value = MagicMock()
        result = model_loader.load_lora("/fake/path/lora.pt")
        assert result is not None


def test_load_embeddings():
    # Test embeddings loading logic
    with patch("airunner.handlers.stablediffusion.model_loader.SomeEmbeddingsClass") as mock_emb:
        mock_emb.return_value = MagicMock()
        result = model_loader.load_embeddings("/fake/path/embeddings.vec")
        assert result is not None


def test_load_compel():
    # Test compel loading logic
    with patch("airunner.handlers.stablediffusion.model_loader.SomeCompelClass") as mock_compel:
        mock_compel.return_value = MagicMock()
        result = model_loader.load_compel("prompt text")
        assert result is not None


def test_deep_cache_loading():
    # Test deep cache loading logic
    with patch("airunner.handlers.stablediffusion.model_loader.SomeDeepCacheClass") as mock_cache:
        mock_cache.return_value = MagicMock()
        result = model_loader.load_deep_cache("/fake/path/cache")
        assert result is not None


def test_deep_cache_unloading():
    # Test deep cache unloading logic
    with patch("airunner.handlers.stablediffusion.model_loader.SomeDeepCacheClass") as mock_cache:
        instance = mock_cache.return_value
        instance.unload.return_value = True
        assert model_loader.unload_deep_cache(instance) is True
