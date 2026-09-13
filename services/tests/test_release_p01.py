"""Regression tests for release issue P01.

Proves:

- The launcher no longer attempts to compile Qt UI resources (or write
  anything into the installed package) at application startup — it only
  verifies the compiled resource module is importable, raising an
  actionable ``RuntimeError`` when it is not, instead of silently
  swallowing a failed build attempt.
- ``scripts/build_ui.py``'s ``find_missing_generated_ui_files`` /
  ``verify_generated_resources`` helpers (the "verify before packaging"
  tool wired into ``setup.py``) correctly detect a missing compiled
  ``_ui.py`` companion and a missing compiled resource module.

No GUI launch, real model, network, or database side effects. The
scripts/build_ui.py helpers are exercised against a synthetic tmp_path
tree, not the real checkout, so this stays independent of any
pre-existing gaps in the real repository's generated files.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

import airunner.launcher as launcher

_BUILD_UI_PATH = (
    Path(__file__).resolve().parents[2] / "scripts" / "build_ui.py"
)


def _load_build_ui_module():
    """Load scripts/build_ui.py in isolation (it is dev tooling, not an
    installed package, so it is not normally importable by name)."""
    scripts_dir = _BUILD_UI_PATH.parent
    sys.path.insert(0, str(scripts_dir))
    try:
        spec = importlib.util.spec_from_file_location(
            "release_p01_build_ui", _BUILD_UI_PATH
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(scripts_dir))
    return module


@pytest.fixture(scope="module")
def build_ui_module():
    return _load_build_ui_module()


def test_verify_ui_resources_available_succeeds_without_subprocess_or_write(
    monkeypatch,
) -> None:
    """Happy path: resources present, no subprocess call, no package write.

    Checks the marker file the old (removed) code used to write is left
    exactly as found — present or absent — rather than assuming a clean
    checkout, since a pre-P01 run may have left one behind.
    """
    monkeypatch.setattr(
        subprocess,
        "run",
        mock.Mock(side_effect=AssertionError("must not spawn a subprocess")),
    )
    marker = Path(launcher.COMPONENTS_PATH) / "ui_build_marker"
    existed_before = marker.exists()

    launcher.verify_ui_resources_available()

    assert marker.exists() == existed_before


def test_verify_ui_resources_available_raises_actionable_error_when_missing(
    monkeypatch,
) -> None:
    """A missing compiled resource module fails loudly, not silently."""
    monkeypatch.setattr(
        subprocess,
        "run",
        mock.Mock(side_effect=AssertionError("must not spawn a subprocess")),
    )
    # sys.modules[name] = None is the standard way to force the next
    # `import name` to raise ImportError without touching real files.
    monkeypatch.setitem(
        sys.modules, "airunner.gui.resources.feather_rc", None
    )

    with pytest.raises(RuntimeError, match="feather_rc"):
        launcher.verify_ui_resources_available()


def test_build_ui_if_needed_is_gone() -> None:
    """The old build-at-startup function must be removed, not just unused."""
    assert not hasattr(launcher, "build_ui_if_needed")


def test_find_missing_generated_ui_files_detects_gap(
    tmp_path, build_ui_module
) -> None:
    complete_ui = tmp_path / "complete.ui"
    complete_ui.write_text("<ui/>")
    (tmp_path / "complete_ui.py").write_text("# generated")

    incomplete_ui = tmp_path / "incomplete.ui"
    incomplete_ui.write_text("<ui/>")

    missing = build_ui_module.find_missing_generated_ui_files(tmp_path)
    assert missing == [incomplete_ui]


def test_verify_generated_resources_flags_missing_resource_module(
    tmp_path, build_ui_module
) -> None:
    problems = build_ui_module.verify_generated_resources(tmp_path)
    assert any("feather_rc.py" in problem for problem in problems)


def test_verify_generated_resources_clean_when_everything_present(
    tmp_path, build_ui_module
) -> None:
    resources_dir = tmp_path / "gui" / "resources"
    resources_dir.mkdir(parents=True)
    (resources_dir / "feather_rc.py").write_text("# generated")

    assert build_ui_module.verify_generated_resources(tmp_path) == []
