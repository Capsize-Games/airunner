"""
Unit tests for melo.data_utils
Covers importability and basic function presence.
"""

import pytest
import airunner.vendor.melo.data_utils as data_utils
from unittest import mock
import torch
import types


# Minimal hparams mock
class HParams:
    def __init__(self):
        self.max_wav_value = 32768
        self.sampling_rate = 22050
        self.filter_length = 1024
        self.hop_length = 256
        self.win_length = 1024
        self.spk2id = types.SimpleNamespace(a=0, b=1)
        self.add_blank = False
        self.cleaned_text = False
        self.min_text_len = 1
        self.max_text_len = 10
        self.use_mel_posterior_encoder = False
        self.n_mel_channels = 80
        self.mel_fmin = 0.0
        self.mel_fmax = 8000.0
        self.disable_bert = True


def test_module_importable():
    assert data_utils is not None


@mock.patch(
    "airunner.vendor.melo.data_utils.load_filepaths_and_text",
    return_value=[["f.wav", "a", "ZH", "text", "1 2", "3 4", "1 2"]],
)
@mock.patch("os.path.getsize", return_value=4096)
def test_loader_filter_and_len(mock_getsize, mock_load):
    hparams = HParams()
    loader = data_utils.TextAudioSpeakerLoader("dummy.txt", hparams)
    assert len(loader) == 1


@mock.patch(
    "airunner.vendor.melo.data_utils.load_filepaths_and_text",
    return_value=[["f.wav", "a", "ZH", "text", "1 2", "3 4", "1 2"]],
)
@mock.patch("os.path.getsize", return_value=4096)
@mock.patch(
    "airunner.vendor.melo.data_utils.load_wav_to_torch",
    return_value=(torch.zeros(22050), 22050),
)
@mock.patch("torch.load", side_effect=FileNotFoundError)
@mock.patch("torch.save")
@mock.patch(
    "airunner.vendor.melo.data_utils.cleaned_text_to_sequence",
    return_value=([1, 2], [3, 4], [5, 6]),
)
def test_loader_getitem_and_audio_text(
    mock_clean, mock_save, mock_load, mock_wav, mock_getsize, mock_file
):
    hparams = HParams()
    loader = data_utils.TextAudioSpeakerLoader("dummy.txt", hparams)
    # Patch get_text to always return tensors
    loader.get_text = lambda *a, **kw: (
        torch.zeros(1024, 2),
        torch.zeros(768, 2),
        torch.LongTensor([1, 2]),
        torch.LongTensor([3, 4]),
        torch.LongTensor([5, 6]),
    )
    loader.get_audio = lambda *a, **kw: (torch.zeros(80, 100), torch.zeros(1, 100))
    loader.spk_map = types.SimpleNamespace(a=0)
    item = loader[0]
    assert isinstance(item, tuple) and len(item) == 8


@mock.patch(
    "airunner.vendor.melo.data_utils.load_filepaths_and_text",
    return_value=[["f.wav", "a", "ZH", "text", "1 2", "3 4", "1 2"]],
)
@mock.patch("os.path.getsize", return_value=4096)
@mock.patch("torch.save")
def test_loader_get_sid(mock_save, mock_getsize, mock_load):
    hparams = HParams()
    loader = data_utils.TextAudioSpeakerLoader("dummy.txt", hparams)
    sid = loader.get_sid(1)
    assert torch.equal(sid, torch.LongTensor([1]))


def test_collate_shapes():
    batch = [
        (
            torch.LongTensor([1, 2]),
            torch.zeros(80, 10),
            torch.zeros(1, 10),
            0,
            torch.LongTensor([1, 2]),
            torch.LongTensor([1, 2]),
            torch.zeros(1024, 2),
            torch.zeros(768, 2),
        ),
        (
            torch.LongTensor([1]),
            torch.zeros(80, 5),
            torch.zeros(1, 5),
            1,
            torch.LongTensor([1]),
            torch.LongTensor([1]),
            torch.zeros(1024, 1),
            torch.zeros(768, 1),
        ),
    ]
    collate = data_utils.TextAudioSpeakerCollate()
    out = collate(batch)
    assert out[0].shape[0] == 2  # batch size
    assert out[0].shape[1] == 2  # max text len
    assert out[2].shape[2] == 10  # max spec len


def test_distributed_bucket_sampler():
    class DummyDataset:
        lengths = [5, 7, 9, 12, 15, 20]

        def __len__(self):
            return len(self.lengths)

    sampler = data_utils.DistributedBucketSampler(
        DummyDataset(),
        batch_size=2,
        boundaries=[0, 6, 10, 20],
        num_replicas=2,
        rank=0,
        shuffle=False,
    )
    batches = list(iter(sampler))
    assert all(isinstance(b, list) for b in batches)
    assert sum(len(b) for b in batches) == sampler.num_samples
    assert len(sampler) == sampler.num_samples // 2
    # Test bisect
    assert sampler._bisect(7) == 1
    assert sampler._bisect(21) == -1
