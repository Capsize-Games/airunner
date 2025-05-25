import pytest
from unittest.mock import MagicMock

from airunner.gui.windows.main.worker_manager import WorkerManager


def test_worker_manager_initializes_attributes():
    wm = WorkerManager(logger=None)
    # All worker attributes should be None before initialization
    assert wm._mask_generator_worker is None
    assert wm._sd_worker is None
    assert wm._stt_audio_capture_worker is None
    assert wm._stt_audio_processor_worker is None
    assert wm._tts_generator_worker is None
    assert wm._tts_vocalizer_worker is None
    assert wm._llm_generate_worker is None


def test_worker_manager_initialize_workers(monkeypatch):
    wm = WorkerManager(logger=None)
    # Patch create_worker to return a MagicMock for all workers
    monkeypatch.setattr(
        "airunner.gui.windows.main.worker_manager.create_worker",
        lambda *a, **kw: MagicMock(),
    )
    wm.initialize_workers()
    # All worker attributes should now be MagicMock instances
    assert isinstance(wm._mask_generator_worker, MagicMock)
    assert isinstance(wm._sd_worker, MagicMock)
    assert isinstance(wm._llm_generate_worker, MagicMock)
    # Optional workers may be None if not available, but if available, should be MagicMock
    if hasattr(wm, "_stt_audio_capture_worker"):
        assert wm._stt_audio_capture_worker is None or isinstance(
            wm._stt_audio_capture_worker, MagicMock
        )
    if hasattr(wm, "_stt_audio_processor_worker"):
        assert wm._stt_audio_processor_worker is None or isinstance(
            wm._stt_audio_processor_worker, MagicMock
        )
    if hasattr(wm, "_tts_generator_worker"):
        assert wm._tts_generator_worker is None or isinstance(
            wm._tts_generator_worker, MagicMock
        )
    if hasattr(wm, "_tts_vocalizer_worker"):
        assert wm._tts_vocalizer_worker is None or isinstance(
            wm._tts_vocalizer_worker, MagicMock
        )


def test_worker_manager_logger(monkeypatch):
    logger = MagicMock()
    wm = WorkerManager(logger=logger)
    monkeypatch.setattr(
        "airunner.gui.windows.main.worker_manager.create_worker",
        lambda *a, **kw: MagicMock(),
    )
    wm.initialize_workers()
    # Logger should have received debug/info calls
    assert logger.debug.called
    assert logger.info.called
