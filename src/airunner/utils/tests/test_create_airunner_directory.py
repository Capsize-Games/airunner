"""
Unit tests for airunner.utils.os.create_airunner_directory.create_airunner_paths
"""

import os
import pytest
from unittest.mock import MagicMock, patch

from airunner.utils.os.create_airunner_directory import create_airunner_paths


class DummyPathSettings:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


@pytest.fixture
def dummy_paths(tmp_path):
    # Provide dummy paths for all required attributes
    paths = {
        "base_path": str(tmp_path / "base"),
        "documents_path": str(tmp_path / "docs"),
        "ebook_path": str(tmp_path / "ebooks"),
        "image_path": str(tmp_path / "images"),
        "llama_index_path": str(tmp_path / "llama_index"),
        "webpages_path": str(tmp_path / "webpages"),
        "stt_model_path": str(tmp_path / "stt_models"),
        "tts_model_path": str(tmp_path / "tts_models"),
    }
    return DummyPathSettings(**paths)


def test_create_airunner_paths_creates_directories(dummy_paths):
    # All directories should not exist before
    for attr in (
        "base_path",
        "documents_path",
        "ebook_path",
        "image_path",
        "llama_index_path",
        "webpages_path",
        "stt_model_path",
        "tts_model_path",
    ):
        path = getattr(dummy_paths, attr)
        assert not os.path.exists(path)
    create_airunner_paths(dummy_paths)
    # All directories should now exist
    for attr in (
        "base_path",
        "documents_path",
        "ebook_path",
        "image_path",
        "llama_index_path",
        "webpages_path",
        "stt_model_path",
        "tts_model_path",
    ):
        path = getattr(dummy_paths, attr)
        assert os.path.isdir(path)


def test_create_airunner_paths_permission_error(dummy_paths, capfd):
    # Simulate PermissionError for one path
    with patch("os.makedirs", side_effect=PermissionError):
        create_airunner_paths(dummy_paths)
    out, err = capfd.readouterr()
    assert (
        "PermissionError" in out
        or "PermissionError" in err
        or "permission" in out.lower()
        or "permission" in err.lower()
    )


def test_create_airunner_paths_handles_other_exceptions(dummy_paths, capfd):
    # Simulate generic Exception for one path
    with patch("os.makedirs", side_effect=Exception("fail")):
        create_airunner_paths(dummy_paths)
    out, err = capfd.readouterr()
    assert (
        "fail" in out
        or "fail" in err
        or "Exception" in out
        or "Exception" in err
    )


def test_create_airunner_paths_sanitizes_path(dummy_paths):
    # Path with '..' should be sanitized
    dummy_paths.base_path = str(dummy_paths.base_path) + "/../bad"
    with patch("os.makedirs") as makedirs:
        create_airunner_paths(dummy_paths)
        # The path passed to makedirs should not contain '..'
        args, kwargs = makedirs.call_args
        assert ".." not in args[0]


def test_create_airunner_paths_file_exists_error(dummy_paths):
    # Simulate FileExistsError for one path
    with patch("os.makedirs", side_effect=FileExistsError):
        # Should not raise
        create_airunner_paths(dummy_paths)
