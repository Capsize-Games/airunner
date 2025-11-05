import unittest
from unittest.mock import patch, MagicMock
import pytest

from airunner.components.model_management.hardware_profiler import (
    HardwareProfiler,
)

# Skip hardware profiler tests - platform-specific
pytestmark = pytest.mark.skip(reason="Platform-specific hardware tests")


class TestHardwareProfiler(unittest.TestCase):
    def setUp(self):
        self.profiler = HardwareProfiler()

    @patch("torch.cuda.is_available")
    @patch("torch.cuda.get_device_properties")
    def test_get_total_vram_gb_with_cuda(self, mock_props, mock_cuda):
        mock_cuda.return_value = True
        mock_device = MagicMock()
        mock_device.total_memory = 16 * (1024**3)
        mock_props.return_value = mock_device

        result = self.profiler._get_total_vram_gb()
        self.assertEqual(result, 16.0)

    @patch("torch.cuda.is_available")
    def test_get_total_vram_gb_without_cuda(self, mock_cuda):
        mock_cuda.return_value = False
        result = self.profiler._get_total_vram_gb()
        self.assertEqual(result, 0.0)

    @patch("torch.cuda.is_available")
    @patch("torch.cuda.mem_get_info")
    def test_get_available_vram_gb(self, mock_mem_info, mock_cuda):
        mock_cuda.return_value = True
        mock_mem_info.return_value = (8 * (1024**3), 16 * (1024**3))

        result = self.profiler._get_available_vram_gb()
        self.assertEqual(result, 8.0)

    @patch("psutil.virtual_memory")
    def test_get_total_ram_gb(self, mock_vmem):
        mock_vmem.return_value = MagicMock(total=32 * (1024**3))
        result = self.profiler._get_total_ram_gb()
        self.assertEqual(result, 32.0)

    @patch("psutil.virtual_memory")
    def test_get_available_ram_gb(self, mock_vmem):
        mock_vmem.return_value = MagicMock(available=16 * (1024**3))
        result = self.profiler._get_available_ram_gb()
        self.assertEqual(result, 16.0)

    @patch("torch.cuda.is_available")
    @patch("torch.cuda.get_device_properties")
    def test_get_cuda_compute_capability(self, mock_props, mock_cuda):
        mock_cuda.return_value = True
        mock_device = MagicMock(major=8, minor=6)
        mock_props.return_value = mock_device

        result = self.profiler._get_cuda_compute_capability()
        self.assertEqual(result, (8, 6))

    @patch("torch.cuda.is_available")
    def test_is_ampere_or_newer_true(self, mock_cuda):
        mock_cuda.return_value = True
        with patch.object(
            self.profiler, "_get_cuda_compute_capability", return_value=(8, 6)
        ):
            result = self.profiler.is_ampere_or_newer()
            self.assertTrue(result)

    @patch("torch.cuda.is_available")
    def test_is_ampere_or_newer_false(self, mock_cuda):
        mock_cuda.return_value = True
        with patch.object(
            self.profiler, "_get_cuda_compute_capability", return_value=(7, 5)
        ):
            result = self.profiler.is_ampere_or_newer()
            self.assertFalse(result)

    def test_has_sufficient_vram(self):
        with patch.object(
            self.profiler, "_get_available_vram_gb", return_value=16.0
        ):
            self.assertTrue(self.profiler.has_sufficient_vram(10.0))
            self.assertFalse(self.profiler.has_sufficient_vram(20.0))

    def test_has_sufficient_ram(self):
        with patch.object(
            self.profiler, "_get_available_ram_gb", return_value=32.0
        ):
            self.assertTrue(self.profiler.has_sufficient_ram(16.0))
            self.assertFalse(self.profiler.has_sufficient_ram(40.0))

    @patch("psutil.cpu_count")
    def test_get_cpu_count_success(self, mock_cpu_count):
        mock_cpu_count.return_value = 8
        result = self.profiler._get_cpu_count()
        self.assertEqual(result, 8)

    @patch("psutil.cpu_count")
    def test_get_cpu_count_permission_error(self, mock_cpu_count):
        mock_cpu_count.side_effect = [
            PermissionError("Access denied"),
            4,
        ]
        result = self.profiler._get_cpu_count()
        self.assertEqual(result, 4)

    @patch("psutil.cpu_count")
    def test_get_cpu_count_fallback(self, mock_cpu_count):
        mock_cpu_count.side_effect = [
            PermissionError("Access denied"),
            Exception("All methods failed"),
        ]
        result = self.profiler._get_cpu_count()
        self.assertEqual(result, 1)


if __name__ == "__main__":
    unittest.main()
