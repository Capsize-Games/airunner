"""Tests for BaseDownloadWorker abstract class."""

from unittest.mock import patch
from pathlib import Path
import tempfile

from airunner.components.application.workers.base_download_worker import (
    BaseDownloadWorker,
)
from airunner.enums import SignalCode


class ConcreteDownloadWorker(BaseDownloadWorker):
    """Concrete implementation for testing."""

    @property
    def _complete_signal(self) -> SignalCode:
        return SignalCode.HUGGINGFACE_DOWNLOAD_COMPLETE

    @property
    def _failed_signal(self) -> SignalCode:
        return SignalCode.HUGGINGFACE_DOWNLOAD_FAILED

    def _download_model(self, **kwargs):
        """Minimal implementation for testing."""

    def _download_file(self, **kwargs):
        """Minimal implementation for testing."""


class TestBaseDownloadWorker:
    """Test suite for BaseDownloadWorker."""

    def test_initialization(self):
        """Test worker initialization."""
        worker = ConcreteDownloadWorker()
        assert worker._model_path is None
        assert worker._temp_dir is None
        assert worker._total_downloaded == 0
        assert worker._total_size == 0
        assert len(worker._file_threads) == 0
        assert len(worker._file_progress) == 0
        assert len(worker._file_sizes) == 0
        assert len(worker._completed_files) == 0
        assert len(worker._failed_files) == 0
        assert worker.is_cancelled is False

    def test_handle_message_calls_download_model(self):
        """Test that handle_message calls _download_model."""
        worker = ConcreteDownloadWorker()
        message = {"model_id": "test", "output_dir": "/tmp"}

        with patch.object(worker, "_download_model") as mock_download:
            worker.handle_message(message)
            mock_download.assert_called_once_with(
                model_id="test", output_dir="/tmp"
            )

    def test_handle_message_emits_failed_on_error(self):
        """Test that handle_message emits failed signal on error."""
        worker = ConcreteDownloadWorker()

        with patch.object(
            worker, "_download_model", side_effect=Exception("Test error")
        ):
            with patch.object(worker, "emit_signal") as mock_emit:
                worker.handle_message({})
                # Should emit failed signal
                mock_emit.assert_called()
                call_args = mock_emit.call_args_list[-1]
                assert (
                    call_args[0][0] == SignalCode.HUGGINGFACE_DOWNLOAD_FAILED
                )
                assert "Test error" in call_args[0][1]["error"]

    def test_update_file_progress(self):
        """Test file progress tracking."""
        worker = ConcreteDownloadWorker()
        worker._total_size = 10000

        with patch.object(worker, "emit_signal") as mock_emit:
            worker._update_file_progress("test.bin", 100, 1000)

            # Should update progress
            assert worker._file_progress["test.bin"] == 100
            assert worker._total_downloaded == 100

            # Should emit signals
            assert (
                mock_emit.call_count >= 2
            )  # File progress + overall progress

    def test_cleanup_temp_files(self):
        """Test temporary file cleanup."""
        worker = ConcreteDownloadWorker()

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir) / ".downloading"
            temp_dir.mkdir()
            (temp_dir / "test.bin").touch()

            worker._temp_dir = temp_dir

            with patch.object(worker, "emit_signal"):
                worker._cleanup_temp_files()

            assert not temp_dir.exists()

    def test_initialize_download(self):
        """Test download initialization."""
        worker = ConcreteDownloadWorker()

        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = worker._initialize_download(tmpdir, "test-model")

            assert worker.is_cancelled is False
            assert len(worker._completed_files) == 0
            assert len(worker._failed_files) == 0
            assert worker._total_downloaded == 0
            assert worker._model_path == model_path
            assert worker._temp_dir is not None
            assert worker._temp_dir.exists()

    def test_mark_file_complete(self):
        """Test marking file as complete."""
        worker = ConcreteDownloadWorker()

        with patch.object(worker, "emit_signal") as mock_emit:
            worker._mark_file_complete("test.bin")

            assert "test.bin" in worker._completed_files
            mock_emit.assert_called()

    def test_mark_file_failed(self):
        """Test marking file as failed."""
        worker = ConcreteDownloadWorker()

        worker._mark_file_failed("test.bin")

        assert "test.bin" in worker._failed_files

    def test_cancel(self):
        """Test download cancellation."""
        worker = ConcreteDownloadWorker()

        with patch.object(worker, "emit_signal") as mock_emit:
            worker.cancel()

            assert worker.is_cancelled is True
            mock_emit.assert_called()


class TestDownloadThreading:
    """Test download threading functionality."""

    def test_wait_for_completion_success(self):
        """Test successful completion wait."""
        worker = ConcreteDownloadWorker()
        worker._completed_files = {"file1.bin", "file2.bin"}

        with patch.object(worker, "emit_signal"):
            result = worker._wait_for_completion(2)

        assert result is True

    def test_wait_for_completion_cancelled(self):
        """Test completion wait when cancelled."""
        worker = ConcreteDownloadWorker()
        worker.is_cancelled = True

        with patch.object(worker, "emit_signal"):
            with patch.object(worker, "_cleanup_temp_files"):
                result = worker._wait_for_completion(2)

        assert result is False

    def test_wait_for_completion_with_failures(self):
        """Test completion wait with failed files."""
        worker = ConcreteDownloadWorker()
        worker._completed_files = {"file1.bin"}
        worker._failed_files = {"file2.bin"}

        with patch.object(worker, "emit_signal") as mock_emit:
            result = worker._wait_for_completion(2)

        assert result is False
        # Should emit failed signal
        assert any(
            call[0][0] == SignalCode.HUGGINGFACE_DOWNLOAD_FAILED
            for call in mock_emit.call_args_list
        )
