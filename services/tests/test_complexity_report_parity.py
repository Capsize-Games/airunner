"""Guard tests for the active services complexity report (issue #2052)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_DIR = _PROJECT_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

# These imports require the optional analysis tooling (radon), which lives in
# the ``[analysis]`` extra of the root package (setup.py). Skip the module when
# that extra is absent instead of failing collection: the runtime smoke suites
# select by marker across this whole directory, so a collection error here
# fails four jobs that have nothing to do with complexity reports.
pytest.importorskip("radon")

from scripts import services_complexity_report  # noqa: E402


def test_default_excludes_cover_generated_and_dependency_directories() -> None:
    """The services analyzer excludes generated and vendored trees by default."""
    assert {"build", "dist", "vendor", "__pycache__"}.issubset(
        services_complexity_report.DEFAULT_EXCLUDES
    )
    assert services_complexity_report.DEFAULT_ROOT == Path(
        "services/src/airunner_services"
    )


@pytest.mark.parametrize(
    "path",
    [
        "foo_ui.py",
        "foo_rc.py",
        "feather_rc.py",
        "bar.py",
        "x/y/baz_ui.py",
        "x/y/baz_rc.py",
        "x/y/plain.py",
        "widget.py",
    ],
)
def test_is_generated_verdicts(path: str) -> None:
    """The services report skips generated modules and retains ordinary source."""
    p = Path(path)
    expected = p.stem.endswith(("_ui", "_rc"))
    assert services_complexity_report._is_generated(p) is expected


def test_complexity_report_handles_missing_xenon_without_losing_radon(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Radon report data survives when the optional Xenon executable is absent."""
    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "sample.py").write_text("def sample():\n    return 1\n")
    output_dir = tmp_path / "out"
    arguments = SimpleNamespace(
        path=source_root,
        output_dir=output_dir,
        exclude="build,dist,vendor,__pycache__",
        max_file_lines=250,
        max_class_lines=250,
        max_function_lines=20,
        max_complexity_rank="B",
        min_mi=65.0,
        xenon_max_average=None,
        xenon_max_modules=None,
    )
    monkeypatch.setattr(services_complexity_report, "parse_args", lambda: arguments)
    monkeypatch.setattr(services_complexity_report.shutil, "which", lambda _: None)
    monkeypatch.setattr(
        services_complexity_report.Path,
        "is_file",
        lambda self: False,
    )

    assert services_complexity_report.main() == 0
    payload = json.loads(
        (output_dir / "services_complexity_report.json").read_text()
    )
    assert payload["summary"]["files_analyzed"] == 1
    assert payload["file_reports"][0]["path"] == "sample.py"
    assert payload["xenon"]["status"] == "unavailable"
    markdown = (output_dir / "services_complexity_report.md").read_text()
    assert "Status: **unavailable**" in markdown


def test_xenon_nonzero_is_reported_as_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    """A Xenon violation is never mislabeled as unavailable or passed."""
    arguments = SimpleNamespace(
        xenon_max_average=None,
        xenon_max_modules=None,
        max_complexity_rank="B",
    )

    monkeypatch.setattr(services_complexity_report.Path, "is_file", lambda self: True)
    monkeypatch.setattr(
        services_complexity_report.subprocess,
        "run",
        lambda *args, **kwargs: type(
            "Result", (), {"returncode": 2, "stdout": "violation", "stderr": ""}
        )(),
    )

    result = services_complexity_report.run_xenon(Path("."), (), arguments)
    assert result == {"status": "failed", "returncode": 2, "output": "violation"}


def test_xenon_zero_is_reported_as_passed(monkeypatch: pytest.MonkeyPatch) -> None:
    """A successful Xenon execution is explicitly distinguished from a skip."""
    arguments = SimpleNamespace(
        xenon_max_average=None,
        xenon_max_modules=None,
        max_complexity_rank="B",
    )

    monkeypatch.setattr(services_complexity_report.Path, "is_file", lambda self: True)
    monkeypatch.setattr(
        services_complexity_report.subprocess,
        "run",
        lambda *args, **kwargs: type(
            "Result", (), {"returncode": 0, "stdout": "", "stderr": ""}
        )(),
    )

    result = services_complexity_report.run_xenon(Path("."), (), arguments)
    assert result == {"status": "passed", "returncode": 0, "output": ""}


def test_complexity_report_rejects_empty_source_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """An empty or fully excluded tree cannot produce an empty success report."""
    arguments = SimpleNamespace(
        path=tmp_path,
        output_dir=tmp_path / "out",
        exclude="build,dist,vendor,__pycache__",
        max_file_lines=250,
        max_class_lines=250,
        max_function_lines=20,
        max_complexity_rank="B",
        min_mi=65.0,
        xenon_max_average=None,
        xenon_max_modules=None,
    )
    monkeypatch.setattr(services_complexity_report, "parse_args", lambda: arguments)
    assert services_complexity_report.main() == 2
    assert "No Python source files found" in capsys.readouterr().err
