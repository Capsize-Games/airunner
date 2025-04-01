import unittest
from unittest.mock import MagicMock
from airunner.handlers.tts.tts_handler import TTSHandler

class MockTTSHandler(TTSHandler):
    def reload_speaker_embeddings(self):
        pass

    def interrupt_process_signal(self):
        pass

    def offload_to_cpu(self):
        pass

    def move_to_device(self, device=None):
        pass

    def generate(self, message):
        return f"Generated: {message}"

class TestTTSHandler(unittest.TestCase):
    def setUp(self):
        self.mock_settings = MagicMock()
        self.handler = MockTTSHandler(
            tts_settings=self.mock_settings,
            path_settings=MagicMock()
        )

    def test_generate(self):
        result = self.handler.generate("Test message")
        self.assertEqual(result, "Generated: Test message")

if __name__ == "__main__":
    unittest.main()