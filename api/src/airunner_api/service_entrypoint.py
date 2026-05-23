"""Standalone API service entrypoint for the airunner API backend.

Starts the FastAPI server with the full route set, independent of the
GUI process. Intended for daemon mode, sidecar processes, or Docker
deployment.

Usage:
    python -m airunner_api.service_entrypoint --host 127.0.0.1 --port 8188
"""

from __future__ import annotations

import argparse
import os
import signal
import sys
from typing import Optional

import uvicorn


def _configure_service_environment() -> None:
    """Set headless-safe environment defaults before imports."""
    os.environ.setdefault("AIRUNNER_HEADLESS", "1")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _build_app():
    """Create the FastAPI application with all routes registered."""
    from airunner_api.server import create_app

    return create_app(
        allowed_origins=[
            "http://localhost",
            "http://localhost:*",
            "http://127.0.0.1",
            "http://127.0.0.1:*",
        ],
        enable_cors=True,
    )


def start_server(
    host: str = "127.0.0.1",
    port: int = 8188,
    *,
    reload: bool = False,
    log_level: str = "info",
    access_log: bool = False,
) -> None:
    """Start the API server with the given configuration."""
    app = _build_app()
    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level=log_level,
        access_log=access_log,
        reload=reload,
    )
    server = uvicorn.Server(config)

    def _handle_shutdown(signum: int, _frame) -> None:
        print(f"\nReceived signal {signum}, shutting down...")
        server.should_exit = True

    signal.signal(signal.SIGTERM, _handle_shutdown)
    signal.signal(signal.SIGINT, _handle_shutdown)

    print(f"Starting AI Runner API on {host}:{port}")
    server.run()


def main(argv: Optional[list[str]] = None) -> None:
    """Parse arguments and start the API server."""
    _configure_service_environment()

    parser = argparse.ArgumentParser(
        description="AI Runner API Service",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("AIRUNNER_API_HOST", "127.0.0.1"),
        help="Host to bind to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("AIRUNNER_API_PORT", "8188")),
        help="Port to listen on (default: 8188)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=False,
        help="Enable auto-reload for development",
    )
    parser.add_argument(
        "--log-level",
        default="info",
        choices=["critical", "error", "warning", "info", "debug"],
        help="Log level (default: info)",
    )
    parser.add_argument(
        "--access-log",
        action="store_true",
        default=False,
        help="Enable uvicorn access log",
    )

    args = parser.parse_args(argv)

    start_server(
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level,
        access_log=args.access_log,
    )


if __name__ == "__main__":
    main()
