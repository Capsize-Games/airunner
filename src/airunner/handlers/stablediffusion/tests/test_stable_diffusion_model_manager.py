"""
Unit tests for stable_diffusion_model_manager.py in stablediffusion handler.
Covers StableDiffusionModelManager logic, including model loading, unloading, and property access.
"""

import pytest
from unittest.mock import patch, MagicMock, PropertyMock
import airunner.handlers.stablediffusion.stable_diffusion_model_manager as sd_model_manager


def test_stable_diffusion_model_manager_init():
    with patch.object(
        sd_model_manager, "BaseDiffusersModelManager", autospec=True
    ) as mock_base:
        mock_base.return_value = None
        manager = sd_model_manager.StableDiffusionModelManager()
        assert manager is not None
        assert hasattr(manager, "load_model")


def test_stable_diffusion_model_manager_load_model():
    with patch.object(
        sd_model_manager.StableDiffusionModelManager, "_load_model"
    ) as mock_load:
        manager = sd_model_manager.StableDiffusionModelManager()
        mock_load.return_value = "model_obj"
        result = manager.load_model("/fake/path/model.safetensors")
        assert result == "model_obj"


def test_stable_diffusion_model_manager_unload_model():
    with patch.object(
        sd_model_manager.StableDiffusionModelManager, "_unload_model"
    ) as mock_unload:
        manager = sd_model_manager.StableDiffusionModelManager()
        mock_unload.return_value = True
        assert manager.unload_model() is True


def test_stable_diffusion_model_manager_properties():
    manager = sd_model_manager.StableDiffusionModelManager()
    # Patch properties as needed
    manager._model_status = {"SD": "LOADED"}
    assert manager.model_status["SD"] == "LOADED"
