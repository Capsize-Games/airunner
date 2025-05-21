import logging
import unittest
from unittest.mock import patch, MagicMock
from shadowlogger.shadowlogger_manager import ShadowLoggerManager


class TestShadowLoggerManager(unittest.TestCase):
    def setUp(self):
        self.manager = ShadowLoggerManager()

    def test_install(self):
        with patch('logging.getLogger') as mock_getLogger:
            mock_logger = MagicMock()
            mock_getLogger.return_value = mock_logger
            self.manager.activate()
            mock_logger.addHandler.assert_called_once()
            mock_logger.setLevel.assert_called_once_with(logging.INFO)

    def test_uninstall(self):
        with patch('logging.getLogger') as mock_getLogger:
            mock_logger = MagicMock()
            mock_getLogger.return_value = mock_logger
            self.manager.deactivate()
            mock_logger.removeHandler.assert_called_once()

    def test_uninstall_without_install(self):
        with patch('logging.getLogger') as mock_getLogger:
            mock_logger = MagicMock()
            mock_getLogger.return_value = mock_logger
            self.manager.original_handlers = None
            with self.assertRaises(Exception):
                self.manager.deactivate()

if __name__ == '__main__':
    unittest.main()
