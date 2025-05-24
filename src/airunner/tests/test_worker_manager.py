import pytest
from airunner.gui.windows.main.worker_manager import WorkerManager


class DummyLogger:
    def __init__(self):
        self.debug_calls = []
        self.info_calls = []

    def debug(self, msg):
        self.debug_calls.append(msg)

    def info(self, msg):
        self.info_calls.append(msg)


def test_worker_manager_happy_path(monkeypatch):
    # Patch create_worker to return a unique object for each worker type
    created = {}

    def fake_create_worker(cls):
        obj = object()
        created[cls.__name__] = obj
        return obj

    monkeypatch.setattr(
        "airunner.gui.windows.main.worker_manager.create_worker",
        fake_create_worker,
    )
    logger = DummyLogger()
    wm = WorkerManager(logger=logger)
    wm.initialize_workers()
    # All workers should be set
    assert wm.mask_generator_worker is created.get("MaskGeneratorWorker")
    assert wm.sd_worker is created.get("SDWorker")
    assert wm.llm_generate_worker is created.get("LLMGenerateWorker")
    # Audio workers may be None if not available, but if present, should be set
    # (We can't guarantee their presence in all environments)
    # Logger should have been called
    assert any(
        "Initializing worker manager" in msg for msg in logger.debug_calls
    )
    assert any(
        "INITIALIZE WORKERS COMPLETE" in msg for msg in logger.info_calls
    )


def test_worker_manager_double_init(monkeypatch):
    # Should be idempotent (re-initializing just overwrites)
    monkeypatch.setattr(
        "airunner.gui.windows.main.worker_manager.create_worker",
        lambda cls: object(),
    )
    wm = WorkerManager()
    wm.initialize_workers()
    first = wm.mask_generator_worker
    wm.initialize_workers()
    second = wm.mask_generator_worker
    assert first is not second


def test_worker_manager_bad_logger(monkeypatch):
    monkeypatch.setattr(
        "airunner.gui.windows.main.worker_manager.create_worker",
        lambda cls: object(),
    )
    wm = WorkerManager(logger=None)
    wm.initialize_workers()  # Should not raise


def test_worker_manager_properties_before_init():
    wm = WorkerManager()
    # All properties should be None before init
    assert wm.mask_generator_worker is None
    assert wm.sd_worker is None
    assert wm.llm_generate_worker is None
    # ...and so on for other properties
