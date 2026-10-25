"""Launcher for AI Runner's headless service surface.

Services-only entry point (the ``airunner-native`` console script). The
Qt desktop client was removed, so this module only dispatches to the
service-owned headless entry point
(``airunner_services.bin.airunner_headless``). There is no desktop
bootstrap here: no splash screen, no Qt runtime, no component-settings
registration, and no GUI package resolution.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional, Sequence

from airunner_common.startup_env import (
    configure_early_torch_allocator_environment,
)
from airunner_native.repo_paths import resolve_repo_root


configure_early_torch_allocator_environment()

from airunner_common.get_logger import get_logger
from airunner_common.settings import AIRUNNER_BASE_PATH
from airunner_common.settings import AIRUNNER_DISABLE_FACEHUGGERSHIELD
from airunner_common.settings import AIRUNNER_LOG_LEVEL
from airunner_native.crash_handler import install_crash_handlers
from airunner_common.logging_utils import (
    configure_noisy_loggers,
)

_HEADLESS_VALUES = {"1", "true", "yes", "on"}

logger = get_logger(__name__, level=AIRUNNER_LOG_LEVEL)


def _activate_facehugger_shield() -> None:
    """Activate the standalone Facehugger Shield package."""
    if AIRUNNER_DISABLE_FACEHUGGERSHIELD:
        return

    from facehuggershield.huggingface import activate

    activate(**_facehugger_activate_kwargs())


def _facehugger_activate_kwargs() -> dict[str, object]:
    """Return Facehugger activation settings for the service process."""
    airunner_path = AIRUNNER_BASE_PATH
    venv_path = os.path.dirname(os.path.dirname(sys.executable))
    site_packages_path = os.path.join(
        venv_path,
        "lib",
        f"python{sys.version_info.major}.{sys.version_info.minor}",
        "site-packages",
    )
    repo_root = resolve_repo_root(Path(__file__))
    api_src_path = str(repo_root / "api" / "src")
    model_src_path = str(repo_root / "model" / "src")
    services_src_path = str(repo_root / "services" / "src")
    native_src_path = str(repo_root / "native" / "src")

    return {
        "activate_shadowlogger": True,
        "darklock_os_allow_network": True,
        "darklock_os_whitelisted_operations": [
            "makedirs",
            "mkdir",
            "open",
        ],
        "darklock_os_whitelisted_directories": [
            airunner_path,
            os.path.join(airunner_path, "cache"),
            os.path.join(airunner_path, "cache/.webcache"),
            os.path.join(airunner_path, "code"),
            os.path.join(airunner_path, "data"),
            os.path.join(airunner_path, "static"),
            os.path.join(airunner_path, "text"),
            os.path.join(airunner_path, "text/other"),
            os.path.join(airunner_path, "text/other/documents"),
            os.path.join(airunner_path, "text/other/ebooks"),
            os.path.join(airunner_path, "text/other/research"),
            os.path.join(airunner_path, "text/other/webpages"),
            os.path.join(airunner_path, "text/models"),
            os.path.join(airunner_path, "text/rag"),
            os.path.join(airunner_path, "art"),
            os.path.join(airunner_path, "art/models"),
            os.path.join(airunner_path, "art/other"),
            os.path.join(airunner_path, "art/other/images"),
            os.path.join(airunner_path, "certs"),
            os.path.join(os.path.expanduser("~"), ".triton/cache/"),
            os.path.join(os.path.expanduser("~"), ".cache/airunner-rag/"),
            os.path.join(os.path.expanduser("~"), "Desktop/"),
            "/dev/",
            "/proc/",
            site_packages_path,
            "/usr/share/zoneinfo/",
            api_src_path,
            model_src_path,
            services_src_path,
            native_src_path,
            "/tmp/",
            "/etc/",
            "/var/log/airunner/",
            os.path.join(os.path.expanduser("~"), "nltk_data/"),
            os.path.join(
                os.path.expanduser("~"),
                "nltk_data/corpora/stopwords/english",
            ),
            os.path.join(
                os.path.expanduser("~"),
                "nltk_data/corpora/stopwords/",
            ),
            os.path.join(os.path.expanduser("~"), "nltk_data/corpora/"),
            os.path.join(
                os.path.expanduser("~"),
                "nltk_data/corpora/stopwords",
            ),
            os.path.join(os.path.expanduser("~"), "nltk_data"),
            os.path.join(os.path.expanduser("~"), "nltk_data/corpora"),
        ],
        "nullscream_whitelist": [
            "transformers",
            "diffusers",
            "sentencepiece",
        ],
        "nullscream_blacklist": [
            "huggingface_hub",
            "google.cloud.storage",
        ],
    }


def _parse_launcher_args(
    argv: Optional[Sequence[str]] = None,
) -> tuple[bool, list[str]]:
    """Return whether headless mode is requested and sanitized args."""
    requested = os.environ.get("AIRUNNER_HEADLESS", "0")
    headless_requested = requested.strip().lower() in _HEADLESS_VALUES
    sanitized_args: list[str] = []
    for arg in argv or sys.argv[1:]:
        if arg == "--headless":
            headless_requested = True
            continue
        sanitized_args.append(arg)
    return headless_requested, sanitized_args


def _run_headless_launcher(
    argv: Optional[Sequence[str]] = None,
) -> int:
    """Delegate execution to the service-owned headless entry point."""
    from airunner_services.bin.airunner_headless import main as headless_main

    return headless_main(argv)


def _configure_test_mode():
    """Configure database settings for test mode.

    Kept here because the services sidecar launchers import this helper
    to avoid opening a real GUI during tests (see
    scripts/import_boundary_allowlist.py). The imports below stay
    function-scoped so importing this module never requires the
    application packages.
    """
    from airunner.components.llm.data.llm_generator_settings import (
        LLMGeneratorSettings,
    )
    from airunner.components.settings.data.application_settings import (
        ApplicationSettings,
    )
    from airunner.components.settings.data.path_settings import PathSettings

    PathSettings.objects.first() or PathSettings.objects.create()
    ApplicationSettings.objects.first() or ApplicationSettings.objects.create()

    llm_settings = LLMGeneratorSettings.objects.first()
    if llm_settings is None:
        llm_settings = LLMGeneratorSettings.objects.create()

    test_model_path = os.environ.get("AIRUNNER_TEST_MODEL_PATH")
    if test_model_path:
        LLMGeneratorSettings.objects.update(
            llm_settings.id,
            model_path=test_model_path,
        )
        logger.info(f"Test mode: Using model path: {test_model_path}")
    else:
        logger.warning(
            "Test mode: AIRUNNER_TEST_MODEL_PATH not set. "
            "Tests requiring LLM will fail. "
            "Use pytest --model=/path/to/model or set environment variable."
        )


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Dispatch to the headless launcher flow.

    The desktop client was removed: a non-headless launch is an
    explicit error, not a desktop bootstrap.
    """
    install_crash_handlers()
    configure_noisy_loggers()
    headless_requested, sanitized_args = _parse_launcher_args(argv)
    if not headless_requested:
        print(
            "The AIRunner desktop client was removed; only the headless "
            "service surface remains. Re-run with --headless (or set "
            "AIRUNNER_HEADLESS=1).",
            file=sys.stderr,
        )
        return 2
    if argv is not None:
        sys.argv = [sys.argv[0], *sanitized_args]
    return _run_headless_launcher(sanitized_args)


if __name__ == "__main__":
    raise SystemExit(main())
