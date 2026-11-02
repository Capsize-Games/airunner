"""Dispatch frozen console-script aliases without installing Python packages."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path


_ENTRY_POINTS = {
    "airunner-core": ("airunner_services.daemon", "main"),
    "airunner-daemon": ("airunner_services.daemon", "main"),
    "airunner-headless": ("airunner_services.bin.airunner_headless", "main"),
    "airunner-service": ("airunner_services.bin.airunner_service", "main"),
    "airunner-generate-migration": (
        "airunner_services.bin.generate_migration", "main"
    ),
    "airunner-hf-download": ("airunner_services.bin.airunner_hf_download", "main"),
    "airunner-civitai-download": (
        "airunner_services.bin.airunner_civitai_download", "main"
    ),
    "airunner-cleanup-llm-models": (
        "airunner_services.bin.cleanup_llm_models", "main"
    ),
    "airunner-docker-build": ("airunner_services.bin.docker_build", "main"),
    "airunner-docker-wrapper": ("airunner_services.bin.docker_wrapper", "main"),
    "airunner-generate-cert": ("airunner_services.bin.generate_cert", "main"),
}


def main() -> object:
    """Run the entry point selected by the installed executable name."""
    executable = Path(sys.argv[0]).name
    try:
        module_name, function_name = _ENTRY_POINTS[executable]
    except KeyError as exc:
        raise SystemExit(f"unknown AIRunner console command: {executable}") from exc
    function = getattr(importlib.import_module(module_name), function_name)
    return function()
