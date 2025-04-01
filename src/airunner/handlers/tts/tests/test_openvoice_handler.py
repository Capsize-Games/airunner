import unittest
from unittest.mock import patch, MagicMock
from airunner.handlers.tts.openvoice_model_manager import OpenVoiceModelManager

class TestOpenVoiceModelManager(unittest.TestCase):
    def setUp(self):
        self.mock_settings = MagicMock()
        self.mock_settings.tts_model_path = "mock_path"
        self.mock_settings.speaker_recording_path = "mock_speaker_path"

        with patch("airunner.handlers.tts.openvoice_model_manager.se_extractor.get_se", return_value=(MagicMock(), "mock_audio_name")):
            self.handler = OpenVoiceModelManager(
                tts_settings=self.mock_settings,
                path_settings=MagicMock()
            )

    @patch("airunner.handlers.tts.openvoice_model_manager.TTS")
    def test_load(self, mock_tts):
        mock_tts.return_value = MagicMock()
        self.handler.load()
        self.assertIsNotNone(self.handler.model)

    def test_unload(self):
        self.handler.model = MagicMock()
        self.handler.unload()
        self.assertIsNone(self.handler.model)

    @patch("airunner.handlers.tts.openvoice_model_manager.TTS")
    @patch("airunner.handlers.tts.openvoice_model_manager.StreamingToneColorConverter.convert", return_value="mock_audio")
    def test_generate(self, mock_convert, mock_tts):
        mock_tts.return_value = MagicMock()
        self.handler.model = mock_tts.return_value
        self.handler.model.hps.data.spk2id = {"test_speaker": 1}

        with patch("torch.load", return_value=MagicMock()):
            self.handler.generate("Test message")
            mock_convert.assert_called_once()

if __name__ == "__main__":
    unittest.main()