"""Unit tests for the OpenVoice convert helpers.

_load_reference_audio and _convert_spectrogram were extracted to keep
ToneColorConverter.convert within the long-function threshold. These
tests pin the load-failure None paths and the conversion wiring.
"""

import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock

import numpy as np
import pytest

if "librosa" not in sys.modules:
    try:
        import librosa  # noqa: F401
    except ImportError:
        stub = types.ModuleType("librosa")
        stub.load = lambda *args, **kwargs: ([0.0], 24000)
        sys.modules["librosa"] = stub

for _name in (
    "airunner_tts_vendor",
    "airunner_tts_vendor.melo",
    "airunner_tts_vendor.melo.api",
    "airunner_tts_vendor.openvoice",
    "airunner_tts_vendor.openvoice.api",
    "airunner_tts_vendor.openvoice.mel_processing",
    "airunner_tts_vendor.openvoice.se_extractor",
):
    if _name not in sys.modules:
        try:
            __import__(_name)
        except ImportError:
            _mod = types.ModuleType(_name)
            _mod.__path__ = []
            sys.modules[_name] = _mod

_ov_pkg = sys.modules["airunner_tts_vendor.openvoice"]
if not hasattr(_ov_pkg, "se_extractor"):
    _ov_pkg.se_extractor = sys.modules["airunner_tts_vendor.openvoice.se_extractor"]
_melo_api = sys.modules["airunner_tts_vendor.melo.api"]
if not hasattr(_melo_api, "TTS"):
    _melo_api.TTS = object
    _melo_api.set_memory_cleanup_hook = lambda *args, **kwargs: None
_ov_api = sys.modules["airunner_tts_vendor.openvoice.api"]
if not hasattr(_ov_api, "ToneColorConverter"):
    _ov_api.ToneColorConverter = object
    _ov_api.OpenVoiceBaseClass = object
_mel = sys.modules["airunner_tts_vendor.openvoice.mel_processing"]
if not hasattr(_mel, "spectrogram_torch"):
    _mel.spectrogram_torch = lambda *args, **kwargs: None

import airunner_services.runtimes.openvoice_runtime_helpers as helpers_mod
from airunner_services.runtimes.openvoice_runtime_helpers import (
    StreamingToneColorConverter,
)


def _make_obj():
    obj = StreamingToneColorConverter.__new__(StreamingToneColorConverter)
    obj.logger = MagicMock()
    obj.hps = SimpleNamespace(
        data=SimpleNamespace(
            sampling_rate=22050,
            filter_length=1024,
            hop_length=256,
            win_length=1024,
        )
    )
    obj.device = "cpu"
    obj.model = MagicMock()
    return obj


def test_convert_short_circuits_when_load_returns_none(monkeypatch):
    obj = _make_obj()
    obj._load_reference_audio = MagicMock(return_value=None)
    obj._convert_spectrogram = MagicMock()
    assert obj.convert("a.wav", "src", "tgt") is None
    obj._convert_spectrogram.assert_not_called()


def test_convert_delegates_to_spectrogram_helper(monkeypatch):
    obj = _make_obj()
    obj._load_reference_audio = MagicMock(return_value=np.zeros(8))
    obj._convert_spectrogram = MagicMock(return_value="done")
    assert obj.convert("a.wav", "src", "tgt", tau=0.5) == "done"
    obj._convert_spectrogram.assert_called_once()
    args = obj._convert_spectrogram.call_args[0]
    assert args[1] == "src" and args[2] == "tgt" and args[3] == 0.5


def test_load_returns_none_on_missing_file(monkeypatch):
    obj = _make_obj()
    monkeypatch.setattr(
        helpers_mod.librosa, "load", MagicMock(side_effect=FileNotFoundError("no"))
    )
    assert obj._load_reference_audio("missing.wav") is None


def test_load_returns_none_on_empty_audio(monkeypatch):
    obj = _make_obj()
    monkeypatch.setattr(
        helpers_mod.librosa, "load", MagicMock(return_value=(np.array([]), 22050))
    )
    assert obj._load_reference_audio("empty.wav") is None


def test_load_returns_audio_on_success(monkeypatch):
    obj = _make_obj()
    samples = np.zeros(16)
    monkeypatch.setattr(
        helpers_mod.librosa, "load", MagicMock(return_value=(samples, 22050))
    )
    assert obj._load_reference_audio("ok.wav") is samples


def test_convert_spectrogram_returns_none_on_runtime_error(monkeypatch):
    obj = _make_obj()
    monkeypatch.setattr(
        helpers_mod,
        "spectrogram_torch",
        MagicMock(side_effect=RuntimeError("gpu gone")),
    )
    assert obj._convert_spectrogram(np.zeros(16), "s", "t", 0.3) is None


def test_convert_spectrogram_runs_voice_conversion(monkeypatch):
    import torch

    obj = _make_obj()
    spec = torch.zeros(1, 1026, 4)
    monkeypatch.setattr(helpers_mod, "spectrogram_torch", MagicMock(return_value=spec))
    converted = torch.zeros(1, 1, 1, 8)
    obj.model.voice_conversion.return_value = (converted,)
    out = obj._convert_spectrogram(np.zeros(16), "s", "t", 0.3)
    assert out is not None
    assert obj.model.voice_conversion.called
