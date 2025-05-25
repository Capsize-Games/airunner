"""
Unit tests for sdxl_model_manager.py in stablediffusion handler.
Covers SDXL model manager logic, including model loading, unloading, and property access.
"""

import pytest
from unittest.mock import patch, MagicMock, PropertyMock
import airunner.handlers.stablediffusion.sdxl_model_manager as sdxl_model_manager


def test_sdxl_model_manager_init():
    with patch.object(
        sdxl_model_manager, "BaseDiffusersModelManager", autospec=True
    ) as mock_base:
        mock_base.return_value = None
        manager = sdxl_model_manager.SDXLModelManager()
        assert manager is not None
        assert hasattr(manager, "load_model")


def test_sdxl_model_manager_load_model():
    with patch.object(
        sdxl_model_manager.SDXLModelManager, "_load_model"
    ) as mock_load:
        manager = sdxl_model_manager.SDXLModelManager()
        mock_load.return_value = "model_obj"
        result = manager.load_model("/fake/path/model.safetensors")
        assert result == "model_obj"


def test_sdxl_model_manager_unload_model():
    with patch.object(
        sdxl_model_manager.SDXLModelManager, "_unload_model"
    ) as mock_unload:
        manager = sdxl_model_manager.SDXLModelManager()
        mock_unload.return_value = True
        assert manager.unload_model() is True


def test_sdxl_model_manager_properties():
    manager = sdxl_model_manager.SDXLModelManager()
    # Patch properties as needed
    manager._model_status = {"SDXL": "LOADED"}
    assert manager.model_status["SDXL"] == "LOADED"
