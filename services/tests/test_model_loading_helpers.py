"""Unit tests for the model loading extraction helpers.

_unregistered_response and _prepared_success were extracted to keep
prepare_model_loading within the long-function threshold. These
tests pin the require-registered state transition and the success
summary shape.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

from airunner_services.model_management.mixins._base_model_loading_mixin import (
    ModelLoadingMixin,
)
from airunner_services.model_management.types import ModelState


def _make_obj():
    obj = ModelLoadingMixin.__new__(ModelLoadingMixin)
    obj.logger = MagicMock()
    obj.set_model_state = MagicMock()
    obj._prepare_unregistered_model = MagicMock(return_value="unreg")
    return obj


def test_require_registered_marks_unloaded_and_blocks():
    obj = _make_obj()
    out = obj._unregistered_response("m1", "llm", True, True)
    assert out["can_load"] is False
    assert "not registered" in out["reason"]
    assert out["swapped_models"] == []
    obj.set_model_state.assert_called_once_with("m1", ModelState.UNLOADED)


def test_unregistered_without_require_delegates():
    obj = _make_obj()
    out = obj._unregistered_response("m1", "llm", False, True)
    assert out == "unreg"
    obj._prepare_unregistered_model.assert_called_once_with(
        "m1", "llm", True
    )
    obj.set_model_state.assert_not_called()


def test_prepared_success_shape():
    obj = _make_obj()
    metadata = SimpleNamespace(name="N")
    quantization = SimpleNamespace(description="Q")
    out = obj._prepared_success(metadata, quantization, "alloc", ["s1"])
    assert out == {
        "can_load": True,
        "metadata": metadata,
        "quantization": quantization,
        "allocation": "alloc",
        "swapped_models": ["s1"],
    }
    obj.logger.info.assert_called_once()
