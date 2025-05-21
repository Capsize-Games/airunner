import logging
import unittest

from shadowlogger.shadowlogger import ShadowLogger


class CustomLevelShadowLogger(ShadowLogger):
    log_level = logging.WARNING

    def handle_message(self, formatted_message: str, level_name: str, data: dict = None) -> None:
        self.last_formatted_message = formatted_message
        self.last_level_name = level_name


class TestCustomLevel(unittest.TestCase):
    def setUp(self):
        self.logger = CustomLevelShadowLogger()

    def test_custom_level(self):
        message = "test message"
        level = logging.WARNING

        # Log a message
        self.logger.warning(message)

        # Check if the level name matches the custom level
        self.assertEqual(self.logger.last_level_name, level)
