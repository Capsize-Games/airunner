"""Synchronous HTTP client for the daemon's video API (MCP side)."""

from __future__ import annotations

import time
from typing import Any

import httpx

from airunner_services.mcp.config import MCPConfig
from airunner_services.mcp.daemon_client import DaemonError

_TERMINAL_OK = "completed"
_TERMINAL_BAD = ("failed", "cancelled")


class VideoDaemonClient:
    """Thin wrapper over /api/v1/video (no model code here)."""

    def __init__(self, config: MCPConfig,
                 transport: httpx.BaseTransport | None = None) -> None:
        headers = {"Accept": "application/json"}
        if config.api_key:
            headers["Authorization"] = f"Bearer {config.api_key}"
        self._config = config
        self._http = httpx.Client(
            base_url=config.daemon_url, headers=headers,
            timeout=max(config.request_timeout_s, 30.0),
            transport=transport,
        )

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
        response = self._http.post("/api/v1/video/generate",
                                   json=payload)
        body = self._checked(response)
        job_id = str((body or {}).get("job_id", ""))
        if not job_id or "/" in job_id:
            raise DaemonError(f"daemon returned a bad job id: {job_id!r}")
        return job_id

    def get_status(self, job_id: str) -> dict[str, Any]:
        """Return one job's status payload."""
        return dict(self._checked(
            self._http.get(f"/api/v1/video/status/{job_id}")))

    def fetch_mp4(self, job_id: str) -> bytes:
        """Return MP4 bytes for a completed job."""
        response = self._http.get(f"/api/v1/video/result/{job_id}")
        if response.status_code >= 400:
            raise DaemonError(
                f"result unavailable ({response.status_code})",
                status_code=response.status_code,
            )
        return response.content

    def cancel(self, job_id: str) -> dict[str, Any]:
        """Cancel one job (best-effort)."""
        return dict(self._checked(
            self._http.delete(f"/api/v1/video/cancel/{job_id}")))

    def list_models(self) -> Any:
        """Return installed video checkpoints."""
        return self._checked(self._http.get("/api/v1/video/models"))

    def wait_for_completion(self, job_id: str,
                            timeout_s: float = 900.0,
                            poll_s: float = 5.0) -> dict[str, Any]:
        """Poll until completed/failed or the timeout elapses."""
        deadline = time.monotonic() + timeout_s
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
            time.sleep(poll_s)
