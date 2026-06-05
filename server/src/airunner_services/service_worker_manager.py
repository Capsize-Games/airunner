"""Service-owned worker container for daemon and daemon execution."""

from __future__ import annotations

from typing import Any, Callable, Optional

from airunner_services.contract_enums import ModelStatus
from airunner_services.utils.application.create_worker import create_worker

WorkerFactory = Callable[[type[Any]], Any]


class ServiceWorkerManager:
    """Lazily create service-owned workers without the GUI WorkerManager."""

    def __init__(
        self,
        worker_factory: Optional[WorkerFactory] = None,
    ) -> None:
        """Initialize the service-owned worker registry."""
        self._worker_factory = worker_factory or create_worker
        self._image_export_worker: Optional[Any] = None
        self._llm_generate_worker: Optional[Any] = None
        self._sd_worker: Optional[Any] = None
        self._stt_audio_processor_worker: Optional[Any] = None
        self._tts_generator_worker: Optional[Any] = None

    @property
    def image_export_worker(self) -> Any:
        """Return the shared image export worker for art execution."""
        if self._image_export_worker is None:
            from airunner_services.workers.image_export_worker import (
                ImageExportWorker,
            )

            self._image_export_worker = self._worker_factory(ImageExportWorker)
        return self._image_export_worker

    @property
    def llm_generate_worker(self) -> Any:
        """Return the shared LLM worker for orchestration."""
        if self._llm_generate_worker is None:
            from airunner_services.workers.llm_generate_worker import (
                LLMGenerateWorker,
            )

            self._llm_generate_worker = self._worker_factory(LLMGenerateWorker)
        return self._llm_generate_worker

    @property
    def sd_worker(self) -> Any:
        """Return the shared art worker used by compatibility code."""
        if self._sd_worker is None:
            from airunner_services.workers.sd_worker import SDWorker

            self._sd_worker = self._worker_factory(
                SDWorker,
                image_export_worker=self.image_export_worker,
            )
        return self._sd_worker

    @property
    def stt_audio_processor_worker(self) -> Any:
        """Return the shared STT processor worker when requested."""
        if self._stt_audio_processor_worker is None:
            from airunner_services.workers.audio_processor_worker import (
                AudioProcessorWorker,
            )

            self._stt_audio_processor_worker = self._worker_factory(
                AudioProcessorWorker
            )
        return self._stt_audio_processor_worker

    @property
    def tts_generator_worker(self) -> Any:
        """Return the shared TTS worker when optional dependencies exist."""
        if self._tts_generator_worker is None:
            try:
                from airunner_services.workers.tts_generator_worker import (
                    TTSGeneratorWorker,
                )
            except ModuleNotFoundError:
                return None

            self._tts_generator_worker = self._worker_factory(
                TTSGeneratorWorker
            )
        return self._tts_generator_worker

    def loaded_model_names(self) -> list[str]:
        """Return the names of models already loaded by instantiated workers."""
        loaded = []
        if self._llm_loaded():
            loaded.append("LLM")
        if self._tts_loaded():
            loaded.append("TTS")
        if self._stt_loaded():
            loaded.append("STT")
        if self._art_loaded():
            loaded.append("SD")
        return loaded

    def _llm_loaded(self) -> bool:
        """Return whether the instantiated LLM worker has a loaded model."""
        worker = self._llm_generate_worker
        if worker is None:
            return False
        status_getter = getattr(worker, "current_model_status", None)
        if callable(status_getter):
            status = status_getter()
            if status in (ModelStatus.LOADED, ModelStatus.READY):
                return True
        model_manager = getattr(worker, "_model_manager", None)
        return bool(
            model_manager is not None
            and getattr(model_manager, "_chat_model", None) is not None
        )

    def _tts_loaded(self) -> bool:
        """Return whether the instantiated TTS worker has a loaded model."""
        worker = self._tts_generator_worker
        if worker is None:
            return False
        status_getter = getattr(worker, "_current_tts_status", None)
        if callable(status_getter):
            return status_getter() in (ModelStatus.LOADED, ModelStatus.READY)
        return False

    def _stt_loaded(self) -> bool:
        """Return whether the instantiated STT worker has a loaded model."""
        worker = self._stt_audio_processor_worker
        if worker is None:
            return False
        executor = getattr(worker, "_executor", None)
        return bool(executor is not None and executor.stt_is_loaded)

    def _art_loaded(self) -> bool:
        """Return whether the instantiated art worker has a loaded model."""
        worker = self._sd_worker
        if worker is None:
            return False
        manager = getattr(worker, "_model_manager", None)
        if manager is None:
            return False
        try:
            status = manager.model_status.get(manager.model_type)
        except Exception:
            status = None
        if status in (ModelStatus.LOADED, ModelStatus.READY):
            return True
        return bool(getattr(manager, "model_is_loaded", False))
