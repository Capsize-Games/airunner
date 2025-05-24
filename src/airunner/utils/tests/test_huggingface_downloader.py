"""
Tests for HuggingfaceDownloader in airunner.utils.network.huggingface_downloader.
All Qt, DownloadWorker, and mediator dependencies are mocked for headless/CI safety.
"""

import pytest
from unittest.mock import patch, MagicMock, call
from airunner.utils.network.huggingface_downloader import HuggingfaceDownloader


@pytest.fixture
def mock_worker():
    worker = MagicMock()
    worker.progress = MagicMock()
    worker.finished = MagicMock()
    worker.add_to_queue = MagicMock()
    worker.cancel = MagicMock()
    return worker


@patch("airunner.utils.network.huggingface_downloader.create_worker")
def test_init_connects_signals(mock_create_worker):
    callback = MagicMock()
    worker = MagicMock()
    worker.progress = MagicMock()
    worker.finished = MagicMock()
    mock_create_worker.return_value = worker
    downloader = HuggingfaceDownloader(callback=callback)
    assert worker.progress.connect.called
    assert worker.finished.connect.called


@patch("airunner.utils.network.huggingface_downloader.create_worker")
def test_download_model_adds_to_queue(mock_create_worker):
    worker = MagicMock()
    worker.progress = MagicMock()
    worker.finished = MagicMock()
    worker.add_to_queue = MagicMock()
    mock_create_worker.return_value = worker
    downloader = HuggingfaceDownloader(callback=lambda c, t: None)
    cb = MagicMock()
    downloader.download_model("/foo", "bar.bin", "/foo/bar.bin", cb)
    worker.add_to_queue.assert_called_once()
    args, kwargs = worker.add_to_queue.call_args
    assert args[0]["requested_path"] == "/foo"
    assert args[0]["requested_file_name"] == "bar.bin"
    assert args[0]["requested_file_path"] == "/foo/bar.bin"
    assert args[0]["requested_callback"] == cb


@patch("airunner.utils.network.huggingface_downloader.create_worker")
def test_handle_completed_emits_signal(mock_create_worker, qtbot):
    worker = MagicMock()
    worker.progress = MagicMock()
    worker.finished = MagicMock()
    mock_create_worker.return_value = worker
    downloader = HuggingfaceDownloader(callback=lambda c, t: None)
    with qtbot.waitSignal(downloader.completed, timeout=1000):
        downloader.handle_completed()


@patch("airunner.utils.network.huggingface_downloader.create_worker")
def test_stop_download_calls_cancel(mock_create_worker):
    worker = MagicMock()
    worker.progress = MagicMock()
    worker.finished = MagicMock()
    worker.cancel = MagicMock()
    mock_create_worker.return_value = worker
    downloader = HuggingfaceDownloader(callback=lambda c, t: None)
    downloader.worker = worker
    downloader.stop_download()
    worker.cancel.assert_called_once()


@patch("airunner.utils.network.huggingface_downloader.create_worker")
def test_stop_download_no_worker(mock_create_worker):
    # Provide a dummy worker for __init__, then set to None
    worker = MagicMock()
    worker.progress = MagicMock()
    worker.finished = MagicMock()
    mock_create_worker.return_value = worker
    downloader = HuggingfaceDownloader(callback=lambda c, t: None)
    downloader.worker = None
    # Should not raise
    downloader.stop_download()
