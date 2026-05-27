"""Service-owned file completeness checks for OpenVoice assets."""

from __future__ import annotations

from pathlib import Path

from airunner_services.database.bootstrap.openvoice_bootstrap_data import OPENVOICE_FILES


def get_required_openvoice_files(model_id: str) -> list[str] | None:
    """Return the required file list for an OpenVoice model repo."""
    model_data = OPENVOICE_FILES.get(model_id)
    if not model_data:
        return None
    return model_data.get("files")


def check_missing_openvoice_files(
    model_path: str,
    model_id: str,
) -> tuple[bool, list[str]]:
    """Check whether an OpenVoice model directory has all required files."""
    if not model_path or not Path(model_path).exists():
        return False, []
    required_files = get_required_openvoice_files(model_id)
    if required_files is None:
        return True, []
    model_dir = Path(model_path)
    missing_files = [
        file_path
        for file_path in required_files
        if not (model_dir / file_path).exists()
    ]
    return len(missing_files) == 0, missing_files


def should_trigger_openvoice_download(
    model_path: str,
    model_id: str,
) -> tuple[bool, dict[str, object]]:
    """Return whether missing OpenVoice files should trigger a download."""
    all_exist, missing_files = check_missing_openvoice_files(
        model_path,
        model_id,
    )
    if all_exist:
        return False, {}
    return True, {
        "repo_id": model_id,
        "missing_files": missing_files,
        "model_path": model_path,
        "model_type": "tts_openvoice",
    }


__all__ = [
    "check_missing_openvoice_files",
    "get_required_openvoice_files",
    "should_trigger_openvoice_download",
]
