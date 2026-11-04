"""Test-mode database defaults for service launchers."""

from __future__ import annotations

import logging
import os

from airunner_services.database.models.application_settings import (
    ApplicationSettings,
)
from airunner_services.database.models.llm_generator_settings import (
    LLMGeneratorSettings,
)
from airunner_services.database.models.path_settings import PathSettings

logger = logging.getLogger(__name__)


def configure_test_mode() -> None:
    """Create test-mode settings and apply an optional test model path."""
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
        logger.info("Test mode: Using model path: %s", test_model_path)
    else:
        logger.warning(
            "Test mode: AIRUNNER_TEST_MODEL_PATH not set. "
            "Tests requiring LLM will fail. "
            "Use pytest --model=/path/to/model or set environment variable."
        )


__all__ = ["configure_test_mode"]
