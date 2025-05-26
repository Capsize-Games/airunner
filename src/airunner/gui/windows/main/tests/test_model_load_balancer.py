"""
Unit tests for ModelLoadBalancer.
"""

import pytest
from unittest.mock import MagicMock
from airunner.enums import ModelType
from airunner.gui.windows.main.model_load_balancer import ModelLoadBalancer


class DummyWorker:
    def __init__(self):
        self.loaded = True
        self.load_called = False
        self.unload_called = False
        self.load_model_manager_called = False

    def is_loaded(self):
        return self.loaded

    def load(self):
        self.load_called = True
        self.loaded = True

    def unload(self):
        self.unload_called = True
        self.loaded = False

    def load_model_manager(self):
        self.load_model_manager_called = True
        self.loaded = True


class DummyWorkerManager:
    def __init__(self):
        self.llm_generate_worker = DummyWorker()
        self.tts_generator_worker = DummyWorker()
        self.stt_audio_processor_worker = DummyWorker()
        self.sd_worker = DummyWorker()


@pytest.fixture
def balancer():
    wm = DummyWorkerManager()
    return ModelLoadBalancer(wm)


def test_switch_to_art_mode_unloads_non_art_and_loads_sd(balancer):
    balancer.switch_to_art_mode()
    assert not balancer.worker_manager.llm_generate_worker.loaded
    assert not balancer.worker_manager.tts_generator_worker.loaded
    assert not balancer.worker_manager.stt_audio_processor_worker.loaded
    # Accept either .load() or .load_model_manager() for SD worker
    assert (
        balancer.worker_manager.sd_worker.load_called
        or balancer.worker_manager.sd_worker.load_model_manager_called
    )
    assert set(balancer._last_non_art_models) == {
        ModelType.LLM,
        ModelType.TTS,
        ModelType.STT,
    }


def test_switch_to_non_art_mode_loads_previous(balancer):
    balancer._last_non_art_models = [ModelType.LLM, ModelType.TTS]
    balancer.worker_manager.llm_generate_worker.loaded = False
    balancer.worker_manager.tts_generator_worker.loaded = False
    balancer.switch_to_non_art_mode()
    assert balancer.worker_manager.llm_generate_worker.load_called
    assert balancer.worker_manager.tts_generator_worker.load_called
    assert balancer._last_non_art_models == []


def test_get_loaded_models(balancer):
    balancer.worker_manager.llm_generate_worker.loaded = True
    balancer.worker_manager.tts_generator_worker.loaded = False
    balancer.worker_manager.stt_audio_processor_worker.loaded = True
    balancer.worker_manager.sd_worker.loaded = True
    loaded = balancer.get_loaded_models()
    assert set(loaded) == {ModelType.LLM, ModelType.STT, ModelType.SD}
