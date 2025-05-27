import unittest
from unittest.mock import patch, MagicMock, PropertyMock
from airunner.handlers.tts.openvoice_model_manager import OpenVoiceModelManager


class TestOpenVoiceModelManager(unittest.TestCase):
    def setUp(self):
        self.mock_settings = MagicMock()
        self.mock_settings.tts_model_path = "mock_path"
        self.mock_settings.speaker_recording_path = "mock_speaker_path"

        with patch(
            "airunner.handlers.tts.openvoice_model_manager.se_extractor.get_se",
            return_value=(MagicMock(), "mock_audio_name"),
        ):
            self.handler = OpenVoiceModelManager(path_settings=MagicMock())
        # Patch in a dummy api attribute to avoid AttributeError
        self.handler.api = MagicMock()

    @patch("os.makedirs")
    @patch("os.path.isfile", return_value=True)
    @patch(
        "airunner.handlers.tts.openvoice_model_manager.se_extractor.get_se",
        return_value=(MagicMock(), "mock_audio_name"),
    )
    @patch("airunner.handlers.tts.openvoice_model_manager.TTS")
    def test_load(self, mock_tts, mock_get_se, mock_isfile, mock_makedirs):
        mock_tts.return_value = MagicMock()
        self.handler.load()
        self.assertIsNotNone(self.handler.model)

    def test_unload(self):
        self.handler.model = MagicMock()
        self.handler.unload()
        self.assertIsNone(self.handler.model)

    @patch("airunner.handlers.tts.openvoice_model_manager.TTS")
    @patch(
        "airunner.handlers.tts.openvoice_model_manager.StreamingToneColorConverter",
        autospec=True,
    )
    def test_generate(self, mock_converter, mock_tts):
        mock_tts.return_value = MagicMock()
        self.handler.model = mock_tts.return_value
        # Add both 'test_speaker' and 'EN-Newest' to spk2id to avoid KeyError
        self.handler.model.hps.data.spk2id = {
            "test_speaker": 1,
            "EN-Newest": 2,
        }

        # Set the return value for the convert method on the mock instance
        mock_converter.return_value.convert.return_value = "mock_audio"

        from airunner.handlers.tts.tts_request import OpenVoiceTTSRequest

        tts_request = OpenVoiceTTSRequest(message="Test message")
        # Patch language_settings property to return a mock with bot_language
        with patch.object(
            type(self.handler), "language_settings", new_callable=PropertyMock
        ) as mock_lang:
            mock_lang.return_value = MagicMock(bot_language="EN")
            with patch("torch.load", return_value=MagicMock()):
                self.handler.generate(tts_request)
                mock_converter.return_value.convert.assert_called_once()


if __name__ == "__main__":
    unittest.main()
