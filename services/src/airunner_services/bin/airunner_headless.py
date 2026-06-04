#!/usr/bin/env python3
"""
Headless AI Runner daemon supervisor for eval testing and API access.

This command no longer creates its own App or worker graph. Instead it
connects to an already running daemon or launches a managed daemon and lets
that daemon own the external HTTP API.

Startup, shutdown, and logging behavior:
        - Existing daemon: verifies connectivity and exits without stopping it.
        - Managed daemon: launches a child daemon, forwards its stdout/stderr to
            the terminal, and stops only that child on shutdown.
        - Daemon logging still writes to the configured daemon log file.

Usage:
    airunner-headless
    airunner-headless --host 0.0.0.0 --port 8080
        airunner-headless --connect-only
        airunner-headless \
            --daemon-config ~/.local/share/airunner/runtime/configs/daemon.yaml
    airunner-headless --ollama-mode  # Run as Ollama replacement on port 11434
    airunner-headless --model "/path/to/llm/model"  # Load specific LLM model
    airunner-headless --art-model "/path/to/art/model"  # Load specific art model
    airunner-headless --tts-model "/path/to/tts/model"  # Load specific TTS model
    airunner-headless --stt-model "/path/to/stt/model"  # Load specific STT model
    airunner-headless --no-preload  # Don't preload models, load on first request
    airunner-headless --help

Environment Variables:
    AIRUNNER_HEADLESS: Set to 1 (automatically set by this script)
    AIRUNNER_DAEMON_CONFIG: Base daemon config to clone for this session
    AIRUNNER_HTTP_HOST: Override host (default: 127.0.0.1)
    AIRUNNER_HTTP_PORT: Override port (default: 8080)
    AIRUNNER_INSECURE_NO_AUTH: Set to 1 to allow binding to non-loopback without AIRUNNER_API_KEY
    AIRUNNER_OLLAMA_MODE: Run as Ollama replacement (default: 0)
    AIRUNNER_LLM_ON: Enable LLM service (default: 1)
    AIRUNNER_TTS_ON: Enable TTS service (default: 0)
    AIRUNNER_STT_ON: Enable STT service (default: 0)
    AIRUNNER_SD_ON: Enable Stable Diffusion (default: 0)
    AIRUNNER_CN_ON: Enable ControlNet (default: 0)
    AIRUNNER_LLM_MODEL_PATH: Path to LLM model to preload
    AIRUNNER_ART_MODEL_PATH: Path to art model to preload
    AIRUNNER_TTS_MODEL_PATH: Path to TTS model to preload
    AIRUNNER_STT_MODEL_PATH: Path to STT model to preload
    AIRUNNER_NO_PRELOAD: Set to 1 to disable model preloading

Examples:
    # Start with defaults (127.0.0.1:8080)
    airunner-headless

    # Start on custom port
    airunner-headless --port 9000

    # Start on localhost only
    airunner-headless --host 127.0.0.1 --port 8080

    # Verify and reuse an already running daemon
    airunner-headless --connect-only --host 127.0.0.1 --port 8080

    # Run as Ollama replacement (port 11434) for VS Code integration
    airunner-headless --ollama-mode

    # Load a specific LLM model at startup
    airunner-headless --model "/path/to/Qwen2.5-7B-Instruct-4bit"

    # Run without preloading models (load on first request)
    airunner-headless --no-preload

    # Enable Stable Diffusion and load a specific art model
    airunner-headless --enable-art --art-model "/path/to/stable-diffusion-v1-5"

    # Enable all services with specific models
    airunner-headless --enable-llm --enable-art --enable-tts --enable-stt \\
        --model "/path/to/llm" --art-model "/path/to/art"

Important:
    Quote any model path that contains spaces, such as
    "/home/joe/.local/share/airunner/art/models/Z-Image Turbo/txt2img/model.safetensors".
"""

import argparse
import copy
import os
import signal
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional, Sequence


BANNER = """
\033[96m
     █████╗ ██╗    ██████╗ ██╗   ██╗███╗   ██╗███╗   ██╗███████╗██████╗
    ██╔══██╗██║    ██╔══██╗██║   ██║████╗  ██║████╗  ██║██╔════╝██╔══██╗
    ███████║██║    ██████╔╝██║   ██║██╔██╗ ██║██╔██╗ ██║█████╗  ██████╔╝
    ██╔══██║██║    ██╔══██╗██║   ██║██║╚██╗██║██║╚██╗██║██╔══╝  ██╔══██╗
    ██║  ██║██║    ██║  ██║╚██████╔╝██║ ╚████║██║ ╚████║███████╗██║  ██║
    ╚═╝  ╚═╝╚═╝    ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝
\033[0m
\033[93m    ╔══════════════════════════════════════════════════════════════╗
    ║  💖 Support AI Runner development! Send crypto:              ║
    ║  \033[97m0x02030569e866e22C9991f55Db0445eeAd2d646c8\033[93m                  ║
    ╚══════════════════════════════════════════════════════════════╝\033[0m
"""


def _build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser for the headless daemon supervisor."""
    parser = argparse.ArgumentParser(
        description="AI Runner Headless Server - daemon-backed HTTP API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--host",
        type=str,
        default=os.environ.get("AIRUNNER_HTTP_HOST", "127.0.0.1"),
        help="Host address to bind to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port to listen on (default: 8080, or 11434 in ollama-mode)",
    )
    parser.add_argument(
        "--daemon-config",
        type=Path,
        default=_default_daemon_config(),
        help="Base daemon config to clone for this headless session",
    )
    parser.add_argument(
        "--connect-only",
        action="store_true",
        help="Only connect to an already running daemon; do not launch one",
    )
    parser.add_argument(
        "--ollama-mode",
        action="store_true",
        default=os.environ.get("AIRUNNER_OLLAMA_MODE", "0") == "1",
        help="Run as Ollama replacement on port 11434 for VS Code integration",
    )
    parser.add_argument(
        "--insecure-no-auth",
        action="store_true",
        default=os.environ.get("AIRUNNER_INSECURE_NO_AUTH", "0") == "1",
        help=(
            "Allow binding to non-loopback addresses without AIRUNNER_API_KEY. "
            "Not recommended."
        ),
    )
    _add_model_args(parser)
    _add_service_args(parser)
    return parser


def _default_daemon_config() -> Path:
    """Return the default daemon config path for this bundle/runtime."""
    config_path = os.environ.get("AIRUNNER_DAEMON_CONFIG")
    if config_path:
        return Path(config_path)

    from airunner_services.config.runtime_layout import (
        build_runtime_directory_layout,
    )

    return build_runtime_directory_layout().config_file("daemon")


def _add_model_args(parser: argparse.ArgumentParser) -> None:
    """Register model-path related CLI arguments."""
    parser.add_argument(
        "--model",
        "-m",
        type=str,
        default=os.environ.get("AIRUNNER_LLM_MODEL_PATH"),
        help=(
            "Path to LLM model to load at startup (or first request). "
            "Also enables the LLM service."
        ),
    )
    parser.add_argument(
        "--art-model",
        type=str,
        default=os.environ.get("AIRUNNER_ART_MODEL_PATH"),
        help=(
            "Path to art or Stable Diffusion model to load. "
            "Also enables the art service."
        ),
    )
    parser.add_argument(
        "--tts-model",
        type=str,
        default=os.environ.get("AIRUNNER_TTS_MODEL_PATH"),
        help=(
            "Path to TTS model to load. Also enables the TTS service."
        ),
    )
    parser.add_argument(
        "--stt-model",
        type=str,
        default=os.environ.get("AIRUNNER_STT_MODEL_PATH"),
        help=(
            "Path to STT model to load. Also enables the STT service."
        ),
    )


def _add_service_args(parser: argparse.ArgumentParser) -> None:
    """Register service and preload CLI arguments."""
    parser.add_argument(
        "--enable-llm",
        action="store_true",
        default=None,
        help="Enable LLM service (default: enabled unless disabled)",
    )
    parser.add_argument(
        "--enable-art",
        action="store_true",
        default=None,
        help="Enable Stable Diffusion or art service",
    )
    parser.add_argument(
        "--enable-tts",
        action="store_true",
        default=None,
        help="Enable TTS service",
    )
    parser.add_argument(
        "--enable-stt",
        action="store_true",
        default=None,
        help="Enable STT service",
    )
    parser.add_argument(
        "--no-preload",
        action="store_true",
        default=os.environ.get("AIRUNNER_NO_PRELOAD", "0") == "1",
        help="Don't preload models at startup, load on first request instead",
    )


def _resolve_port(args: argparse.Namespace) -> int:
    """Return the requested external API port."""
    if args.ollama_mode:
        return 11434
    if args.port is not None:
        return args.port
    return int(os.environ.get("AIRUNNER_HTTP_PORT", "8080"))


def _validate_host_binding(args: argparse.Namespace) -> bool:
    """Refuse unsafe non-loopback binding without explicit auth or override."""
    from airunner_services.api.server import is_loopback_host

    configured_api_key = (os.environ.get("AIRUNNER_API_KEY") or "").strip()
    if is_loopback_host(args.host) or args.insecure_no_auth:
        return True
    if configured_api_key:
        return True
    print(
        "Refusing to bind to a non-loopback host without AIRUNNER_API_KEY.\n"
        "Set AIRUNNER_API_KEY, or re-run with --insecure-no-auth "
        "(NOT recommended).",
        file=sys.stderr,
    )
    return False


def _configure_environment(args: argparse.Namespace, port: int) -> None:
    """Set headless environment variables inherited by the daemon."""
    from airunner_services.runtimes.bundle_layout import (
        build_linux_bundle_layout,
    )

    bundle_layout = build_linux_bundle_layout()
    os.environ.setdefault("AIRUNNER_HEADLESS", "1")
    os.environ.setdefault(
        "AIRUNNER_BUNDLE_ROOT",
        str(bundle_layout.bundle_root),
    )
    os.environ.setdefault(
        "AIRUNNER_PYTHON",
        str(bundle_layout.python_executable),
    )
    os.environ["AIRUNNER_HEADLESS_SERVER_HOST"] = args.host
    os.environ["AIRUNNER_HEADLESS_SERVER_PORT"] = str(port)
    os.environ["AIRUNNER_HTTP_HOST"] = args.host
    os.environ["AIRUNNER_HTTP_PORT"] = str(port)
    os.environ["AIRUNNER_OLLAMA_MODE"] = "1" if args.ollama_mode else "0"
    insecure = "1" if args.insecure_no_auth else "0"
    os.environ["AIRUNNER_INSECURE_NO_AUTH"] = insecure
    _configure_model_paths(args)
    _configure_service_flags(args)


def _configure_model_paths(args: argparse.Namespace) -> None:
    """Propagate CLI model-path overrides to the daemon environment."""
    if args.model:
        os.environ["AIRUNNER_LLM_MODEL_PATH"] = args.model
    if args.art_model:
        os.environ["AIRUNNER_ART_MODEL_PATH"] = args.art_model
    if args.tts_model:
        os.environ["AIRUNNER_TTS_MODEL_PATH"] = args.tts_model
    if args.stt_model:
        os.environ["AIRUNNER_STT_MODEL_PATH"] = args.stt_model
    if args.no_preload:
        os.environ["AIRUNNER_NO_PRELOAD"] = "1"


def _configure_service_flags(args: argparse.Namespace) -> None:
    """Populate service toggles inherited by the daemon."""
    _set_service_env(args.enable_llm, args.model, "AIRUNNER_LLM_ON", "1")
    _set_service_env(args.enable_art, args.art_model, "AIRUNNER_SD_ON", "1")
    _set_service_env(args.enable_tts, args.tts_model, "AIRUNNER_TTS_ON", "1")
    _set_service_env(args.enable_stt, args.stt_model, "AIRUNNER_STT_ON", "1")
    os.environ.setdefault("AIRUNNER_CN_ON", "0")
    os.environ.setdefault("AIRUNNER_KNOWLEDGE_ON", "0")


def _set_service_env(
    enabled: Optional[bool],
    model_path: Optional[str],
    env_name: str,
    default: str,
) -> None:
    """Set one service toggle from explicit flags, model paths, or defaults."""
    if enabled is not None:
        os.environ[env_name] = "1" if enabled else "0"
        return
    if model_path:
        os.environ[env_name] = "1"
        return
    os.environ.setdefault(env_name, default)


def _configure_logging():
    """Configure supervisor logging and return the logger and level."""
    from airunner_services.settings import AIRUNNER_LOG_LEVEL
    from airunner_services.utils.application import get_logger
    from airunner_services.utils.application.logging_utils import (
        configure_headless_logging,
    )

    configure_headless_logging()
    logger = get_logger(__name__, level=AIRUNNER_LOG_LEVEL)
    return logger, AIRUNNER_LOG_LEVEL


def _log_startup(
    logger,
    args: argparse.Namespace,
    port: int,
    log_level: int,
) -> None:
    """Log the daemon-backed headless startup configuration."""
    logger.info("=" * 60)
    logger.info("AI Runner Headless Supervisor")
    logger.info("Daemon-backed mode; no local worker graph is created")
    logger.info("=" * 60)
    logger.info("Host: %s", args.host)
    logger.info("Port: %s", port)
    logger.info("Log Level: %s", log_level)
    _log_ollama_endpoints(logger, args.ollama_mode)
    _log_preload_mode(logger, args.no_preload)
    logger.info("Enabled services: %s", ", ".join(_enabled_services(args)))
    logger.info("=" * 60)


def _log_ollama_endpoints(logger, ollama_mode: bool) -> None:
    """Log the compatibility endpoints when Ollama mode is enabled."""
    if not ollama_mode:
        return
    logger.info("Ollama API: http://localhost:11434/api/")
    logger.info("OpenAI API: http://localhost:11434/v1/")


def _log_preload_mode(logger, no_preload: bool) -> None:
    """Log whether preloading is enabled for the managed daemon."""
    if no_preload:
        logger.info("Model preloading: DISABLED (will load on first request)")
        return
    logger.info("Model preloading: ENABLED")


def _enabled_services(args: argparse.Namespace) -> list[str]:
    """Return formatted service descriptions for startup logging."""
    services = [
        _service_description("AIRUNNER_LLM_ON", "LLM", os.environ.get("AIRUNNER_LLM_MODEL_PATH")),
        _service_description("AIRUNNER_SD_ON", "Stable Diffusion", args.art_model),
        _service_description("AIRUNNER_TTS_ON", "TTS", args.tts_model),
        _service_description("AIRUNNER_STT_ON", "STT", args.stt_model),
    ]
    enabled = [service for service in services if service]
    return enabled or ["None"]


def _service_description(
    env_name: str,
    label: str,
    model_path: Optional[str],
) -> Optional[str]:
    """Format one enabled-service startup description."""
    if os.environ.get(env_name) != "1":
        return None
    if not model_path:
        return label
    return f"{label} ({model_path})"


def _prepare_daemon_config(args: argparse.Namespace, port: int) -> Path:
    """Clone daemon config with per-invocation host and port overrides."""
    from airunner_services.runtimes.daemon_config import DaemonConfig
    from airunner_services.config.runtime_layout import (
        build_runtime_directory_layout,
    )

    base_config = DaemonConfig(args.daemon_config)
    config = copy.deepcopy(base_config.config)
    server = config.setdefault("server", {})
    server["host"] = args.host
    server["port"] = port
    layout = build_runtime_directory_layout()
    layout.ensure_exists()
    fd, temp_path = tempfile.mkstemp(
        dir=layout.config_dir,
        prefix="airunner-headless-",
        suffix=".yaml",
    )
    os.close(fd)
    temp_config = DaemonConfig(Path(temp_path))
    temp_config.config = config
    temp_config.save()
    return Path(temp_path)


def _build_daemon_client(config_path: Path):
    """Create the daemon client used by the headless supervisor."""
    from airunner_services.daemon_client.launcher import DaemonLauncher
    from airunner_services.daemon_client.gui_daemon_client import (
        GuiDaemonClient,
    )
    from airunner_services.runtimes.bundle_layout import (
        build_linux_bundle_layout,
    )
    from airunner_services.settings import DEV_ENV

    bundle_layout = build_linux_bundle_layout()

    launcher = DaemonLauncher(
        config_path=config_path,
        stdout=None,
        stderr=None,
        working_directory=bundle_layout.bundle_root,
    )
    return GuiDaemonClient(
        config_path=config_path,
        launcher=launcher,
        auto_start=False,
        detect_stale_dev_daemon=DEV_ENV,
    )


def _prepare_managed_daemon_launch() -> None:
    """Run database and test-mode setup before launching a managed daemon."""
    from airunner_services.database.setup_database import setup_database

    setup_database()


def _register_shutdown_handlers() -> None:
    """Translate process signals into KeyboardInterrupt for cleanup flow."""
    signal.signal(signal.SIGINT, _handle_shutdown_signal)
    signal.signal(signal.SIGTERM, _handle_shutdown_signal)


def _handle_shutdown_signal(_signum, _frame) -> None:
    """Raise KeyboardInterrupt so the normal cleanup path runs."""
    raise KeyboardInterrupt()


def _monitor_managed_daemon(client, logger) -> int:
    """Keep the supervisor alive while the managed daemon remains healthy."""
    logger.info("Managed daemon ready at %s", client.base_url)
    logger.info("Press Ctrl+C to stop the managed daemon.")
    while True:
        client.health_check()
        time.sleep(1)


def _cleanup_client(client) -> None:
    """Stop only the managed daemon subprocess, when one exists."""
    if client is None:
        return
    client.disconnect(stop_process=True)


def _cleanup_config(config_path: Optional[Path]) -> None:
    """Remove the temporary daemon config used for this invocation."""
    if config_path is None:
        return
    try:
        config_path.unlink(missing_ok=True)
    except TypeError:
        if config_path.exists():
            config_path.unlink()


def _print_banner() -> None:
    """Print the existing AI Runner headless banner."""
    print(BANNER)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the daemon-backed headless CLI."""
    args = _build_parser().parse_args(argv)
    if not _validate_host_binding(args):
        return 2

    port = _resolve_port(args)
    _configure_environment(args, port)
    _print_banner()
    logger, log_level = _configure_logging()
    _log_startup(logger, args, port, log_level)
    _register_shutdown_handlers()

    config_path: Optional[Path] = None
    client = None

    try:
        config_path = _prepare_daemon_config(args, port)
        client = _build_daemon_client(config_path)
        if client.ensure_connected(auto_start=False):
            logger.info("Connected to existing daemon at %s", client.base_url)
            logger.info("Leaving existing daemon running.")
            return 0
        if args.connect_only:
            logger.error("No running daemon found at %s", client.base_url)
            return 1
        _prepare_managed_daemon_launch()
        logger.info("Starting managed daemon at %s", client.base_url)
        if not client.ensure_connected(auto_start=True):
            logger.error("Failed to start daemon: %s", client.last_error)
            return 1
        return _monitor_managed_daemon(client, logger)
    except KeyboardInterrupt:
        logger.info("Shutdown requested")
        return 0
    except RuntimeError as exc:
        logger.error("Daemon became unavailable: %s", exc)
        return 1
    except Exception as exc:
        logger.error("Fatal error: %s", exc, exc_info=True)
        return 1
    finally:
        _cleanup_client(client)
        _cleanup_config(config_path)

if __name__ == "__main__":
    raise SystemExit(main())
