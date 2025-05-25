import logging
import re
import io
import sys
import traceback
import pytest
from airunner.utils.application.get_logger import get_logger, Logger


def test_get_logger_returns_logger_instance():
    logger = get_logger("test_logger")
    assert isinstance(logger, Logger)
    assert logger.name == "test_logger"


def test_logger_debug_info_warning_critical(monkeypatch):
    logger = get_logger("test_logger")
    stream = io.StringIO()
    for handler in logger.logger.handlers:
        handler.stream = stream
    # Patch _get_caller_info to return fixed values for test stability
    monkeypatch.setattr(
        logger,
        "_get_caller_info",
        lambda: {
            "caller_module": "mod",
            "caller_function": "func",
            "caller_lineno": 123,
        },
    )
    logger.debug("debug message")
    logger.info("info message")
    logger.warning("warn message")
    logger.critical("critical message")
    output = stream.getvalue()
    assert "debug message" in output
    assert "info message" in output
    assert "warn message" in output
    assert "critical message" in output
    assert "mod" in output and "func" in output and "123" in output


def test_logger_error_prints_stack(monkeypatch):
    logger = get_logger("test_logger")
    stream = io.StringIO()
    for handler in logger.logger.handlers:
        handler.stream = stream
    monkeypatch.setattr(
        logger,
        "_get_caller_info",
        lambda: {
            "caller_module": "mod",
            "caller_function": "func",
            "caller_lineno": 123,
        },
    )
    # Patch traceback.print_stack to capture call
    stack_called = {}

    def fake_print_stack():
        stack_called["called"] = True

    monkeypatch.setattr(traceback, "print_stack", fake_print_stack)
    logger.error("error message")
    output = stream.getvalue()
    assert "error message" in output
    assert stack_called["called"]


def test_logger_handler_cleanup():
    logger1 = get_logger("cleanup_logger")
    logger2 = get_logger("cleanup_logger")
    # Should not duplicate handlers
    assert len(logger2.logger.handlers) == 1
