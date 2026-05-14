"""Regression tests for shared CUDA cleanup helpers."""

import unittest
from unittest.mock import patch

import torch

from airunner.utils.memory.clear_memory import clear_memory


class TestClearMemory(unittest.TestCase):
    """Cover device normalization for shared cleanup."""

    def test_cpu_device_skips_cuda_calls(self):
        with patch(
            "airunner.utils.memory.clear_memory.torch.cuda.is_available",
            return_value=True,
        ), patch(
            "airunner.utils.memory.clear_memory.torch.cuda.set_device"
        ) as mock_set_device, patch(
            "airunner.utils.memory.clear_memory.gc.collect"
        ) as mock_gc_collect:
            clear_memory(torch.device("cpu"))

        mock_set_device.assert_not_called()
        mock_gc_collect.assert_called_once_with()

    def test_cuda_string_uses_resolved_index(self):
        with patch(
            "airunner.utils.memory.clear_memory.torch.cuda.is_available",
            return_value=True,
        ), patch(
            "airunner.utils.memory.clear_memory.torch.cuda.set_device"
        ) as mock_set_device, patch(
            "airunner.utils.memory.clear_memory.torch.cuda.empty_cache"
        ) as mock_empty_cache, patch(
            "airunner.utils.memory.clear_memory.torch.cuda.reset_max_memory_allocated"
        ) as mock_reset_allocated, patch(
            "airunner.utils.memory.clear_memory.torch.cuda.reset_max_memory_cached"
        ) as mock_reset_cached, patch(
            "airunner.utils.memory.clear_memory.torch.cuda.synchronize"
        ) as mock_synchronize, patch(
            "airunner.utils.memory.clear_memory.gc.collect"
        ) as mock_gc_collect:
            clear_memory("cuda:2")

        mock_set_device.assert_called_once_with(2)
        mock_empty_cache.assert_called_once_with()
        mock_reset_allocated.assert_called_once_with(device=2)
        mock_reset_cached.assert_called_once_with(device=2)
        mock_synchronize.assert_called_once_with(device=2)
        mock_gc_collect.assert_called_once_with()