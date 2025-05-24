"""
Unit tests for airunner.utils.memory.gpu_memory_stats
Covers all code paths for gpu_memory_stats(device), including CUDA and non-CUDA devices.
"""

import pytest
from unittest.mock import patch, MagicMock
from airunner.utils.memory.gpu_memory_stats import gpu_memory_stats


def test_gpu_memory_stats_cuda():
    # Mock device and torch.cuda methods for CUDA device
    mock_device = MagicMock()
    mock_device.type = "cuda"
    with patch("airunner.utils.memory.gpu_memory_stats.torch") as torch_mock:
        torch_mock.cuda.get_device_properties.return_value.total_memory = (
            8 * 1024**3
        )
        torch_mock.cuda.memory_allocated.return_value = 2 * 1024**3
        torch_mock.cuda.get_device_name.return_value = "Mock GPU"
        stats = gpu_memory_stats(mock_device)
        assert stats["total"] == 8
        assert stats["allocated"] == 2
        assert stats["free"] == 6
        assert stats["device_name"] == "Mock GPU"


def test_gpu_memory_stats_non_cuda():
    # Mock device for non-CUDA device
    mock_device = MagicMock()
    mock_device.type = "cpu"
    stats = gpu_memory_stats(mock_device)
    assert stats == {
        "total": 0,
        "allocated": 0,
        "free": 0,
        "device_name": "N/A",
    }
