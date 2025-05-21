import unittest
from unittest.mock import Mock, call
from logging import LogRecord
from shadowlogger.intercept_handler import InterceptHandler
from shadowlogger.shadowlogger import ShadowLogger

class TestInterceptHandler(unittest.TestCase):
    def setUp(self):
        self.shadow_logger = ShadowLogger()
        self.intercept_handler = InterceptHandler(self.shadow_logger)

    def test_emit(self):
        self.shadow_logger.handle_message = Mock()
        level = 20
        record = LogRecord(name='test', level=level, pathname='', lineno=0, msg='test message', args=(), exc_info=None)
        self.intercept_handler.emit(record)
        self.shadow_logger.handle_message.assert_called_once()

    def test_handle(self):
        self.intercept_handler.emit = Mock()
        record = LogRecord(name='test', level=20, pathname='', lineno=0, msg='test message', args=(), exc_info=None)
        self.intercept_handler.handle(record)
        self.intercept_handler.emit.assert_called_once_with(record)

    def test_handle_message_requires_level_name(self):
        with self.assertRaises(TypeError):
            self.shadow_logger.handle_message('test message')

if __name__ == '__main__':
    unittest.main()
