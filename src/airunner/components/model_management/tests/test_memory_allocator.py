import unittest

from airunner.components.model_management.memory_allocator import (
    MemoryAllocator,
)
from airunner.components.model_management.quantization_strategy import (
    QuantizationConfig,
    QuantizationLevel,
)
from airunner.components.model_management.hardware_profiler import (
    HardwareProfile,
)


class TestMemoryAllocator(unittest.TestCase):
    def setUp(self):
        self.hardware = HardwareProfile(
            total_vram_gb=16.0,
            available_vram_gb=14.0,
            total_ram_gb=32.0,
            available_ram_gb=28.0,
            cuda_available=True,
            cuda_compute_capability=(8, 6),
            device_name="NVIDIA RTX 3080",
            cpu_count=8,
            platform="Linux",
        )
        self.allocator = MemoryAllocator(self.hardware)
        self.quantization = QuantizationConfig(
            level=QuantizationLevel.INT4,
            description="4-bit quantization",
            estimated_memory_gb=5.0,
        )

    def test_can_allocate_sufficient_memory(self):
        result = self.allocator.can_allocate("model1", self.quantization)
        self.assertTrue(result)

    def test_can_allocate_insufficient_memory(self):
        large_quantization = QuantizationConfig(
            level=QuantizationLevel.NONE,
            description="Full precision",
            estimated_memory_gb=20.0,
        )
        result = self.allocator.can_allocate("model1", large_quantization)
        self.assertFalse(result)

    def test_allocate_success(self):
        allocation = self.allocator.allocate("model1", self.quantization)
        self.assertIsNotNone(allocation)
        self.assertEqual(allocation.model_id, "model1")
        self.assertEqual(allocation.vram_allocated_gb, 5.0)

    def test_allocate_failure(self):
        large_quantization = QuantizationConfig(
            level=QuantizationLevel.NONE,
            description="Full precision",
            estimated_memory_gb=20.0,
        )
        allocation = self.allocator.allocate("model1", large_quantization)
        self.assertIsNone(allocation)

    def test_deallocate(self):
        self.allocator.allocate("model1", self.quantization)
        self.assertIn("model1", self.allocator._allocations)

        self.allocator.deallocate("model1")
        self.assertNotIn("model1", self.allocator._allocations)

    def test_get_total_allocated_vram(self):
        self.allocator.allocate("model1", self.quantization)
        total = self.allocator.get_total_allocated_vram()
        self.assertEqual(total, 5.0)

    def test_multiple_allocations(self):
        quant1 = QuantizationConfig(
            level=QuantizationLevel.INT4,
            description="4-bit",
            estimated_memory_gb=3.0,
        )
        quant2 = QuantizationConfig(
            level=QuantizationLevel.INT4,
            description="4-bit",
            estimated_memory_gb=4.0,
        )

        self.allocator.allocate("model1", quant1)
        self.allocator.allocate("model2", quant2)

        total = self.allocator.get_total_allocated_vram()
        self.assertEqual(total, 7.0)

    def test_memory_pressure_detection(self):
        self.assertFalse(self.allocator.is_under_memory_pressure())

        large_quant = QuantizationConfig(
            level=QuantizationLevel.FLOAT16,
            description="FP16",
            estimated_memory_gb=11.0,
        )
        self.allocator.allocate("large_model", large_quant)

        self.assertTrue(self.allocator.is_under_memory_pressure())


if __name__ == "__main__":
    unittest.main()
