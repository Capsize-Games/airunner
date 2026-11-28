"""License consistency guard for the AIRunner package surfaces (issue #2058).

The project is Apache-2.0 (relicensed 2026-11-28, see RELICENSING.md). The
repo-root LICENSE, every ``license=`` metadata field, the PyPI license
classifiers and the README license statement must agree, or downstream
users/redistributors cannot determine their obligations and PyPI metadata
misleads. These tests lock that invariant in place.
"""

from __future__ import annotations

from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]

EXPECTED_LICENSE = "Apache-2.0"
EXPECTED_CLASSIFIER = "License :: OSI Approved :: Apache Software License"


def test_repo_root_license_is_apache_with_copyright() -> None:
    """The LICENSE file is the full Apache-2.0 text and NOTICE carries copyright."""
    text = (_PROJECT_ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "Apache License" in text
    assert "Version 2.0" in text
    notice = (_PROJECT_ROOT / "NOTICE").read_text(encoding="utf-8")
    assert "Copyright" in notice, "NOTICE must carry a copyright statement"


def test_vendored_services_setup_metadata_is_apache() -> None:
    """services/setup.py is self-contained; its vendored metadata must agree."""
    import runpy
    import sys

    captured: dict = {}
    import setuptools

    def _fake_setup(**kwargs) -> None:
        captured.update(kwargs)

    _orig_setup = setuptools.setup
    setuptools.setup = _fake_setup
    try:
        runpy.run_path(
            str(_PROJECT_ROOT / "services" / "setup.py"),
            run_name="__airunner_services_setup_probe__",
        )
    finally:
        setuptools.setup = _orig_setup
        sys.modules.pop("setup", None)
    assert captured, "services setup() was not called"
    assert captured["license"] == EXPECTED_LICENSE
    assert EXPECTED_CLASSIFIER in captured["classifiers"]


def test_vendored_native_setup_metadata_is_apache() -> None:
    """native/setup.py is self-contained; its vendored metadata must agree."""
    import runpy
    import sys

    captured: dict = {}
    import setuptools

    def _fake_setup(**kwargs) -> None:
        captured.update(kwargs)

    _orig_setup = setuptools.setup
    setuptools.setup = _fake_setup
    try:
        runpy.run_path(
            str(_PROJECT_ROOT / "native" / "setup.py"),
            run_name="__airunner_native_setup_probe__",
        )
    finally:
        setuptools.setup = _orig_setup
        sys.modules.pop("setup", None)
    assert captured, "native setup() was not called"
    assert captured["license"] == EXPECTED_LICENSE
    assert EXPECTED_CLASSIFIER in captured["classifiers"]


def test_readme_declares_apache() -> None:
    """The README license statement must agree with the metadata."""
    readme = (_PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    assert "Apache-2.0 licensed" in readme
