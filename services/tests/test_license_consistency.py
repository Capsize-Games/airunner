"""License consistency guard for the AIRunner package surfaces (issue #2058).

The project is GPL-3.0-only. The repo-root LICENSE, every ``license=``
metadata field, the PyPI license classifiers and the README license badge must
agree, or downstream users/redistributors cannot determine their obligations
and PyPI metadata misleads. These tests lock that invariant in place.
"""

from __future__ import annotations

from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]

EXPECTED_LICENSE = "GPL-3.0-only"
EXPECTED_CLASSIFIER = (
    "License :: OSI Approved :: GNU General Public License v3 (GPLv3)"
)


def _root_setup_kwargs() -> dict:
    """Build the root GUI package setup kwargs via runpy in-process.

    Importing ``setup`` would trigger the full setuptools machinery; running
    the file as a script and capturing ``setup()`` kwargs keeps the test cheap
    and side-effect free.
    """
    import runpy
    import sys

    captured: dict = {}
    import setuptools

    def _fake_setup(**kwargs) -> None:
        captured.update(kwargs)

    _orig_setup = setuptools.setup
    setuptools.setup = _fake_setup
    try:
        # setup.py inserts <repo>/shared into sys.path itself.
        runpy.run_path(
            str(_PROJECT_ROOT / "setup.py"),
            run_name="__airunner_setup_probe__",
        )
    finally:
        setuptools.setup = _orig_setup
        sys.modules.pop("setup", None)
    assert captured, "root setup() was not called"
    return captured


def test_repo_root_license_is_gpl_with_copyright() -> None:
    """The LICENSE file is the full GPL-3.0 text and carries a copyright line."""
    text = (_PROJECT_ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "GNU GENERAL PUBLIC LICENSE" in text
    assert "Version 3" in text
    assert "Copyright" in text, "LICENSE must carry a copyright notice"


def test_root_setup_metadata_is_gpl() -> None:
    kwargs = _root_setup_kwargs()
    assert kwargs["license"] == EXPECTED_LICENSE
    assert EXPECTED_CLASSIFIER in kwargs["classifiers"]


def test_services_and_native_metadata_are_gpl() -> None:
    """Both builder surfaces share airunner_common metadata and must agree."""
    from airunner_common.package_metadata import (  # noqa: E402
        build_native_setup_kwargs,
        build_services_setup_kwargs,
        LICENSE_CLASSIFIERS,
    )

    assert LICENSE_CLASSIFIERS == [EXPECTED_CLASSIFIER]
    for kwargs in (
        build_services_setup_kwargs(package_source_dir="src"),
        build_native_setup_kwargs(package_source_dir="src"),
    ):
        assert kwargs["license"] == EXPECTED_LICENSE
        assert kwargs["classifiers"] == LICENSE_CLASSIFIERS


def test_vendored_services_setup_metadata_is_gpl() -> None:
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


def test_vendored_native_setup_metadata_is_gpl() -> None:
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


def test_readme_badge_declares_gpl() -> None:
    """The README license badge must agree with the metadata."""
    readme = (_PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    assert "License: GPL v3" in readme
    assert "License-GPLv3-blue" in readme
