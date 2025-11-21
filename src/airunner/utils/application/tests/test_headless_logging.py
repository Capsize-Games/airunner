"""
Tests for headless logging configuration.

This test verifies that when headless logging is enabled, log messages
emitted through the project's get_logger wrapper propagate to the root
logger and are captured by the configured file handler.
"""

import importlib
import logging
import os
import time

import pytest


def test_headless_logging_writes_to_file(tmp_path, monkeypatch):
    # Use a temporary file to verify logging output
    log_file = tmp_path / "headless_test.log"
    monkeypatch.setenv("AIRUNNER_SAVE_LOG_TO_FILE", "1")
    monkeypatch.setenv("AIRUNNER_LOG_FILE", str(log_file))
    monkeypatch.setenv("DEV_ENV", "0")

    # Reload modules so they pick up the environment variables
    logging_utils = importlib.import_module(
        "airunner.utils.application.logging_utils"
    )
    get_logger_mod = importlib.import_module(
        "airunner.utils.application.get_logger"
    )

    importlib.reload(logging_utils)
    importlib.reload(get_logger_mod)

    # Call configure_headless_logging to set root handlers
    logging_utils.configure_headless_logging()

    # Obtain a logger via the wrapper and log some messages
    get_logger = get_logger_mod.get_logger
    logger = get_logger("test_headless_logger", level=logging.DEBUG)
    logger.info("hello headless file logger")
    logger.debug("debug info should also be present")
    logger.error("an error occurred")

    # Allow tiny pause for the file handler to flush
    logging.shutdown()
    time.sleep(0.05)

    # Read the log file and assert that the entries exist
    assert log_file.exists(), f"Log file was not created: {log_file}"
    contents = log_file.read_text(encoding="utf8")
    assert "hello headless file logger" in contents
    assert "debug info should also be present" in contents
    assert "an error occurred" in contents


def test_headless_logging_reconfigures_preexisting_loggers(
    tmp_path, monkeypatch
):
    """Simulate a logger created before headless configuration.

    The logger is initially created in GUI mode (with its own handlers).
    After switching to headless mode and calling configure_headless_logging,
    the existing logger should propagate to root and write to the headless file.
    """
    # File paths
    pre_file = tmp_path / "pre.log"
    headless_file = tmp_path / "headless_final.log"

    # Step 1 - Create pre-existing GUI logger
    monkeypatch.setenv("AIRUNNER_SAVE_LOG_TO_FILE", "1")
    monkeypatch.setenv("AIRUNNER_LOG_FILE", str(pre_file))
    monkeypatch.setenv("DEV_ENV", "0")

    import importlib as _importlib

    get_logger_mod = _importlib.import_module(
        "airunner.utils.application.get_logger"
    )
    _importlib.reload(get_logger_mod)

    pre_logger = get_logger_mod.get_logger(
        "pre_existing_logger", level=logging.DEBUG
    )
    pre_logger.info("message_before_headless")

    # Step 2 - Switch to headless mode and configure headless logging
    monkeypatch.setenv("AIRUNNER_LOG_FILE", str(headless_file))

    logging_utils = _importlib.import_module(
        "airunner.utils.application.logging_utils"
    )
    _importlib.reload(logging_utils)
    _importlib.reload(get_logger_mod)
    logging_utils.configure_headless_logging()

    # Step 3 - The pre-existing logger should now propagate to root
    pre_logger.info("message_after_headless")
    logging.shutdown()

    assert headless_file.exists(), "Headless log file was not created"
    contents = headless_file.read_text(encoding="utf8")
    assert "message_after_headless" in contents
