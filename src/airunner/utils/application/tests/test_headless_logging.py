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


def test_headless_logging_sanitizes_paths(tmp_path, monkeypatch):
    """Headless logging should redact filesystem paths in output."""
    log_file = tmp_path / "sanitized_headless.log"
    secret_path = "/tmp/private/models/secret.gguf"

    monkeypatch.setenv("AIRUNNER_SAVE_LOG_TO_FILE", "1")
    monkeypatch.setenv("AIRUNNER_LOG_FILE", str(log_file))
    monkeypatch.setenv("DEV_ENV", "0")

    logging_utils = importlib.import_module(
        "airunner.utils.application.logging_utils"
    )
    get_logger_mod = importlib.import_module(
        "airunner.utils.application.get_logger"
    )

    importlib.reload(logging_utils)
    importlib.reload(get_logger_mod)
    logging_utils.configure_headless_logging()

    logger = get_logger_mod.get_logger("test_headless_logger_sanitized")
    logger.info("Loading %s", secret_path)
    logger.info(f"Loading model from {secret_path}")

    logging.shutdown()
    time.sleep(0.05)

    contents = log_file.read_text(encoding="utf8")
    assert secret_path not in contents
    assert "path_hash=" in contents


def test_get_logger_sanitizes_paths(tmp_path, monkeypatch):
    """GUI-style logger handlers should redact filesystem paths too."""
    log_file = tmp_path / "sanitized_gui.log"
    secret_path = "/tmp/private/models/secret.gguf"

    monkeypatch.setenv("AIRUNNER_SAVE_LOG_TO_FILE", "1")
    monkeypatch.setenv("AIRUNNER_LOG_FILE", str(log_file))

    get_logger_mod = importlib.import_module(
        "airunner.utils.application.get_logger"
    )
    importlib.reload(get_logger_mod)

    logger = get_logger_mod.get_logger("test_gui_logger_sanitized")
    logger.info("Loading %s", secret_path)
    logger.info(f"Loading model from {secret_path}")

    logging.shutdown()
    time.sleep(0.05)

    contents = log_file.read_text(encoding="utf8")
    assert secret_path not in contents
    assert "path_hash=" in contents


def test_get_logger_reuses_existing_logger_wrapper(monkeypatch):
    """Repeated get_logger calls should reuse one configured wrapper."""
    monkeypatch.setenv("AIRUNNER_SAVE_LOG_TO_FILE", "0")

    get_logger_mod = importlib.import_module(
        "airunner.utils.application.get_logger"
    )
    importlib.reload(get_logger_mod)

    first = get_logger_mod.get_logger("cached_logger", level=logging.INFO)
    second = get_logger_mod.get_logger("cached_logger", level=logging.DEBUG)

    assert first is second
    assert first._logger.level == logging.DEBUG
    assert len(first._logger.handlers) == 1


def test_get_logger_skips_file_handler_by_default(monkeypatch):
    """File logging should remain disabled unless explicitly enabled."""
    monkeypatch.delenv("AIRUNNER_SAVE_LOG_TO_FILE", raising=False)

    get_logger_mod = importlib.import_module(
        "airunner.utils.application.get_logger"
    )
    importlib.reload(get_logger_mod)

    logger = get_logger_mod.get_logger("default_console_only")

    assert len(logger._logger.handlers) == 1
    assert not any(
        isinstance(handler, logging.FileHandler)
        for handler in logger._logger.handlers
    )


def test_headless_logging_does_not_fallback_to_tmp(monkeypatch, tmp_path):
    log_file = tmp_path / "blocked.log"
    attempted_paths = []

    monkeypatch.setenv("AIRUNNER_SAVE_LOG_TO_FILE", "1")
    monkeypatch.setenv("AIRUNNER_LOG_FILE", str(log_file))
    monkeypatch.setenv("DEV_ENV", "0")

    logging_utils = importlib.import_module(
        "airunner.utils.application.logging_utils"
    )
    importlib.reload(logging_utils)

    def fake_file_handler(path, mode="a"):
        attempted_paths.append(str(path))
        raise PermissionError("denied")

    monkeypatch.setattr(
        logging_utils.logging,
        "FileHandler",
        fake_file_handler,
    )

    logging_utils.configure_headless_logging()

    assert attempted_paths == [str(log_file)]
    assert "/tmp/airunner.log" not in attempted_paths


def test_configure_noisy_loggers_suppresses_sqlalchemy_children():
    logging_utils = importlib.import_module(
        "airunner.utils.application.logging_utils"
    )
    importlib.reload(logging_utils)

    logging_utils.configure_noisy_loggers()

    assert (
        logging.getLogger("sqlalchemy.orm.mapper.Mapper").level
        == logging.WARNING
    )
    assert (
        logging.getLogger(
            "sqlalchemy.orm.relationships.RelationshipProperty"
        ).level
        == logging.WARNING
    )
    assert (
        logging.getLogger("sqlalchemy.orm.strategies.LazyLoader").level
        == logging.WARNING
    )
