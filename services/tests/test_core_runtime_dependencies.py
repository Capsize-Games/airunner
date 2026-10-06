"""Core service imports must be declared by the services distribution."""

from __future__ import annotations

import types
from pathlib import Path

from packaging.requirements import Requirement

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SETUP = _PROJECT_ROOT / "services" / "setup.py"


def _core_requirements() -> set[str]:
    source = _SETUP.read_text(encoding="utf-8").replace(
        'setup(**build_services_setup_kwargs(package_source_dir="src"))', ""
    )
    module = types.ModuleType("services_setup_probe")
    module.__file__ = str(_SETUP)
    exec(compile(source, str(_SETUP), "exec"), module.__dict__)
    return {Requirement(value).name.lower() for value in module.CORE_REQUIREMENTS}


def test_services_core_declares_text_formatter_dependencies() -> None:
    """A services-only install imports all three from its core text path."""
    assert {"pygments", "markdown", "requests"} <= _core_requirements()

