"""
Unit tests for openvoice.se_extractor
Covers importability and basic function presence.
"""

import pytest
import airunner.vendor.openvoice.se_extractor as se_extractor
import torch
import os
from unittest.mock import MagicMock


def test_module_importable():
    assert se_extractor is not None


# Add more specific tests for public functions/classes as needed
def test_hash_numpy_array(monkeypatch, tmp_path):
    # Patch librosa.load to return a known array
    import numpy as np

    dummy_array = np.arange(10, dtype=np.float32)
    monkeypatch.setattr(
        "librosa.load", lambda path, sr=None, mono=True: (dummy_array, 16000)
    )
    dummy_file = tmp_path / "dummy.wav"
    dummy_file.write_bytes(b"dummy")
    result = se_extractor.hash_numpy_array(str(dummy_file))
    assert isinstance(result, str)
    assert len(result) == 16


def test_split_audio_vad_success(monkeypatch, tmp_path):
    # Patch all audio/model dependencies
    dummy_audio_path = tmp_path / "audio.wav"
    dummy_audio_path.write_bytes(b"dummy")
    dummy_audio_name = "audio"
    target_dir = tmp_path / "target"
    (target_dir).mkdir()

    # Patch torch.hub.load
    class DummyVAD:
        pass

    def dummy_hub_load(*a, **k):
        return DummyVAD(), [lambda *a, **k: [{"start": 0, "end": 16000}]]

    monkeypatch.setattr("torch.hub.load", dummy_hub_load)
    # Patch torchaudio.load
    monkeypatch.setattr("torchaudio.load", lambda path: (torch.ones(1, 16000), 16000))

    # Patch torchaudio.transforms.Resample
    class DummyResample:
        def __init__(self, a, b):
            pass

        def __call__(self, x):
            return x

    monkeypatch.setattr("torchaudio.transforms.Resample", DummyResample)

    # Patch AudioSegment
    class DummyAudio:
        duration_seconds = 1.0

        def __getitem__(self, sl):
            return self

        def export(self, out, format):
            return None

        def __iadd__(self, other):
            return self

    monkeypatch.setattr("pydub.AudioSegment.from_file", lambda path: DummyAudio())
    monkeypatch.setattr("pydub.AudioSegment.silent", lambda duration: DummyAudio())
    # Patch os.makedirs
    monkeypatch.setattr("os.makedirs", lambda *a, **k: None)
    # Patch os.path.exists to always return True for wavs_folder
    monkeypatch.setattr("os.path.exists", lambda path: True)
    # Patch logger
    monkeypatch.setattr("logging.getLogger", lambda *a, **k: MagicMock())
    wavs_folder = se_extractor.split_audio_vad(
        str(dummy_audio_path), dummy_audio_name, str(target_dir), split_seconds=0.5
    )
    assert os.path.exists(wavs_folder)


def test_split_audio_vad_too_short(monkeypatch, tmp_path):
    # Patch all audio/model dependencies
    dummy_audio_path = tmp_path / "audio.wav"
    dummy_audio_path.write_bytes(b"dummy")
    dummy_audio_name = "audio"
    target_dir = tmp_path / "target"
    (target_dir).mkdir()

    # Patch torch.hub.load
    class DummyVAD:
        pass

    def dummy_hub_load(*a, **k):
        return DummyVAD(), [lambda *a, **k: [{"start": 0, "end": 16000}]]

    monkeypatch.setattr("torch.hub.load", dummy_hub_load)
    # Patch torchaudio.load
    monkeypatch.setattr("torchaudio.load", lambda path: (torch.ones(1, 16000), 16000))

    # Patch torchaudio.transforms.Resample
    class DummyResample:
        def __init__(self, a, b):
            pass

        def __call__(self, x):
            return x

    monkeypatch.setattr("torchaudio.transforms.Resample", DummyResample)

    # Patch AudioSegment
    class DummyAudio:
        duration_seconds = 0.1

        def __getitem__(self, sl):
            return self

        def export(self, out, format):
            return None

        def __iadd__(self, other):
            return self

    monkeypatch.setattr("pydub.AudioSegment.from_file", lambda path: DummyAudio())
    monkeypatch.setattr("pydub.AudioSegment.silent", lambda duration: DummyAudio())
    # Patch os.makedirs
    monkeypatch.setattr("os.makedirs", lambda *a, **k: None)
    # Patch logger
    monkeypatch.setattr("logging.getLogger", lambda *a, **k: MagicMock())
    with pytest.raises(AssertionError):
        se_extractor.split_audio_vad(
            str(dummy_audio_path), dummy_audio_name, str(target_dir), split_seconds=1.0
        )


def test_get_se_success(monkeypatch, tmp_path):
    # Patch dependencies
    dummy_audio_path = tmp_path / "audio.wav"
    dummy_audio_path.write_bytes(b"dummy")
    # Patch hash_numpy_array
    monkeypatch.setattr(se_extractor, "hash_numpy_array", lambda path: "hashval")
    # Patch split_audio_vad
    wavs_folder = tmp_path / "wavs"
    wavs_folder.mkdir()
    dummy_wav = wavs_folder / "seg0.wav"
    dummy_wav.write_bytes(b"dummy")
    monkeypatch.setattr(
        se_extractor, "split_audio_vad", lambda *a, **k: str(wavs_folder)
    )
    # Patch glob
    monkeypatch.setattr(se_extractor, "glob", lambda pattern: [str(dummy_wav)])
    # Patch logger
    monkeypatch.setattr("logging.getLogger", lambda *a, **k: MagicMock())

    # Dummy vc_model
    class DummyVC:
        version = "v1"

        def extract_se(self, audio_segs, se_save_path=None):
            return "se_result"

    se, audio_name = se_extractor.get_se(
        str(dummy_audio_path), DummyVC(), target_dir=str(tmp_path)
    )
    assert se == "se_result"
    assert isinstance(audio_name, str)


def test_get_se_no_segments(monkeypatch, tmp_path):
    dummy_audio_path = tmp_path / "audio.wav"
    dummy_audio_path.write_bytes(b"dummy")
    monkeypatch.setattr(se_extractor, "hash_numpy_array", lambda path: "hashval")
    monkeypatch.setattr(se_extractor, "split_audio_vad", lambda *a, **k: str(tmp_path))
    monkeypatch.setattr(se_extractor, "glob", lambda pattern: [])
    monkeypatch.setattr("logging.getLogger", lambda *a, **k: MagicMock())

    class DummyVC:
        version = "v1"

        def extract_se(self, audio_segs, se_save_path=None):
            return None

    se, audio_name = se_extractor.get_se(
        str(dummy_audio_path), DummyVC(), target_dir=str(tmp_path)
    )
    assert se is None and audio_name is None


def test_get_se_exception(monkeypatch, tmp_path):
    dummy_audio_path = tmp_path / "audio.wav"
    dummy_audio_path.write_bytes(b"dummy")
    monkeypatch.setattr(se_extractor, "hash_numpy_array", lambda path: "hashval")
    monkeypatch.setattr(
        se_extractor,
        "split_audio_vad",
        lambda *a, **k: (_ for _ in ()).throw(Exception("fail")),
    )
    monkeypatch.setattr("logging.getLogger", lambda *a, **k: MagicMock())

    class DummyVC:
        version = "v1"

        def extract_se(self, audio_segs, se_save_path=None):
            return None

    se, audio_name = se_extractor.get_se(
        str(dummy_audio_path), DummyVC(), target_dir=str(tmp_path)
    )
    assert se is None and audio_name is None


def test_split_audio_vad_initializes_vad(monkeypatch, tmp_path):
    # Remove vad_model attribute if present
    if hasattr(se_extractor.split_audio_vad, "vad_model"):
        delattr(se_extractor.split_audio_vad, "vad_model")
    dummy_audio_path = tmp_path / "audio.wav"
    dummy_audio_path.write_bytes(b"dummy")
    dummy_audio_name = "audio"
    target_dir = tmp_path / "target"
    target_dir.mkdir()

    # Patch torch.hub.load to check it is called
    called = {}

    def dummy_hub_load(*a, **k):
        called["loaded"] = True

        class DummyVAD:
            pass

        return DummyVAD(), [lambda *a, **k: [{"start": 0, "end": 16000}]]

    monkeypatch.setattr("torch.hub.load", dummy_hub_load)
    monkeypatch.setattr("torchaudio.load", lambda path: (torch.ones(1, 16000), 16000))

    class DummyResample:
        def __init__(self, a, b):
            pass

        def __call__(self, x):
            return x

    monkeypatch.setattr("torchaudio.transforms.Resample", DummyResample)

    class DummyAudio:
        duration_seconds = 1.0

        def __getitem__(self, sl):
            return self

        def export(self, out, format):
            return None

        def __iadd__(self, other):
            return self

    monkeypatch.setattr("pydub.AudioSegment.from_file", lambda path: DummyAudio())
    monkeypatch.setattr("pydub.AudioSegment.silent", lambda duration: DummyAudio())
    monkeypatch.setattr("os.makedirs", lambda *a, **k: None)
    monkeypatch.setattr("os.path.exists", lambda path: True)
    monkeypatch.setattr("logging.getLogger", lambda *a, **k: MagicMock())
    wavs_folder = se_extractor.split_audio_vad(
        str(dummy_audio_path), dummy_audio_name, str(target_dir), split_seconds=0.5
    )
    assert os.path.exists(wavs_folder)
    assert called.get("loaded")


def test_split_audio_vad_resample_branch(monkeypatch, tmp_path):
    dummy_audio_path = tmp_path / "audio.wav"
    dummy_audio_path.write_bytes(b"dummy")
    dummy_audio_name = "audio"
    target_dir = tmp_path / "target"
    target_dir.mkdir()
    monkeypatch.setattr(
        "torch.hub.load",
        lambda *a, **k: (MagicMock(), [lambda *a, **k: [{"start": 0, "end": 16000}]]),
    )
    # Simulate sample_rate != 16000
    monkeypatch.setattr("torchaudio.load", lambda path: (torch.ones(1, 16000), 8000))
    called = {}

    class DummyResample:
        def __init__(self, a, b):
            called["resample"] = (a, b)

        def __call__(self, x):
            return x

    monkeypatch.setattr("torchaudio.transforms.Resample", DummyResample)

    class DummyAudio:
        duration_seconds = 1.0

        def __getitem__(self, sl):
            return self

        def export(self, out, format):
            return None

        def __iadd__(self, other):
            return self

    monkeypatch.setattr("pydub.AudioSegment.from_file", lambda path: DummyAudio())
    monkeypatch.setattr("pydub.AudioSegment.silent", lambda duration: DummyAudio())
    monkeypatch.setattr("os.makedirs", lambda *a, **k: None)
    monkeypatch.setattr("os.path.exists", lambda path: True)
    monkeypatch.setattr("logging.getLogger", lambda *a, **k: MagicMock())
    wavs_folder = se_extractor.split_audio_vad(
        str(dummy_audio_path), dummy_audio_name, str(target_dir), split_seconds=0.5
    )
    assert os.path.exists(wavs_folder)
    assert called.get("resample") == (8000, 16000)


def test_get_se_extract_se_none_logs(monkeypatch, tmp_path):
    dummy_audio_path = tmp_path / "audio.wav"
    dummy_audio_path.write_bytes(b"dummy")
    monkeypatch.setattr(se_extractor, "hash_numpy_array", lambda path: "hashval")
    wavs_folder = tmp_path / "wavs"
    wavs_folder.mkdir()
    dummy_wav = wavs_folder / "seg0.wav"
    dummy_wav.write_bytes(b"dummy")
    monkeypatch.setattr(
        se_extractor, "split_audio_vad", lambda *a, **k: str(wavs_folder)
    )
    monkeypatch.setattr(se_extractor, "glob", lambda pattern: [str(dummy_wav)])
    logger = MagicMock()
    monkeypatch.setattr("logging.getLogger", lambda *a, **k: logger)

    class DummyVC:
        version = "v1"

        def extract_se(self, audio_segs, se_save_path=None):
            return None

    se, audio_name = se_extractor.get_se(
        str(dummy_audio_path), DummyVC(), target_dir=str(tmp_path)
    )
    assert se is None and isinstance(audio_name, str)
    logger.error.assert_any_call("vc_model.extract_se returned None!")
