"""Daemon-aware model lifecycle compatibility layer for the GUI."""

from __future__ import annotations

from typing import List, Optional

from airunner.enums import ModelType, SignalCode, ModelStatus
from airunner.utils.memory.gpu_memory_stats import gpu_memory_stats
from airunner.utils.application.mediator_mixin import MediatorMixin


_DAEMON_MODEL_TYPES = {
    "LLM": ModelType.LLM,
    "TTS": ModelType.TTS,
    "STT": ModelType.STT,
    "SD": ModelType.SD,
}

_RUNTIME_MODEL_TYPES = {
    "llm": ModelType.LLM,
    "tts": ModelType.TTS,
    "stt": ModelType.STT,
    "art": ModelType.SD,
}

_RUNTIME_NAMES = {
    ModelType.LLM: "llm",
    ModelType.TTS: "tts",
    ModelType.STT: "stt",
    ModelType.SD: "art",
}


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

    def _worker_manager_daemon_client(self):
        """Return the worker manager daemon client when available."""
        manager = getattr(self, "worker_manager", None)
        daemon_getter = getattr(manager, "_daemon_client", None)
        if callable(daemon_getter):
            return daemon_getter()
        return None

    def _worker_manager_runtime_control(self, action: str, model_type) -> bool:
        """Delegate one daemon runtime action to WorkerManager when available."""
        manager = getattr(self, "worker_manager", None)
        controller = getattr(manager, "_control_daemon_runtime", None)
        runtime_name = _RUNTIME_NAMES.get(model_type)
        if runtime_name is None or not callable(controller):
            return False
        route_metadata = None
        if action == "load" and model_type is ModelType.TTS:
            metadata_getter = getattr(manager, "_tts_runtime_route_metadata", None)
            if callable(metadata_getter):
                route_metadata = metadata_getter()
        return bool(
            controller(
                runtime_name,
                action,
                model_type,
                route_metadata=route_metadata,
            )
        )

    def switch_to_art_mode(self):
        """
        Unload all non-art models (LLM, TTS, STT), load SD model.
        Tracks which models were previously loaded for restoration.
        """
        if self._daemon_client() is not None:
            daemon_models = self._daemon_loaded_models() or []
            self._last_non_art_models = self._non_art_models(daemon_models)
            self._daemon_unload(self._last_non_art_models)
            return

        self._last_non_art_models = []
        # LLM state tracked by daemon; local worker removed
        # TTS/STT workers removed; daemon handles all runtimes
        for model_type, worker in [
            (ModelType.TTS, None),
            (ModelType.STT, None),
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
        # SD model loading now handled exclusively by daemon
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
        if self._daemon_client() is not None:
            restore_types = self._restore_types(additional_types)
            self._daemon_load(restore_types)
            self._last_non_art_models = []
            return

        # First reload those that were actually unloaded previously
        for model_type in self._last_non_art_models:
            worker = None
            if model_type == ModelType.LLM:
                worker = None  # local LLM worker removed; daemon handles LLM
            elif model_type == ModelType.TTS:
                worker = None
            elif model_type == ModelType.STT:
                worker = None
            if worker:
                worker.load()
                self._emit_model_status(model_type, ModelStatus.LOADED)
        # Then load any additional types requested that aren't already restored
        for model_type in additional_types:
            if model_type not in self._last_non_art_models:
                worker = None
                if model_type == ModelType.LLM:
                    worker = None  # local LLM worker removed; daemon handles LLM
                elif model_type == ModelType.TTS:
                    worker = None
                elif model_type == ModelType.STT:
                    worker = None
                if worker:
                    worker.load()
                    self._emit_model_status(model_type, ModelStatus.LOADED)
        if self.logger:
            self.logger.info(
                f"Restored non-art models: {self._last_non_art_models}"
            )
        self._last_non_art_models = []

    def get_loaded_models(self) -> List[ModelType]:
        if self._daemon_client() is not None:
            loaded_models = self._daemon_loaded_models() or []
            return self._merge_local_llm_loaded_model(loaded_models)

        loaded = []
        # LLM/SD state tracked by daemon; local workers removed
        # TTS/STT workers removed; daemon handles all runtimes
        for model_type, worker in [
            (ModelType.TTS, None),
            (ModelType.STT, None),
        ]:
            if worker and getattr(worker, "is_loaded", lambda: True)():
                loaded.append(model_type)
        return loaded

    def _merge_local_llm_loaded_model(
        self,
        loaded_models: List[ModelType],
    ) -> List[ModelType]:
        """Keep local LLM state visible when daemon status is stale."""
        # Local LLM worker removed; daemon handles all LLM state
        worker = None
        if worker is None:
            return loaded_models
        status_getter = getattr(worker, "current_model_status", None)
        if not callable(status_getter):
            return loaded_models
        if status_getter() is not ModelStatus.LOADED:
            return loaded_models
        if ModelType.LLM in loaded_models:
            return loaded_models
        return [*loaded_models, ModelType.LLM]

    def vram_stats(self, device):
        return gpu_memory_stats(device)

    def _daemon_client(self):
        """Return the GUI daemon client when daemon-backed control is active."""
        worker_manager_client = self._worker_manager_daemon_client()
        if worker_manager_client is not None:
            return worker_manager_client
        refresher = getattr(self, "refresh_api_reference", None)
        if callable(refresher):
            refreshed_api = refresher()
            if refreshed_api is not None:
                self.api = refreshed_api
        if self.api is None or getattr(self.api, "headless", False):
            return None
        return getattr(self.api, "daemon_client", None)

    def _daemon_loaded_models(self) -> Optional[List[ModelType]]:
        """Return loaded models from daemon status when available."""
        client = self._daemon_client()
        if client is None:
            return None
        availability_check = getattr(client, "is_available", None)
        if callable(availability_check):
            try:
                if not availability_check(timeout_seconds=0.2):
                    return None
            except TypeError:
                if not availability_check():
                    return None
        try:
            status = client.daemon_runtime_status(auto_start=False)
        except RuntimeError:
            return None
        if "runtimes" in status:
            return self._runtime_summary_models(status.get("runtimes") or [])
        lifecycle = status.get("lifecycle") or {}
        loaded = []
        for name in lifecycle.get("loaded_models") or []:
            model_type = _DAEMON_MODEL_TYPES.get(str(name).upper())
            if model_type is not None:
                loaded.append(model_type)
        return loaded

    def _daemon_load(self, model_types: List[ModelType]) -> None:
        """Load models through the daemon control API without blocking the GUI thread.

        Delegates to the worker manager's async runtime control so the
        LOADING/LOADED/FAILED lifecycle runs in a background thread.
        """
        client = self._daemon_client()
        if client is None:
            return
        for model_type in model_types:
            runtime_name = _RUNTIME_NAMES.get(model_type)
            if runtime_name is None:
                continue
            # Use async dispatch to avoid blocking the GUI thread on
            # daemon HTTP calls that may take seconds to time out.
            manager = getattr(self, "worker_manager", None)
            controller = getattr(
                manager, "_control_daemon_runtime_async", None
            )
            if controller is not None:
                controller(runtime_name, "load", model_type)
                continue
            # Fallback: synchronous dispatch (legacy path)
            self._emit_model_status(model_type, ModelStatus.LOADING)
            try:
                client.load_runtime(runtime_name)
            except RuntimeError:
                self._emit_model_status(model_type, ModelStatus.FAILED)
                continue
            if not client.wait_runtime_ready(
                runtime_name,
                loaded=True,
                auto_start=False,
            ):
                self._emit_model_status(model_type, ModelStatus.FAILED)
                continue
            self._emit_model_status(model_type, ModelStatus.LOADED)

    def _daemon_unload(self, model_types: List[ModelType]) -> None:
        """Unload models through the daemon control API."""
        client = self._daemon_client()
        if client is None:
            return
        for model_type in model_types:
            if self._worker_manager_runtime_control("unload", model_type):
                continue
            runtime_name = _RUNTIME_NAMES.get(model_type)
            if runtime_name is None:
                continue
            try:
                client.unload_runtime(runtime_name)
            except RuntimeError:
                self._emit_model_status(model_type, ModelStatus.FAILED)
                continue
            if not client.wait_runtime_ready(
                runtime_name,
                loaded=False,
                auto_start=False,
            ):
                self._emit_model_status(model_type, ModelStatus.FAILED)
                continue
            self._emit_model_status(model_type, ModelStatus.UNLOADED)

    @staticmethod
    def _runtime_summary_models(runtimes: List[dict]) -> List[ModelType]:
        """Return loaded models derived from daemon runtime summaries."""
        loaded = []
        seen = set()
        for runtime in runtimes:
            if not runtime.get("loaded"):
                continue
            runtime_name = str(runtime.get("runtime", "")).lower()
            model_type = _RUNTIME_MODEL_TYPES.get(runtime_name)
            if model_type is None or model_type in seen:
                continue
            loaded.append(model_type)
            seen.add(model_type)
        return loaded

    @staticmethod
    def _non_art_models(model_types: List[ModelType]) -> List[ModelType]:
        """Return only non-art model types from a loaded model list."""
        return [model_type for model_type in model_types if model_type is not ModelType.SD]

    def _restore_types(
        self,
        additional_types: List[ModelType],
    ) -> List[ModelType]:
        """Return the non-art models that should be restored for chat mode."""
        restore_types = list(self._last_non_art_models)
        for model_type in additional_types:
            if model_type not in restore_types:
                restore_types.append(model_type)
        if not restore_types:
            restore_types.append(ModelType.LLM)
        return self._non_art_models(restore_types)
