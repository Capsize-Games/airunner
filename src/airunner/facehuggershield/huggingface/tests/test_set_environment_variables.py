"""
Unit tests for set_environment_variables.py in the facehuggershield.huggingface module.

Covers all branches and environment variable settings.
"""

import os
import pytest
from unittest.mock import patch

import airunner.facehuggershield.huggingface.set_environment_variables as set_env_mod


def _get_all_hf_env_vars():
    # List of all env vars set by set_huggingface_environment_variables
    return [
        "HF_ALLOW_DOWNLOADS",
        "HF_HUB_DISABLE_TELEMETRY",
        "HF_HUB_OFFLINE",
        "HF_HOME",
        "HF_ENDPOINT",
        "HF_INFERENCE_ENDPOINT",
        "HF_HUB_DISABLE_PROGRESS_BARS",
        "HF_HUB_DISABLE_SYMLINKS_WARNING",
        "HF_HUB_DISABLE_EXPERIMENTAL_WARNING",
        "HF_ASSETS_CACHE",
        "HF_TOKEN",
        "HF_HUB_VERBOSITY",
        "HF_HUB_LOCAL_DIR_AUTO_SYMLINK_THRESHOLD",
        "HF_HUB_DOWNLOAD_TIMEOUT",
        "HF_HUB_ETAG_TIMEOUT",
        "HF_HUB_DISABLE_IMPLICIT_TOKEN",
        "HF_DATASETS_OFFLINE",
        "TRANSFORMERS_OFFLINE",
        "DIFFUSERS_VERBOSITY",
    ]


def test_set_huggingface_environment_variables_sets_all(monkeypatch):
    # Clear all relevant env vars
    for var in _get_all_hf_env_vars():
        os.environ.pop(var, None)
    monkeypatch.setattr(set_env_mod, "HF_ALLOW_DOWNLOADS", True)
    monkeypatch.setattr(set_env_mod, "HF_HUB_DISABLE_TELEMETRY", "1")
    monkeypatch.setattr(set_env_mod, "HF_HUB_OFFLINE", "1")
    monkeypatch.setattr(set_env_mod, "HF_HOME", "/tmp/hf")
    monkeypatch.setattr(set_env_mod, "HF_ENDPOINT", "https://hf.co")
    monkeypatch.setattr(
        set_env_mod, "HF_INFERENCE_ENDPOINT", "https://hf-infer.co"
    )
    monkeypatch.setattr(set_env_mod, "HF_HUB_DISABLE_PROGRESS_BARS", "1")
    monkeypatch.setattr(set_env_mod, "HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    monkeypatch.setattr(
        set_env_mod, "HF_HUB_DISABLE_EXPERIMENTAL_WARNING", "1"
    )
    monkeypatch.setattr(set_env_mod, "HF_ASSETS_CACHE", "/tmp/hf-cache")
    monkeypatch.setattr(set_env_mod, "HF_TOKEN", "token")
    monkeypatch.setattr(set_env_mod, "HF_HUB_VERBOSITY", "info")
    monkeypatch.setattr(
        set_env_mod, "HF_HUB_LOCAL_DIR_AUTO_SYMLINK_THRESHOLD", "10"
    )
    monkeypatch.setattr(set_env_mod, "HF_HUB_DOWNLOAD_TIMEOUT", "100")
    monkeypatch.setattr(set_env_mod, "HF_HUB_ETAG_TIMEOUT", "100")
    monkeypatch.setattr(set_env_mod, "HF_HUB_DISABLE_IMPLICIT_TOKEN", "1")
    monkeypatch.setattr(set_env_mod, "HF_DATASETS_OFFLINE", "1")
    monkeypatch.setattr(set_env_mod, "TRANSFORMERS_OFFLINE", "1")
    monkeypatch.setattr(set_env_mod, "DIFFUSERS_VERBOSITY", "info")

    set_env_mod.set_huggingface_environment_variables(allow_downloads=True)
    for var in _get_all_hf_env_vars():
        assert os.environ.get(var) is not None
    assert os.environ["HF_ALLOW_DOWNLOADS"] == "1"


def test_set_huggingface_environment_variables_no_download(monkeypatch):
    # Test with allow_downloads False disables download
    monkeypatch.setattr(set_env_mod, "HF_ALLOW_DOWNLOADS", False)
    set_env_mod.set_huggingface_environment_variables(allow_downloads=False)
    assert os.environ["HF_ALLOW_DOWNLOADS"] != "1"


def test_set_huggingface_environment_variables_default(monkeypatch):
    # Test with allow_downloads None uses module default
    monkeypatch.setattr(set_env_mod, "HF_ALLOW_DOWNLOADS", True)
    set_env_mod.set_huggingface_environment_variables()
    assert os.environ["HF_ALLOW_DOWNLOADS"] == "1"


def test_set_huggingface_environment_variables_print(monkeypatch):
    # Ensure the print statement is called
    with patch("builtins.print") as mock_print:
        monkeypatch.setattr(set_env_mod, "HF_ALLOW_DOWNLOADS", True)
        set_env_mod.set_huggingface_environment_variables()
        mock_print.assert_any_call(
            "Setting Hugging Face environment variables"
        )
