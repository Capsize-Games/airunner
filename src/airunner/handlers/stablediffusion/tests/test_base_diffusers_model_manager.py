"""
Unit tests for BaseDiffusersModelManager core logic.
Covers: _get_results, _initialize_metadata, and interruption logic.
"""

import pytest
from unittest.mock import MagicMock, patch
import torch
from airunner.handlers.stablediffusion.base_diffusers_model_manager import (
    BaseDiffusersModelManager,
)
from airunner.exceptions import InterruptedException


class DummyPipe:
    def __call__(self, **data):
        return {"images": [1, 2, 3]}


def make_manager(monkeypatch=None, n_samples=2, infinite=False):
    mgr = MagicMock(spec=BaseDiffusersModelManager)
    mgr._pipe = DummyPipe()
    mgr.data_type = torch.float32
    mgr.image_request = MagicMock()
    mgr.image_request.n_samples = n_samples
    mgr.image_request.generate_infinite_images = infinite
    mgr.do_interrupt_image_generation = False
    return mgr


def test_get_results_yields_expected(monkeypatch):
    mgr = make_manager()
    data = {"foo": "bar"}
    # Patch torch.no_grad and torch.amp.autocast to be no-ops
    monkeypatch.setattr(torch, "no_grad", lambda: patch("builtins.open"))
    monkeypatch.setattr(
        torch.amp, "autocast", lambda *a, **k: patch("builtins.open")
    )
    results = list(BaseDiffusersModelManager._get_results(mgr, data))
    assert len(results) == mgr.image_request.n_samples
    for r in results:
        assert r["images"] == [1, 2, 3]


def test_get_results_interrupt(monkeypatch):
    mgr = make_manager(n_samples=2)
    data = {"foo": "bar"}
    monkeypatch.setattr(torch, "no_grad", lambda: patch("builtins.open"))
    monkeypatch.setattr(
        torch.amp, "autocast", lambda *a, **k: patch("builtins.open")
    )
    mgr.do_interrupt_image_generation = True
    with pytest.raises(InterruptedException):
        next(BaseDiffusersModelManager._get_results(mgr, data))


def test_initialize_metadata_basic():
    mgr = MagicMock(spec=BaseDiffusersModelManager)
    mgr.metadata_settings.export_metadata = True
    mgr.metadata_settings.image_export_metadata_prompt = True
    mgr.metadata_settings.image_export_metadata_negative_prompt = False
    mgr.metadata_settings.image_export_metadata_scale = False
    mgr.metadata_settings.image_export_metadata_seed = False
    mgr.metadata_settings.image_export_metadata_steps = False
    mgr.metadata_settings.image_export_metadata_ddim_eta = False
    mgr.metadata_settings.image_export_metadata_iterations = False
    mgr.metadata_settings.image_export_metadata_samples = False
    mgr.metadata_settings.image_export_metadata_model = False
    mgr.metadata_settings.image_export_metadata_version = False
    mgr.metadata_settings.image_export_metadata_scheduler = False
    mgr.metadata_settings.image_export_metadata_strength = False
    mgr.metadata_settings.image_export_metadata_lora = False
    mgr.metadata_settings.image_export_metadata_embeddings = False
    mgr.metadata_settings.image_export_metadata_timestamp = False
    mgr.metadata_settings.image_export_metadata_controlnet = False
    mgr.is_txt2img = True
    mgr.is_img2img = False
    mgr.is_outpaint = False
    mgr._current_prompt = "prompt"
    mgr._current_prompt_2 = "prompt2"
    mgr._memory_settings_flags = {"use_tome_sd": False, "tome_ratio": 0.5}
    images = [1, 2]
    data = {}
    meta = BaseDiffusersModelManager._initialize_metadata(mgr, images, data)
    assert isinstance(meta, list)
    assert len(meta) == len(images)
    assert meta[0]["prompt"] == "prompt"
    assert meta[0]["prompt_2"] == "prompt2"
    assert meta[0]["action"] == "txt2img"


def test_initialize_metadata_none():
    mgr = MagicMock(spec=BaseDiffusersModelManager)
    mgr.metadata_settings.export_metadata = False
    images = [1, 2]
    data = {}
    meta = BaseDiffusersModelManager._initialize_metadata(mgr, images, data)
    assert meta is None
