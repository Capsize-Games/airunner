"""
Unit tests for openvoice.mel_processing
Covers mel spectrogram and audio processing utilities.
"""

import pytest
import torch
import airunner.vendor.openvoice.mel_processing as mel_processing


def test_module_importable():
    assert mel_processing is not None


def test_dynamic_range_compression_and_decompression():
    x = torch.rand(10) * 10
    compressed = mel_processing.dynamic_range_compression_torch(x)
    decompressed = mel_processing.dynamic_range_decompression_torch(compressed)
    assert torch.allclose(x, decompressed, atol=1e-4)


def test_spectral_normalize_and_denormalize():
    x = torch.rand(10) * 10
    normed = mel_processing.spectral_normalize_torch(x)
    denormed = mel_processing.spectral_de_normalize_torch(normed)
    assert torch.allclose(x, denormed, atol=1e-4)


def test_spectrogram_torch_shape():
    y = torch.randn(1, 16000)  # 1 second of fake audio at 16kHz
    n_fft = 400
    hop_size = 160
    win_size = 400
    spec = mel_processing.spectrogram_torch(y, n_fft, 16000, hop_size, win_size)
    assert spec.shape[0] == 1
    assert spec.shape[1] > 0


def test_spec_to_mel_torch_shape():
    # Generate a spectrogram with correct shape: (n_fft // 2 + 1, frames)
    n_fft = 400
    num_mels = 80
    sampling_rate = 16000
    fmin = 0
    fmax = 8000
    frames = 100
    spec = torch.abs(torch.randn(n_fft // 2 + 1, frames))
    mel = mel_processing.spec_to_mel_torch(
        spec, n_fft, num_mels, sampling_rate, fmin, fmax
    )
    assert mel.shape[0] == num_mels
    assert mel.shape[1] == frames


def test_mel_spectrogram_torch_shape():
    y = torch.randn(1, 16000)
    n_fft = 400
    num_mels = 80
    sampling_rate = 16000
    hop_size = 160
    win_size = 400
    fmin = 0
    fmax = 8000
    mel = mel_processing.mel_spectrogram_torch(
        y, n_fft, num_mels, sampling_rate, hop_size, win_size, fmin, fmax
    )
    # mel shape: (batch, num_mels, time)
    assert mel.shape[0] == 1  # batch size
    assert mel.shape[1] == num_mels
    assert mel.shape[2] > 0


def test_spectrogram_torch_conv_runs():
    y = torch.randn(1, 400)  # Short fake audio
    n_fft = 400
    hop_size = 160
    win_size = 400
    # Should not raise assertion error (center=False)
    mel_processing.spectrogram_torch_conv(
        y, n_fft, 16000, hop_size, win_size, center=False
    )


def test_spectrogram_torch_conv_assertion():
    y = torch.randn(1, 400)
    n_fft = 400
    hop_size = 160
    win_size = 400
    # Should raise assertion error if center=True
    with pytest.raises(AssertionError):
        mel_processing.spectrogram_torch_conv(
            y, n_fft, 16000, hop_size, win_size, center=True
        )


def test_global_cache_exercise():
    # Exercise mel_basis and hann_window cache logic
    y = torch.randn(1, 400)
    n_fft = 400
    hop_size = 160
    win_size = 400
    num_mels = 80
    sampling_rate = 16000
    fmin = 0
    fmax = 8000
    # First call (cache miss)
    mel_processing.mel_spectrogram_torch(
        y, n_fft, num_mels, sampling_rate, hop_size, win_size, fmin, fmax
    )
    # Second call (cache hit)
    mel_processing.mel_spectrogram_torch(
        y, n_fft, num_mels, sampling_rate, hop_size, win_size, fmin, fmax
    )


def test_spectrogram_torch_conv_padding_and_shape():
    # Covers line 88: after padding, with different input shapes
    y = torch.randn(2, 401)  # Odd length, batch size 2
    n_fft = 400
    hop_size = 160
    win_size = 400
    out = mel_processing.spectrogram_torch_conv(
        y, n_fft, 16000, hop_size, win_size, center=False
    )
    assert out.shape[0] == 2
    assert out.shape[1] == n_fft // 2 + 1
    assert out.shape[2] > 0


def test_spec_to_mel_torch_cache_miss_and_hit():
    # Clear mel_basis to force cache miss
    mel_processing.mel_basis.clear()
    n_fft = 400
    num_mels = 80
    sampling_rate = 16000
    fmin = 0
    fmax = 8000
    frames = 10
    spec = torch.abs(torch.randn(n_fft // 2 + 1, frames))
    # Cache miss
    mel1 = mel_processing.spec_to_mel_torch(
        spec, n_fft, num_mels, sampling_rate, fmin, fmax
    )
    # Cache hit
    mel2 = mel_processing.spec_to_mel_torch(
        spec, n_fft, num_mels, sampling_rate, fmin, fmax
    )
    assert torch.allclose(mel1, mel2)


def test_mel_spectrogram_torch_cache_miss_and_hit():
    # Clear caches to force both branches
    mel_processing.mel_basis.clear()
    mel_processing.hann_window.clear()
    y = torch.randn(1, 16000)
    n_fft = 400
    num_mels = 80
    sampling_rate = 16000
    hop_size = 160
    win_size = 400
    fmin = 0
    fmax = 8000
    # Cache miss for both
    mel1 = mel_processing.mel_spectrogram_torch(
        y, n_fft, num_mels, sampling_rate, hop_size, win_size, fmin, fmax
    )
    # Cache hit for both
    mel2 = mel_processing.mel_spectrogram_torch(
        y, n_fft, num_mels, sampling_rate, hop_size, win_size, fmin, fmax
    )
    assert torch.allclose(mel1, mel2)


def test_mel_spectrogram_torch_padding_and_stft():
    # Covers lines after padding and after STFT
    y = torch.randn(1, 800)  # Shorter input
    n_fft = 400
    num_mels = 80
    sampling_rate = 16000
    hop_size = 160
    win_size = 400
    fmin = 0
    fmax = 8000
    mel = mel_processing.mel_spectrogram_torch(
        y, n_fft, num_mels, sampling_rate, hop_size, win_size, fmin, fmax
    )
    assert mel.shape[0] == 1
    assert mel.shape[1] == num_mels
    assert mel.shape[2] > 0
