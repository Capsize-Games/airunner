"""Tests for BaseDownloadWorker abstract class."""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from pathlib import Path
import tempfile

from airunner.components.application.workers.base_download_worker import (
    BaseDownloadWorker,
)


class ConcreteDownloadWorker(BaseDownloadWorker):
    """Concrete implementation for testing."""

    def _download_file_impl(
        self, url: str, dest_path: Path, file_info: dict
    ) -> bool:
        """Concrete implementation of download."""
        # Simulate download by creating the file
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.touch()
        return True


class TestBaseDownloadWorker:
    """Test suite for BaseDownloadWorker."""

    def test_initialization(self):
        """Test worker initialization."""
        worker = ConcreteDownloadWorker()
        assert worker.current_file == ""
        assert worker.total_files == 0
        assert worker.completed_files == 0
        assert worker.total_bytes == 0
        assert worker.downloaded_bytes == 0
        assert worker.current_speed == 0.0
        assert worker._download_active is False

    def test_handle_message_starts_download(self):
        """Test that handle_message initiates download process."""
        worker = ConcreteDownloadWorker()

        message = {
            "files": [
                {
                    "url": "https://example.com/file1.bin",
                    "dest_path": "/tmp/file1.bin",
                    "size": 1024,
                }
            ],
            "callback": None,
        }

        with patch.object(worker, "_process_downloads"):
            worker.handle_message(message)
            worker._process_downloads.assert_called_once()

    def test_calculate_speed_zero_time(self):
        """Test speed calculation with zero time difference."""
        worker = ConcreteDownloadWorker()
        speed = worker._calculate_speed(1024, 0.0)
        assert speed == 0.0

    def test_calculate_speed_normal(self):
        """Test speed calculation with normal values."""
        worker = ConcreteDownloadWorker()
        # 1024 bytes in 1 second = 1 KB/s
        speed = worker._calculate_speed(1024, 1.0)
        assert speed == pytest.approx(1.0, rel=0.01)

    def test_format_speed_bytes(self):
        """Test formatting speed in bytes per second."""
        worker = ConcreteDownloadWorker()
        formatted = worker._format_speed(512.0)
        assert "512.00 B/s" in formatted

    def test_format_speed_kilobytes(self):
        """Test formatting speed in kilobytes per second."""
        worker = ConcreteDownloadWorker()
        formatted = worker._format_speed(1024.0)
        assert "1.00 KB/s" in formatted

    def test_format_speed_megabytes(self):
        """Test formatting speed in megabytes per second."""
        worker = ConcreteDownloadWorker()
        formatted = worker._format_speed(1024.0 * 1024)
        assert "1.00 MB/s" in formatted

    def test_format_size_bytes(self):
        """Test formatting size in bytes."""
        worker = ConcreteDownloadWorker()
        formatted = worker._format_size(512)
        assert "512.00 B" in formatted

    def test_format_size_kilobytes(self):
        """Test formatting size in kilobytes."""
        worker = ConcreteDownloadWorker()
        formatted = worker._format_size(1024)
        assert "1.00 KB" in formatted

    def test_format_size_megabytes(self):
        """Test formatting size in megabytes."""
        worker = ConcreteDownloadWorker()
        formatted = worker._format_size(1024 * 1024)
        assert "1.00 MB" in formatted

    def test_format_size_gigabytes(self):
        """Test formatting size in gigabytes."""
        worker = ConcreteDownloadWorker()
        formatted = worker._format_size(1024 * 1024 * 1024)
        assert "1.00 GB" in formatted

    def test_emit_progress_signal(self):
        """Test progress signal emission."""
        worker = ConcreteDownloadWorker()
        worker.current_file = "test.bin"
        worker.total_files = 10
        worker.completed_files = 5
        worker.total_bytes = 10240
        worker.downloaded_bytes = 5120
        worker.current_speed = 1024.0

        with patch.object(worker, "emit_signal") as mock_emit:
            worker._emit_progress()

            # Should emit progress signal
            assert mock_emit.called
            call_args = mock_emit.call_args
            assert "current_file" in call_args[0][1]
            assert call_args[0][1]["total_files"] == 10
            assert call_args[0][1]["completed_files"] == 5

    def test_process_downloads_success(self):
        """Test successful download processing."""
        worker = ConcreteDownloadWorker()

        with tempfile.TemporaryDirectory() as tmpdir:
            file_info = {
                "url": "https://example.com/file.bin",
                "dest_path": str(Path(tmpdir) / "file.bin"),
                "size": 1024,
            }

            worker.files = [file_info]
            worker.callback = None

            with patch.object(worker, "emit_signal"):
                worker._process_downloads()

                # Check file was created
                assert Path(file_info["dest_path"]).exists()
                assert worker.completed_files == 1

    def test_process_downloads_with_callback(self):
        """Test download processing with callback."""
        worker = ConcreteDownloadWorker()
        callback = Mock()

        with tempfile.TemporaryDirectory() as tmpdir:
            file_info = {
                "url": "https://example.com/file.bin",
                "dest_path": str(Path(tmpdir) / "file.bin"),
                "size": 1024,
            }

            worker.files = [file_info]
            worker.callback = callback

            with patch.object(worker, "emit_signal"):
                worker._process_downloads()

                # Callback should be called on completion
                callback.assert_called_once()

    def test_download_file_creates_directory(self):
        """Test that download creates parent directories."""
        worker = ConcreteDownloadWorker()

        with tempfile.TemporaryDirectory() as tmpdir:
            nested_path = Path(tmpdir) / "nested" / "dir" / "file.bin"
            file_info = {
                "url": "https://example.com/file.bin",
                "size": 1024,
            }

            result = worker._download_file(
                "https://example.com/file.bin", nested_path, file_info
            )

            assert result is True
            assert nested_path.exists()
            assert nested_path.parent.exists()

    def test_download_file_skips_existing(self):
        """Test that download skips existing files."""
        worker = ConcreteDownloadWorker()

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "existing.bin"
            file_path.touch()

            file_info = {
                "url": "https://example.com/file.bin",
                "size": 1024,
            }

            with patch.object(worker, "_download_file_impl") as mock_impl:
                result = worker._download_file(
                    "https://example.com/file.bin", file_path, file_info
                )

                # Should skip download
                assert result is True
                mock_impl.assert_not_called()

    def test_cancel_download(self):
        """Test canceling an active download."""
        worker = ConcreteDownloadWorker()
        worker._download_active = True

        with patch.object(worker, "emit_signal") as mock_emit:
            worker.cancel_download()

            assert worker._download_active is False
            # Should emit cancelled signal
            assert mock_emit.called

    def test_abstract_implementation_required(self):
        """Test that _download_file_impl must be implemented."""

        class IncompleteWorker(BaseDownloadWorker):
            pass

        # Should not be able to instantiate without implementing abstract method
        with pytest.raises(TypeError):
            worker = IncompleteWorker()


class TestDownloadStatistics:
    """Test download statistics tracking."""

    def test_statistics_initialization(self):
        """Test initial statistics values."""
        worker = ConcreteDownloadWorker()
        assert worker.total_files == 0
        assert worker.completed_files == 0
        assert worker.total_bytes == 0
        assert worker.downloaded_bytes == 0

    def test_statistics_update_during_download(self):
        """Test statistics are updated during downloads."""
        worker = ConcreteDownloadWorker()

        with tempfile.TemporaryDirectory() as tmpdir:
            files = [
                {
                    "url": f"https://example.com/file{i}.bin",
                    "dest_path": str(Path(tmpdir) / f"file{i}.bin"),
                    "size": 1024,
                }
                for i in range(3)
            ]

            worker.files = files
            worker.callback = None

            with patch.object(worker, "emit_signal"):
                worker._process_downloads()

                assert worker.total_files == 3
                assert worker.completed_files == 3
                assert worker.total_bytes == 3072  # 3 * 1024

    def test_progress_percentage_calculation(self):
        """Test progress percentage is calculated correctly."""
        worker = ConcreteDownloadWorker()
        worker.total_files = 10
        worker.completed_files = 5

        with patch.object(worker, "emit_signal") as mock_emit:
            worker._emit_progress()

            call_args = mock_emit.call_args[0][1]
            # 5/10 = 50%
            assert call_args["completed_files"] == 5
            assert call_args["total_files"] == 10
