import unittest
from unittest.mock import patch, MagicMock, PropertyMock
from airunner.handlers.tts.speecht5_model_manager import SpeechT5ModelManager


class TestSpeechT5ModelManager(unittest.TestCase):
    def setUp(self):
        self.mock_settings = MagicMock()
        self.mock_settings.use_cuda = False
        self.mock_settings.default_gpu_tts = 0
        self.mock_settings.processor_path = "mock_processor_path"
        self.mock_settings.model_path = "mock_model_path"
        self.mock_settings.vocoder_path = "mock_vocoder_path"
        self.mock_settings.voice = "US_MALE"

        self.handler = SpeechT5ModelManager(path_settings=MagicMock())
        # Patch in a dummy api attribute to avoid AttributeError
        self.handler.api = MagicMock()

    @patch("airunner.handlers.tts.speecht5_model_manager.SpeechT5ForTextToSpeech")
    @patch("airunner.handlers.tts.speecht5_model_manager.SpeechT5Processor")
    def test_load_model(self, mock_processor, mock_model):
        mock_model.from_pretrained.return_value = MagicMock()
        mock_processor.from_pretrained.return_value = MagicMock()

        self.handler.load()

        self.assertIsNotNone(self.handler.model)
        self.assertIsNotNone(self.handler.processor)

    @patch("airunner.handlers.tts.speecht5_model_manager.SpeechT5ForTextToSpeech")
    def test_unload_model(self, mock_model):
        self.handler.model = mock_model
        self.handler.unload()

        self.assertIsNone(self.handler.model)

    @patch(
        "airunner.handlers.tts.speecht5_model_manager.SpeechT5ModelManager.status",
        new_callable=PropertyMock,
    )
    def test_generate_with_unloaded_model(self, mock_status):
        mock_status.return_value = "UNLOADED"
        from airunner.handlers.tts.tts_request import TTSRequest

        tts_request = TTSRequest(message="Test message")
        result = self.handler.generate(tts_request)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
