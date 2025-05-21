import unittest

from shadowlogger.shadowlogger import ShadowLogger


class CustomPrefixShadowLogger(ShadowLogger):
    prefix = "CustomPrefix"

    def handle_message(self, formatted_message: str, level_name: str, data: dict = None):
        self.last_formatted_message = formatted_message
        self.last_level_name = level_name


class TestCustomPrefix(unittest.TestCase):
    def setUp(self):
        self.logger = CustomPrefixShadowLogger()

    def test_custom_prefix(self):
        message = "test message"
        level = "DEBUG"

        # Log a message
        self.logger.debug(message)

        # Check if the formatted message contains the custom prefix
        self.assertIn(self.logger.prefix, self.logger.last_formatted_message)
