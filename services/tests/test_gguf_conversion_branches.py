"""Unit tests for the GGUF-conversion branch helpers.

_safetensor_files, _convert_safetensors_branch, and
_download_safetensors_branch were extracted to keep
_try_convert_safetensors_to_gguf within the long-function threshold.
These tests pin the inventory, the convert/unavailable signals, and
the download signal behavior.
"""

import os
from unittest.mock import MagicMock

from airunner_services.llm.managers.mixins.model_availability_mixin import (
    ModelAvailabilityMixin,
)
from airunner_services.art.runtime_enums import SignalCode


def _make_obj():
    obj = ModelAvailabilityMixin.__new__(ModelAvailabilityMixin)
    obj.logger = MagicMock()
    obj.emit_signal = MagicMock()
    obj.model_name = "model-x"
    obj._get_repo_id_for_model = MagicMock(return_value="org/repo")
    return obj


def test_safetensor_files_lists_only_safetensors(tmp_path):
    (tmp_path / "a.safetensors").write_bytes(b"")
    (tmp_path / "b.gguf").write_bytes(b"")
    (tmp_path / "c.bin").write_bytes(b"")
    assert ModelAvailabilityMixin._safetensor_files(str(tmp_path)) == [
        "a.safetensors"
    ]


def test_safetensor_files_missing_path_returns_empty(tmp_path):
    assert (
        ModelAvailabilityMixin._safetensor_files(str(tmp_path / "nope"))
        == []
    )


def test_convert_branch_emits_convert_signal(monkeypatch):
    obj = _make_obj()
    optimizer = MagicMock()
    optimizer.has_llama_cpp_convert.return_value = True
    monkeypatch.setattr(
        "airunner_services.utils.model_optimizer.get_model_optimizer",
        lambda: optimizer,
    )
    assert obj._convert_safetensors_branch("/models/x") is False
    code, payload = obj.emit_signal.call_args[0]
    assert code == SignalCode.LLM_CONVERT_TO_GGUF_SIGNAL
    assert payload["model_name"] == "model-x"
    assert payload["quantization"] == "Q4_K_M"


def test_convert_branch_reports_unavailable_tool(monkeypatch):
    obj = _make_obj()
    optimizer = MagicMock()
    optimizer.has_llama_cpp_convert.return_value = False
    monkeypatch.setattr(
        "airunner_services.utils.model_optimizer.get_model_optimizer",
        lambda: optimizer,
    )
    assert obj._convert_safetensors_branch("/models/x") is False
    code, payload = obj.emit_signal.call_args[0]
    assert code == SignalCode.APPLICATION_SETTINGS_ERROR
    assert payload["error"] == "GGUF Conversion Not Available"


def test_download_branch_emits_download_signal():
    obj = _make_obj()
    assert obj._download_safetensors_branch("/models/x") is False
    code, payload = obj.emit_signal.call_args[0]
    assert code == SignalCode.LLM_MODEL_DOWNLOAD_REQUIRED
    assert payload["repo_id"] == "org/repo"
    assert payload["convert_to_gguf"] is True


def test_download_branch_without_repo_emits_nothing():
    obj = _make_obj()
    obj._get_repo_id_for_model.return_value = None
    assert obj._download_safetensors_branch("/models/x") is False
    obj.emit_signal.assert_not_called()
