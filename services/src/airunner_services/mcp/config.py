"""Environment-based configuration for the MCP server."""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_DAEMON_URL = "http://127.0.0.1:8188"
DEFAULT_REQUEST_TIMEOUT_S = 30.0
DEFAULT_GENERATION_TIMEOUT_S = 600.0
DEFAULT_POLL_INTERVAL_S = 2.0
DEFAULT_OUTPUT_DIR = "~/.local/share/airunner/mcp-images"
DEFAULT_AUTO_START_DAEMON = True
DEFAULT_DAEMON_STARTUP_TIMEOUT_S = 90.0


def _parse_float(raw: str | None, default: float) -> float:
    """Return the parsed float or the default when missing/invalid."""
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def _parse_bool(raw: str | None, default: bool) -> bool:
    """Return the parsed bool or the default when missing/invalid."""
    if raw is None or not str(raw).strip():
        return default
    value = str(raw).strip().lower()
    if value in ("1", "true", "yes", "on"):
        return True
    if value in ("0", "false", "no", "off"):
        return False
    return default


@dataclass(frozen=True)
class MCPConfig:
    """Runtime settings for the image-generation MCP server."""

    daemon_url: str = DEFAULT_DAEMON_URL
    api_key: str = ""
    request_timeout_s: float = DEFAULT_REQUEST_TIMEOUT_S
    generation_timeout_s: float = DEFAULT_GENERATION_TIMEOUT_S
    poll_interval_s: float = DEFAULT_POLL_INTERVAL_S
    output_dir: str = DEFAULT_OUTPUT_DIR
    auto_start_daemon: bool = DEFAULT_AUTO_START_DAEMON
    daemon_startup_timeout_s: float = DEFAULT_DAEMON_STARTUP_TIMEOUT_S

    @classmethod
    def from_env(cls) -> MCPConfig:
        """Build configuration from environment with safe defaults."""
        return cls(
            daemon_url=os.environ.get(
                "AIRUNNER_DAEMON_URL", DEFAULT_DAEMON_URL
            ).rstrip("/"),
            api_key=os.environ.get("AIRUNNER_API_KEY", ""),
            request_timeout_s=_parse_float(
                os.environ.get("AIRUNNER_MCP_REQUEST_TIMEOUT_S"),
                DEFAULT_REQUEST_TIMEOUT_S,
            ),
            generation_timeout_s=_parse_float(
                os.environ.get("AIRUNNER_MCP_GENERATION_TIMEOUT_S"),
                DEFAULT_GENERATION_TIMEOUT_S,
            ),
            poll_interval_s=_parse_float(
                os.environ.get("AIRUNNER_MCP_POLL_INTERVAL_S"),
                DEFAULT_POLL_INTERVAL_S,
            ),
            output_dir=os.environ.get(
                "AIRUNNER_MCP_OUTPUT_DIR", DEFAULT_OUTPUT_DIR
            ),
            auto_start_daemon=_parse_bool(
                os.environ.get("AIRUNNER_MCP_AUTO_START_DAEMON"),
                DEFAULT_AUTO_START_DAEMON,
            ),
            daemon_startup_timeout_s=_parse_float(
                os.environ.get("AIRUNNER_MCP_DAEMON_STARTUP_TIMEOUT_S"),
                DEFAULT_DAEMON_STARTUP_TIMEOUT_S,
            ),
        )
