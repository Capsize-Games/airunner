import os

os.environ["AIRUNNER_DB_NAME"] = "test.db"

import unittest
from unittest.mock import patch, MagicMock, PropertyMock
from PIL import Image

from PySide6.QtWidgets import QApplication

from airunner.handlers.stablediffusion.stable_diffusion_model_manager import (
    StableDiffusionModelManager,
)
from airunner.handlers.stablediffusion.image_request import ImageRequest
from airunner.enums import (
    ModelStatus,
    ModelType,
    HandlerState,
    SignalCode,
    EngineResponseCode,
    GeneratorSection,
)

import airunner.setup_database as setup_database

# Set test environment variables


class TestStableDiffusionModelManager(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Initialize the QApplication for PySide6
        cls.app = QApplication.instance()
        if not cls.app:
            cls.app = QApplication([])

        # Setup the test database
        setup_database.setup_database()

    def setUp(self):
        # Mock dependencies
        self.mock_mediator = MagicMock()
        self.mock_path_settings = MagicMock()
        self.mock_path_settings.base_path = "/test/path"

        # Mock logger before creating the handler
        self.mock_logger = MagicMock()
        self.mock_model_status = {
            ModelType.SD: ModelStatus.UNLOADED,
            ModelType.SAFETY_CHECKER: ModelStatus.UNLOADED,
            ModelType.FEATURE_EXTRACTOR: ModelStatus.UNLOADED,
            ModelType.CONTROLNET: ModelStatus.UNLOADED,
            ModelType.SCHEDULER: ModelStatus.UNLOADED,
        }

        # Create a StableDiffusionModelManager instance with mocked dependencies
        with patch(
            "airunner.handlers.stablediffusion.stable_diffusion_model_manager.torch.Generator"
        ) as mock_generator, patch(
            "airunner.handlers.stablediffusion.stable_diffusion_model_manager.StableDiffusionSafetyChecker"
        ) as mock_safety_checker, patch(
            "airunner.handlers.stablediffusion.stable_diffusion_model_manager.CLIPFeatureExtractor"
        ) as mock_feature_extractor, patch(
            "airunner.handlers.stablediffusion.stable_diffusion_model_manager.ControlNetModel"
        ) as mock_controlnet_model, patch(
            "airunner.handlers.base_model_manager.BaseModelManager.__init__"
        ) as mock_base_init, patch.object(
            StableDiffusionModelManager,
            "path_settings_cached",
            self.mock_path_settings,
            create=True,
        ), patch.object(
            StableDiffusionModelManager,
            "logger",
            self.mock_logger,
            create=True,
        ):

            mock_base_init.return_value = None
            mock_generator.return_value = MagicMock()

            self.handler = StableDiffusionModelManager()

            # Setup necessary properties on the handler
            self.handler._model_status = self.mock_model_status
            self.handler.change_model_status = MagicMock()

    def tearDown(self):
        # Clean up after test
        self.handler = None

    def test_initialization(self):
        """Test the initialization of StableDiffusionModelManager"""
        self.assertEqual(self.handler._model_path, "/test/model/path")
        self.assertEqual(self.handler._model_version, "SD 1.5")
        self.assertEqual(self.handler._pipeline, "txt2img")
        self.assertEqual(
            self.handler._scheduler_name, "DPMSolverMultistepScheduler"
        )
        self.assertEqual(self.handler._use_compel, True)
        self.assertEqual(
            self.handler._current_state, HandlerState.UNINITIALIZED
        )
        self.assertEqual(self.handler.model_type, ModelType.SD)

    def test_properties(self):
        """Test the properties of StableDiffusionModelManager"""
        self.assertEqual(self.handler.model_path, "/test/model/path")

        # Test model_status property
        self.assertEqual(self.handler.model_status, self.mock_model_status)

        # Test scheduler_name property
        self.assertEqual(
            self.handler.scheduler_name, "DPMSolverMultistepScheduler"
        )

        # Test use_compel property
        self.assertEqual(self.handler.use_compel, True)

        # Test version property
        self.assertEqual(self.handler.version, "SD 1.5")

        # Test is_txt2img property
        with patch.object(
            StableDiffusionModelManager, "section", new_callable=PropertyMock
        ) as mock_section:
            mock_section.return_value = GeneratorSection.TXT2IMG
            self.assertTrue(self.handler.is_txt2img)

    def test_image_request_property(self):
        """Test the image_request property setter and getter"""
        mock_request = MagicMock(spec=ImageRequest)
        self.handler.image_request = mock_request
        self.assertEqual(self.handler.image_request, mock_request)

    def test_load_safety_checker(self):
        """Test the load_safety_checker method"""
        with patch.object(
            self.handler, "_load_safety_checker"
        ) as mock_load, patch.object(
            StableDiffusionModelManager,
            "safety_checker_is_loading",
            new_callable=PropertyMock,
        ) as mock_loading:
            # Test that it doesn't call _load_safety_checker when safety_checker_is_loading is True
            mock_loading.return_value = True
            self.handler.load_safety_checker()
            mock_load.assert_not_called()
            mock_load.reset_mock()

            # Test that it calls _load_safety_checker when safety_checker_is_loading is False
            mock_loading.return_value = False
            self.handler.load_safety_checker()
            mock_load.assert_called_once()

    def test_unload_safety_checker(self):
        """Test the unload_safety_checker method"""
        with patch.object(
            self.handler, "_unload_safety_checker"
        ) as mock_unload, patch.object(
            StableDiffusionModelManager,
            "safety_checker_is_loading",
            new_callable=PropertyMock,
        ) as mock_loading:
            # Test that it doesn't call _unload_safety_checker when safety_checker_is_loading is True
            mock_loading.return_value = True
            self.handler.unload_safety_checker()
            mock_unload.assert_not_called()
            mock_unload.reset_mock()

            # Test that it calls _unload_safety_checker when safety_checker_is_loading is False
            mock_loading.return_value = False
            self.handler.unload_safety_checker()
            mock_unload.assert_called_once()

    def test_load_controlnet(self):
        """Test the load_controlnet method"""
        with patch.object(
            self.handler, "_load_controlnet"
        ) as mock_load, patch.object(
            StableDiffusionModelManager,
            "controlnet_enabled",
            new_callable=PropertyMock,
        ) as mock_enabled, patch.object(
            StableDiffusionModelManager,
            "controlnet_is_loading",
            new_callable=PropertyMock,
        ) as mock_loading:
            # Don't load when controlnet is not enabled
            mock_enabled.return_value = False
            mock_loading.return_value = False
            self.handler.load_controlnet()
            mock_load.assert_not_called()
            mock_load.reset_mock()

            # Don't load when controlnet is already loading
            mock_enabled.return_value = True
            mock_loading.return_value = True
            self.handler.load_controlnet()
            mock_load.assert_not_called()
            mock_load.reset_mock()

            # Load when controlnet is enabled and not already loading
            mock_enabled.return_value = True
            mock_loading.return_value = False
            self.handler.load_controlnet()
            self.assertIsNone(self.handler._controlnet_model)
            self.assertIsNone(self.handler._controlnet_settings)
            mock_load.assert_called_once()

    def test_unload_controlnet(self):
        """Test the unload_controlnet method"""
        with patch.object(
            self.handler, "_unload_controlnet"
        ) as mock_unload, patch.object(
            StableDiffusionModelManager,
            "controlnet_is_loading",
            new_callable=PropertyMock,
        ) as mock_loading:
            # Test that it doesn't call _unload_controlnet when controlnet_is_loading is True
            mock_loading.return_value = True
            self.handler.unload_controlnet()
            mock_unload.assert_not_called()
            mock_unload.reset_mock()

            # Test that it calls _unload_controlnet when controlnet_is_loading is False
            mock_loading.return_value = False
            self.handler.unload_controlnet()
            mock_unload.assert_called_once()

    def test_load_scheduler(self):
        """Test the load_scheduler method"""
        with patch.object(self.handler, "_load_scheduler") as mock_load:
            scheduler_name = "MockScheduler"
            self.handler.load_scheduler(scheduler_name)
            mock_load.assert_called_once_with(scheduler_name)

    def test_reload(self):
        """Test the reload method"""
        with patch.object(self.handler, "unload") as mock_unload, patch.object(
            self.handler, "load"
        ) as mock_load, patch.object(
            self.handler, "_clear_cached_properties"
        ) as mock_clear:
            self.handler.reload()
            mock_clear.assert_called_once()
            mock_unload.assert_called_once()
            mock_load.assert_called_once()

    def test_load(self):
        """Test the load method"""
        # Case 1: Already loading or loaded
        with patch.object(
            StableDiffusionModelManager,
            "sd_is_loading",
            new_callable=PropertyMock,
        ) as mock_is_loading, patch.object(
            self.handler, "_load_safety_checker"
        ) as mock_load_safety:
            mock_is_loading.return_value = True
            self.handler.load()
            mock_load_safety.assert_not_called()

        # Case 2: Normal load case
        with patch.object(
            StableDiffusionModelManager,
            "sd_is_loading",
            new_callable=PropertyMock,
        ) as mock_is_loading, patch.object(
            StableDiffusionModelManager,
            "sd_is_loaded",
            new_callable=PropertyMock,
        ) as mock_is_loaded, patch.object(
            self.handler, "_load_safety_checker"
        ) as mock_load_safety, patch.object(
            self.handler, "_load_controlnet"
        ) as mock_load_controlnet, patch.object(
            self.handler, "_load_pipe"
        ) as mock_load_pipe, patch.object(
            self.handler, "_load_scheduler"
        ) as mock_load_scheduler, patch.object(
            self.handler, "_load_lora"
        ) as mock_load_lora, patch.object(
            self.handler, "_load_embeddings"
        ) as mock_load_embeddings, patch.object(
            self.handler, "_load_compel"
        ) as mock_load_compel, patch.object(
            self.handler, "_load_deep_cache"
        ) as mock_load_deep_cache, patch.object(
            self.handler, "_make_memory_efficient"
        ) as mock_memory_efficient, patch.object(
            self.handler, "_finalize_load_stable_diffusion"
        ) as mock_finalize:

            mock_is_loading.return_value = False
            mock_is_loaded.return_value = False

            self.handler.load()

            self.handler.change_model_status.assert_any_call(
                ModelType.SD, ModelStatus.LOADING
            )
            mock_load_safety.assert_called_once()
            mock_load_controlnet.assert_called_once()
            mock_load_pipe.assert_called_once()
            mock_load_scheduler.assert_called_once()
            mock_load_lora.assert_called_once()
            mock_load_embeddings.assert_called_once()
            mock_load_compel.assert_called_once()
            mock_load_deep_cache.assert_called_once()
            mock_memory_efficient.assert_called_once()
            mock_finalize.assert_called_once()

    def test_unload(self):
        """Test the unload method"""
        # Case 1: Already unloading or unloaded
        with patch.object(
            StableDiffusionModelManager,
            "sd_is_loading",
            new_callable=PropertyMock,
        ) as mock_is_loading, patch.object(
            self.handler, "_unload_safety_checker"
        ) as mock_unload_safety:
            mock_is_loading.return_value = True
            self.handler.unload()
            mock_unload_safety.assert_not_called()

        # Case 2: Normal unload case
        with patch.object(
            StableDiffusionModelManager,
            "sd_is_loading",
            new_callable=PropertyMock,
        ) as mock_is_loading, patch.object(
            StableDiffusionModelManager,
            "sd_is_unloaded",
            new_callable=PropertyMock,
        ) as mock_is_unloaded, patch.object(
            self.handler, "_unload_safety_checker"
        ) as mock_unload_safety, patch.object(
            self.handler, "_unload_scheduler"
        ) as mock_unload_scheduler, patch.object(
            self.handler, "_unload_controlnet"
        ) as mock_unload_controlnet, patch.object(
            self.handler, "_unload_loras"
        ) as mock_unload_loras, patch.object(
            self.handler, "_unload_emebeddings"
        ) as mock_unload_embeddings, patch.object(
            self.handler, "_unload_compel"
        ) as mock_unload_compel, patch.object(
            self.handler, "_unload_generator"
        ) as mock_unload_generator, patch.object(
            self.handler, "_unload_deep_cache"
        ) as mock_unload_deep_cache, patch.object(
            self.handler, "_unload_pipe"
        ) as mock_unload_pipe, patch.object(
            self.handler, "_clear_memory_efficient_settings"
        ) as mock_clear_settings, patch(
            "airunner.handlers.stablediffusion.stable_diffusion_model_manager.clear_memory"
        ) as mock_clear_memory:

            mock_is_loading.return_value = False
            mock_is_unloaded.return_value = False
            self.handler._current_state = HandlerState.READY

            self.handler.unload()

            self.handler.change_model_status.assert_any_call(
                ModelType.SD, ModelStatus.LOADING
            )
            self.handler.change_model_status.assert_any_call(
                ModelType.SD, ModelStatus.UNLOADED
            )
            mock_unload_safety.assert_called_once()
            mock_unload_scheduler.assert_called_once()
            mock_unload_controlnet.assert_called_once()
            mock_unload_loras.assert_called_once()
            mock_unload_embeddings.assert_called_once()
            mock_unload_compel.assert_called_once()
            mock_unload_generator.assert_called_once()
            mock_unload_deep_cache.assert_called_once()
            mock_unload_pipe.assert_called_once()
            mock_clear_settings.assert_called_once()
            mock_clear_memory.assert_called_once()

    def test_handle_generate_signal(self):
        """Test the handle_generate_signal method"""
        # Create mock image request
        mock_image_request = MagicMock()
        mock_image_request.scheduler = "TestScheduler"
        mock_image_request.callback = None

        # Create mock message
        mock_message = {"image_request": mock_image_request}

        with patch.object(
            self.handler, "_load_scheduler"
        ) as mock_load_scheduler, patch.object(
            self.handler, "load"
        ) as mock_load, patch.object(
            self.handler, "_clear_cached_properties"
        ) as mock_clear_cached, patch.object(
            self.handler, "_swap_pipeline"
        ) as mock_swap_pipeline, patch.object(
            self.handler, "_generate"
        ) as mock_generate, patch.object(
            self.handler, "emit_signal"
        ) as mock_emit, patch.object(
            self.handler, "handle_requested_action"
        ) as mock_handle_action, patch(
            "airunner.handlers.stablediffusion.stable_diffusion_model_manager.clear_memory"
        ) as mock_clear_memory:

            # Setup the current state and mock behavior
            self.handler._current_state = HandlerState.READY
            mock_generate.return_value = "Generated image"

            # Call the method
            self.handler.handle_generate_signal(mock_message)

            # Verify the calls
            self.assertEqual(self.handler.image_request, mock_image_request)
            mock_load_scheduler.assert_called_with("TestScheduler")
            mock_load.assert_called_once()
            mock_clear_cached.assert_called_once()
            mock_swap_pipeline.assert_called_once()
            mock_generate.assert_called_once()
            mock_emit.assert_called_with(
                SignalCode.ENGINE_RESPONSE_WORKER_RESPONSE_SIGNAL,
                {
                    "code": EngineResponseCode.IMAGE_GENERATED,
                    "message": "Generated image",
                },
            )
            self.assertEqual(self.handler._current_state, HandlerState.READY)
            mock_clear_memory.assert_called_once()
            mock_handle_action.assert_called_once()

    def test_reload_lora(self):
        """Test the reload_lora method"""
        # Setup the handler to simulate different model status conditions
        with patch.object(
            self.handler, "_unload_loras"
        ) as mock_unload, patch.object(
            self.handler, "_load_lora"
        ) as mock_load, patch.object(
            self.handler, "emit_signal"
        ) as mock_emit:

            # Case 1: SD is not loaded or generating, should not reload lora
            self.mock_model_status[ModelType.SD] = ModelStatus.FAILED
            self.handler._current_state = HandlerState.READY
            self.handler.reload_lora()
            mock_unload.assert_not_called()
            mock_load.assert_not_called()
            mock_emit.assert_not_called()

            # Case 2: SD is loaded and not generating, should reload lora
            self.mock_model_status[ModelType.SD] = ModelStatus.LOADED
            self.handler._current_state = HandlerState.READY

            self.handler.reload_lora()

            self.handler.change_model_status.assert_any_call(
                ModelType.SD, ModelStatus.LOADING
            )
            self.handler.change_model_status.assert_any_call(
                ModelType.SD, ModelStatus.LOADED
            )
            mock_unload.assert_called_once()
            mock_load.assert_called_once()
            mock_emit.assert_called_with(SignalCode.LORA_UPDATED_SIGNAL)

    def test_reload_embeddings(self):
        """Test the reload_embeddings method"""
        # Setup the handler to simulate different model status conditions
        with patch.object(
            self.handler, "_load_embeddings"
        ) as mock_load, patch.object(self.handler, "emit_signal") as mock_emit:

            # Case 1: SD is not loaded or generating, should not reload embeddings
            self.mock_model_status[ModelType.SD] = ModelStatus.FAILED
            self.handler._current_state = HandlerState.READY
            self.handler.reload_embeddings()
            mock_load.assert_not_called()
            mock_emit.assert_not_called()

            # Case 2: SD is loaded and not generating, should reload embeddings
            self.mock_model_status[ModelType.SD] = ModelStatus.LOADED
            self.handler._current_state = HandlerState.READY

            self.handler.reload_embeddings()

            self.handler.change_model_status.assert_any_call(
                ModelType.SD, ModelStatus.LOADING
            )
            self.handler.change_model_status.assert_any_call(
                ModelType.SD, ModelStatus.LOADED
            )
            mock_load.assert_called_once()
            mock_emit.assert_called_with(SignalCode.EMBEDDING_UPDATED_SIGNAL)

    def test_load_embeddings(self):
        """Test the load_embeddings method"""
        with patch.object(self.handler, "_load_embeddings") as mock_load:
            self.handler.load_embeddings()
            mock_load.assert_called_once()

    def test_interrupt_image_generation(self):
        """Test the interrupt_image_generation method"""
        # Test when current state is not generating
        self.handler._current_state = HandlerState.READY
        self.handler.do_interrupt_image_generation = False
        self.handler.interrupt_image_generation()
        self.assertFalse(self.handler.do_interrupt_image_generation)

        # Test when current state is generating
        self.handler._current_state = HandlerState.GENERATING
        self.handler.do_interrupt_image_generation = False
        self.handler.interrupt_image_generation()
        self.assertTrue(self.handler.do_interrupt_image_generation)

    def test_resize_image_static_method(self):
        """Test the _resize_image static method"""
        # Create a test image
        test_image = Image.new("RGB", (200, 100), color="red")

        # Test case: Image already fits within max dimensions
        result = StableDiffusionModelManager._resize_image(
            test_image, 300, 200
        )
        self.assertEqual(result.size, (200, 100))

        # Test case: Image needs to be resized (landscape orientation)
        result = StableDiffusionModelManager._resize_image(
            test_image, 100, 200
        )
        self.assertEqual(
            result.size[0], 100
        )  # Width should be exactly max_width
        self.assertLess(
            result.size[1], 100
        )  # Height should be proportionally smaller

        # Test case: Image is None
        result = StableDiffusionModelManager._resize_image(None, 100, 100)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
