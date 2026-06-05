"""Helper utilities for the AI Runner daemon process."""

from __future__ import annotations

import logging
import socket
import threading
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from airunner_services.settings import AIRUNNER_LOG_FILE
from airunner_services.utils.application import get_logger

logger = get_logger(__name__)

_SIDECAR_MISSING_MSG = (
    "%s sidecar not available: %s "
    "(build sidecar binaries or run without them)"
)


def configure_logging(
    log_config: dict[str, Any],
    log_level: int,
) -> None:
    """Configure root logger with file and console handlers."""
    log_file = Path(AIRUNNER_LOG_FILE).expanduser().resolve()
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(log_level)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    log_file.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        log_file,
        maxBytes=log_config.get("max_bytes", 50 * 1024 * 1024),
        backupCount=log_config.get("backup_count", 5),
    )
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)


def resolve_lock_host_port(config: dict[str, Any]) -> tuple[str, int]:
    """Return the (host, port) used for the daemon port lock."""
    server_config = config.get("server", {})
    return (
        server_config.get("host", "127.0.0.1"),
        int(server_config.get("port", 8188)),
    )


def is_port_free(host: str, port: int) -> bool:
    """Return True when no process is listening on host:port."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.5)
    try:
        sock.connect((host, port))
        return False
    except (OSError, ConnectionRefusedError, socket.timeout):
        return True
    finally:
        sock.close()


def write_heartbeat(heartbeat_file: Path) -> None:
    """Write a current timestamp to the heartbeat file."""
    try:
        heartbeat_file.write_text(str(time.time()))
    except Exception as exc:
        logger.error("Failed to write heartbeat: %s", exc)


def start_heartbeat_loop(
    heartbeat_file: Path,
    interval: int,
    stop_event: threading.Event,
) -> threading.Thread:
    """Return a daemon thread that writes heartbeats on an interval."""

    def _loop():
        while not stop_event.is_set():
            write_heartbeat(heartbeat_file)
            time.sleep(interval)

    thread = threading.Thread(target=_loop, daemon=True)
    thread.start()
    return thread


def resolve_heartbeat_config(
    config: dict[str, Any],
) -> tuple[Path, int]:
    """Return (heartbeat_file, interval) from daemon config."""
    health_config = config.get("health", {})
    hb_file = Path(
        health_config.get(
            "heartbeat_file",
            "~/.airunner/daemon_heartbeat",
        )
    ).expanduser()
    hb_file.parent.mkdir(parents=True, exist_ok=True)
    interval = health_config.get("heartbeat_interval", 30)
    return hb_file, interval


def _launch_sidecar(launcher: Any, name: str) -> None:
    """Start one sidecar and log its status."""
    try:
        launcher.start()
        logger.info("%s sidecar daemon ready", name)
    except Exception as exc:
        logger.warning(_SIDECAR_MISSING_MSG, name, exc)


def start_sidecar_daemons(runtime_registry: Any) -> None:
    """Start sidecar processes in background threads."""
    if runtime_registry is None:
        return
    seen: set[int] = set()
    for route in runtime_registry.list_routes():
        client = _resolve_client(runtime_registry, route)
        if client is None or id(client) in seen:
            continue
        seen.add(id(client))
        launcher = getattr(client, "_launcher", None)
        if launcher is None:
            continue
        name = _route_name(route)
        thread = threading.Thread(
            target=lambda launcher_=launcher, n=name: _launch_sidecar(
                launcher_, n
            ),
            daemon=True,
        )
        thread.start()


def shutdown_runtime_clients(runtime_registry: Any) -> None:
    """Close all runtime clients in the registry."""
    if runtime_registry is None:
        return

    seen: set[int] = set()
    for route in runtime_registry.list_routes():
        client = _resolve_client(runtime_registry, route)
        if client is None:
            continue
        client_id = id(client)
        if client_id in seen:
            continue
        seen.add(client_id)
        client.close()


def parse_daemon_args(args: list[str] | None = None) -> Any:
    """Return parsed daemon CLI arguments."""
    import argparse

    parser = argparse.ArgumentParser(description="AI Runner Daemon")
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to daemon configuration file (daemon.yaml)",
    )
    parser.add_argument(
        "--generate-config",
        action="store_true",
        help="Generate default configuration file and exit",
    )
    return parser.parse_args(args)


def _resolve_client(registry: Any, route: Any) -> Any:
    """Resolve a runtime client or return None on KeyError."""
    try:
        return registry.resolve(
            route.runtime,
            route.provider,
            route.deployment_mode,
        )
    except KeyError:
        return None


def _route_name(route: Any) -> str:
    """Return a human-readable name for a runtime route."""
    return str(
        route.runtime.value
        if hasattr(route.runtime, "value")
        else route.runtime
    )
