"""Extras-surface regression tests for services/setup.py (issue #2198).

Pre-extraction hardening before airunner-services moves to its own
repository. #2061 and #2039 were both caused by an extras name that was
referenced (in README.md, in the Dockerfile) but did not exist in
services/setup.py's own ``extras_require`` -- a class of bug an
extraction is a prime opportunity to reintroduce, per #2198's own
verification requirement. These tests lock two invariants in place:

- Every extras group has a real dependency payload, except a small,
  explicit allowlist of intentional no-op profile flags.
- Every extras name referenced in the README actually exists.
- Every extras group's dependency set is resolvable by pip (``--dry-run``,
  so this doesn't actually install anything -- it exercises the real
  resolver against the real index without downloading multi-gigabyte
  wheels).
"""

from __future__ import annotations

import subprocess
import sys
import types
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SETUP = _PROJECT_ROOT / "services" / "setup.py"

# "core" and "linux" are documented profile flags with no dependency
# payload of their own (they select apt packages / Dockerfile branches,
# not Python packages) -- an empty list there is intentional, not a typo.
_INTENTIONALLY_EMPTY_EXTRAS = frozenset({"core", "linux"})


def _load_setup_module() -> types.ModuleType:
    """Execute services/setup.py without running setup()."""
    source = _SETUP.read_text(encoding="utf-8").replace(
        'setup(**build_services_setup_kwargs(package_source_dir="src"))', ""
    )
    module = types.ModuleType("services_setup_probe")
    module.__file__ = str(_SETUP)
    exec(compile(source, str(_SETUP), "exec"), module.__dict__)
    return module


def _extras() -> dict[str, list[str]]:
    return _load_setup_module().build_services_extras_require()


def test_no_accidentally_empty_extras() -> None:
    """Every extras group has dependencies, except the documented no-ops."""
    extras = _extras()
    for name, deps in extras.items():
        if name in _INTENTIONALLY_EMPTY_EXTRAS:
            assert deps == [], (
                f"{name!r} is documented as an intentional no-op profile "
                "flag but now has dependencies -- update "
                "_INTENTIONALLY_EMPTY_EXTRAS or investigate the regression"
            )
        else:
            assert deps, f"{name!r} has no dependencies (issues #2061/#2039)"


def test_readme_extras_references_all_exist() -> None:
    """Every `airunner-services[...]` extra named in the README is real."""
    import re

    extras = _extras()
    readme = (_PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    referenced = re.findall(r'airunner-services\[([a-zA-Z0-9_,-]+)\]', readme)
    assert referenced, "no airunner-services[...] references found in README"
    for group in referenced:
        for name in group.split(","):
            assert name in extras, (
                f"README references airunner-services[{name}], which is "
                "not a real extras name (issue #2061)"
            )


@pytest.mark.slow
@pytest.mark.parametrize("extra_name", sorted(_extras()))
def test_extra_resolves_with_pip_dry_run(extra_name: str) -> None:
    """Every extras group's dependency set actually resolves."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--dry-run",
            "--extra-index-url",
            "https://download.pytorch.org/whl/cu129",
            "-e",
            f"{_PROJECT_ROOT / 'services'}[{extra_name}]",
        ],
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0, (
        f"pip could not resolve airunner-services[{extra_name}]:\n"
        f"{result.stdout}\n{result.stderr}"
    )
