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


def test_importing_build_ui_does_not_require_pyside6() -> None:
    """A prior version of this fix crashed a real isolated build (see the
    two tests below): build_ui.py imported process_qss at module scope,
    which imports PySide6 -- unavailable in a PEP 517 isolated build
    environment (pyproject.toml's [build-system] requires only
    setuptools/wheel). Confirmed here at the module-graph level, and
    end to end by the sdist tests below."""
    scripts_dir = str(_BUILD_UI_PATH.parent)
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; sys.path.insert(0, sys.argv[1]); import build_ui; "
            "hits = [m for m in sys.modules if 'pyside' in m.lower() or "
            "'shiboken' in m.lower()]; "
            "print(','.join(hits)); sys.exit(1 if hits else 0)",
            scripts_dir,
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"PySide6-related modules loaded: {proc.stdout}"


_REPO_ROOT = _BUILD_UI_PATH.parent.parent


@pytest.fixture(scope="module")
def built_sdist(tmp_path_factory):
    """Actually run `setup.py sdist` and return the resulting tarball path.

    Exercises the real sdist-to-wheel packaging path end to end rather
    than only a synthetic tmp_path fixture (release issue P01 review
    finding F1): a prior version of this fix built a wheel successfully
    from a full checkout but crashed with ModuleNotFoundError when built
    from the sdist alone, because scripts/ was never shipped in it.
    """
    dist_dir = tmp_path_factory.mktemp("p01_sdist")
    proc = subprocess.run(
        [sys.executable, "setup.py", "sdist", "--dist-dir", str(dist_dir)],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    tarballs = list(dist_dir.glob("*.tar.gz"))
    assert len(tarballs) == 1, tarballs
    return tarballs[0]


def test_sdist_ships_the_scripts_packaging_verification_needs(
    built_sdist,
) -> None:
    import tarfile

    with tarfile.open(built_sdist) as archive:
        names = archive.getnames()

    assert any(name.endswith("scripts/build_ui.py") for name in names)
    assert any(name.endswith("scripts/process_qss.py") for name in names)


def test_build_py_from_extracted_sdist_does_not_hit_modulenotfounderror(
    built_sdist, tmp_path
) -> None:
    """The real regression: building from the sdist alone (not a full
    checkout) must reach the actual verification logic, not crash on a
    missing scripts/ import. The checkout has one known, pre-existing,
    unrelated generated-file gap (see the P01 PR description) which is
    an acceptable and expected failure reason here -- a ModuleNotFoundError
    for build_ui/process_qss is not."""
    import tarfile

    extract_dir = tmp_path / "extracted"
    extract_dir.mkdir()
    with tarfile.open(built_sdist) as archive:
        archive.extractall(extract_dir)

    (package_dir,) = extract_dir.iterdir()
    proc = subprocess.run(
        [
            sys.executable,
            "setup.py",
            "build_py",
            "--build-lib",
            str(tmp_path / "buildlib"),
        ],
        cwd=package_dir,
        capture_output=True,
        text=True,
        timeout=120,
    )

    combined_output = proc.stdout + proc.stderr
    assert "ModuleNotFoundError" not in combined_output, combined_output
    assert "No module named 'build_ui'" not in combined_output, combined_output
    if proc.returncode != 0:
        # Only the known, pre-existing, unrelated gap may cause a failure
        # here -- anything else is a real regression in this fix.
        assert "tts_setup.ui" in combined_output, combined_output
