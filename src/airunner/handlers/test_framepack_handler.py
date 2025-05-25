import unittest
from airunner.handlers import framepack_handler
from unittest.mock import patch, MagicMock
import numpy as np
from PIL import Image


class TestFramepackHandler(unittest.TestCase):
    @patch(
        "airunner.handlers.framepack_handler.FramePackHandler.load",
        return_value=True,
    )
    def test_generate_video_status_not_ready(self, mock_load):
        handler = framepack_handler.FramePackHandler()
        handler.api = MagicMock()
        handler._model_status[framepack_handler.ModelType.VIDEO] = (
            framepack_handler.ModelStatus.UNLOADED
        )
        with self.assertRaises(RuntimeError):
            handler.generate_video(
                np.zeros((64, 64, 3), dtype=np.uint8), "prompt"
            )

    @patch(
        "airunner.handlers.framepack_handler.FramePackHandler.load",
        return_value=True,
    )
    def test_generate_video_already_generating(self, mock_load):
        handler = framepack_handler.FramePackHandler()
        handler.api = MagicMock()
        handler._model_status[framepack_handler.ModelType.VIDEO] = (
            framepack_handler.ModelStatus.READY
        )
        handler.is_generating = True
        with self.assertRaises(RuntimeError):
            handler.generate_video(
                np.zeros((64, 64, 3), dtype=np.uint8), "prompt"
            )

    def test_unload_sets_models_to_none(self):
        handler = framepack_handler.FramePackHandler()
        handler.api = MagicMock()
        handler.text_encoder = MagicMock()
        handler.text_encoder_2 = MagicMock()
        handler.tokenizer = MagicMock()
        handler.tokenizer_2 = MagicMock()
        handler.image_encoder = MagicMock()
        handler.feature_extractor = MagicMock()
        handler.vae = MagicMock()
        handler.transformer = MagicMock()
        handler.is_generating = False
        handler.generation_thread = None
        handler.unload()
        self.assertIsNone(handler.text_encoder)
        self.assertIsNone(handler.text_encoder_2)
        self.assertIsNone(handler.tokenizer)
        self.assertIsNone(handler.tokenizer_2)
        self.assertIsNone(handler.image_encoder)
        self.assertIsNone(handler.feature_extractor)
        self.assertIsNone(handler.vae)
        self.assertIsNone(handler.transformer)


if __name__ == "__main__":
    unittest.main()
