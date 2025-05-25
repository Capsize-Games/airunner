"""
Unit tests for download_civitai.py utility functions in stablediffusion handler.
Covers CivitAI model download logic and error handling.
"""

import pytest
from unittest.mock import patch, MagicMock
import airunner.handlers.stablediffusion.download_civitai as download_civitai


def test_download_model_success():
    # Simulate a successful download
    with patch(
        "airunner.handlers.stablediffusion.download_civitai.CivitAIDownloader"
    ) as mock_downloader:
        instance = mock_downloader.return_value
        instance.download.return_value = "/fake/path/model.safetensors"
        result = download_civitai.download_model("model_id", "1.0")
        assert result == "/fake/path/model.safetensors"


def test_download_model_failure():
    # Simulate a download failure
    with patch(
        "airunner.handlers.stablediffusion.download_civitai.CivitAIDownloader",
        side_effect=RuntimeError("fail"),
    ):
        with pytest.raises(RuntimeError):
            download_civitai.download_model("bad_id", "1.0")
