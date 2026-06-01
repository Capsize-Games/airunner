"""
Daemon mode entry point for AI Runner.

Runs AI Runner as a background service without GUI, providing:
- HTTP API server
- Model persistence and management
- Graceful shutdown handling
- Health monitoring
"""

import argparse
import logging
import os
import signal
import sys
import threading
import time
from pathlib import Path

from airunner_services.startup_env import (
    configure_early_torch_allocator_environment,
)


def _configure_daemon_environment() -> None:
    """Set headless-safe environment defaults before imports."""
    os.environ.setdefault("AIRUNNER_HEADLESS", "1")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault(
        "QT_LOGGING_RULES",
        "*.debug=false;qt.qpa.*=false",
    )
    configure_early_torch_allocator_environment()


_configure_daemon_environment()

from logging.handlers import RotatingFileHandler

from airunner_services.runtimes.daemon_config import DaemonConfig
from airunner_services.api.server import APIServer
from airunner_services.app import ServiceApp
from airunner_services.model_management.model_resource_manager import (
    ModelResourceManager,
)
from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)
App = ServiceApp


class AIRunnerDaemon:
    """AI Runner daemon process."""

    def __init__(self, config: DaemonConfig):
        """
        Initialize daemon.

        Args:
            config: Daemon configuration
        """
        self.config = config
        self.app = None
        self.api_server = None
        self.shutdown_requested = False
        self._setup_logging()
        self._setup_signal_handlers()
        self.lifecycle_service = None

    def _acquire_lock(self) -> bool:
        """Return True when no other daemon is listening on the configured port.

        Attempts a TCP connection to the port.  If something answers,
        another daemon is already running.
        """
        import socket

        server_config = self.config.config.get("server", {})
        host = server_config.get("host", "127.0.0.1")
        port = int(server_config.get("port", 8188))

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        try:
            sock.connect((host, port))
            # Connected — another daemon is listening
            return False
        except (OSError, ConnectionRefusedError, socket.timeout):
            # Nothing listening — port is free
            return True
        finally:
            sock.close()

    def _setup_logging(self):
        """Configure logging for daemon mode."""
        log_config = self.config.config.get("logging", {})
        log_file = Path(
            log_config.get("file", "~/.airunner/logs/daemon.log")
        ).expanduser()
        log_level = getattr(logging, log_config.get("level", "INFO"))
        log_to_file = (
            os.environ.get("AIRUNNER_SAVE_LOG_TO_FILE", "0") == "1"
            or bool(log_config.get("to_file", False))
        )

        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        root_logger.setLevel(log_level)

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        if log_to_file:
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

        if log_to_file:
            logger.info("Daemon logging initialized with file output")
        else:
            logger.info("Daemon logging initialized without file output")

    def _setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""
        signal.signal(signal.SIGTERM, self._handle_shutdown_signal)
        signal.signal(signal.SIGINT, self._handle_shutdown_signal)

        if hasattr(signal, "SIGHUP"):
            signal.signal(signal.SIGHUP, self._handle_reload_signal)

    def _handle_shutdown_signal(self, signum, frame):
        """Handle shutdown signals (SIGTERM, SIGINT)."""
        del frame
        logger.info(
            f"Received signal {signum}, initiating graceful shutdown..."
        )
        self.shutdown_requested = True
        self.shutdown()

    def _handle_reload_signal(self, signum, frame):
        """Handle reload signal (SIGHUP) - reload configuration."""
        del signum, frame
        logger.info("Received SIGHUP, reloading configuration...")
        self.config = DaemonConfig(self.config.config_path)
        logger.info("Configuration reloaded")

    def start(self):
        """Start the daemon."""
        logger.info("Starting AI Runner daemon...")

        if not self._acquire_lock():
            logger.error(
                "Daemon is already running on port %s. "
                "Stop the existing instance first.",
                self.config.config.get("server", {}).get("port", 8188),
            )
            sys.exit(1)

        try:
            self.app = self._create_headless_app()
            self._initialize_lifecycle_service()

            logger.info("AI Runner app initialized in headless mode")
            self._preload_models()
            self._start_health_monitor()
            self._start_api_server()

            logger.info("AI Runner daemon started successfully")
            self._run_loop()

        except Exception as e:
            logger.error(f"Fatal error in daemon: {e}", exc_info=True)
            sys.exit(1)

    def _create_headless_app(self) -> App:
        """Create the daemon-owned app without embedded server ownership."""
        return App(
            headless=True,
            no_splash=True,
            start_headless_api_server=False,
            initialize_headless_lifecycle=False,
        )

    def _initialize_lifecycle_service(self) -> None:
        """Initialize runtime lifecycle through the reusable service."""
        if not self.app:
            raise RuntimeError("Daemon App must exist before lifecycle init")
        self.lifecycle_service = self.app.ensure_lifecycle_service()
        self.lifecycle_service.initialize()
        self.lifecycle_service.preload_llm_model()

    def _preload_models(self):
        """Preload configured models on startup."""
        preload_list = self.config.config.get("models", {}).get("preload", [])

        if not preload_list:
            logger.info("No models configured for preloading")
            return

        logger.info(f"Preloading {len(preload_list)} models: {preload_list}")

        ModelResourceManager()

        for model_id in preload_list:
            try:
                logger.info(f"Preloading model: {model_id}")
                logger.info(f"Model {model_id} queued for preload")
            except Exception as e:
                logger.error(f"Failed to preload model {model_id}: {e}")

    def _start_health_monitor(self):
        """Start health monitoring heartbeat."""
        health_config = self.config.config.get("health", {})
        heartbeat_file = Path(
            health_config.get("heartbeat_file", "~/.airunner/daemon_heartbeat")
        ).expanduser()

        heartbeat_file.parent.mkdir(parents=True, exist_ok=True)
        self._write_heartbeat(heartbeat_file)

        interval = health_config.get("heartbeat_interval", 30)

        def heartbeat_loop():
            while not self.shutdown_requested:
                self._write_heartbeat(heartbeat_file)
                time.sleep(interval)

        self.heartbeat_thread = threading.Thread(
            target=heartbeat_loop, daemon=True
        )
        self.heartbeat_thread.start()

        logger.info(
            f"Health monitoring started, heartbeat file: {heartbeat_file}, "
            f"interval: {interval}s"
        )

    def _write_heartbeat(self, heartbeat_file: Path):
        """Write heartbeat timestamp to file."""
        try:
            heartbeat_file.write_text(str(time.time()))
        except Exception as e:
            logger.error(f"Failed to write heartbeat: {e}")

    def _start_api_server(self):
        """Start FastAPI server."""
        server_config = self.config.config.get("server", {})
        host = server_config.get("host", "127.0.0.1")
        port = server_config.get("port", 8188)

        try:
            self.api_server = APIServer(
                host=host, port=port, app_instance=self.app
            )

            self.server_thread = threading.Thread(
                target=self.api_server.start, daemon=True
            )
            self.server_thread.start()

            logger.info(f"FastAPI server started on {host}:{port}")
            logger.info(f"API docs available at http://{host}:{port}/docs")

        except Exception as e:
            logger.error(f"Failed to start API server: {e}", exc_info=True)
            raise

    def _run_loop(self):
        """Main daemon loop."""
        logger.info("Entering daemon main loop")

        try:
            while not self.shutdown_requested:
                time.sleep(1)

        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
            self.shutdown()

    def shutdown(self):
        """Gracefully shutdown the daemon."""
        if self.shutdown_requested:
            return

        self.shutdown_requested = True
        logger.info("Shutting down AI Runner daemon...")

        try:
            if self.api_server:
                logger.info("Stopping API server...")
                try:
                    self.api_server.stop()
                except Exception as e:
                    logger.error(f"Error stopping API server: {e}")
                self.api_server = None

            if hasattr(self, "heartbeat_thread") and self.heartbeat_thread:
                logger.info("Stopping heartbeat monitor...")
                self.heartbeat_thread.join(timeout=2)

            if self.app:
                logger.info("Cleaning up application...")
                try:
                    self._shutdown_runtime_clients()
                    if hasattr(self.app, "cleanup"):
                        self.app.cleanup()
                except Exception as e:
                    logger.error(f"Error during app cleanup: {e}")
                self.app = None

            logger.info("Daemon shutdown complete")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}", exc_info=True)

        finally:
            sys.exit(0)

    def _shutdown_runtime_clients(self) -> None:
        """Close runtime clients owned by the daemon-backed app instance."""
        runtime_registry = getattr(self.app, "runtime_registry", None)
        if runtime_registry is None:
            return

        seen_clients = set()
        for route in runtime_registry.list_routes():
            client = runtime_registry.resolve(
                route.runtime,
                route.provider,
                route.deployment_mode,
            )
            client_id = id(client)
            if client_id in seen_clients:
                continue
            seen_clients.add(client_id)
            client.close()


def main():
    """Main entry point for daemon."""
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

    args = parser.parse_args()

    if args.generate_config:
        config = DaemonConfig(args.config)
        config.save()
        print(f"Generated default configuration: {config.config_path}")
        sys.exit(0)

    config = DaemonConfig(args.config)
    daemon = AIRunnerDaemon(config)
    daemon.start()


if __name__ == "__main__":
    main()
