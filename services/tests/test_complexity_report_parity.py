"""Guard test for complexity-report parity between GUI and services (issue #2052).

Both ``scripts/gui_complexity_report.py`` and
``scripts/services_complexity_report.py`` must keep an identical skip rule
(``_is_generated``) and identical default excludes so the two reports measure
the same source surface. If one side starts skipping (or including) a class of
files that the other does not, this test fails fast.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_DIR = _PROJECT_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

# These imports require the optional analysis tooling (radon), which lives in
# the ``[analysis]`` extra of the root package (setup.py). They are imported
# here rather than at module top so the test collection failure is explicit.
from scripts import gui_complexity_report  # noqa: E402
from scripts import services_complexity_report  # noqa: E402


def test_default_excludes_are_identical() -> None:
    """Both report scripts must skip the same default directories."""
    assert (
        gui_complexity_report.DEFAULT_EXCLUDES
        == services_complexity_report.DEFAULT_EXCLUDES
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
def test_is_generated_verdicts_are_identical(path: str) -> None:
    """``_is_generated`` must agree for representative paths."""
    p = Path(path)
    assert (
        gui_complexity_report._is_generated(p)
        == services_complexity_report._is_generated(p)
    ), (
        f"Complexity skip-rule divergence for {path!r}: "
        f"gui={gui_complexity_report._is_generated(p)}, "
        f"services={services_complexity_report._is_generated(p)}"
    )


def test_is_generated_skips_generated_and_keeps_source() -> None:
    """Sanity check the shared skip rule itself."""
    assert gui_complexity_report._is_generated(Path("foo_ui.py")) is True
    assert gui_complexity_report._is_generated(Path("feather_rc.py")) is True
    assert services_complexity_report._is_generated(Path("foo_ui.py")) is True
    assert services_complexity_report._is_generated(Path("bar.py")) is False
    assert services_complexity_report._is_generated(Path("x/y/baz_ui.py")) is True
