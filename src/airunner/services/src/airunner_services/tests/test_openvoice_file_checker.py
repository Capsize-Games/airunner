"""Tests for service-owned OpenVoice runtime helpers."""

from pathlib import Path
from tempfile import TemporaryDirectory

from airunner_services.contract_enums import AvailableLanguage
from airunner_services.bootstrap.openvoice_bootstrap_data import OPENVOICE_FILES
from airunner_services.runtimes.openvoice_file_checker import (
    should_trigger_openvoice_download,
)
from airunner_services.utils.text.language_detection import detect_language


_OPENVOICE_MODEL_ID = "myshell-ai/MeloTTS-English"


def test_detect_language_ignores_code_blocks() -> None:
    """Language detection should ignore fenced code in the input."""
    text = (
        "```python\nprint('bonjour')\n```\n"
        "This is an English sentence about testing OpenVoice loading."
    )

    assert detect_language(text) is AvailableLanguage.EN


def test_should_trigger_openvoice_download_for_missing_files() -> None:
    """Missing OpenVoice model files should trigger a download."""
    should_download, info = should_trigger_openvoice_download(
        "/nonexistent/openvoice/model",
        _OPENVOICE_MODEL_ID,
    )

    assert should_download
    assert info["missing_files"] == []
    assert info["repo_id"] == _OPENVOICE_MODEL_ID


def test_should_not_trigger_openvoice_download_when_files_exist() -> None:
    """Complete OpenVoice model directories should not trigger download."""
    with TemporaryDirectory() as tmpdir:
        for file_name in OPENVOICE_FILES[_OPENVOICE_MODEL_ID]["files"]:
            full_path = Path(tmpdir) / file_name
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.touch()

        should_download, info = should_trigger_openvoice_download(
            tmpdir,
            _OPENVOICE_MODEL_ID,
        )

    assert not should_download
    assert info == {}
