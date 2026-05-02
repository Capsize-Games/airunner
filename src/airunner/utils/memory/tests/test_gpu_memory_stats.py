"""Regression tests for GPU memory statistics helpers."""

import unittest
from unittest.mock import MagicMock, patch

import torch

from airunner.utils.memory.gpu_memory_stats import gpu_memory_stats


class TestGpuMemoryStats(unittest.TestCase):
    """Cover torch-backed GPU memory reporting and fallback logic."""

    def test_non_cuda_device_returns_default_stats(self):
        """CPU devices should return empty GPU stats."""
        stats = gpu_memory_stats(torch.device("cpu"))

        self.assertEqual(stats["total"], 0.0)
        self.assertEqual(stats["used"], 0.0)
        self.assertEqual(stats["allocated"], 0.0)
        self.assertEqual(stats["reserved"], 0.0)
        self.assertEqual(stats["free"], 0.0)
        self.assertEqual(stats["device_name"], "N/A")

    @patch("airunner.utils.memory.gpu_memory_stats.torch.cuda.get_device_name")
    @patch("airunner.utils.memory.gpu_memory_stats.torch.cuda.memory_reserved")
    @patch("airunner.utils.memory.gpu_memory_stats.torch.cuda.memory_allocated")
    @patch("airunner.utils.memory.gpu_memory_stats.torch.cuda.mem_get_info")
    @patch(
        "airunner.utils.memory.gpu_memory_stats.torch.cuda.get_device_properties"
    )
    def test_cuda_stats_use_driver_memory_when_available(
        self,
        mock_props,
        mock_mem_info,
        mock_allocated,
        mock_reserved,
        mock_name,
    ):
        """Driver memory info should populate used/free VRAM fields."""
        gib = 1024**3
        mock_props.return_value = MagicMock(total_memory=16 * gib)
        mock_mem_info.return_value = (10 * gib, 16 * gib)
        mock_allocated.return_value = 2 * gib
        mock_reserved.return_value = 3 * gib
        mock_name.return_value = "Test GPU"

        stats = gpu_memory_stats(torch.device("cuda:0"))

        self.assertEqual(stats["device_name"], "Test GPU")
        self.assertEqual(stats["total"], 16.0)
        self.assertEqual(stats["used"], 6.0)
        self.assertEqual(stats["free"], 10.0)
        self.assertEqual(stats["allocated"], 2.0)
        self.assertEqual(stats["reserved"], 3.0)

    @patch("airunner.utils.memory.gpu_memory_stats.torch.cuda.get_device_name")
    @patch("airunner.utils.memory.gpu_memory_stats.torch.cuda.memory_reserved")
    @patch("airunner.utils.memory.gpu_memory_stats.torch.cuda.memory_allocated")
    @patch("airunner.utils.memory.gpu_memory_stats.torch.cuda.mem_get_info")
    @patch(
        "airunner.utils.memory.gpu_memory_stats.torch.cuda.get_device_properties"
    )
    def test_cuda_stats_fall_back_without_driver_memory(
        self,
        mock_props,
        mock_mem_info,
        mock_allocated,
        mock_reserved,
        mock_name,
    ):
        """Reserved memory should backfill used/free when mem_get_info fails."""
        gib = 1024**3
        mock_props.return_value = MagicMock(total_memory=16 * gib)
        mock_mem_info.side_effect = RuntimeError("driver unavailable")
        mock_allocated.return_value = 2 * gib
        mock_reserved.return_value = 3 * gib
        mock_name.return_value = "Fallback GPU"

        stats = gpu_memory_stats(torch.device("cuda:0"))

        self.assertEqual(stats["device_name"], "Fallback GPU")
        self.assertEqual(stats["total"], 16.0)
        self.assertEqual(stats["used"], 3.0)
        self.assertEqual(stats["free"], 13.0)
        self.assertEqual(stats["allocated"], 2.0)
        self.assertEqual(stats["reserved"], 3.0)


if __name__ == "__main__":
    unittest.main()