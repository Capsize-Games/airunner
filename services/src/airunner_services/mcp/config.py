"""Environment-based configuration for the MCP server."""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_DAEMON_URL = "http://127.0.0.1:8080"
DEFAULT_REQUEST_TIMEOUT_S = 30.0
DEFAULT_GENERATION_TIMEOUT_S = 600.0
DEFAULT_POLL_INTERVAL_S = 2.0
DEFAULT_OUTPUT_DIR = "~/.local/share/airunner/mcp-images"


def _parse_float(raw: str | None, default: float) -> float:
    """Return the parsed float or the default when missing/invalid."""
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    return value if value > 0 else default


@dataclass(frozen=True)
class MCPConfig:
    """Runtime settings for the image-generation MCP server."""

    daemon_url: str = DEFAULT_DAEMON_URL
    api_key: str = ""
    request_timeout_s: float = DEFAULT_REQUEST_TIMEOUT_S
    generation_timeout_s: float = DEFAULT_GENERATION_TIMEOUT_S
    poll_interval_s: float = DEFAULT_POLL_INTERVAL_S
    output_dir: str = DEFAULT_OUTPUT_DIR

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
        )
