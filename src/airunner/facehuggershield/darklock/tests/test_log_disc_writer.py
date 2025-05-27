"""
Unit tests for log_disc_writer.py in the facehuggershield.darklock module.

Uses pytest and unittest.mock for isolation. All print and traceback are mocked.
"""

import pytest
from unittest.mock import patch, MagicMock

import airunner.facehuggershield.darklock.log_disc_writer as log_disc_writer


def test_log_disc_writer_call_increments_attempts_and_prints(monkeypatch):
    """Test that calling LogDiscWriter increments attempts and prints info."""
    writer = log_disc_writer.LogDiscWriter()
    with patch("builtins.print") as mock_print, patch(
        "traceback.extract_stack"
    ) as mock_stack:
        mock_stack.return_value = [
            MagicMock(filename="dummy1.py"),
            MagicMock(filename="dummy2.py"),
        ]
        writer()
        assert writer.total_write_attempts == 1
        # Should print attempt and filename (stack[-2] is dummy1.py)
        mock_print.assert_any_call("Write attempt: 1")
        mock_print.assert_any_call("Write attempt from: dummy1.py")


def test_log_disc_writer_call_with_filename_kwarg(monkeypatch):
    """Test that LogDiscWriter uses filename kwarg if provided."""
    writer = log_disc_writer.LogDiscWriter()
    with patch("builtins.print") as mock_print:
        writer(filename="explicit.py")
        assert writer.total_write_attempts == 1
        mock_print.assert_any_call("Write attempt: 1")
        mock_print.assert_any_call("Write attempt from: explicit.py")


def test_log_disc_writer_multiple_calls(monkeypatch):
    """Test that total_write_attempts increments with multiple calls."""
    writer = log_disc_writer.LogDiscWriter()
    with patch("builtins.print") as mock_print, patch(
        "traceback.extract_stack"
    ) as mock_stack:
        mock_stack.return_value = [
            MagicMock(filename="a.py"),
            MagicMock(filename="b.py"),
        ]
        writer()
        writer()
        assert writer.total_write_attempts == 2
        mock_print.assert_any_call("Write attempt: 2")
        # Both calls will use stack[-2] which is a.py
        mock_print.assert_any_call("Write attempt from: a.py")


def test_log_disc_writer_call_without_stack(monkeypatch):
    """Test fallback if extract_stack returns empty (should not crash)."""
    writer = log_disc_writer.LogDiscWriter()
    with patch("builtins.print") as mock_print, patch(
        "traceback.extract_stack", return_value=[]
    ):
        writer()
        mock_print.assert_any_call("Write attempt: 1")
        mock_print.assert_any_call("Write attempt from: None")
