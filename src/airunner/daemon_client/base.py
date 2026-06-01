"""Base daemon HTTP client — connection, health checks, and request
infrastructure shared by all domain mixins.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, Optional

import requests

from airunner.runtimes.daemon_config import DaemonConfig
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger


class _DaemonClientBase:
    """Core connection and low-level HTTP helpers for the GUI daemon
    client.  Domain-specific endpoints live in separate mixin classes.
    """

    def __init__(
        self,
        config_path: Optional[Path] = None,
        *,
        session: Optional[requests.Session] = None,
        poll_interval_seconds: float = 0.25,
        request_timeout_seconds: float = 30.0,
        time_fn: Callable[[], float] = None,
        sleep: Callable[[float], None] = None,
    ) -> None:
        import time as _time

        self.config = DaemonConfig(config_path)
        self._session = session or requests.Session()
        self._poll_interval_seconds = poll_interval_seconds
        self._request_timeout_seconds = request_timeout_seconds
        self._time_fn = time_fn or _time.monotonic
        self._sleep = sleep or _time.sleep
        self.logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    @property
    def base_url(self) -> str:
        """Return the configured daemon base URL."""
        server = self.config.config.get("server", {})
        host = server.get("host", "127.0.0.1")
        port = server.get("port", 8188)
        return f"http://{host}:{port}"

    def is_available(self, *, timeout_seconds: float = 0.2) -> bool:
        """Return True when the daemon health endpoint responds."""
        return self._healthcheck_payload(
            timeout_seconds=timeout_seconds,
        ) is not None

    def health_check(self) -> Dict[str, Any]:
        """Return the daemon health payload."""
        response = self._request("GET", "/api/v1/health")
        return response.json()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _healthcheck_payload(
        self, *, timeout_seconds: float = 5.0
    ) -> Optional[Dict[str, Any]]:
        """Return the daemon /health payload when it is reachable."""
        try:
            response = self._session.request(
                "GET",
                f"{self.base_url}/api/v1/health",
                timeout=timeout_seconds,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            return None

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_payload: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        stream: bool = False,
        timeout_seconds: Optional[float] = None,
    ) -> requests.Response:
        """Perform an HTTP request against the daemon.

        Raises RuntimeError when the daemon is unreachable or the
        request fails.
        """
        try:
            response = self._session.request(
                method,
                f"{self.base_url}{path}",
                json=json_payload,
                files=files,
                headers=headers,
                stream=stream,
                timeout=timeout_seconds or self._request_timeout_seconds,
            )
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            raise RuntimeError(str(exc)) from exc
