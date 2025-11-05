"""
ModelLoadBalancer: Orchestrates model loading/unloading for VRAM/resource management.

- Tracks which models are loaded/unloaded.
- Delegates actual load/unload to worker manager(s).
- Can be extended to use VRAM stats and model size for smarter balancing.
- API: switch_to_art_mode(), switch_to_non_art_mode(), get_loaded_models(), etc.

TDD: See tests/model_load_balancer/test_model_load_balancer.py
"""

from typing import List, Optional
from airunner.enums import ModelType, SignalCode, ModelStatus
from airunner.utils.memory.gpu_memory_stats import gpu_memory_stats
from airunner.utils.application.mediator_mixin import MediatorMixin


class ModelLoadBalancer(MediatorMixin):
    def __init__(self, worker_manager, logger=None, api=None):
        self.worker_manager = worker_manager
        self.logger = logger
        self.api = api
        self._last_non_art_models: List[ModelType] = []
        super().__init__()

    def _emit_model_status(self, model_type, status):
        if self.api and hasattr(self.api, "change_model_status"):
            self.api.change_model_status(model_type, status)
        else:
            self.emit_signal(
                SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
                {"model": model_type, "status": status},
            )

    def switch_to_art_mode(self):
        """
        Unload all non-art models (LLM, TTS, STT), load SD model.
        Tracks which models were previously loaded for restoration.
        """
        self._last_non_art_models = []
        for model_type, worker in [
            (ModelType.LLM, self.worker_manager.llm_generate_worker),
            (ModelType.TTS, self.worker_manager.tts_generator_worker),
            (ModelType.STT, self.worker_manager.stt_audio_processor_worker),
        ]:
            if not worker:
                continue
            # Use application settings to determine if a model was enabled/"loaded"
            try:
                if model_type is ModelType.LLM:
                    was_enabled = worker.application_settings.llm_enabled
                elif model_type is ModelType.TTS:
                    was_enabled = worker.application_settings.tts_enabled
                elif model_type is ModelType.STT:
                    was_enabled = worker.application_settings.stt_enabled
                else:
                    was_enabled = False
            except Exception:
                was_enabled = False

            if was_enabled:
                self._last_non_art_models.append(model_type)
                worker.unload()
                self._emit_model_status(model_type, ModelStatus.UNLOADED)
        if self.worker_manager.sd_worker:
            self.worker_manager.sd_worker.load_model_manager()
            self._emit_model_status(ModelType.SD, ModelStatus.LOADED)
        if self.logger:
            self.logger.info(
                f"Switched to art mode. Unloaded: {self._last_non_art_models}"
            )

    def switch_to_non_art_mode(
        self, additional_types: Optional[List[ModelType]] = None
    ):
        """
        Reload previously unloaded non-art models (LLM, TTS, STT).
        Optionally load additional model types (e.g., [ModelType.LLM]) even if they
        were not previously enabled.
        """
        additional_types = additional_types or []
        # First reload those that were actually unloaded previously
        for model_type in self._last_non_art_models:
            worker = None
            if model_type == ModelType.LLM:
                worker = self.worker_manager.llm_generate_worker
            elif model_type == ModelType.TTS:
                worker = self.worker_manager.tts_generator_worker
            elif model_type == ModelType.STT:
                worker = self.worker_manager.stt_audio_processor_worker
            if worker:
                worker.load()
                self._emit_model_status(model_type, ModelStatus.LOADED)
        # Then load any additional types requested that aren't already restored
        for model_type in additional_types:
            if model_type not in self._last_non_art_models:
                worker = None
                if model_type == ModelType.LLM:
                    worker = self.worker_manager.llm_generate_worker
                elif model_type == ModelType.TTS:
                    worker = self.worker_manager.tts_generator_worker
                elif model_type == ModelType.STT:
                    worker = self.worker_manager.stt_audio_processor_worker
                if worker:
                    worker.load()
                    self._emit_model_status(model_type, ModelStatus.LOADED)
        if self.logger:
            self.logger.info(
                f"Restored non-art models: {self._last_non_art_models}"
            )
        self._last_non_art_models = []

    def get_loaded_models(self) -> List[ModelType]:
        loaded = []
        for model_type, worker in [
            (ModelType.LLM, self.worker_manager.llm_generate_worker),
            (ModelType.TTS, self.worker_manager.tts_generator_worker),
            (ModelType.STT, self.worker_manager.stt_audio_processor_worker),
            (ModelType.SD, self.worker_manager.sd_worker),
        ]:
            if worker and getattr(worker, "is_loaded", lambda: True)():
                loaded.append(model_type)
        return loaded

    def vram_stats(self, device):
        return gpu_memory_stats(device)
