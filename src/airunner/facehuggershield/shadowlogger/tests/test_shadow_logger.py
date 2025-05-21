import unittest
from unittest.mock import patch
import logging
from shadowlogger.shadowlogger import ShadowLogger


class TestShadowLogger(unittest.TestCase):
    def setUp(self):
        self.logger = ShadowLogger()

    @patch('logging.Logger.debug')
    def test_debug(self, mock_debug):
        message = "debug message"
        self.logger.debug(message)
        mock_debug.assert_called_once_with(message)

    @patch('logging.Logger.info')
    def test_info(self, mock_info):
        message = "info message"
        self.logger.info(message)
        mock_info.assert_called_once_with(message)

    @patch('logging.Logger.warning')
    def test_warning(self, mock_warning):
        message = "warning message"
        self.logger.warning(message)
        mock_warning.assert_called_once_with(message)

    @patch('logging.Logger.error')
    def test_error(self, mock_error):
        message = "error message"
        self.logger.error(message)
        mock_error.assert_called_once_with(message)

    @patch.object(ShadowLogger, 'handle_message')
    def test_handle_calls_handle_message(self, mock_handle_message):
        unique_message = 'unique test message'
        unique_level = 99
        record = logging.LogRecord(
            name='test',
            level=unique_level,
            pathname='',
            lineno=0,
            msg=unique_message,
            args=(),
            exc_info=None
        )
        self.logger.handle(record)
        mock_handle_message.assert_called()


if __name__ == '__main__':
    unittest.main()
