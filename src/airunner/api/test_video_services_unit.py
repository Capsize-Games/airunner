import pytest
from unittest.mock import MagicMock
from airunner.api.video_services import VideoAPIService
from airunner.enums import SignalCode


@pytest.fixture
def video_service():
    mock_emit_signal = MagicMock()
    service = VideoAPIService(emit_signal=mock_emit_signal)
    return service


def test_generate(video_service):
    data = {"test": "data"}
    video_service.generate(data)
    video_service.emit_signal.assert_called_once_with(
        SignalCode.VIDEO_GENERATE_SIGNAL, data
    )


def test_frame_update(video_service):
    frame = "test_frame_data"
    video_service.frame_update(frame)
    video_service.emit_signal.assert_called_once_with(
        SignalCode.VIDEO_FRAME_UPDATE_SIGNAL, {"frame": frame}
    )


def test_generation_complete(video_service):
    path = "/path/to/video.mp4"
    video_service.generation_complete(path)
    video_service.emit_signal.assert_called_once_with(
        SignalCode.VIDEO_GENERATED_SIGNAL, {"path": path}
    )


def test_video_generate_step(video_service):
    percent = 75
    message = "Processing frame 75/100"
    video_service.video_generate_step(percent, message)
    video_service.emit_signal.assert_called_once_with(
        SignalCode.VIDEO_PROGRESS_SIGNAL,
        {"percent": percent, "message": message},
    )


def test_generate_bad_path(video_service):
    # Bad path: Test with None data (no validation in method, so just verify it passes through)
    video_service.generate(None)
    video_service.emit_signal.assert_called_once_with(
        SignalCode.VIDEO_GENERATE_SIGNAL, None
    )


def test_frame_update_bad_path(video_service):
    # Bad path: Test with None frame (no validation in method, so just verify it passes through)
    video_service.frame_update(None)
    video_service.emit_signal.assert_called_once_with(
        SignalCode.VIDEO_FRAME_UPDATE_SIGNAL, {"frame": None}
    )


def test_generation_complete_bad_path(video_service):
    # Bad path: Test with None path (no validation in method, so just verify it passes through)
    video_service.generation_complete(None)
    video_service.emit_signal.assert_called_once_with(
        SignalCode.VIDEO_GENERATED_SIGNAL, {"path": None}
    )


def test_video_generate_step_bad_path(video_service):
    # Bad path: Test with None values (no validation in method, so just verify it passes through)
    video_service.video_generate_step(None, None)
    video_service.emit_signal.assert_called_once_with(
        SignalCode.VIDEO_PROGRESS_SIGNAL, {"percent": None, "message": None}
    )
