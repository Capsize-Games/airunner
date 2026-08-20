"""Daemon runtime status refresh and GUI model-status reconciliation."""

from __future__ import annotations

import threading
import time

from airunner.components.application.gui.windows.main.controllers.base import (
    MainWindowBase,
)
from airunner.components.application.gui.windows.main.controllers.runtime_resource_mapper import (
    RuntimeResourceMapper,
)
from airunner.enums import ModelStatus, ModelType, SignalCode


class RuntimeStatusController(RuntimeResourceMapper):
    """Reconcile daemon runtime truth into GUI model status state."""

    def _refresh_model_status_from_daemon(self) -> None:
        """Refresh GUI model status from daemon lifecycle state."""
        if self.api is None or self._daemon_status_refresh_inflight:
            return
        client = getattr(self.api, "daemon_client", None)
        if client is None:
            return
        self._daemon_status_refresh_inflight = True
        threading.Thread(
            target=self._fetch_daemon_runtime_status,
            args=(client,),
            daemon=True,
        ).start()

    def _fetch_daemon_runtime_status(self, client) -> None:
        """Fetch one daemon runtime snapshot without blocking the UI."""
        status = None
        try:
            status = client.daemon_runtime_status(
                timeout_seconds=self._daemon_status_request_timeout_seconds,
            )
        except Exception:
            # A transient failure must not wedge the refresh flag: emit an
            # empty snapshot so the next timer tick can retry. Without this the
            # stats panel would stay stuck on "No models loaded" even though a
            # model is consuming VRAM.
            status = None
        self.daemon_runtime_status_ready.emit(status)

    def _on_daemon_runtime_status_ready(self, status: object) -> None:
        """Apply one daemon runtime snapshot on the GUI thread."""
        self._daemon_status_refresh_inflight = False
        if not isinstance(status, dict):
            return
        runtime_statuses = self._runtime_statuses_from_daemon_status(status)
        if runtime_statuses:
            self._apply_runtime_statuses(runtime_statuses)
        else:
            self._apply_lifecycle_statuses(status)
        self._sync_model_resource_manager_from_daemon(status)
        self._reconcile_optional_runtime_preferences(
            self._loaded_model_names_from_runtime_status(status)
        )

    def _apply_runtime_statuses(self, runtime_statuses) -> None:
        """Sync statuses derived from daemon runtime summaries."""
        runtime_statuses[ModelType.LLM] = self._effective_llm_status(
            runtime_statuses.get(ModelType.LLM, ModelStatus.UNLOADED)
        )
        for model_type in (ModelType.LLM, ModelType.TTS, ModelType.STT, ModelType.SD):
            self._sync_model_status_value(
                model_type,
                runtime_statuses.get(model_type, ModelStatus.UNLOADED),
            )

    def _apply_lifecycle_statuses(self, status: dict) -> None:
        """Sync statuses derived from the daemon lifecycle payload."""
        loaded_models = self._loaded_model_names_from_runtime_status(status)
        llm_status = self._effective_llm_status(
            ModelStatus.LOADED if "LLM" in loaded_models else ModelStatus.UNLOADED
        )
        self._sync_model_status_value(ModelType.LLM, llm_status)
        self._sync_model_status(ModelType.TTS, "TTS", loaded_models)
        self._sync_model_status(ModelType.STT, "STT", loaded_models)
        self._sync_model_status(ModelType.SD, "SD", loaded_models)

    def _effective_llm_status(self, daemon_status: ModelStatus) -> ModelStatus:
        """Prefer live local worker state over non-ready daemon summaries."""
        return daemon_status

    def _normalize_direct_llm_status(self, status: ModelStatus) -> ModelStatus:
        """Ignore stale failed events while a local load is still healthy."""
        return status

    def _optional_runtime_preference_specs(self):
        """Return daemon-backed runtime preference sync definitions."""
        return (
            (ModelType.TTS, "TTS", "tts_enabled", SignalCode.TTS_ENABLE_SIGNAL, SignalCode.TTS_DISABLE_SIGNAL),
            (ModelType.STT, "STT", "stt_enabled", SignalCode.STT_LOAD_SIGNAL, SignalCode.STT_UNLOAD_SIGNAL),
        )

    def _reconcile_optional_runtime_preferences(
        self, loaded_models: set[str]
    ) -> None:
        """Align daemon-backed TTS/STT state with persisted preferences."""
        now = time.monotonic()
        for spec in self._optional_runtime_preference_specs():
            self._reconcile_optional_runtime_preference(spec, loaded_models, now)

    def _reconcile_optional_runtime_preference(
        self, spec, loaded_models: set[str], now: float
    ) -> None:
        """Emit one load or unload signal when a preference is out of sync."""
        model_type, loaded_name, setting_name, load_signal, unload_signal = spec
        desired_enabled = bool(
            getattr(self.application_settings, setting_name, False)
        )
        is_loaded = loaded_name in loaded_models
        if self._preference_is_settled(
            model_type, desired_enabled, is_loaded, loaded_models
        ):
            return
        if now < self._runtime_preference_retry_after.get(model_type, 0.0):
            return
        self._runtime_preference_retry_after[model_type] = (
            now + self._runtime_preference_retry_seconds
        )
        signal = load_signal if desired_enabled else unload_signal
        self.emit_signal(signal, {"source": "runtime_preference_sync"})

    def _preference_is_settled(
        self, model_type, desired_enabled, is_loaded, loaded_models
    ) -> bool:
        """Return True when a runtime preference needs no further action."""
        if desired_enabled == is_loaded:
            self._runtime_preference_retry_after.pop(model_type, None)
            return True
        if model_type is ModelType.TTS and desired_enabled and not is_loaded:
            self._runtime_preference_retry_after.pop(model_type, None)
            return True
        if desired_enabled and self._model_status[model_type] is ModelStatus.LOADING:
            return True
        return False

    def _sync_model_status(
        self, model_type: ModelType, loaded_name: str, loaded_models: set[str]
    ) -> None:
        """Emit one model-status update when daemon truth changed."""
        status = ModelStatus.LOADED
        if loaded_name not in loaded_models:
            status = ModelStatus.UNLOADED
        self._sync_model_status_value(model_type, status)

    def _sync_model_status_value(
        self, model_type: ModelType, status: ModelStatus
    ) -> None:
        """Emit one model-status update when the status changed."""
        if self._model_status[model_type] is status:
            return
        self.emit_signal(
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
            {"model": model_type, "status": status},
        )

    def on_model_status_changed_signal(self, data):
        if not isinstance(data, dict):
            return
        model = data.get("model")
        status = data.get("status")
        if model is None or status is None:
            return
        if model is ModelType.LLM:
            status = self._normalize_direct_llm_status(status)
        self._sync_model_resource_manager_from_status_signal(data, model, status)
        if self._model_status.get(model) is status:
            return
        self._model_status[model] = status
        self._sync_setting_from_model_status(model, status)

    def _sync_setting_from_model_status(self, model, status) -> None:
        """Persist application settings driven by one model status."""
        if model is ModelType.SD:
            self._sync_sd_enabled(status)
        elif model is ModelType.LLM:
            self._sync_llm_enabled(status)
        elif model is ModelType.TTS:
            self._enable_button("text_to_speech_button")
        elif model is ModelType.STT:
            self._enable_button("speech_to_text_button")

    def _sync_sd_enabled(self, status) -> None:
        """Sync the SD enabled setting from its model status."""
        if status is ModelStatus.LOADED:
            self.update_application_settings(sd_enabled=True)
        elif status is ModelStatus.UNLOADED:
            self.update_application_settings(sd_enabled=False)

    def _sync_llm_enabled(self, status) -> None:
        """Sync the LLM enabled setting from its model status."""
        if status is ModelStatus.LOADED:
            self.update_application_settings(llm_enabled=True)
        elif status is ModelStatus.FAILED:
            self.logger.warning("LLM failed to load")
        elif status is ModelStatus.UNLOADED:
            self.update_application_settings(llm_enabled=False)

    def _enable_button(self, attr: str) -> None:
        """Re-enable one toggle button after a model status settles."""
        button = getattr(self.ui, attr, None)
        if button is not None:
            button.setDisabled(False)
