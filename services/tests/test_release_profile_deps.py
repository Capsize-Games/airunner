"""Regression tests for release issues #2439 and #2441.

#2439: the computer_use extra shipped platform-wrong, apparently
unused dependencies (pyautogui/pygetwindow/pyscreeze with no Linux
marker, bundled into the desktop aggregate) while nothing under
services/src or native/src imports them.
#2441: the native launcher admitted services/common combinations
that predate the APIs it consumes.

Static analysis only: setup.py probing plus source-tree text scans.
No installs, no network, no models.
"""

from __future__ import annotations

import types
from pathlib import Path

from packaging.markers import default_environment
from packaging.requirements import Requirement

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SERVICES_SETUP = _PROJECT_ROOT / "services" / "setup.py"
_NATIVE_SETUP = _PROJECT_ROOT / "native" / "setup.py"
_SERVICES_SRC = _PROJECT_ROOT / "services" / "src"
_NATIVE_SRC = _PROJECT_ROOT / "native" / "src"

_LINUX_ENV = {**default_environment(), "platform_system": "Linux"}
_LINUX_ENV["python_version"] = "3.13"
_WINDOWS_ENV = {**default_environment(), "platform_system": "Windows"}
_WINDOWS_ENV["python_version"] = "3.13"

_UNUSED_GUI_MODULES = ("pyautogui", "pygetwindow", "pyscreeze")
_LINUX_ONLY_DISTS = ("pyautogui", "pyscreeze", "pygetwindow",
                     "python-xlib")


def _load_setup_module(path: Path, setup_call: str) -> types.ModuleType:
    """Execute a setup.py without running its final setup() call."""
    text = path.read_text(encoding="utf-8")
    text = text[: text.rindex(setup_call)]
    module = types.ModuleType(f"profile_deps_{path.parent.name}")
    module.__file__ = str(path)
    exec(compile(text, str(path), "exec"), module.__dict__)
    return module


def _services() -> types.ModuleType:
    """Load the services setup module without side effects."""
    return _load_setup_module(
        _SERVICES_SETUP,
        "\nsetup(**build_services_setup_kwargs",
    )


def _native() -> types.ModuleType:
    """Load the native setup module without side effects."""
    return _load_setup_module(
        _NATIVE_SETUP,
        "\nsetup(**build_native_setup_kwargs",
    )


def _dist_names(requirements: list[str]) -> set[str]:
    """Linux-evaluated distribution names for requirement strings."""
    names: set[str] = set()
    for raw in requirements:
        req = Requirement(raw)
        if req.marker is not None and not req.marker.evaluate(
            _LINUX_ENV
        ):
            continue
        names.add(req.name)
    return names


def test_computer_use_deps_are_linux_gated() -> None:
    """Every computer_use wheel dep carries a Linux marker."""
    module = _services()
    for raw in module.COMPUTER_USE_REQUIREMENTS:
        req = Requirement(raw)
        assert req.name in _LINUX_ONLY_DISTS, req.name
        assert req.marker is not None, raw
        assert req.marker.evaluate(_LINUX_ENV), raw
        assert not req.marker.evaluate(_WINDOWS_ENV), raw


def test_desktop_aggregate_excludes_computer_use() -> None:
    """The release profile no longer bundles the unused slice."""
    module = _services()
    extras = module.build_services_extras_require()
    desktop = _dist_names(extras["desktop"])
    unused = _dist_names(module.COMPUTER_USE_REQUIREMENTS)
    assert desktop.isdisjoint(unused), desktop & unused


def test_no_source_imports_computer_use_modules() -> None:
    """Nothing imports the gated modules, so dropping them is safe."""
    roots = (_SERVICES_SRC, _NATIVE_SRC)
    for root in roots:
        assert root.is_dir(), root
        for path in sorted(root.rglob("*.py")):
            text = path.read_text(encoding="utf-8")
            for module_name in _UNUSED_GUI_MODULES:
                assert module_name not in text, (
                    f"{path} references {module_name}"
                )


def test_native_common_floor_matches_services() -> None:
    """Native and services must resolve the same common line."""
    module = _native()
    for raw in module.NATIVE_BASE_REQUIREMENTS:
        req = Requirement(raw)
        if req.name == "airunner-common":
            assert req.specifier == Requirement(
                "airunner-common~=6.1.7"
            ).specifier, raw
            return
    raise AssertionError("airunner-common missing from native base")


def test_native_services_floors_exclude_stale_apis() -> None:
    """Native extras refuse services older than the shared-table line."""
    module = _native()
    extras = module.build_native_extras_require()
    for extra in ("services", "daemon", "gui", "desktop"):
        found = False
        for raw in extras[extra]:
            req = Requirement(raw)
            if req.name != "airunner-services":
                continue
            found = True
            assert req.specifier.contains(
                "6.1.5", prereleases=True
            ), raw
            assert not req.specifier.contains(
                "6.1.4", prereleases=True
            ), raw
        assert found, extra
