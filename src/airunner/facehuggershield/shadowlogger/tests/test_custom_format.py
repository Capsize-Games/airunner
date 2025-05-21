import unittest

from shadowlogger.shadowlogger import ShadowLogger


class CustomFormatShadowLogger(ShadowLogger):
    message_format = "%(asctime)s - %(levelname)s - %(message)s"

    def handle_message(self, formatted_message: str, level_index: int, data: dict = None) -> None:
        self.last_formatted_message = formatted_message
        self.last_level_name = level_index


class TestCustomFormat(unittest.TestCase):
    def setUp(self):
        self.logger = CustomFormatShadowLogger()

    def test_custom_format(self):
        message = "test message"
        import logging
        level = logging.DEBUG

        # Log a message
        self.logger.debug(message)

        # Check if the formatted message matches the custom format
        self.assertTrue(self.logger.last_formatted_message.endswith(f"- DEBUG - {message}"))
        self.assertEqual(self.logger.last_level_name, level)
