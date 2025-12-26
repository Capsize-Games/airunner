#!/usr/bin/env python3
"""
Headless AI Runner server for eval testing and API access.

This script starts AI Runner in headless mode (no GUI) with just
the HTTP API server for /llm, /art, /stt, /tts endpoints.

Usage:
    airunner-headless
    airunner-headless --host 0.0.0.0 --port 8080
    airunner-headless --ollama-mode  # Run as Ollama replacement on port 11434
    airunner-headless --model /path/to/llm/model  # Load specific LLM model
    airunner-headless --art-model /path/to/art/model  # Load specific art model
    airunner-headless --tts-model /path/to/tts/model  # Load specific TTS model
    airunner-headless --stt-model /path/to/stt/model  # Load specific STT model
    airunner-headless --no-preload  # Don't preload models, load on first request
    airunner-headless --help

Environment Variables:
    AIRUNNER_HEADLESS: Set to 1 (automatically set by this script)
    AIRUNNER_HTTP_HOST: Override host (default: 0.0.0.0)
    AIRUNNER_HTTP_PORT: Override port (default: 8080)
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
    # Start with defaults (0.0.0.0:8080)
    airunner-headless

    # Start on custom port
    airunner-headless --port 9000

    # Start on localhost only
    airunner-headless --host 127.0.0.1 --port 8080

    # Run as Ollama replacement (port 11434) for VS Code integration
    airunner-headless --ollama-mode

    # Load a specific LLM model at startup
    airunner-headless --model /path/to/Qwen2.5-7B-Instruct-4bit

    # Run without preloading models (load on first request)
    airunner-headless --no-preload

    # Enable Stable Diffusion and load a specific art model
    airunner-headless --enable-art --art-model /path/to/stable-diffusion-v1-5

    # Enable all services with specific models
    airunner-headless --enable-llm --enable-art --enable-tts --enable-stt \\
        --model /path/to/llm --art-model /path/to/art
"""

import argparse
import sys
import os
import signal

def main():
    """Main entry point for headless AI Runner server."""
    parser = argparse.ArgumentParser(
        description="AI Runner Headless Server - HTTP API for LLM, Art, TTS, STT",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--host",
        type=str,
        default=os.environ.get("AIRUNNER_HTTP_HOST", "0.0.0.0"),
        help="Host address to bind to (default: 0.0.0.0)",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=None,  # Will be set based on --ollama-mode
        help="Port to listen on (default: 8080, or 11434 in ollama-mode)",
    )

    parser.add_argument(
        "--ollama-mode",
        action="store_true",
        default=os.environ.get("AIRUNNER_OLLAMA_MODE", "0") == "1",
        help="Run as Ollama replacement on port 11434 for VS Code integration",
    )

    # Model path arguments
    parser.add_argument(
        "--model", "-m",
        type=str,
        # NOTE: Do not import settings/DB models here.
        # Importing DB models pulls in airunner.settings at module import time, which
        # would freeze AIRUNNER_HEADLESS_SERVER_HOST before we set it below.
        default=os.environ.get("AIRUNNER_LLM_MODEL_PATH"),
        help="Path to LLM model to load at startup (or load on first request)",
    )

    parser.add_argument(
        "--art-model",
        type=str,
        default=os.environ.get("AIRUNNER_ART_MODEL_PATH"),
        help="Path to art/Stable Diffusion model to load",
    )

    parser.add_argument(
        "--tts-model",
        type=str,
        default=os.environ.get("AIRUNNER_TTS_MODEL_PATH"),
        help="Path to TTS model to load",
    )

    parser.add_argument(
        "--stt-model",
        type=str,
        default=os.environ.get("AIRUNNER_STT_MODEL_PATH"),
        help="Path to STT model to load",
    )

    # Service enable flags
    parser.add_argument(
        "--enable-llm",
        action="store_true",
        default=None,
        help="Enable LLM service (default: enabled unless --no-preload)",
    )

    parser.add_argument(
        "--enable-art",
        action="store_true",
        default=None,
        help="Enable Stable Diffusion/art service",
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
        help="Don't preload models at startup, load them on first request instead",
    )

    args = parser.parse_args()

    # Determine port based on mode
    if args.ollama_mode:
        port = 11434  # Ollama's default port
    elif args.port is not None:
        port = args.port
    else:
        port = int(os.environ.get("AIRUNNER_HTTP_PORT", "8080"))

    # Set environment variables from args BEFORE importing settings
    # AIRUNNER_HEADLESS_SERVER_HOST/PORT are used by settings.py at import time
    os.environ["AIRUNNER_HEADLESS_SERVER_HOST"] = args.host
    os.environ["AIRUNNER_HEADLESS_SERVER_PORT"] = str(port)
    # Also set the old names for backwards compatibility
    os.environ["AIRUNNER_HTTP_HOST"] = args.host
    os.environ["AIRUNNER_HTTP_PORT"] = str(port)
    
    # Set Ollama mode flag for server.py to use
    os.environ["AIRUNNER_OLLAMA_MODE"] = "1" if args.ollama_mode else "0"

    # Set model paths if provided
    if args.model:
        os.environ["AIRUNNER_LLM_MODEL_PATH"] = args.model
    if args.art_model:
        os.environ["AIRUNNER_ART_MODEL_PATH"] = args.art_model
    if args.tts_model:
        os.environ["AIRUNNER_TTS_MODEL_PATH"] = args.tts_model
    if args.stt_model:
        os.environ["AIRUNNER_STT_MODEL_PATH"] = args.stt_model

    # Set no-preload flag
    if args.no_preload:
        os.environ["AIRUNNER_NO_PRELOAD"] = "1"

    # Now import settings after environment is configured
    from airunner.settings import AIRUNNER_LOG_LEVEL
    from airunner.utils.application import get_logger
    from airunner.launcher import _configure_test_mode
    from airunner.setup_database import setup_database
    from airunner.components.application.api.api import API
    from airunner.components.server.api import server

    # Configure logging
    logger = get_logger(__name__, level=AIRUNNER_LOG_LEVEL)

    # Determine which services to enable based on:
    # 1. Explicit --enable-* flags
    # 2. Model path provided (implies service should be enabled)
    # 3. Environment variables
    # 4. Defaults (LLM on, others off)
    
    # LLM service
    if args.enable_llm is not None:
        os.environ["AIRUNNER_LLM_ON"] = "1" if args.enable_llm else "0"
    elif args.model:
        # If a model path is provided, enable the service
        os.environ["AIRUNNER_LLM_ON"] = "1"
    else:
        os.environ.setdefault("AIRUNNER_LLM_ON", "1")
    
    # Art/Stable Diffusion service (enable by default in headless)
    if args.enable_art is not None:
        os.environ["AIRUNNER_SD_ON"] = "1" if args.enable_art else "0"
    elif args.art_model:
        os.environ["AIRUNNER_SD_ON"] = "1"
    else:
        os.environ.setdefault("AIRUNNER_SD_ON", "1")
    
    # TTS service (enable by default in headless)
    if args.enable_tts is not None:
        os.environ["AIRUNNER_TTS_ON"] = "1" if args.enable_tts else "0"
    elif args.tts_model:
        os.environ["AIRUNNER_TTS_ON"] = "1"
    else:
        os.environ.setdefault("AIRUNNER_TTS_ON", "1")
    
    # STT service (enable by default in headless)
    if args.enable_stt is not None:
        os.environ["AIRUNNER_STT_ON"] = "1" if args.enable_stt else "0"
    elif args.stt_model:
        os.environ["AIRUNNER_STT_ON"] = "1"
    else:
        os.environ.setdefault("AIRUNNER_STT_ON", "1")

    # ControlNet defaults to off
    os.environ.setdefault("AIRUNNER_CN_ON", "0")

    # Disable knowledge system in headless mode (has GUI dependencies)
    os.environ.setdefault("AIRUNNER_KNOWLEDGE_ON", "0")

    # Print ASCII banner
    banner = """
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
    print(banner)

    logger.info("=" * 60)
    if args.ollama_mode:
        logger.info("AI Runner Headless Server (Ollama Mode)")
        logger.info("Running as Ollama replacement for VS Code integration")
    else:
        logger.info("AI Runner Headless Server")
    logger.info("=" * 60)
    logger.info(f"Host: {args.host}")
    logger.info(f"Port: {port}")
    if args.ollama_mode:
        logger.info("Ollama API: http://localhost:11434/api/")
        logger.info("OpenAI API: http://localhost:11434/v1/")
    logger.info(f"Log Level: {AIRUNNER_LOG_LEVEL}")
    if args.no_preload:
        logger.info("Model preloading: DISABLED (will load on first request)")
    else:
        logger.info("Model preloading: ENABLED")
    logger.info("=" * 60)

    # Show enabled services and model paths
    services = []
    if os.environ.get("AIRUNNER_LLM_ON") == "1":
        model_info = f" ({os.environ.get('AIRUNNER_LLM_MODEL_PATH')})" if os.environ.get("AIRUNNER_LLM_MODEL_PATH") else ""
        services.append(f"LLM{model_info}")
    if os.environ.get("AIRUNNER_SD_ON") == "1":
        model_info = f" ({args.art_model})" if args.art_model else ""
        services.append(f"Stable Diffusion{model_info}")
    if os.environ.get("AIRUNNER_TTS_ON") == "1":
        model_info = f" ({args.tts_model})" if args.tts_model else ""
        services.append(f"TTS{model_info}")
    if os.environ.get("AIRUNNER_STT_ON") == "1":
        model_info = f" ({args.stt_model})" if args.stt_model else ""
        services.append(f"STT{model_info}")

    logger.info(
        f"Enabled services: {', '.join(services) if services else 'None'}"
    )
    logger.info("=" * 60)

    api = None

    def _handle_shutdown_signal(_signum, _frame):
        # Force a Python-level unwind so our `finally` cleanup runs.
        raise KeyboardInterrupt()

    signal.signal(signal.SIGINT, _handle_shutdown_signal)
    signal.signal(signal.SIGTERM, _handle_shutdown_signal)

    try:
        # Setup database (run migrations)
        setup_database()

        # If no model was specified, attempt to load the default from DB settings.
        # This must happen AFTER database setup, and AFTER host/port env vars are set.
        if not os.environ.get("AIRUNNER_LLM_MODEL_PATH"):
            try:
                from airunner.components.llm.data.llm_generator_settings import (
                    LLMGeneratorSettings,
                )

                llm_generator_settings = LLMGeneratorSettings.objects.first()
                if llm_generator_settings and getattr(
                    llm_generator_settings, "model_path", None
                ):
                    os.environ["AIRUNNER_LLM_MODEL_PATH"] = (
                        llm_generator_settings.model_path
                    )
            except Exception:
                # Non-fatal: server can still start without a preselected model.
                pass

        # Configure test mode if running tests
        if os.environ.get("AIRUNNER_ENVIRONMENT") == "test":
            _configure_test_mode()

        # Create API instance (which inherits from App)
        # This initializes the app, workers, and HTTP server.
        #
        # NOTE: API is implemented as a process-wide singleton. In headless
        # mode we need to guarantee we get a *fresh* instance configured for
        # headless operation (and not a previously created GUI-mode instance).
        try:
            API._instance = None  # type: ignore[attr-defined]
        except Exception:
            pass

        api = API(headless=True)

        # Store API instance globally so get_api() can access it
        server._api = api

        logger.info("Starting headless server...")
        api.run()

        # If api.run() ever returns normally, treat it as a clean shutdown.
        return 0

    except KeyboardInterrupt:
        logger.info("Shutdown requested")
        return 0
    except SystemExit as e:
        # Some internal components call sys.exit(), including the Qt event-loop
        # runner. Treat a 0 exit code as normal shutdown.
        code = e.code
        if code in (None, 0):
            return 0
        logger.error(f"SystemExit: {e}", exc_info=True)
        return int(code) if isinstance(code, int) else 1
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1
    finally:
        if api is not None:
            try:
                api.cleanup()
            except Exception:
                logger.exception("Error during headless cleanup")


if __name__ == "__main__":
    raise SystemExit(main())
