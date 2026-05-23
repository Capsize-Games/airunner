"""STT executor backed by the shared runtime registry."""

from __future__ import annotations

import base64
from typing import Any, Optional

from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.ipc.messages import EnvelopeStatus, RequestEnvelope
from airunner_services.runtimes.contracts import RuntimeAction, RuntimeKind
from airunner_services.runtimes.stt_executor import STTExecutor
from airunner_services.utils.application.api_reference import (
    peek_registered_api,
)
from airunner_services.utils.application.get_logger import get_logger


class RuntimeRegistrySTTExecutor(STTExecutor):
    """Route STT model control and transcription through the runtime registry."""

    def __init__(self, *, api: Optional[object] = None) -> None:
        self.logger = get_logger(self.__class__.__name__, AIRUNNER_LOG_LEVEL)
        self.api = api or self._resolve_api_reference()
        self._loaded = False

    def _resolve_api_reference(self) -> Optional[object]:
        """Return the registered shared API reference when available."""
        return peek_registered_api()

    def refresh_api_reference(self) -> Optional[object]:
        """Refresh one stale cached API reference when possible."""
        live_api = self._resolve_api_reference()
        if live_api is not None:
            self.api = live_api
        return getattr(self, "api", None)

    def _resolve_client(self):
        """Resolve the default local STT runtime client."""
        api = self.refresh_api_reference()
        registry = getattr(api, "runtime_registry", None)
        if registry is None:
            raise RuntimeError("STT runtime registry unavailable")
        return registry.resolve(RuntimeKind.STT, provider="local")

    @property
    def stt_is_loaded(self) -> bool:
        """Return whether the runtime-backed executor is ready."""
        return self._loaded

    def load(self, retry: bool = False) -> bool:
        """Start the configured STT runtime and cache one loaded state."""
        del retry
        response = self._invoke(RuntimeAction.LOAD_MODEL)
        self._loaded = response is not None
        return self._loaded

    def unload(self) -> None:
        """Stop the configured STT runtime and clear local loaded state."""
        if not self._loaded:
            return
        self._invoke(RuntimeAction.UNLOAD_MODEL)
        self._loaded = False

    def transcribe(self, audio_data: Any) -> str:
        """Submit one queued audio payload to the STT runtime."""
        item = audio_data.get("item") if audio_data else None
        if not item:
            return ""
        payload = {
            "audio_b64": base64.b64encode(item).decode("ascii"),
            "mime_type": audio_data.get("mime_type", "application/octet-stream"),
        }
        if audio_data.get("language"):
            payload["language"] = audio_data["language"]
        if audio_data.get("sample_rate"):
            payload["sample_rate"] = audio_data["sample_rate"]
        response = self._invoke(RuntimeAction.INVOKE, payload=payload)
        if response is None:
            return ""
        self._loaded = True
        return str(response.get("text", "") or "")

    def _invoke(
        self,
        action: RuntimeAction,
        *,
        payload: Optional[dict[str, Any]] = None,
    ) -> Optional[dict[str, Any]]:
        """Invoke one STT runtime action and normalize failures."""
        try:
            client = self._resolve_client()
            response = client.invoke(
                RequestEnvelope(
                    runtime=RuntimeKind.STT,
                    action=action,
                    provider="local",
                    payload=payload or {},
                )
            )
        except Exception as exc:
            self.logger.warning("STT runtime %s failed: %s", action.value, exc)
            return None
        if response.status is not EnvelopeStatus.SUCCEEDED:
            error = response.error.message if response.error else action.value
            self.logger.warning("STT runtime %s failed: %s", action.value, error)
            return None
        return response.payload


__all__ = ["RuntimeRegistrySTTExecutor"]