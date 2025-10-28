import unittest

from airunner.components.model_management.quantization_strategy import (
    QuantizationStrategy,
    QuantizationLevel,
)
from airunner.components.model_management.hardware_profiler import (
    HardwareProfile,
)


class TestQuantizationStrategy(unittest.TestCase):
    def setUp(self):
        self.strategy = QuantizationStrategy()
        self.hardware = HardwareProfile(
            total_vram_gb=16.0,
            available_vram_gb=12.0,
            total_ram_gb=32.0,
            available_ram_gb=20.0,
            cuda_available=True,
            cuda_compute_capability=(8, 6),
            device_name="NVIDIA RTX 3080",
            cpu_count=8,
            platform="Linux",
        )

    def test_select_quantization_with_preference(self):
        config = self.strategy.select_quantization(
            model_size_gb=10.0,
            hardware=self.hardware,
            preferred_level=QuantizationLevel.INT4,
        )
        self.assertEqual(config.level, QuantizationLevel.INT4)
        self.assertFalse(config.requires_calibration)

    def test_auto_select_quantization_fp16(self):
        config = self.strategy._auto_select_quantization(
            model_size_gb=7.0, hardware=self.hardware
        )
        self.assertEqual(config.level, QuantizationLevel.FLOAT16)

    def test_auto_select_quantization_int8(self):
        hardware = HardwareProfile(
            total_vram_gb=16.0,
            available_vram_gb=9.0,
            total_ram_gb=32.0,
            available_ram_gb=20.0,
            cuda_available=True,
            cuda_compute_capability=(8, 6),
            device_name="NVIDIA RTX 3080",
            cpu_count=8,
            platform="Linux",
        )
        config = self.strategy._auto_select_quantization(
            model_size_gb=10.0, hardware=hardware
        )
        self.assertEqual(config.level, QuantizationLevel.INT8)

    def test_auto_select_quantization_int4(self):
        hardware = HardwareProfile(
            total_vram_gb=8.0,
            available_vram_gb=6.0,
            total_ram_gb=16.0,
            available_ram_gb=10.0,
            cuda_available=True,
            cuda_compute_capability=(8, 6),
            device_name="NVIDIA RTX 3060",
            cpu_count=8,
            platform="Linux",
        )
        config = self.strategy._auto_select_quantization(
            model_size_gb=10.0, hardware=hardware
        )
        self.assertEqual(config.level, QuantizationLevel.INT4)

    def test_get_config_for_level_fp16(self):
        config = self.strategy._get_config_for_level(
            QuantizationLevel.FLOAT16, 10.0
        )
        self.assertEqual(config.level, QuantizationLevel.FLOAT16)
        self.assertEqual(config.estimated_memory_gb, 20.0)
        self.assertFalse(config.requires_calibration)

    def test_get_config_for_level_int4(self):
        config = self.strategy._get_config_for_level(
            QuantizationLevel.INT4, 10.0
        )
        self.assertEqual(config.level, QuantizationLevel.INT4)
        self.assertEqual(config.estimated_memory_gb, 5.0)
        self.assertFalse(config.requires_calibration)

    def test_get_config_for_level_int2(self):
        config = self.strategy._get_config_for_level(
            QuantizationLevel.INT2, 10.0
        )
        self.assertEqual(config.level, QuantizationLevel.INT2)
        self.assertEqual(config.estimated_memory_gb, 2.5)
        self.assertTrue(config.requires_calibration)


if __name__ == "__main__":
    unittest.main()
