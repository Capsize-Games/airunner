"""Unit tests for the Z-Image preflight extraction helpers.

_preflight_plan and _register_pretrained_model were extracted to
keep _resource_preflight_options within the long-function
threshold. These tests pin the plan caching, the source byte
total, and the registry metadata.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

from airunner_services.model_management.zimage_model_manager import (
    ZImageModelManager,
)
from airunner_services.model_management.quantization_strategy import (
    QuantizationLevel,
)


def _make_obj():
    return ZImageModelManager.__new__(ZImageModelManager)


def _plan():
    component = SimpleNamespace(
        source_tensor_bytes=10,
        estimated_resident_bytes=20,
    )
    plan = SimpleNamespace(
        transformer=component,
        text_encoder=component,
        vae=component,
        estimated_vram_gib=4.5,
        estimated_ram_gib=8.0,
    )
    return plan


def test_preflight_plan_sums_source_bytes_and_caches(monkeypatch):
    monkeypatch.setattr(ZImageModelManager, "use_quantization", False)
    obj = _make_obj()
    plan = _plan()
    loader = MagicMock()
    loader.build_memory_plan.return_value = plan
    obj._get_pretrained_loader_helper = lambda: loader
    got_plan, source = obj._preflight_plan("/m", None)
    assert got_plan is plan
    assert source == 30
    assert obj._zimage_memory_plan is plan


def test_register_model_metadata_and_quantization():
    obj = _make_obj()
    resource_manager = MagicMock()
    plan = _plan()
    out = obj._register_pretrained_model(
        resource_manager, plan, "org/repo", 4, 30, "/models/z"
    )
    assert out == QuantizationLevel.INT4
    metadata = resource_manager.registry.register_model.call_args[0][0]
    assert metadata.name == "Z-Image Turbo"
    assert metadata.huggingface_id == "org/repo"
    assert metadata.model_id == "/models/z"
    assert metadata.size_gb == 30 / (1024**3)
    assert metadata.min_vram_gb == 4.5


def test_register_model_int8_and_none():
    obj = _make_obj()
    manager = MagicMock()
    plan = _plan()
    assert (
        obj._register_pretrained_model(manager, plan, "r", 8, 30, "m")
        == QuantizationLevel.INT8
    )
    assert (
        obj._register_pretrained_model(manager, plan, "r", None, 30, "m")
        == QuantizationLevel.NONE
    )
