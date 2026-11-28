"""Unit tests for the HuggingFace file-job extraction helpers.

The progress-reporter factory and completion helper were extracted to
keep _run_huggingface_file_job within the long-function threshold. The
tests pin the throttle behavior and the completion payload.
"""

from unittest.mock import AsyncMock, MagicMock

from airunner_services.downloads.job_service import DownloadJobService


def _make_service():
    service = DownloadJobService.__new__(DownloadJobService)
    service._tracker = MagicMock()
    service._tracker.update_progress = AsyncMock()
    service._record_file_progress = MagicMock()
    service._complete_job = MagicMock()
    return service


def test_progress_reporter_reports_first_call():
    service = _make_service()
    progress = service._make_huggingface_progress_reporter("j1", "f.bin")
    progress(50, 100)
    service._record_file_progress.assert_called_once_with("j1", "f.bin", 50, 100)


def test_progress_reporter_throttles_small_increments():
    service = _make_service()
    progress = service._make_huggingface_progress_reporter("j1", "f.bin")
    progress(50, 100)  # 50%
    progress(55, 100)  # 55% — within 1.0 of last reported? no: 55-50=5 → reports
    assert service._record_file_progress.call_count == 2
    progress(56, 100)  # 56-55=1 → not < 1.0 → reports
    assert service._record_file_progress.call_count == 3
    progress(565, 1000)  # 56.5 - 56 = 0.5 < 1.0 and < 100 → throttled
    assert service._record_file_progress.call_count == 3


def test_progress_reporter_throttles_repeated_capped_value():
    service = _make_service()
    progress = service._make_huggingface_progress_reporter("j1", "f.bin")
    progress(100, 100)  # coerced to 99.0 cap → reports
    progress(100, 100)  # 99.0 - 99.0 = 0 < 1.0 → throttled
    assert service._record_file_progress.call_count == 1


def test_progress_reporter_updates_tracker():
    service = _make_service()
    progress = service._make_huggingface_progress_reporter("j1", "f.bin")
    progress(25, 100)
    service._tracker.update_progress.assert_called_once()


def test_complete_job_payload():
    service = _make_service()
    service._complete_huggingface_job("j1", "org/repo", "f.bin", "/tmp/f.bin")
    service._complete_job.assert_called_once_with(
        "j1",
        {
            "provider": "huggingface",
            "repo_id": "org/repo",
            "filename": "f.bin",
            "paths": ["/tmp/f.bin"],
        },
    )
