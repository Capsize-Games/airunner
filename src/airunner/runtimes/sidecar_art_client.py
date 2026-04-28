"""HTTP runtime client for the supervised art sidecar."""

from __future__ import annotations

import base64
import threading
import time
from dataclasses import replace
from typing import Any, Optional

import requests

from airunner.ipc.messages import (
    EnvelopeStatus,
    ErrorEnvelope,
    RequestEnvelope,
    ResponseEnvelope,
)
from airunner.runtimes.art_daemon_runtime_settings import (
    ArtDaemonRuntimeSettings,
    resolve_art_daemon_runtime_settings,
)
from airunner.runtimes.base import RuntimeClient
from airunner.runtimes.contracts import (
    ArtInvocationRequest,
    RuntimeAction,
    RuntimeDescriptor,
    RuntimeHealth,
    RuntimeKind,
    RuntimeMode,
    TransportKind,
)
from airunner.runtimes.registry import RuntimeRegistry, RuntimeRoute
from airunner.runtimes.sidecar_art_launcher import SidecarArtLauncher

DEFAULT_PROVIDER = "local"


class SidecarArtClient(RuntimeClient):
    """Route art envelopes through one supervised sidecar daemon."""

    def __init__(
        self,
        provider: str = DEFAULT_PROVIDER,
        *,
        settings: Optional[ArtDaemonRuntimeSettings] = None,
        launcher: Optional[SidecarArtLauncher] = None,
        session: Optional[requests.Session] = None,
    ) -> None:
        resolved_settings = settings or resolve_art_daemon_runtime_settings()
        self._base_settings = resolved_settings
        self._settings = resolved_settings
        self._launcher = launcher or SidecarArtLauncher(resolved_settings)
        self._managed_launcher = launcher is None
        self._session = session or requests.Session()
        self._active_jobs: dict[str, str] = {}
        self._active_jobs_lock = threading.Lock()
        self._invoke_lock = threading.Lock()
        self.descriptor = RuntimeDescriptor(
            runtime=RuntimeKind.ART,
            provider=provider,
            mode=RuntimeMode.SIDECAR,
            transport=TransportKind.HTTP,
            endpoint=resolved_settings.endpoint,
            supports_streaming=False,
            allows_model_control=True,
        )

    def invoke(self, request: RequestEnvelope) -> ResponseEnvelope:
        """Invoke one sidecar control action or art request."""
        if request.runtime is not RuntimeKind.ART:
            raise ValueError("SidecarArtClient only supports art")
        if request.action is RuntimeAction.STATUS:
            return self._status_response(request.request_id)
        if request.action is RuntimeAction.LOAD_MODEL:
            return self._load_runtime(request.request_id)
        if request.action is RuntimeAction.UNLOAD_MODEL:
            return self._unload_runtime(request.request_id)
        if request.action is not RuntimeAction.INVOKE:
            raise ValueError("SidecarArtClient only supports invoke")
        return self._generate_image(request)

    def healthcheck(self) -> RuntimeHealth:
        """Return the health of the managed art runtime."""
        status, details = self._launcher.health_status()
        return RuntimeHealth(
            descriptor=self.descriptor,
            status=status,
            details=details,
            metadata=self._metadata(),
        )

    def cancel(self, request_id: str) -> ResponseEnvelope:
        """Cancel an active art job on a best-effort basis."""
        job_id = self._untrack_job(request_id)
        if job_id is not None:
            try:
                self._request("DELETE", f"/cancel/{job_id}")
            except RuntimeError:
                pass
        return ResponseEnvelope(
            request_id=request_id,
            status=EnvelopeStatus.CANCELLED,
            metadata={"best_effort": True, **self._metadata()},
        )

    def close(self) -> None:
        """Release the managed sidecar process during shutdown."""
        self._launcher.stop()
        close = getattr(self._session, "close", None)
        if close is not None:
            close()

    def _status_response(self, request_id: str) -> ResponseEnvelope:
        """Return a neutral status envelope for runtime control callers."""
        health = self.healthcheck()
        return ResponseEnvelope(
            request_id=request_id,
            status=EnvelopeStatus.SUCCEEDED,
            payload={"status": health.status.value},
            metadata=health.metadata,
        )

    def _load_runtime(self, request_id: str) -> ResponseEnvelope:
        """Start the managed art daemon."""
        try:
            self._ensure_launcher(self._settings)
            self._launcher.start()
        except RuntimeError as exc:
            return self._failure_response(
                request_id,
                "art_load_failed",
                str(exc),
            )
        return ResponseEnvelope(
            request_id=request_id,
            status=EnvelopeStatus.SUCCEEDED,
            payload={"model_status": "loaded"},
            metadata=self._metadata(),
        )

    def _unload_runtime(self, request_id: str) -> ResponseEnvelope:
        """Stop the managed art daemon."""
        self._launcher.stop()
        return ResponseEnvelope(
            request_id=request_id,
            status=EnvelopeStatus.SUCCEEDED,
            payload={"model_status": "unloaded"},
            metadata=self._metadata(),
        )

    def _generate_image(self, request: RequestEnvelope) -> ResponseEnvelope:
        """Execute an art request through the supervised sidecar daemon."""
        invocation = ArtInvocationRequest.model_validate(request.payload)
        with self._invoke_lock:
            try:
                settings = self._settings_for_invocation(invocation)
                self._ensure_launcher(settings)
                self._launcher.start()
                job_id = self._submit_job(invocation)
                self._track_job(request.request_id, job_id)
                status, payload, error = self._wait_for_job(job_id)
            except RuntimeError as exc:
                return self._runtime_error_response(request.request_id, str(exc))
            finally:
                self._untrack_job(request.request_id)

        if status is EnvelopeStatus.CANCELLED:
            return ResponseEnvelope(
                request_id=request.request_id,
                status=EnvelopeStatus.CANCELLED,
                metadata={"job_id": job_id, **self._metadata()},
            )
        if status is EnvelopeStatus.FAILED:
            return self._runtime_error_response(
                request.request_id,
                error or "Art generation failed",
            )
        return ResponseEnvelope(
            request_id=request.request_id,
            status=EnvelopeStatus.SUCCEEDED,
            payload=payload,
            metadata={"job_id": job_id, **self._metadata()},
        )

    def _settings_for_invocation(
        self,
        invocation: ArtInvocationRequest,
    ) -> ArtDaemonRuntimeSettings:
        """Return sidecar settings adjusted for one art invocation."""
        metadata = invocation.metadata
        return replace(
            self._base_settings,
            art_model_path=invocation.model or self._base_settings.art_model_path,
            art_model_version=(
                metadata.get("version")
                or self._base_settings.art_model_version
            ),
            art_scheduler=(
                metadata.get("scheduler")
                or self._base_settings.art_scheduler
            ),
        )

    def _ensure_launcher(self, settings: ArtDaemonRuntimeSettings) -> None:
        """Refresh the managed launcher when request settings change."""
        if not self._managed_launcher:
            self._settings = settings
            return
        if settings == self._settings:
            return
        self._launcher.stop()
        self._settings = settings
        self._launcher = SidecarArtLauncher(settings)

    def _submit_job(self, invocation: ArtInvocationRequest) -> str:
        """Start one remote art job and return its job identifier."""
        payload = {
            "prompt": invocation.prompt,
            "negative_prompt": invocation.negative_prompt,
            "width": invocation.width,
            "height": invocation.height,
            "steps": invocation.steps,
            "cfg_scale": invocation.cfg_scale,
            "seed": invocation.seed,
            "num_images": invocation.num_images,
        }
        response = self._request("POST", "/generate", json_payload=payload)
        job_id = str(response.get("job_id", "") or "")
        if not job_id:
            raise RuntimeError("Art runtime did not return a job id")
        return job_id

    def _wait_for_job(
        self,
        job_id: str,
    ) -> tuple[EnvelopeStatus, dict[str, Any], Optional[str]]:
        """Poll the remote art job until it completes or fails."""
        deadline = self._deadline()
        while time.monotonic() < deadline:
            response = self._request("GET", f"/status/{job_id}")
            status = str(response.get("status", "")).lower()
            if status == "completed":
                return EnvelopeStatus.SUCCEEDED, self._result_payload(job_id), None
            if status == "failed":
                message = response.get("error") or "Art generation failed"
                return EnvelopeStatus.FAILED, {}, str(message)
            if status == "cancelled":
                return EnvelopeStatus.CANCELLED, {}, None
            time.sleep(self._settings.status_poll_interval_seconds)
        self._best_effort_cancel(job_id)
        return EnvelopeStatus.FAILED, {}, "Timed out waiting for art response"

    def _result_payload(self, job_id: str) -> dict[str, Any]:
        """Download one remote art result and encode it as base64 PNG."""
        image_bytes = self._request(
            "GET",
            f"/result/{job_id}",
            expect_json=False,
        )
        return {
            "images": [base64.b64encode(image_bytes).decode("ascii")],
            "image_count": 1,
        }

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_payload: Optional[dict[str, Any]] = None,
        expect_json: bool = True,
    ) -> Any:
        """Perform one HTTP request against the sidecar daemon."""
        url = f"{self._launcher.api_base_url}{path}"
        try:
            response = self._session.request(
                method,
                url,
                json=json_payload,
                timeout=self._settings.request_timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(self._request_error_message(exc)) from exc
        if expect_json:
            return response.json()
        return response.content

    def _deadline(self) -> float:
        """Return the absolute deadline for one remote art invocation."""
        return time.monotonic() + self._settings.invocation_timeout_seconds

    def _best_effort_cancel(self, job_id: str) -> None:
        """Attempt to cancel one remote job without surfacing failures."""
        try:
            self._request("DELETE", f"/cancel/{job_id}")
        except RuntimeError:
            return

    def _track_job(self, request_id: str, job_id: str) -> None:
        """Track one active job for cancellation."""
        with self._active_jobs_lock:
            self._active_jobs[request_id] = job_id

    def _untrack_job(self, request_id: str) -> Optional[str]:
        """Remove and return one active job mapping when it exists."""
        with self._active_jobs_lock:
            return self._active_jobs.pop(request_id, None)

    def _metadata(self) -> dict[str, Any]:
        """Return stable sidecar metadata for health and control responses."""
        metadata = {
            "endpoint": self._launcher.endpoint,
            "art_api_url": self._launcher.api_base_url,
        }
        if self._settings.art_model_path:
            metadata["model_path"] = self._settings.art_model_path
        if self._settings.art_model_version:
            metadata["model_version"] = self._settings.art_model_version
        if self._settings.art_scheduler:
            metadata["scheduler"] = self._settings.art_scheduler
        return metadata

    @staticmethod
    def _request_error_message(error: requests.RequestException) -> str:
        """Return a useful message extracted from one request failure."""
        response = getattr(error, "response", None)
        if response is not None and getattr(response, "text", ""):
            return str(response.text)
        return str(error)

    @staticmethod
    def _failure_response(
        request_id: str,
        code: str,
        message: str,
        *,
        retryable: bool = False,
    ) -> ResponseEnvelope:
        """Return a normalized failure envelope."""
        return ResponseEnvelope(
            request_id=request_id,
            status=EnvelopeStatus.FAILED,
            error=ErrorEnvelope(
                code=code,
                message=message,
                retryable=retryable,
            ),
        )

    def _runtime_error_response(
        self,
        request_id: str,
        message: str,
    ) -> ResponseEnvelope:
        """Return a runtime failure response inferred from one message."""
        if "Timed out" in message:
            return self._failure_response(
                request_id,
                "art_timeout",
                message,
                retryable=True,
            )
        return self._failure_response(
            request_id,
            "art_invoke_failed",
            message,
            retryable=True,
        )


def register_sidecar_art_client(
    registry: RuntimeRegistry,
    art_client: Optional[RuntimeClient] = None,
) -> RuntimeRegistry:
    """Register the sidecar-backed art client under the sidecar route."""
    client = art_client or SidecarArtClient()
    registry.register(
        RuntimeRoute(
            RuntimeKind.ART,
            provider=client.descriptor.provider,
            deployment_mode=RuntimeMode.SIDECAR.value,
        ),
        client,
    )
    return registry