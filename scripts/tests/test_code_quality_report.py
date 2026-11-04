"""Regression checks for service-scoped code-quality path handling."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import code_quality_report  # noqa: E402


def test_service_scan_is_same_for_relative_and_absolute_roots() -> None:
    """Absolute checkout prefixes must not trigger path exclusions."""
    relative = Path("services/src/airunner_services")
    exclusions = ["alembic", "/data/", "vendor", "/bin/", "/db/", "/gui/"]

    relative_files = code_quality_report.find_python_files(relative, exclusions)
    absolute_files = code_quality_report.find_python_files(
        PROJECT_ROOT / relative, exclusions
    )

    assert relative_files
    assert set(relative_files) == set(absolute_files)


def test_slash_delimited_exclusion_matches_relative_component_only(
    tmp_path: Path,
) -> None:
    """Directory exclusions apply inside the scan root, not its absolute path."""
    root = tmp_path / "services" / "src"
    (root / "keep").mkdir(parents=True)
    (root / "services").mkdir()
    (root / "keep" / "module.py").write_text("value = 1\n")
    (root / "services" / "nested.py").write_text("value = 2\n")

    found = code_quality_report.find_python_files(root, ["/services/"])

    assert [path.relative_to(root).as_posix() for path in found] == [
        "keep/module.py"
    ]


def test_empty_scan_is_an_explicit_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A requested tree with no Python files exits nonzero with a clear reason."""
    monkeypatch.setattr(
        sys,
        "argv",
        ["code_quality_report.py", "--path", str(tmp_path), "--json"],
    )

    with pytest.raises(SystemExit) as exc_info:
        code_quality_report.main()

    assert exc_info.value.code == 2
    assert "No Python files found" in capsys.readouterr().err


def test_default_path_targets_services() -> None:
    """The CLI default points at the current service source tree."""
    assert code_quality_report.DEFAULT_PATH == Path(
        "services/src/airunner_services"
    )
