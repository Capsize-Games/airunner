"""Shared bootstrap metadata for multiple runtime consumers."""

from airunner.bootstrap.controlnet_bootstrap_data import (
    controlnet_bootstrap_data,
)
from airunner.bootstrap.openvoice_languages import (
    OPENVOICE_CORE_MODELS,
    OPENVOICE_LANGUAGE_MODELS,
    get_models_for_languages,
)
from airunner.bootstrap.llm_file_bootstrap_data import (
    LLM_FILE_BOOTSTRAP_DATA,
)
from airunner.bootstrap.openvoice_bootstrap_data import OPENVOICE_FILES
from airunner.bootstrap.path_settings_data import PATH_SETTINGS_DATA
from airunner.bootstrap.rmbg_bootstrap_data import RMBG_FILES
from airunner.bootstrap.sd_file_bootstrap_data import (
    SD_FILE_BOOTSTRAP_DATA,
)
from airunner.bootstrap.espeak_settings_data import (
    ESPEAK_SETTINGS_DATA,
)
from airunner.bootstrap.whisper import WHISPER_FILES

__all__ = [
    "controlnet_bootstrap_data",
    "ESPEAK_SETTINGS_DATA",
    "LLM_FILE_BOOTSTRAP_DATA",
    "OPENVOICE_FILES",
    "OPENVOICE_CORE_MODELS",
    "OPENVOICE_LANGUAGE_MODELS",
    "PATH_SETTINGS_DATA",
    "RMBG_FILES",
    "SD_FILE_BOOTSTRAP_DATA",
    "WHISPER_FILES",
    "get_models_for_languages",
]