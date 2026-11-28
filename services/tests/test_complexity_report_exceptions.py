"""Opt-in hotspot gate tests for scripts/services_complexity_report.py (#2410).

The report stays advisory by default; ``--fail-on-hotspot`` turns
unexcepted hotspots (and stale exception entries) into a non-zero exit.
Radon is stubbed with the stdlib only when the real package is absent;
the stub is installed per-test via monkeypatch so the parity suite's
``importorskip("radon")`` keeps skipping.
"""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest


_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_DIR = _PROJECT_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


def _install_radon_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provide a minimal radon surface so the report module imports."""

    complexity = types.ModuleType("radon.complexity")
    complexity.cc_rank = lambda _complexity: "A"  # noqa: E731
    complexity.cc_visit = lambda _source: []  # noqa: E731

    metrics = types.ModuleType("radon.metrics")

    class _Total:
        volume = 0.0

    class _Halstead:
        total = _Total()

    metrics.h_visit = lambda _source: _Halstead()  # noqa: E731
    metrics.mi_visit = lambda _source, multi=True: 100.0  # noqa: E731

    raw = types.ModuleType("radon.raw")

    class _Raw:
        def __init__(self, source: str) -> None:
            lines = [ln for ln in source.splitlines() if ln.strip()]
            self.sloc = len(lines)
            self.lloc = len(lines)
            self.comments = 0
            self.blank = 0

    raw.analyze = lambda source: _Raw(source)  # noqa: E731

    package = types.ModuleType("radon")
    package.__path__ = []
    package.complexity = complexity
    package.metrics = metrics
    package.raw = raw

    monkeypatch.setitem(sys.modules, "radon", package)
    monkeypatch.setitem(sys.modules, "radon.complexity", complexity)
    monkeypatch.setitem(sys.modules, "radon.metrics", metrics)
    monkeypatch.setitem(sys.modules, "radon.raw", raw)


@pytest.fixture()
def report_module(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Import the report module with a stubbed radon, cleaned up after."""
    _install_radon_stub(monkeypatch)
    monkeypatch.chdir(tmp_path)
    import importlib

    module = importlib.import_module("scripts.services_complexity_report")
    importlib.reload(module)
    return module


def _write_tree(root: Path, files: dict[str, str]) -> Path:
    """Create a fake source tree and return it."""
    for rel, content in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return root


def _long_function_body(lines: int = 25) -> str:
    """Return a function body exceeding the 20-line default limit."""
    assigns = "\n".join(f"    value_{index} = {index}" for index in range(lines))
    return f"def long_function():\n{assigns}\n    return value_0\n"


def _run_main(module, source: Path, output: Path, **overrides) -> int:
    """Run the report main() against the fake tree with test arguments."""
    arguments = SimpleNamespace(
        path=source,
        output_dir=output,
        exclude="build,dist,vendor,__pycache__",
        max_file_lines=250,
        max_class_lines=250,
        max_function_lines=20,
        max_complexity_rank="B",
        min_mi=65.0,
        xenon_max_average=None,
        xenon_max_modules=None,
        fail_on_hotspot=False,
    )
    for key, value in overrides.items():
        setattr(arguments, key, value)
    original_parse_args = module.parse_args
    module.parse_args = lambda: arguments
    try:
        return module.main()
    finally:
        module.parse_args = original_parse_args


def _payload(output: Path) -> dict:
    return json.loads((output / "services_complexity_report.json").read_text())


def test_known_exceptions_default_empty_and_report_stays_advisory(
    report_module, tmp_path: Path
) -> None:
    """No broad exceptions granted; unflagged runs stay green (exit 0)."""
    assert report_module.KNOWN_HOTSPOT_EXCEPTIONS == ()
    source = _write_tree(tmp_path / "src", {"hot.py": _long_function_body()})
    output = tmp_path / "out"
    assert _run_main(report_module, source, output) == 0
    assert _payload(output)["summary"]["unexcepted_hotspots"] == 1


def test_fail_flag_passes_on_clean_tree(report_module, tmp_path: Path) -> None:
    """A tree with no hotspots passes the opt-in gate."""
    source = _write_tree(tmp_path / "src", {"ok.py": "def ok():\n    return 1\n"})
    output = tmp_path / "out"
    assert _run_main(report_module, source, output, fail_on_hotspot=True) == 0


def test_fail_flag_fails_on_unexcepted_hotspot_and_still_writes_outputs(
    report_module, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The gate fails loudly but still emits the JSON/Markdown reports."""
    source = _write_tree(tmp_path / "src", {"hot.py": _long_function_body()})
    output = tmp_path / "out"
    assert _run_main(report_module, source, output, fail_on_hotspot=True) == 1
    assert (output / "services_complexity_report.json").is_file()
    assert (output / "services_complexity_report.md").is_file()
    assert "Unexcepted hotspots remain" in capsys.readouterr().err


def test_excepted_hotspot_passes_gate(
    report_module, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Listed hotspots are accepted when the gate is on."""
    monkeypatch.setattr(report_module, "KNOWN_HOTSPOT_EXCEPTIONS", ("hot.py",))
    source = _write_tree(tmp_path / "src", {"hot.py": _long_function_body()})
    output = tmp_path / "out"
    assert _run_main(report_module, source, output, fail_on_hotspot=True) == 0
    assert _payload(output)["summary"]["excepted_hotspots"] == 1


def test_stale_exception_fails_gate(
    report_module,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exception entries that match no hotspot fail instead of rotting."""
    monkeypatch.setattr(report_module, "KNOWN_HOTSPOT_EXCEPTIONS", ("gone.py",))
    source = _write_tree(tmp_path / "src", {"ok.py": "def ok():\n    return 1\n"})
    output = tmp_path / "out"
    assert _run_main(report_module, source, output, fail_on_hotspot=True) == 1
    assert "stale exception: gone.py" in capsys.readouterr().err


def test_summary_counts_partitioned_hotspots(report_module) -> None:
    """Summary counts split excepted from unexcepted hotspot files."""
    thresholds = report_module.Thresholds()
    reports = [
        {
            "path": "kept.py",
            "long_functions": [{"name": "f", "line_count": 30}],
            "long_classes": [],
            "complex_blocks": [],
            "file_lines": 40,
            "mi": 90.0,
        },
        {
            "path": "todo.py",
            "long_functions": [{"name": "g", "line_count": 40}],
            "long_classes": [],
            "complex_blocks": [],
            "file_lines": 50,
            "mi": 90.0,
        },
        {
            "path": "clean.py",
            "long_functions": [],
            "long_classes": [],
            "complex_blocks": [],
            "file_lines": 10,
            "mi": 90.0,
        },
    ]
    summary = report_module.summarize_reports(
        reports, thresholds, exceptions=("kept.py",)
    )
    assert summary["excepted_hotspots"] == 1
    assert summary["unexcepted_hotspots"] == 1
    assert summary["hotspot_files"] == 2
    unexcepted, excepted = report_module.partition_hotspots(
        reports, thresholds, ("kept.py",)
    )
    assert [report["path"] for report in excepted] == ["kept.py"]
    assert [report["path"] for report in unexcepted] == ["todo.py"]
    assert report_module.stale_exceptions(reports, thresholds, ("gone.py",)) == [
        "gone.py"
    ]
