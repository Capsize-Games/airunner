"""Cloud runtime client for Muse image generation."""

from __future__ import annotations

import threading
from typing import Any, Callable, Optional
from uuid import uuid4

import requests

from airunner_services.runtimes.base import RuntimeClient
from airunner_services.runtimes.contracts import (
    ArtInvocationRequest, RuntimeAction, RuntimeDescriptor,
    RuntimeHealth, RuntimeHealthStatus, RuntimeKind, RuntimeMode,
    TransportKind,
)
from airunner_services.runtimes.message_envelopes import load_message_types
from airunner_services.runtimes.muse_art_helpers import (
    MuseArtError, MuseArtSettings, MuseSession, post_images,
    validate_muse_invocation,
)
from airunner_services.runtimes.muse_request_parse import (
    parse_muse_request,
)
from airunner_services.runtimes.muse_usage import (
    MuseUsageLedger, MuseUsageLimitError,
)
from airunner_services.runtimes.registry import RuntimeRegistry, RuntimeRoute

ProgressCallback = Callable[[dict[str, Any]], None]

class MuseArtClient(RuntimeClient):
    """Route art envelopes to the Meta Muse image endpoint."""

    def __init__(
        self,
        provider: str = "muse",
        *,
        settings: Optional[MuseArtSettings] = None,
        session: Optional[MuseSession] = None,
        ledger: Optional[MuseUsageLedger] = None,
    ) -> None:
        self._settings = settings or MuseArtSettings.from_env()
        self._ledger = ledger if ledger is not None else MuseUsageLedger()
        self._session: MuseSession = session or requests.Session()
        self._lock = threading.Lock()
        self._active: set[str] = set()
        self._cancelled: set[str] = set()
        self.descriptor = self._descriptor(provider)

    def _descriptor(self, provider: str) -> RuntimeDescriptor:
        return RuntimeDescriptor(
            runtime=RuntimeKind.ART, provider=provider,
            mode=RuntimeMode.CLOUD, transport=TransportKind.HTTP,
            endpoint=self._settings.base_url,
            supports_streaming=False, allows_model_control=False)

    def invoke(self, request: Any) -> Any:
        return self.invoke_with_progress(request)

    def invoke_with_progress(
        self,
        request: Any,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> Any:
        request_id, invocation = parse_muse_request(request)
        action = getattr(request, "action", RuntimeAction.INVOKE)
        if action is RuntimeAction.STATUS:
            return self._status_response(request_id)
        if action in (RuntimeAction.LOAD_MODEL, RuntimeAction.UNLOAD_MODEL):
            return self._failure(
                request_id, "muse_model_control_unsupported",
                "Muse cloud has no local model control", False,
                self._model_for(invocation),
            )
        if action is not RuntimeAction.INVOKE:
            raise ValueError("MuseArtClient only supports invoke")
        return self._generate(request_id, invocation, progress_callback)

    def healthcheck(self) -> RuntimeHealth:
        metadata = {"provider": "muse", "model": self._settings.model}
        if not self._settings.api_key:
            return RuntimeHealth(descriptor=self.descriptor,
                status=RuntimeHealthStatus.FAILED, metadata=metadata,
                details="Muse API key is not configured")
        return RuntimeHealth(descriptor=self.descriptor,
            status=RuntimeHealthStatus.READY, metadata=metadata,
            details="Muse art runtime is configured")

    def cancel(self, request_id: str) -> Any:
        messages = load_message_types()
        with self._lock:
            self._cancelled.add(request_id)
            active = request_id in self._active
        return messages.ResponseEnvelope(
            request_id=request_id,
            status=messages.EnvelopeStatus.CANCELLED,
            metadata={
                "provider": "muse", "model": self._settings.model,
                "best_effort": True, "active": active,
            },
        )

    def close(self) -> None:
        close = getattr(self._session, "close", None)
        if callable(close):
            close()

    def _model_for(self, inv: Optional[ArtInvocationRequest]) -> str:
        if inv is not None and inv.model:
            return inv.model
        return self._settings.model

    def _generate(self, request_id: str, invocation: Any,
            progress_callback: Optional[ProgressCallback]) -> Any:
        if invocation is None:
            raise ValueError("Muse invocation payload is required")
        validate_muse_invocation(invocation)
        model = self._model_for(invocation)
        if not self._settings.api_key:
            return self._failure(request_id, "muse_auth_error",
                "Muse API key is not configured", False, model)
        return self._tracked(request_id, invocation, model, progress_callback)

    def _tracked(self, request_id: str, invocation: Any, model: str,
            cb: Optional[ProgressCallback]) -> Any:
        with self._lock:
            self._active.add(request_id)
        try:
            return self._run(request_id, invocation, model, cb)
        finally:
            with self._lock:
                self._active.discard(request_id)
                self._cancelled.discard(request_id)

    def _run(self, request_id: str, invocation: Any, model: str,
            cb: Optional[ProgressCallback]) -> Any:
        self._emit(cb, "running", 0.0)
        quota = self._quota_failure(request_id, invocation, model)
        if quota is not None:
            return quota
        try:
            images = post_images(
                self._session, self._settings, invocation, model
            )
        except MuseArtError as exc:
            return self._failure(
                request_id, exc.code, str(exc), exc.retryable, model
            )
        if self._is_cancelled(request_id):
            return self._cancelled_response(request_id, model)
        self._record_usage(request_id, model, len(images))
        self._emit(cb, "completed", 100.0)
        return self._success(request_id, images, model)

    def _quota_failure(self, request_id: str, invocation: Any,
            model: str) -> Any:
        try:
            self._ledger.enforce_limit(request_id, invocation.num_images)
        except MuseUsageLimitError:
            return self._failure(request_id, "muse_quota_exceeded",
                "Muse per-job image limit exceeded", False, model)
        return None

    def _record_usage(self, request_id: str, model: str, count: int) -> None:
        try:
            self._ledger.record(request_id, model, count)
        except MuseUsageLimitError:
            pass

    @property
    def usage_ledger(self) -> MuseUsageLedger:
        return self._ledger

    @staticmethod
    def _success(request_id: str, images: list[str], model: str) -> Any:
        messages = load_message_types()
        return messages.ResponseEnvelope(
            request_id=request_id,
            status=messages.EnvelopeStatus.SUCCEEDED,
            payload={"images": images},
            metadata={
                "provider": "muse", "model": model,
                "image_count": len(images),
            },
        )

    def _is_cancelled(self, request_id: str) -> bool:
        with self._lock:
            return request_id in self._cancelled

    def _cancelled_response(self, request_id: str, model: str) -> Any:
        messages = load_message_types()
        return messages.ResponseEnvelope(
            request_id=request_id,
            status=messages.EnvelopeStatus.CANCELLED,
            metadata={"provider": "muse", "model": model},
        )

    def _status_response(self, request_id: str) -> Any:
        messages = load_message_types()
        health = self.healthcheck()
        return messages.ResponseEnvelope(
            request_id=request_id,
            status=messages.EnvelopeStatus.SUCCEEDED,
            payload={"status": health.status.value},
            metadata=health.metadata,
        )

    @staticmethod
    def _emit(cb: Optional[ProgressCallback], st: str, p: float) -> None:
        if cb is None:
            return
        try:
            cb({"status": st, "progress": p})
        except Exception:
            return

    @staticmethod
    def _failure(request_id: str, code: str, message: str,
            retryable: bool, model: str) -> Any:
        messages = load_message_types()
        return messages.ResponseEnvelope(
            request_id=request_id,
            status=messages.EnvelopeStatus.FAILED,
            error=messages.ErrorEnvelope(
                code=code, message=message, retryable=retryable
            ),
            metadata={"provider": "muse", "model": model},
        )

def register_muse_art_client(registry: RuntimeRegistry,
        muse_client: Optional[RuntimeClient] = None) -> RuntimeRegistry:
    client = muse_client or MuseArtClient()
    provider = client.descriptor.provider
    route = RuntimeRoute(RuntimeKind.ART, provider=provider,
        deployment_mode=RuntimeMode.CLOUD.value)
    registry.register(route, client)
    return registry

__all__ = ["MuseArtClient", "MuseArtSettings", "register_muse_art_client"]
