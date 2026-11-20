"""Synchronous HTTP client for the daemon's public art API."""

from __future__ import annotations

import time
from typing import Any

import httpx

from airunner_services.mcp.config import MCPConfig

_TERMINAL_OK = "completed"
_TERMINAL_BAD = ("failed", "cancelled")


class DaemonError(Exception):
    """Raised when the daemon rejects a call or a job fails."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        """Store the message plus the HTTP status when there is one."""
        super().__init__(message)
        self.status_code = status_code


class ArtDaemonClient:
    """Thin wrapper over the daemon art routes (no model code here)."""

    def __init__(
        self,
        config: MCPConfig,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        """Build a loopback-first client; transport is for tests."""
        headers = {"Accept": "application/json"}
        if config.api_key:
            headers["Authorization"] = f"Bearer {config.api_key}"
        self._config = config
        self._http = httpx.Client(
            base_url=config.daemon_url,
            headers=headers,
            timeout=config.request_timeout_s,
            transport=transport,
        )

    def _post(self, path: str, body: dict[str, Any]) -> Any:
        """POST JSON and return the decoded payload or raise."""
        try:
            response = self._http.post(path, json=body)
        except httpx.HTTPError as exc:
            raise DaemonError(f"daemon unreachable: {exc}") from exc
        return self._checked(response)

    def _get(self, path: str) -> Any:
        """GET and return the decoded payload or raise."""
        try:
            response = self._http.get(path)
        except httpx.HTTPError as exc:
            raise DaemonError(f"daemon unreachable: {exc}") from exc
        return self._checked(response)

    def _checked(self, response: httpx.Response) -> Any:
        """Raise DaemonError on error statuses, else decode JSON."""
        if response.status_code >= 400:
            raise DaemonError(
                f"daemon refused {response.status_code}: "
                f"{response.text[:200]}",
                status_code=response.status_code,
            )
        return response.json()

    def start_generation(self, payload: dict[str, Any]) -> str:
        """Start one art job and return its job id."""
        body = self._post("/api/v1/art/generate", payload)
        job_id = (body or {}).get("job_id", "")
        if not job_id or "/" in job_id:
            raise DaemonError(f"daemon returned a bad job id: {job_id!r}")
        return str(job_id)

    def get_status(self, job_id: str) -> dict[str, Any]:
        """Return the tracked status payload for one job."""
        self._checked_job_id(job_id)
        return dict(self._get(f"/api/v1/art/status/{job_id}"))

    def fetch_png(self, job_id: str, index: int = 0) -> bytes:
        """Return PNG bytes for one finished batch image."""
        self._checked_job_id(job_id)
        if index < 0:
            raise DaemonError(f"bad image index: {index}")
        try:
            response = self._http.get(
                f"/api/v1/art/result/{job_id}/{index}"
            )
        except httpx.HTTPError as exc:
            raise DaemonError(f"daemon unreachable: {exc}") from exc
        if response.status_code >= 400:
            raise DaemonError(
                f"result unavailable ({response.status_code}): "
                f"{response.text[:200]}",
                status_code=response.status_code,
            )
        return response.content

    def cancel_job(self, job_id: str) -> dict[str, Any]:
        """Cancel one job; the daemon call is best-effort."""
        self._checked_job_id(job_id)
        try:
            response = self._http.delete(f"/api/v1/art/cancel/{job_id}")
        except httpx.HTTPError as exc:
            raise DaemonError(f"daemon unreachable: {exc}") from exc
        return dict(self._checked(response))

    def list_models(self) -> dict[str, Any]:
        """Return installed art models usable as generate_image input."""
        return dict(self._get("/api/v1/art/models"))

    def list_registry_models(self) -> list[Any]:
        """Return catalog registry entries with loaded flags."""
        return list(self._get("/api/v1/art/models/registry"))

    def wait_for_completion(self, job_id: str) -> dict[str, Any]:
        """Poll until the job completes, fails, or the timeout hits."""
        self._checked_job_id(job_id)
        deadline = time.monotonic() + self._config.generation_timeout_s
        while True:
            status = self.get_status(job_id)
            state = str(status.get("status", ""))
            if state == _TERMINAL_OK:
                return status
            if state in _TERMINAL_BAD:
                raise DaemonError(
                    f"job {job_id} ended with status {state}: "
                    f"{str(status.get('error') or '')[:200]}"
                )
            if time.monotonic() >= deadline:
                raise DaemonError(f"timed out waiting for job {job_id}")
            time.sleep(self._config.poll_interval_s)

    def _checked_job_id(self, job_id: str) -> None:
        """Reject empty or path-like job ids before any HTTP call."""
        if not job_id or "/" in job_id or "\\" in job_id:
            raise DaemonError(f"bad job id: {job_id!r}")

    def close(self) -> None:
        """Release the underlying HTTP connection pool."""
        self._http.close()
