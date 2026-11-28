"""Regression coverage for stale download cleanup and disappearing entries."""

import os
from pathlib import Path
from unittest.mock import Mock

import pytest

from airunner_services import download_temp_cleanup as cleanup


@pytest.fixture
def temp_dir(tmp_path, monkeypatch):
    path = tmp_path / ".downloading"
    path.mkdir()
    monkeypatch.setattr(cleanup.time, "time", lambda: 2000)
    return path


def _stamp(path, mtime):
    os.utime(path, (mtime, mtime))


def test_keeps_recent_directory(temp_dir):
    _stamp(temp_dir, 1950)
    assert cleanup.cleanup_stale_download_dir(temp_dir, 100) is False
    assert temp_dir.is_dir()


def test_removes_stale_directory(temp_dir):
    _stamp(temp_dir, 1800)
    assert cleanup.cleanup_stale_download_dir(temp_dir, 100) is True
    assert not temp_dir.exists()


def test_keeps_stale_directory_with_recent_nested_file(temp_dir):
    nested = temp_dir / "nested"
    nested.mkdir()
    recent = nested / "part"
    recent.touch()
    for directory in (temp_dir, nested):
        _stamp(directory, 1800)
    _stamp(recent, 1950)

    assert cleanup.cleanup_stale_download_dir(temp_dir, 100) is False
    assert recent.is_file()


def test_ignores_file_removed_after_walk_listed_it(temp_dir, monkeypatch):
    part = temp_dir / "part"
    part.touch()
    _stamp(temp_dir, 1800)

    def walk(path):
        part.unlink()
        _stamp(temp_dir, 1800)
        yield str(path), [], [part.name]

    monkeypatch.setattr(cleanup.os, "walk", walk)
    assert cleanup.cleanup_stale_download_dir(temp_dir, 100) is True
    assert not temp_dir.exists()


def test_returns_false_when_root_vanishes_before_scan(temp_dir, monkeypatch):
    original_stat = Path.stat
    root_stats = 0

    def stat(path, *args, **kwargs):
        nonlocal root_stats
        if path == temp_dir:
            root_stats += 1
            if root_stats == 3:
                temp_dir.rmdir()
        return original_stat(path, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", stat)
    assert cleanup.cleanup_stale_download_dir(temp_dir, 100) is False
    assert not temp_dir.exists()


def test_permission_error_removing_directory_is_not_success(temp_dir, monkeypatch):
    _stamp(temp_dir, 1800)
    logger = Mock()
    monkeypatch.setattr(cleanup.shutil, "rmtree", Mock(side_effect=PermissionError))

    assert cleanup.cleanup_stale_download_dir(temp_dir, 100, logger) is False
    logger.warning.assert_called_once()
    assert temp_dir.is_dir()
