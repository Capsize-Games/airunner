import unittest

from airunner.components.model_management.model_registry import (
    ModelRegistry,
    ModelMetadata,
    ModelProvider,
    ModelType,
)


class TestModelRegistry(unittest.TestCase):
    def setUp(self):
        self.registry = ModelRegistry()

    def test_registry_initialized_with_models(self):
        models = self.registry.list_models()
        self.assertGreater(len(models), 0)

    def test_get_model_by_id(self):
        model = self.registry.get_model("qwen3-8b")
        self.assertIsNotNone(model)
        self.assertEqual(model.name, "Qwen3-8B")
        self.assertEqual(model.provider, ModelProvider.QWEN)
        self.assertEqual(model.preferred_runtime_format, "gguf")
        self.assertEqual(model.runtime_backend, "llama.cpp")

    def test_get_model_by_download_alias(self):
        model = self.registry.get_model("Qwen/Qwen3-8B-GGUF")

        self.assertIsNotNone(model)
        self.assertEqual(model.model_id, "qwen3-8b")

    def test_get_nonexistent_model(self):
        model = self.registry.get_model("nonexistent/model")
        self.assertIsNone(model)

    def test_list_models_by_provider(self):
        models = self.registry.list_models(provider=ModelProvider.QWEN)
        self.assertGreater(len(models), 0)
        for model in models:
            self.assertEqual(model.provider, ModelProvider.QWEN)

    def test_list_models_by_type(self):
        models = self.registry.list_models(model_type=ModelType.LLM)
        self.assertGreater(len(models), 0)
        for model in models:
            self.assertEqual(model.model_type, ModelType.LLM)

    def test_list_models_with_filters(self):
        models = self.registry.list_models(
            provider=ModelProvider.MISTRAL, model_type=ModelType.LLM
        )
        self.assertGreater(len(models), 0)
        for model in models:
            self.assertEqual(model.provider, ModelProvider.MISTRAL)
            self.assertEqual(model.model_type, ModelType.LLM)

    def test_register_new_model(self):
        new_model = ModelMetadata(
            name="Test Model",
            provider=ModelProvider.LLAMA,
            model_type=ModelType.LLM,
            size_gb=10.0,
            min_vram_gb=8.0,
            min_ram_gb=16.0,
            recommended_vram_gb=12.0,
            recommended_ram_gb=32.0,
            supports_quantization=True,
            huggingface_id="test/model",
            model_id="test-model",
        )

        self.registry.register_model(new_model)
        retrieved = self.registry.get_model("test-model")

        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, "Test Model")
        self.assertEqual(retrieved.provider, ModelProvider.LLAMA)
        self.assertEqual(self.registry.get_model("test/model").model_id, "test-model")


if __name__ == "__main__":
    unittest.main()
