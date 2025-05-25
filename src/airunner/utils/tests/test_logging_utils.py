"""
Unit tests for log_method_entry_exit decorator in logging_utils.py.
Covers logging with and without instance logger, and exception handling.
"""

import logging
import pytest
from airunner.utils.application.logging_utils import log_method_entry_exit


class Dummy:
    def __init__(self, logger=None):
        self.logger = logger

    @log_method_entry_exit
    def foo(self, x):
        return x * 2

    @log_method_entry_exit
    def fail(self):
        raise ValueError("fail!")


def test_log_method_entry_exit_with_real_logger(caplog):
    logger = logging.getLogger("dummy_logger")
    d = Dummy(logger=logger)
    with caplog.at_level(logging.DEBUG, logger="dummy_logger"):
        result = d.foo(5)
    assert result == 10
    assert "Entering Dummy.foo" in caplog.text
    assert "Exiting Dummy.foo" in caplog.text


def test_log_method_entry_exit_without_logger_uses_root(caplog):
    d = Dummy(logger=None)
    with caplog.at_level(logging.DEBUG):
        result = d.foo(7)
    assert result == 14
    assert "Entering Dummy.foo" in caplog.text
    assert "Exiting Dummy.foo" in caplog.text


def test_log_method_entry_exit_exception_logs_exit(caplog):
    d = Dummy()
    with caplog.at_level(logging.DEBUG):
        with pytest.raises(ValueError):
            d.fail()
    # Should log entry and exit even on exception
    assert "Entering Dummy.fail" in caplog.text
    assert "Exiting Dummy.fail" in caplog.text


def test_log_method_entry_exit_no_logger_and_exception(monkeypatch, caplog):
    # Remove logger attribute, force exception
    class DummyNoLogger:
        @log_method_entry_exit
        def fail(self):
            raise RuntimeError("fail!")

    d = DummyNoLogger()
    with caplog.at_level(logging.DEBUG):
        with pytest.raises(RuntimeError):
            d.fail()
    # Should log entry and exit even on exception
    # Accept any function name with 'DummyNoLogger.fail' in the log
    assert "Entering" in caplog.text and "DummyNoLogger.fail" in caplog.text
    assert "Exiting" in caplog.text and "DummyNoLogger.fail" in caplog.text
