"""Unit tests for the x4 finalize-response helpers.

The helpers were extracted to keep _finalize_response within the long-function
threshold. These tests assert the I/O orchestration is preserved exactly:
save failures never abort finalization, notification failures are swallowed,
and response build errors trigger the failure path.
"""

from unittest.mock import MagicMock

from airunner_services.art.managers.stablediffusion.x4_upscale_mixins.x4_upscaling_core_mixin import (
    X4UpscalingCoreMixin,
)


def _make_obj():
    obj = X4UpscalingCoreMixin.__new__(X4UpscalingCoreMixin)
    obj.logger = MagicMock()
    obj._save_result_to_disk = MagicMock(return_value="/tmp/out.png")
    obj._save_preview_image = MagicMock()
    obj._build_response_data = MagicMock(return_value={"prompt": "a cat"})
    obj._queue_export = MagicMock()
    obj._emit_completed = MagicMock()
    obj._send_to_canvas = MagicMock()
    obj._emit_failure = MagicMock()
    obj.active_rect = None
    return obj


def test_save_artifacts_returns_path_and_saves_preview():
    obj = _make_obj()
    assert obj._save_finalize_artifacts("img") == "/tmp/out.png"
    obj._save_result_to_disk.assert_called_once_with("img")
    obj._save_preview_image.assert_called_once_with("img")


def test_save_artifacts_never_raises():
    obj = _make_obj()
    obj._save_result_to_disk.side_effect = RuntimeError("disk full")
    assert obj._save_finalize_artifacts("img") is None


def test_build_and_notify_returns_response_and_notifies():
    obj = _make_obj()
    response = obj._build_and_notify_finalize_response(
        "img", "a cat", "blurry", 20, 7.5, 0.3, "/tmp/out.png"
    )
    assert response.data == {"prompt": "a cat"}
    assert response.images == ["img"]
    obj._queue_export.assert_called_once_with(["img"], {"prompt": "a cat"})
    obj._emit_completed.assert_called_once_with("/tmp/out.png", 20)
    obj._send_to_canvas.assert_called_once_with(response)


def test_finalize_returns_response_on_success():
    obj = _make_obj()
    response = obj._finalize_response(
        "img", MagicMock(), "a cat", "blurry", 20, 7.5, 0.3
    )
    assert response.images == ["img"]
    obj._emit_failure.assert_not_called()


def test_finalize_emits_failure_and_returns_none_on_build_error():
    obj = _make_obj()
    obj._build_response_data.side_effect = RuntimeError("bad data")
    assert (
        obj._finalize_response(
            "img", MagicMock(), "a cat", "blurry", 20, 7.5, 0.3
        )
        is None
    )
    obj._emit_failure.assert_called_once()
    obj.logger.exception.assert_called_once()


def test_finalize_survives_notification_failures():
    obj = _make_obj()
    obj._queue_export.side_effect = RuntimeError("nope")
    obj._emit_completed.side_effect = RuntimeError("nope")
    obj._send_to_canvas.side_effect = RuntimeError("nope")
    response = obj._finalize_response(
        "img", MagicMock(), "a cat", "blurry", 20, 7.5, 0.3
    )
    assert response.images == ["img"]
