"""Synchronous HTTP client for the daemon's public art API."""

from __future__ import annotations

import threading
import time
from typing import Any, Callable
from urllib.parse import urlparse

import httpx

from airunner_services.mcp.config import MCPConfig

_TERMINAL_OK = "completed"
_TERMINAL_BAD = ("failed", "cancelled")

_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}
_HEALTH_PROBE_TIMEOUT_S = 2.0
_HEALTH_POLL_INTERVAL_S = 0.5


class DaemonError(Exception):
    """Raised when the daemon rejects a call or a job fails."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        """Store the message plus the HTTP status when there is one."""
        super().__init__(message)
        self.status_code = status_code


def is_loopback_url(url: str) -> bool:
    """Return True when the URL targets this host (safe to auto-start)."""
    try:
        host = (urlparse(url).hostname or "").strip().lower()
    except ValueError:
        return False
    return host in _LOOPBACK_HOSTS


LauncherFactory = Callable[[], Any]


def _default_launcher_factory() -> Any:
    """Build the standard local daemon launcher (imported lazily)."""
    from airunner_services.daemon_client.launcher import DaemonLauncher

    return DaemonLauncher()


def _loopback_token_header(url: str, api_key: str) -> dict[str, str]:
    """Return the loopback token header for loopback daemon URLs."""
    if api_key or not is_loopback_url(url):
        return {}
    try:
        from airunner_services.api.loopback_token import (
            get_or_create_loopback_token,
        )

        token = get_or_create_loopback_token()
    except Exception:
        return {}
    return {"X-Airunner-Token": token} if token else {}


class ArtDaemonClient:
    """Thin wrapper over the daemon art routes (no model code here)."""

    def __init__(
        self,
        config: MCPConfig,
        transport: httpx.BaseTransport | None = None,
        launcher_factory: LauncherFactory | None = None,
    ) -> None:
        """Build a loopback-first client; transport is for tests."""
        headers = {"Accept": "application/json"}
        if config.api_key:
            headers["Authorization"] = f"Bearer {config.api_key}"
        headers.update(_loopback_token_header(config.daemon_url, config.api_key))
        self._config = config
        self._http = httpx.Client(
            base_url=config.daemon_url,
            headers=headers,
            timeout=config.request_timeout_s,
            transport=transport,
        )
        self._launcher_factory = launcher_factory or _default_launcher_factory
        self._start_lock = threading.Lock()

    def _post(self, path: str, body: dict[str, Any]) -> Any:
        """POST JSON and return the decoded payload or raise."""
        try:
            response = self._http.post(path, json=body)
        except httpx.HTTPError as exc:
            raise self._maybe_autostart(exc)
        return self._checked(response)

    def _get(self, path: str) -> Any:
        """GET and return the decoded payload or raise."""
        try:
            response = self._http.get(path)
        except httpx.HTTPError as exc:
            raise self._maybe_autostart(exc)
        return self._checked(response)

    def _checked(self, response: httpx.Response) -> Any:
        """Raise DaemonError on error statuses, else decode JSON."""
        if response.status_code >= 400:
            hint = ""
            if response.status_code == 401 and ":8080" in self._config.daemon_url:
                hint = (
                    " [hint: :8080 is the engine daemon (Bearer auth); "
                    "the desktop daemon for MCP is :8188 with loopback-token "
                    "auth — set AIRUNNER_DAEMON_URL=http://127.0.0.1:8188 "
                    "and remove AIRUNNER_API_KEY]"
                )
            raise DaemonError(
                f"daemon refused {response.status_code}: "
                f"{response.text[:200]}{hint}",
                status_code=response.status_code,
            )
        return response.json()

    def _maybe_autostart(self, exc: httpx.HTTPError) -> DaemonError:
        """Start a local daemon after a connection failure, then report."""
        original = DaemonError(f"daemon unreachable: {exc}")
        if not isinstance(exc, httpx.ConnectError):
            return original
        if not self._config.auto_start_daemon:
            return original
        if not is_loopback_url(self._config.daemon_url):
            return original
        try:
            self.ensure_daemon_running()
        except DaemonError as start_exc:
            return start_exc
        # The caller retries the failed request once after a start.
        started = DaemonError(
            "daemon was not running; started it, retry your request"
        )
        started.__cause__ = exc
        return started

    def ensure_daemon_running(self) -> None:
        """Start the local daemon when it is not reachable, then wait."""
        if self._is_reachable():
            return
        if not self._config.auto_start_daemon:
            raise DaemonError(
                "daemon unreachable: auto-start is disabled "
                "(AIRUNNER_MCP_AUTO_START_DAEMON=0)"
            )
        if not is_loopback_url(self._config.daemon_url):
            raise DaemonError(
                "daemon unreachable: auto-start only supports loopback "
                f"daemon URLs ({self._config.daemon_url})"
            )
        with self._start_lock:
            if self._is_reachable():
                return
            self._launch_and_wait()

    def _is_reachable(self) -> bool:
        """Return True when any HTTP response arrives from the daemon."""
        try:
            self._http.get("/health", timeout=_HEALTH_PROBE_TIMEOUT_S)
        except httpx.HTTPError:
            return False
        return True

    def _launch_and_wait(self) -> None:
        """Launch one daemon subprocess and wait for its health endpoint."""
        try:
            launcher = self._launcher_factory()
            launcher.start()
        except Exception as exc:
            raise DaemonError(
                f"daemon auto-start failed: {exc}"
            ) from exc
        deadline = (
            time.monotonic() + self._config.daemon_startup_timeout_s
        )
        while True:
            if self._is_reachable():
                return
            if time.monotonic() >= deadline:
                raise DaemonError(
                    "daemon auto-start timed out waiting for "
                    f"{self._config.daemon_url}/health"
                )
            time.sleep(_HEALTH_POLL_INTERVAL_S)

    def start_generation(self, payload: dict[str, Any]) -> str:
        """Start one art job and return its job id."""
        try:
            body = self._post("/api/v1/art/generate", payload)
        except DaemonError as exc:
            body = self._retry_after_autostart(
                exc, lambda: self._post("/api/v1/art/generate", payload)
            )
        job_id = (body or {}).get("job_id", "")
        if not job_id or "/" in job_id:
            raise DaemonError(f"daemon returned a bad job id: {job_id!r}")
        return str(job_id)

    def get_status(self, job_id: str) -> dict[str, Any]:
        """Return the tracked status payload for one job."""
        self._checked_job_id(job_id)
        try:
            return dict(self._get(f"/api/v1/art/status/{job_id}"))
        except DaemonError as exc:
            return dict(
                self._retry_after_autostart(
                    exc,
                    lambda: self._get(f"/api/v1/art/status/{job_id}"),
                )
            )

    def fetch_png(self, job_id: str, index: int = 0) -> bytes:
        """Return PNG bytes for one finished batch image."""
        self._checked_job_id(job_id)
        if index < 0:
            raise DaemonError(f"bad image index: {index}")
        try:
            return self._fetch_png_once(job_id, index)
        except DaemonError as exc:
            return self._retry_after_autostart(
                exc, lambda: self._fetch_png_once(job_id, index)
            )

    def _fetch_png_once(self, job_id: str, index: int) -> bytes:
        """Perform one PNG fetch without auto-start retry handling."""
        try:
            response = self._http.get(
                f"/api/v1/art/result/{job_id}/{index}"
            )
        except httpx.HTTPError as exc:
            raise self._maybe_autostart(exc)
        if response.status_code >= 400:
            raise DaemonError(
                f"result unavailable ({response.status_code}): "
                f"{response.text[:200]}",
                status_code=response.status_code,
            )
        return response.content

    def remove_background(self, image_b64: str) -> bytes:
        """Return PNG bytes with the background removed."""
        try:
            return self._remove_background_once(image_b64)
        except DaemonError as exc:
            return self._retry_after_autostart(
                exc, lambda: self._remove_background_once(image_b64)
            )

    def _remove_background_once(self, image_b64: str) -> bytes:
        """Perform one background-removal call without retry handling."""
        try:
            response = self._http.post(
                "/api/v1/art/remove-background",
                json={"image_b64": image_b64},
            )
        except httpx.HTTPError as exc:
            raise self._maybe_autostart(exc)
        if response.status_code >= 400:
            raise DaemonError(
                f"background removal failed "
                f"({response.status_code}): "
                f"{response.text[:200]}",
                status_code=response.status_code,
            )
        return response.content

    def cancel_job(self, job_id: str) -> dict[str, Any]:
        """Cancel one job; the daemon call is best-effort."""
        self._checked_job_id(job_id)
        try:
            return dict(self._cancel_job_once(job_id))
        except DaemonError as exc:
            return dict(
                self._retry_after_autostart(
                    exc, lambda: self._cancel_job_once(job_id)
                )
            )

    def _cancel_job_once(self, job_id: str) -> Any:
        """Perform one job cancellation without retry handling."""
        try:
            response = self._http.delete(f"/api/v1/art/cancel/{job_id}")
        except httpx.HTTPError as exc:
            raise self._maybe_autostart(exc)
        return self._checked(response)

    def list_models(self) -> dict[str, Any]:
        """Return installed art models usable as generate_image input."""
        try:
            return dict(self._get("/api/v1/art/models"))
        except DaemonError as exc:
            return dict(
                self._retry_after_autostart(
                    exc, lambda: self._get("/api/v1/art/models")
                )
            )

    def list_registry_models(self) -> list[Any]:
        """Return catalog registry entries with loaded flags."""
        try:
            return list(self._get("/api/v1/art/models/registry"))
        except DaemonError as exc:
            return list(
                self._retry_after_autostart(
                    exc, lambda: self._get("/api/v1/art/models/registry")
                )
            )

    def _retry_after_autostart(
        self, exc: DaemonError, retry: Callable[[], Any]
    ) -> Any:
        """Retry one call after an auto-start, else re-raise the error."""
        if "started it, retry your request" not in str(exc):
            raise exc
        return retry()

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
