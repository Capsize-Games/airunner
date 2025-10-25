import unittest
from unittest.mock import patch, MagicMock

from airunner.components.model_management.model_resource_manager import (
    ModelResourceManager,
)
from airunner.components.model_management.model_registry import (
    ModelProvider,
    ModelType,
    ModelMetadata,
)
from airunner.components.model_management.quantization_strategy import (
    QuantizationLevel,
)
from airunner.components.model_management.hardware_profiler import (
    HardwareProfile,
)


class TestModelResourceManager(unittest.TestCase):
    def setUp(self):
        ModelResourceManager._instance = None

        self.mock_hardware = HardwareProfile(
            total_vram_gb=24.0,
            available_vram_gb=20.0,
            total_ram_gb=64.0,
            available_ram_gb=50.0,
            cuda_available=True,
            cuda_compute_capability=(8, 6),
            device_name="NVIDIA RTX 3080",
            cpu_count=8,
            platform="Linux",
        )

    @patch(
        "airunner.components.model_management.model_resource_manager.HardwareProfiler"
    )
    def test_singleton_pattern(self, mock_profiler_class):
        mock_profiler = MagicMock()
        mock_profiler.get_profile.return_value = self.mock_hardware
        mock_profiler_class.return_value = mock_profiler

        manager1 = ModelResourceManager()
        manager2 = ModelResourceManager()

        self.assertIs(manager1, manager2)

    @patch(
        "airunner.components.model_management.model_resource_manager.HardwareProfiler"
    )
    def test_select_best_model(self, mock_profiler_class):
        mock_profiler = MagicMock()
        mock_profiler.get_profile.return_value = self.mock_hardware
        mock_profiler_class.return_value = mock_profiler

        manager = ModelResourceManager()
        model = manager.select_best_model(
            provider=ModelProvider.MISTRAL,
            model_type=ModelType.LLM,
        )

        self.assertIsNotNone(model)
        self.assertEqual(model.provider, ModelProvider.MISTRAL)

    @patch(
        "airunner.components.model_management.model_resource_manager.HardwareProfiler"
    )
    def test_select_best_model_insufficient_resources(
        self, mock_profiler_class
    ):
        low_hardware = HardwareProfile(
            total_vram_gb=4.0,
            available_vram_gb=3.0,
            total_ram_gb=8.0,
            available_ram_gb=6.0,
            cuda_available=True,
            cuda_compute_capability=(7, 5),
            device_name="NVIDIA GTX 1050",
            cpu_count=4,
            platform="Linux",
        )

        mock_profiler = MagicMock()
        mock_profiler.get_profile.return_value = low_hardware
        mock_profiler_class.return_value = mock_profiler

        manager = ModelResourceManager()
        model = manager.select_best_model(
            provider=ModelProvider.MISTRAL,
            model_type=ModelType.LLM,
        )

        self.assertIsNone(model)

    @patch(
        "airunner.components.model_management.model_resource_manager.HardwareProfiler"
    )
    def test_prepare_model_loading(self, mock_profiler_class):
        mock_profiler = MagicMock()
        mock_profiler.get_profile.return_value = self.mock_hardware
        mock_profiler._get_available_vram_gb.return_value = 20.0
        mock_profiler_class.return_value = mock_profiler

        manager = ModelResourceManager()
        manager.memory_allocator.hardware = self.mock_hardware

        result = manager.prepare_model_loading(
            model_id="mistralai/Ministral-8B-v0.1"
        )

        self.assertTrue(result["can_load"])
        self.assertIn("metadata", result)
        self.assertIn("quantization", result)
        self.assertIn("allocation", result)
        self.assertEqual(result["metadata"].name, "Ministral 8B")

    @patch(
        "airunner.components.model_management.model_resource_manager.HardwareProfiler"
    )
    def test_prepare_model_loading_with_preference(self, mock_profiler_class):
        mock_profiler = MagicMock()
        mock_profiler.get_profile.return_value = self.mock_hardware
        mock_profiler_class.return_value = mock_profiler

        manager = ModelResourceManager()
        manager.memory_allocator.hardware = self.mock_hardware

        result = manager.prepare_model_loading(
            model_id="mistralai/Ministral-8B-v0.1",
            preferred_quantization=QuantizationLevel.INT4,
        )

        self.assertTrue(result["can_load"])
        self.assertEqual(result["quantization"].level, QuantizationLevel.INT4)

    @patch(
        "airunner.components.model_management.model_resource_manager.HardwareProfiler"
    )
    def test_cleanup_model(self, mock_profiler_class):
        mock_profiler = MagicMock()
        mock_profiler.get_profile.return_value = self.mock_hardware
        mock_profiler_class.return_value = mock_profiler

        manager = ModelResourceManager()
        manager.memory_allocator.hardware = self.mock_hardware
        manager.prepare_model_loading("mistralai/Ministral-8B-v0.1")

        manager.cleanup_model("mistralai/Ministral-8B-v0.1")
        self.assertNotIn(
            "mistralai/Ministral-8B-v0.1",
            manager.memory_allocator._allocations,
        )


if __name__ == "__main__":
    unittest.main()
