"""Tests for RMBG background-removal worker lifecycle updates."""

from types import SimpleNamespace
from unittest.mock import Mock, call

from airunner.components.art.workers import background_removal_worker as module
from airunner.components.art.workers.background_removal_worker import (
    BackgroundRemovalWorker,
)
from airunner.enums import ModelStatus, ModelType, SignalCode


def _make_worker(model_manager):
    worker = BackgroundRemovalWorker.__new__(BackgroundRemovalWorker)
    worker._model_manager = model_manager
    worker.emit_signal = Mock()
    worker._persist_output = Mock()
    worker._refresh_canvas = Mock()
    worker.api = SimpleNamespace(application_error=Mock())
    return worker


def test_remove_background_tracks_rmbg_busy_and_ready(monkeypatch):
    """Successful RMBG inference should publish busy and ready states."""
    model_manager = SimpleNamespace(
        spec=SimpleNamespace(repo_id="briaai/RMBG-2.0"),
        missing_files=lambda: [],
        remove_background_to_png_bytes=Mock(return_value=b"output"),
        is_loaded=True,
        model_id="briaai/RMBG-2.0",
    )
    resource_manager = Mock()
    worker = _make_worker(model_manager)

    monkeypatch.setattr(
        module,
        "ModelResourceManager",
        lambda: resource_manager,
    )
    monkeypatch.setattr(
        module,
        "convert_binary_to_image",
        lambda _data: object(),
    )

    BackgroundRemovalWorker._remove_background(
        worker,
        {"layer_id": 5, "image": b"input"},
    )

    resource_manager.model_busy.assert_called_once_with(
        "briaai/RMBG-2.0",
        "rmbg",
    )
    resource_manager.model_ready.assert_called_once_with(
        "briaai/RMBG-2.0",
        "rmbg",
    )
    resource_manager.cleanup_model.assert_not_called()
    worker.emit_signal.assert_has_calls(
        [
            call(
                SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
                {
                    "model": ModelType.RMBG,
                    "status": ModelStatus.LOADING,
                },
            ),
            call(
                SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
                {
                    "model": ModelType.RMBG,
                    "status": ModelStatus.READY,
                },
            ),
        ]
    )
    worker._persist_output.assert_called_once_with(5, b"output")
    worker._refresh_canvas.assert_called_once_with()
    worker.api.application_error.assert_not_called()


def test_remove_background_cleans_unloaded_rmbg_on_failure(monkeypatch):
    """Failed RMBG inference should clear unloaded worker state."""
    model_manager = SimpleNamespace(
        spec=SimpleNamespace(repo_id="briaai/RMBG-2.0"),
        missing_files=lambda: [],
        remove_background_to_png_bytes=Mock(side_effect=RuntimeError("boom")),
        is_loaded=False,
        model_id="briaai/RMBG-2.0",
    )
    resource_manager = Mock()
    worker = _make_worker(model_manager)

    monkeypatch.setattr(
        module,
        "ModelResourceManager",
        lambda: resource_manager,
    )
    monkeypatch.setattr(
        module,
        "convert_binary_to_image",
        lambda _data: object(),
    )

    BackgroundRemovalWorker._remove_background(
        worker,
        {"layer_id": None, "image": b"input"},
    )

    resource_manager.model_busy.assert_called_once_with(
        "briaai/RMBG-2.0",
        "rmbg",
    )
    resource_manager.cleanup_model.assert_called_once_with(
        "briaai/RMBG-2.0",
        "rmbg",
    )
    resource_manager.model_ready.assert_not_called()
    worker.emit_signal.assert_has_calls(
        [
            call(
                SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
                {
                    "model": ModelType.RMBG,
                    "status": ModelStatus.LOADING,
                },
            ),
            call(
                SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
                {
                    "model": ModelType.RMBG,
                    "status": ModelStatus.FAILED,
                },
            ),
        ]
    )
    worker._persist_output.assert_not_called()
    worker._refresh_canvas.assert_not_called()
    worker.api.application_error.assert_called_once_with(message="boom")


def test_unload_model_releases_rmbg_and_emits_unloaded(monkeypatch):
    """Explicit RMBG unloads should clear resources and emit status."""
    model_manager = SimpleNamespace(
        unload=Mock(),
        model_id="briaai/RMBG-2.0",
    )
    resource_manager = Mock()
    worker = _make_worker(model_manager)

    monkeypatch.setattr(
        module,
        "ModelResourceManager",
        lambda: resource_manager,
    )

    BackgroundRemovalWorker._unload_model(worker)

    model_manager.unload.assert_called_once_with()
    resource_manager.cleanup_model.assert_called_once_with(
        "briaai/RMBG-2.0",
        "rmbg",
    )
    worker.emit_signal.assert_called_once_with(
        SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
        {"model": ModelType.RMBG, "status": ModelStatus.UNLOADED},
    )