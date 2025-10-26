"""
Daemon mode entry point for AI Runner.

Runs AI Runner as a background service without GUI, providing:
- HTTP API server
- Model persistence and management
- Graceful shutdown handling
- Health monitoring
"""

import os
import sys
import signal
import logging
import argparse
import yaml
from pathlib import Path
from typing import Optional, Dict, Any

# Set PyTorch CUDA config before any torch imports
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")


class DaemonConfig:
    """Configuration for daemon mode."""

    def __init__(self, config_path: Optional[Path] = None):
        """
        Load daemon configuration.

        Args:
            config_path: Path to daemon.yaml configuration file
        """
        self.config_path = config_path or self._default_config_path()
        self.config = self._load_config()

    def _default_config_path(self) -> Path:
        """Get default configuration path."""
        if sys.platform == "win32":
            config_dir = Path(os.environ.get("APPDATA", "")) / "airunner"
        else:
            config_dir = Path.home() / ".config" / "airunner"

        return config_dir / "daemon.yaml"

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        if not self.config_path.exists():
            return self._default_config()

        try:
            with open(self.config_path, "r") as f:
                config = yaml.safe_load(f) or {}
            return {**self._default_config(), **config}
        except Exception as e:
            logging.error(
                f"Failed to load config from {self.config_path}: {e}"
            )
            return self._default_config()

    def _default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            # Server settings
            "server": {
                "host": "127.0.0.1",
                "port": 8188,
                "enable_cors": True,
                "allowed_origins": [
                    "http://localhost:*",
                    "http://127.0.0.1:*",
                ],
            },
            # Model persistence
            "models": {
                "persistence_mode": "timeout",  # keep_loaded, timeout, per_request
                "timeout_minutes": 30,
                "preload": [],  # List of model IDs to preload on startup
            },
            # Health monitoring
            "health": {
                "heartbeat_interval": 30,  # seconds
                "heartbeat_file": "~/.airunner/daemon_heartbeat",
            },
            # Logging
            "logging": {
                "level": "INFO",
                "file": "~/.airunner/logs/daemon.log",
                "max_bytes": 50 * 1024 * 1024,  # 50MB
                "backup_count": 5,
            },
        }

    def save(self):
        """Save configuration to file."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w") as f:
                yaml.safe_dump(self.config, f, default_flow_style=False)
        except Exception as e:
            logging.error(f"Failed to save config to {self.config_path}: {e}")


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

    def _setup_logging(self):
        """Configure logging for daemon mode."""
        log_config = self.config.config.get("logging", {})
        log_file = Path(
            log_config.get("file", "~/.airunner/logs/daemon.log")
        ).expanduser()
        log_level = getattr(logging, log_config.get("level", "INFO"))

        # Create log directory
        log_file.parent.mkdir(parents=True, exist_ok=True)

        # Configure rotating file handler
        from logging.handlers import RotatingFileHandler

        handler = RotatingFileHandler(
            log_file,
            maxBytes=log_config.get("max_bytes", 50 * 1024 * 1024),
            backupCount=log_config.get("backup_count", 5),
        )

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)

        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        root_logger.addHandler(handler)

        # Also log to console
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

        logging.info("Daemon logging initialized")

    def _setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""
        signal.signal(signal.SIGTERM, self._handle_shutdown_signal)
        signal.signal(signal.SIGINT, self._handle_shutdown_signal)

        if hasattr(signal, "SIGHUP"):
            signal.signal(signal.SIGHUP, self._handle_reload_signal)

    def _handle_shutdown_signal(self, signum, frame):
        """Handle shutdown signals (SIGTERM, SIGINT)."""
        logging.info(
            f"Received signal {signum}, initiating graceful shutdown..."
        )
        self.shutdown_requested = True
        self.shutdown()

    def _handle_reload_signal(self, signum, frame):
        """Handle reload signal (SIGHUP) - reload configuration."""
        logging.info("Received SIGHUP, reloading configuration...")
        self.config = DaemonConfig(self.config.config_path)
        logging.info("Configuration reloaded")

    def start(self):
        """Start the daemon."""
        logging.info("Starting AI Runner daemon...")

        try:
            # Import App here to avoid circular imports
            from airunner.app import App

            # Initialize App in headless mode (no GUI)
            self.app = App(initialize_gui=False, no_splash=True)

            logging.info("AI Runner app initialized in headless mode")

            # Preload models if configured
            self._preload_models()

            # Start health monitoring
            self._start_health_monitor()

            # Start API server
            self._start_api_server()

            logging.info("AI Runner daemon started successfully")

            # Keep daemon running
            self._run_loop()

        except Exception as e:
            logging.error(f"Fatal error in daemon: {e}", exc_info=True)
            sys.exit(1)

    def _preload_models(self):
        """Preload configured models on startup."""
        preload_list = self.config.config.get("models", {}).get("preload", [])

        if not preload_list:
            logging.info("No models configured for preloading")
            return

        logging.info(f"Preloading {len(preload_list)} models: {preload_list}")

        try:
            from airunner.components.model_management.model_resource_manager import (
                ModelResourceManager,
            )

            manager = ModelResourceManager()

            for model_id in preload_list:
                try:
                    logging.info(f"Preloading model: {model_id}")
                    # Model loading will be handled by specific managers
                    # when they receive the appropriate signals
                    # For now, just log the intent
                    logging.info(f"Model {model_id} queued for preload")
                except Exception as e:
                    logging.error(f"Failed to preload model {model_id}: {e}")

        except ImportError as e:
            logging.warning(f"ModelResourceManager not available: {e}")
            logging.info("Skipping model preloading")

    def _start_health_monitor(self):
        """Start health monitoring heartbeat."""
        health_config = self.config.config.get("health", {})
        heartbeat_file = Path(
            health_config.get("heartbeat_file", "~/.airunner/daemon_heartbeat")
        ).expanduser()

        heartbeat_file.parent.mkdir(parents=True, exist_ok=True)

        # Write initial heartbeat
        self._write_heartbeat(heartbeat_file)

        # Set up periodic heartbeat using threading.Timer
        import threading

        interval = health_config.get("heartbeat_interval", 30)

        def heartbeat_loop():
            while not self.shutdown_requested:
                self._write_heartbeat(heartbeat_file)
                import time

                time.sleep(interval)

        self.heartbeat_thread = threading.Thread(
            target=heartbeat_loop, daemon=True
        )
        self.heartbeat_thread.start()

        logging.info(
            f"Health monitoring started, heartbeat file: {heartbeat_file}, "
            f"interval: {interval}s"
        )

    def _write_heartbeat(self, heartbeat_file: Path):
        """Write heartbeat timestamp to file."""
        import time

        try:
            heartbeat_file.write_text(str(time.time()))
        except Exception as e:
            logging.error(f"Failed to write heartbeat: {e}")

    def _start_api_server(self):
        """Start FastAPI server."""
        from airunner.api.server import APIServer

        server_config = self.config.config.get("server", {})
        host = server_config.get("host", "127.0.0.1")
        port = server_config.get("port", 8188)

        try:
            self.api_server = APIServer(
                host=host, port=port, app_instance=self.app
            )

            # Start server in background thread
            import threading

            self.server_thread = threading.Thread(
                target=self.api_server.start, daemon=True
            )
            self.server_thread.start()

            logging.info(f"FastAPI server started on {host}:{port}")
            logging.info(f"API docs available at http://{host}:{port}/docs")

        except Exception as e:
            logging.error(f"Failed to start API server: {e}", exc_info=True)
            raise

    def _run_loop(self):
        """Main daemon loop."""
        import time

        logging.info("Entering daemon main loop")

        try:
            # Keep daemon running while server is active
            while not self.shutdown_requested:
                time.sleep(1)

        except KeyboardInterrupt:
            logging.info("Keyboard interrupt received")
            self.shutdown()

    def shutdown(self):
        """Gracefully shutdown the daemon."""
        if self.shutdown_requested:
            return

        self.shutdown_requested = True
        logging.info("Shutting down AI Runner daemon...")

        try:
            # Stop API server
            if self.api_server:
                logging.info("Stopping API server...")
                try:
                    self.api_server.stop()
                except Exception as e:
                    logging.error(f"Error stopping API server: {e}")
                self.api_server = None

            # Wait for heartbeat thread to finish
            if hasattr(self, "heartbeat_thread") and self.heartbeat_thread:
                logging.info("Stopping heartbeat monitor...")
                self.heartbeat_thread.join(timeout=2)

            # Cleanup app (unload models, etc.)
            if self.app:
                logging.info("Cleaning up application...")
                try:
                    if hasattr(self.app, "cleanup"):
                        self.app.cleanup()
                except Exception as e:
                    logging.error(f"Error during app cleanup: {e}")
                self.app = None

            logging.info("Daemon shutdown complete")

        except Exception as e:
            logging.error(f"Error during shutdown: {e}", exc_info=True)

        finally:
            sys.exit(0)


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

    # Generate config if requested
    if args.generate_config:
        config = DaemonConfig(args.config)
        config.save()
        print(f"Generated default configuration: {config.config_path}")
        sys.exit(0)

    # Load configuration
    config = DaemonConfig(args.config)

    # Create and start daemon
    daemon = AIRunnerDaemon(config)
    daemon.start()


if __name__ == "__main__":
    main()
