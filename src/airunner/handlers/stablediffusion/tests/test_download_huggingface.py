"""
Unit tests for download_huggingface.py utility functions in stablediffusion handler.
Covers HuggingFace model download logic and error handling.
"""

import pytest
from unittest.mock import patch, MagicMock
import airunner.handlers.stablediffusion.download_huggingface as download_huggingface


def test_download_model_success():
    # Simulate a successful download
    with patch(
        "airunner.handlers.stablediffusion.download_huggingface.HuggingFaceDownloader"
    ) as mock_downloader:
        instance = mock_downloader.return_value
        instance.download.return_value = "/fake/path/model.safetensors"
        result = download_huggingface.download_model("repo_id", "1.0")
        assert result == "/fake/path/model.safetensors"


def test_download_model_failure():
    # Simulate a download failure
    with patch(
        "airunner.handlers.stablediffusion.download_huggingface.HuggingFaceDownloader",
        side_effect=RuntimeError("fail"),
    ):
        with pytest.raises(RuntimeError):
            download_huggingface.download_model("bad_repo", "1.0")
