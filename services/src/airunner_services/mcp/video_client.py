"""Synchronous HTTP client for the daemon's video API (MCP side)."""

from __future__ import annotations

import time
from typing import Any

import httpx

from airunner_services.mcp.config import MCPConfig
from airunner_services.mcp.daemon_client import (
    DaemonError,
    _loopback_token_header,
)

_TERMINAL_OK = "completed"
_TERMINAL_BAD = ("failed", "cancelled")


class VideoDaemonClient:
    """Thin wrapper over /api/v1/video (no model code here)."""

    def __init__(
        self, config: MCPConfig, transport: httpx.BaseTransport | None = None
    ) -> None:
        """Build a video client with the daemon's configured auth and timeout."""
        headers = {"Accept": "application/json"}
        if config.api_key:
            headers["Authorization"] = f"Bearer {config.api_key}"
        headers.update(
            _loopback_token_header(config.daemon_url, config.api_key)
        )
        self._config = config
        self._http = httpx.Client(
            base_url=config.daemon_url,
            headers=headers,
            timeout=config.request_timeout_s,
            transport=transport,
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Send one daemon request and translate transport errors."""
        try:
            return self._http.request(method, path, json=json)
        except httpx.HTTPError as exc:
            raise DaemonError(f"daemon unreachable: {exc}") from exc

    def _checked(self, response: httpx.Response) -> Any:
        if response.status_code >= 400:
            raise DaemonError(
                f"daemon refused {response.status_code}: "
                f"{response.text[:200]}",
                status_code=response.status_code,
            )
        return response.json()

    def start_video(self, payload: dict[str, Any]) -> str:
        """POST /generate and return the job id."""
        body = self._checked(
            self._request("POST", "/api/v1/video/generate", json=payload)
        )
        raw_job_id = (body or {}).get("job_id", "")
        job_id = str(raw_job_id) if raw_job_id else ""
        if not job_id or "/" in job_id or "\\" in job_id:
            raise DaemonError(f"daemon returned a bad job id: {job_id!r}")
        return job_id

    def get_status(self, job_id: str) -> dict[str, Any]:
        """Return one job's status payload."""
        self._checked_job_id(job_id)
        return dict(
            self._checked(
                self._request("GET", f"/api/v1/video/status/{job_id}")
            )
        )

    def fetch_mp4(self, job_id: str) -> bytes:
        """Return MP4 bytes for a completed job."""
        self._checked_job_id(job_id)
        response = self._request("GET", f"/api/v1/video/result/{job_id}")
        if response.status_code >= 400:
            raise DaemonError(
                f"result unavailable ({response.status_code})",
                status_code=response.status_code,
            )
        return response.content

    def cancel(self, job_id: str) -> dict[str, Any]:
        """Cancel one job (best-effort)."""
        self._checked_job_id(job_id)
        return dict(
            self._checked(
                self._request("DELETE", f"/api/v1/video/cancel/{job_id}")
            )
        )

    def list_models(self) -> Any:
        """Return installed video checkpoints."""
        return self._checked(self._request("GET", "/api/v1/video/models"))

    def wait_for_completion(self, job_id: str) -> dict[str, Any]:
        """Poll until completed/failed or the timeout elapses."""
        self._checked_job_id(job_id)
        deadline = time.monotonic() + self._config.generation_timeout_s
        while True:
            status = self.get_status(job_id)
            state = str(status.get("status", ""))
            if state == _TERMINAL_OK:
                return status
            if state in _TERMINAL_BAD:
                raise DaemonError(
                    f"video job {state}: {status.get('error') or ''}"
                )
            if time.monotonic() >= deadline:
                raise DaemonError(f"video job timed out: {job_id}")
            time.sleep(self._config.poll_interval_s)

    def _checked_job_id(self, job_id: str) -> None:
        """Reject empty or path-like job ids before sending a request."""
        if not job_id or "/" in job_id or "\\" in job_id:
            raise DaemonError(f"bad job id: {job_id!r}")
