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
    with patch.object(sdxl_model_manager.SDXLModelManager, "_load_model") as mock_load:
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


def test_sdxl_model_manager_handles_token_sequence_mismatch(monkeypatch):
    """Test that SDXLModelManager handles token sequence mismatch error from compel gracefully."""
    manager = sdxl_model_manager.SDXLModelManager()
    type(manager).use_compel = PropertyMock(return_value=True)
    manager._compel_proc = MagicMock()

    # Simulate RuntimeError from compel
    def raise_runtime_error(*args, **kwargs):
        raise RuntimeError("token sequence mismatch for fragment at index 0")

    manager._compel_proc.build_conditioning_tensor.side_effect = raise_runtime_error
    # Patch prompt/negative_prompt/second_prompt/second_negative_prompt properties to return test values
    type(manager).prompt = PropertyMock(return_value="test prompt")
    type(manager).second_prompt = PropertyMock(return_value="")
    type(manager).negative_prompt = PropertyMock(return_value="")
    type(manager).second_negative_prompt = PropertyMock(return_value="")
    manager._current_prompt = None
    manager._current_prompt_2 = None
    manager._current_negative_prompt = None
    manager._current_negative_prompt_2 = None
    manager._prompt_embeds = None
    manager._pooled_prompt_embeds = None
    manager._negative_prompt_embeds = None
    manager._negative_pooled_prompt_embeds = None
    # Patch _device property to return 'cpu'
    type(manager)._device = PropertyMock(return_value="cpu")
    with pytest.raises(ValueError) as excinfo:
        manager._load_prompt_embeds()
    assert "Prompt could not be processed" in str(excinfo.value)
