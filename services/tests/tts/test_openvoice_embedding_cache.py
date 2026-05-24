"""Tests for cached OpenVoice speaker embeddings."""

from types import SimpleNamespace

import torch

from airunner_services.vendor.openvoice import se_extractor


def test_get_se_reuses_cached_embedding(tmp_path, monkeypatch):
    audio_path = tmp_path / "voice.wav"
    audio_path.write_bytes(b"")

    target_dir = tmp_path / "processed"
    audio_name = "voice_v2_hash123"
    se_path = target_dir / audio_name / "se.pth"
    se_path.parent.mkdir(parents=True)
    expected = torch.ones(1, 2, 1)
    torch.save(expected, se_path)

    monkeypatch.setattr(
        se_extractor,
        "hash_numpy_array",
        lambda _path: "hash123",
    )

    def _fail_split(*args, **kwargs):
        raise AssertionError("split_audio_vad should not run for cached SE")

    monkeypatch.setattr(se_extractor, "split_audio_vad", _fail_split)
    vc_model = SimpleNamespace(version="v2", device="cpu")

    embedding, resolved_audio_name = se_extractor.get_se(
        str(audio_path),
        vc_model,
        str(target_dir),
    )

    assert torch.equal(embedding, expected)
    assert resolved_audio_name == audio_name