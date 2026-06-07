"""
Daemon mode entry point for AI Runner.

Runs AI Runner as a background service without GUI, providing:
- HTTP API server
- Model persistence and management
- Graceful shutdown handling
- Health monitoring
"""

import logging
import os
import signal
import sys
import threading
import time

from airunner_services.startup_env import (
    configure_early_torch_allocator_environment,
)


def _configure_daemon_environment() -> None:
    """Set environment defaults before imports."""
    os.environ.setdefault("AIRUNNER_DAEMON", "1")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault(
        "QT_LOGGING_RULES",
        "*.debug=false;qt.qpa.*=false",
    )
    configure_early_torch_allocator_environment()


_configure_daemon_environment()

from airunner_services.runtimes.daemon_config import DaemonConfig  # noqa: E402
from airunner_services.api.api_server import APIServer  # noqa: E402
from airunner_services.app import ServiceApp  # noqa: E402
from airunner_services.model_management.model_resource_manager import (  # noqa: E402
    ModelResourceManager,
)
from airunner_services.settings import (  # noqa: E402
    AIRUNNER_LOG_LEVEL,
)
from airunner_services.utils.application import get_logger  # noqa: E402
from airunner_services.daemon_helpers import (  # noqa: E402
    configure_logging,
    is_port_free,
    parse_daemon_args,
    resolve_heartbeat_config,
    resolve_lock_host_port,
    shutdown_runtime_clients,
    start_heartbeat_loop,
    write_heartbeat,
)

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)
App = ServiceApp


class AIRunnerDaemon:
    """AI Runner daemon process."""

    def __init__(self, config: DaemonConfig):
        self.config = config
        self.app = None
        self.api_server = None
        self.shutdown_requested = False
        self.lifecycle_service = None
        self.heartbeat_thread = None
        self._stop_heartbeat = threading.Event()
        self._setup_logging()
        self._setup_signal_handlers()

    def _setup_logging(self):
        """Configure root logger with file and console handlers."""
        log_config = self.config.config.get("logging", {})
        level = getattr(logging, log_config.get("level", "INFO"))
        configure_logging(log_config, level)
        logger.info("Daemon logging initialized")

    def _setup_signal_handlers(self):
        """Register SIGTERM, SIGINT, and SIGHUP handlers."""
        signal.signal(signal.SIGTERM, self._handle_shutdown_signal)
        signal.signal(signal.SIGINT, self._handle_shutdown_signal)
        if hasattr(signal, "SIGHUP"):
            signal.signal(signal.SIGHUP, self._handle_reload_signal)

    def _handle_shutdown_signal(self, signum, frame):
        """Trigger graceful shutdown on SIGTERM or SIGINT."""
        del frame
        logger.info("Signal %s received, shutting down...", signum)
        self.shutdown_requested = True
        self.shutdown()

    def _handle_reload_signal(self, signum, frame):
        """Reload daemon configuration on SIGHUP."""
        del signum, frame
        logger.info("SIGHUP received, reloading configuration...")
        self.config = DaemonConfig(self.config.config_path)
        logger.info("Configuration reloaded")

    def _acquire_lock(self):
        """Return True when the configured port is not in use."""
        host, port = resolve_lock_host_port(self.config.config)
        return is_port_free(host, port)

    def start(self):
        """Start the daemon."""
        logger.info("Starting AI Runner daemon...")
        self._run_database_migrations()
        if not self._acquire_lock():
            port = self.config.config.get("server", {}).get("port", 8188)
            logger.error("Daemon already running on port %s.", port)
            sys.exit(1)
        try:
            self.app = App(start_embedded_api_server=False)
            self._initialize_lifecycle_service()
            self._preload_models()
            self._start_health_monitor()
            self._start_api_server()
            logger.info("AI Runner daemon started successfully")
            self._run_loop()
        except Exception as exc:
            logger.error("Fatal daemon error: %s", exc, exc_info=True)
            sys.exit(1)

    def _initialize_lifecycle_service(self):
        """Initialize the runtime lifecycle service."""
        if not self.app:
            raise RuntimeError("Daemon App must exist before lifecycle init")
        self.lifecycle_service = self.app.ensure_lifecycle_service()
        self.lifecycle_service.initialize()

    def _preload_models(self):
        """Preload configured models on startup."""
        preload_list = self.config.config.get("models", {}).get("preload", [])
        if not preload_list:
            logger.info("No models configured for preloading")
            return
        logger.info("Preloading %d models", len(preload_list))
        ModelResourceManager()
        for model_id in preload_list:
            logger.info("Model %s queued for preload", model_id)

    def _start_health_monitor(self):
        """Start the heartbeat-based health monitor thread."""
        hb_file, interval = resolve_heartbeat_config(self.config.config)
        write_heartbeat(hb_file)
        self.heartbeat_thread = start_heartbeat_loop(
            hb_file,
            interval,
            self._stop_heartbeat,
        )
        logger.info(
            "Health monitoring started on %s, interval %ds",
            hb_file,
            interval,
        )

    def _start_api_server(self):
        """Start the FastAPI server on the configured host:port."""
        c = self.config.config.get("server", {})
        h = c.get("host", "127.0.0.1")
        p = c.get("port", 8188)
        try:
            self.api_server = APIServer(host=h, port=p, app_instance=self.app)
            t = threading.Thread(target=self.api_server.start, daemon=True)
            t.start()
            logger.info("API server on %s:%s (docs at /docs)", h, p)
        except Exception:
            logger.error("Failed to start API server", exc_info=True)
            raise

    def _run_loop(self):
        """Main daemon loop — sleep until shutdown."""
        logger.info("Entering daemon main loop")
        try:
            while not self.shutdown_requested:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
            self.shutdown()

    def shutdown(self):
        """Gracefully stop the daemon."""
        if self.shutdown_requested:
            return
        self.shutdown_requested = True
        self._stop_heartbeat.set()
        try:
            if self.api_server:
                self.api_server.stop()
                self.api_server = None
            if self.heartbeat_thread:
                self.heartbeat_thread.join(timeout=2)
            if self.app:
                shutdown_runtime_clients(self.app.runtime_registry)
                self.app.cleanup()
                self.app = None
            logger.info("Daemon shutdown complete")
        except Exception as exc:
            logger.error("Error during shutdown: %s", exc, exc_info=True)
        finally:
            sys.exit(0)

    def _run_database_migrations(self):
        """Run Alembic migrations before any service starts."""
        from airunner_services.database.setup_database import (  # noqa: PLC0415
            setup_database,
        )

        setup_database()


def main():
    """Daemon CLI entry point."""
    args = parse_daemon_args()
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
