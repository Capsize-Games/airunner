"""Coverage config tests: the services suite measures the services tree."""

import configparser
from pathlib import Path


def _config() -> configparser.ConfigParser:
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    with open(Path(__file__).resolve().parents[2] / ".coveragerc") as handle:
        parser.read_file(handle)
    return parser


def test_coverage_measures_services_tree() -> None:
    """Coverage source must be the services package, not the dead GUI tree."""
    assert _config()["run"]["source"].strip() == "services/src/airunner_services"


def test_coverage_has_no_stale_gui_source() -> None:
    """No source entry may be the removed src/airunner tree."""
    root = Path(__file__).resolve().parents[2]
    text = (root / ".coveragerc").read_text(encoding="utf-8")
    assert "\nsource = src/airunner\n" not in text


def test_coverage_omits_no_stale_resource_dirs() -> None:
    """The removed resources_* omits must be gone with the GUI tree."""
    omit = _config()["run"]["omit"]
    assert "resources" not in omit


def test_coverage_omits_local_virtualenvs() -> None:
    """Local venvs must not pollute measured files."""
    omit = _config()["run"]["omit"]
    assert ".venv/*" in omit
