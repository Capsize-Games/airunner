#!/usr/bin/env python3
"""
Headless AI Runner server for eval testing and API access.

This script starts AI Runner in headless mode (no GUI) with just
the HTTP API server for /llm, /art, /stt, /tts endpoints.

Usage:
    airunner-headless
    airunner-headless --host 0.0.0.0 --port 8188
    airunner-headless --help

Environment Variables:
    AIRUNNER_HEADLESS: Set to 1 (automatically set by this script)
    AIRUNNER_HTTP_HOST: Override host (default: 0.0.0.0)
    AIRUNNER_HTTP_PORT: Override port (default: 8188)
    AIRUNNER_LLM_ON: Enable LLM service (default: 1)
    AIRUNNER_TTS_ON: Enable TTS service (default: 0)
    AIRUNNER_STT_ON: Enable STT service (default: 0)
    AIRUNNER_SD_ON: Enable Stable Diffusion (default: 0)
    AIRUNNER_CN_ON: Enable ControlNet (default: 0)

Examples:
    # Start with defaults (0.0.0.0:8188)
    airunner-headless

    # Start on custom port
    airunner-headless --port 9000

    # Start on localhost only
    airunner-headless --host 127.0.0.1 --port 8188

    # Enable all services
    AIRUNNER_LLM_ON=1 AIRUNNER_SD_ON=1 airunner-headless
"""

import argparse
import logging
import sys
import os

# CRITICAL: Set headless mode BEFORE importing App
os.environ["AIRUNNER_HEADLESS"] = "1"

from airunner.app import App


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
        default=int(os.environ.get("AIRUNNER_HTTP_PORT", "8188")),
        help="Port to listen on (default: 8188)",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level (default: INFO)",
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Set environment variables from args
    os.environ["AIRUNNER_HTTP_HOST"] = args.host
    os.environ["AIRUNNER_HTTP_PORT"] = str(args.port)

    # Default to LLM-only in headless mode (can be overridden by env vars)
    os.environ.setdefault("AIRUNNER_LLM_ON", "1")
    os.environ.setdefault("AIRUNNER_TTS_ON", "0")
    os.environ.setdefault("AIRUNNER_STT_ON", "0")
    os.environ.setdefault("AIRUNNER_SD_ON", "0")
    os.environ.setdefault("AIRUNNER_CN_ON", "0")

    # Disable knowledge system in headless mode (has GUI dependencies)
    os.environ.setdefault("AIRUNNER_KNOWLEDGE_ON", "0")

    logging.info("=" * 60)
    logging.info("AI Runner Headless Server")
    logging.info("=" * 60)
    logging.info(f"Host: {args.host}")
    logging.info(f"Port: {args.port}")
    logging.info(f"Log Level: {args.log_level}")
    logging.info("=" * 60)

    # Show enabled services
    services = []
    if os.environ.get("AIRUNNER_LLM_ON") == "1":
        services.append("LLM")
    if os.environ.get("AIRUNNER_SD_ON") == "1":
        services.append("Stable Diffusion")
    if os.environ.get("AIRUNNER_TTS_ON") == "1":
        services.append("TTS")
    if os.environ.get("AIRUNNER_STT_ON") == "1":
        services.append("STT")

    logging.info(
        f"Enabled services: {', '.join(services) if services else 'None'}"
    )
    logging.info("=" * 60)

    try:
        # Create API instance (which inherits from App)
        # This initializes the app, workers, and HTTP server
        from airunner.components.application.api.api import API

        api = API(initialize_gui=False)

        # Store API instance globally so get_api() can access it
        from airunner.components.server.api import server

        server._api = api

        logging.info("Starting headless server...")
        api.run()

    except KeyboardInterrupt:
        logging.info("Shutdown requested")
        sys.exit(0)
    except Exception as e:
        logging.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
