"""
Unit tests for melo.mel_processing
Covers importability and basic function presence.
"""

import pytest
import airunner.vendor.melo.mel_processing as mel_processing
import torch
import numpy as np
import types


def test_module_importable():
    assert mel_processing is not None


# --- dynamic_range_compression_torch / decompression ---
def test_dynamic_range_compression_and_decompression():
    x = torch.linspace(0.01, 10, 10)
    compressed = mel_processing.dynamic_range_compression_torch(x)
    decompressed = mel_processing.dynamic_range_decompression_torch(compressed)
    assert torch.allclose(x, decompressed, atol=1e-5)


# --- spectral_normalize_torch / de_normalize ---
def test_spectral_normalize_and_denormalize():
    x = torch.linspace(0.01, 10, 10)
    normed = mel_processing.spectral_normalize_torch(x)
    denormed = mel_processing.spectral_de_normalize_torch(normed)
    assert torch.allclose(x, denormed, atol=1e-5)


# --- spectrogram_torch ---
def test_spectrogram_torch_shape():
    # Use 1D input of length 2048 (>> 384 pad) to ensure reflect pad works
    y = torch.randn(2048)
    spec = mel_processing.spectrogram_torch(
        y, n_fft=512, sampling_rate=22050, hop_size=128, win_size=512
    )
    assert spec.shape[0] == 257  # n_fft//2+1
    assert spec.shape[1] > 0


# --- spectrogram_torch_conv ---
def test_spectrogram_torch_conv_shape_and_assert():
    y = torch.randn(2048)
    spec = mel_processing.spectrogram_torch_conv(
        y, n_fft=512, sampling_rate=22050, hop_size=128, win_size=512
    )
    assert spec.shape[0] == 257
    assert spec.shape[1] > 0


# --- spec_to_mel_torch ---
def test_spec_to_mel_torch_shape():
    y = torch.randn(2048)
    spec = mel_processing.spectrogram_torch(
        y, n_fft=512, sampling_rate=22050, hop_size=128, win_size=512
    )
    mel = mel_processing.spec_to_mel_torch(
        spec, n_fft=512, num_mels=80, sampling_rate=22050, fmin=0, fmax=8000
    )
    assert mel.shape[0] == 80
    assert mel.shape[1] == spec.shape[1]


# --- mel_spectrogram_torch ---
def test_mel_spectrogram_torch_shape():
    y = torch.randn(2**12)
    mel = mel_processing.mel_spectrogram_torch(
        y,
        n_fft=512,
        num_mels=80,
        sampling_rate=22050,
        hop_size=128,
        win_size=512,
        fmin=0,
        fmax=8000,
    )
    assert mel.shape[0] == 80
    assert mel.shape[1] > 0


# --- edge/error cases ---
def test_dynamic_range_compression_clip():
    x = torch.tensor([-1.0, 0.0, 1.0])
    out = mel_processing.dynamic_range_compression_torch(x)
    assert torch.isfinite(out).all()


def test_dynamic_range_decompression_zero():
    x = torch.zeros(5)
    out = mel_processing.dynamic_range_decompression_torch(x)
    assert torch.allclose(out, torch.ones(5))


# --- test global cache keys ---
def test_mel_basis_and_hann_window_cache():
    y = torch.randn(2**10)
    mel_processing.mel_spectrogram_torch(
        y,
        n_fft=256,
        num_mels=40,
        sampling_rate=22050,
        hop_size=64,
        win_size=256,
        fmin=0,
        fmax=4000,
    )
    # Should have populated global dicts
    assert len(mel_processing.mel_basis) > 0
    assert len(mel_processing.hann_window) > 0
