"""Shared fixtures for the P05 Linux bundle regression tests.

Single concern: repository paths, isolated script loaders, module
fixtures, and synthetic bundle builders shared by the
test_release_p05_* suites. CPU-only; no model, network, or database
side effects.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = REPO_ROOT / "packaging" / "linux" / "services-bundle-spec.toml"
MATRIX_PATH = REPO_ROOT / "release-planning" / "linux-v1" / "feature-matrix.md"
SERVICES_SETUP = REPO_ROOT / "services" / "setup.py"
SERVICES_SRC = REPO_ROOT / "services" / "src" / "airunner_services"
SCRIPTS_DIR = REPO_ROOT / "scripts"

# Synthetic stand-in for the content-safety policy payload. Production
# policy bytes must never appear in a test fixture (P05 guardrail).
SYNTHETIC_POLICY = b"synthetic-test-policy-fixture\n"

WARN_CLEAN = """\
missing module named winreg - imported by os (conditional)
missing module named nt - imported by shutil (conditional)
missing module named _winapi - imported by subprocess (conditional)
missing module named msvcrt - imported by subprocess (optional)
missing module named _frozen_importlib_external - imported by importlib (opt)
missing module named 'collections.abc' - imported by traceback (top-level)
excluded module named _frozen_importlib - imported by importlib (optional)
"""


def _load_script_module(name: str) -> types.ModuleType:
    """Load one scripts/*.py in isolation (dev tooling, not installed)."""
    path = SCRIPTS_DIR / f"{name}.py"
    sys.path.insert(0, str(SCRIPTS_DIR))
    try:
        spec = importlib.util.spec_from_file_location(
            f"release_p05_{name}", path
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        # dataclasses resolves string annotations through the class's
        # module in sys.modules; register before exec (standard
        # importlib practice the P01 loader did not need).
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(SCRIPTS_DIR))
    return module


@pytest.fixture(scope="module")
def inspect_mod() -> types.ModuleType:
    """The bundle inspector as a module object."""
    return _load_script_module("inspect_linux_bundle")


@pytest.fixture(scope="module")
def assemble_mod() -> types.ModuleType:
    """The bundle assembler as a module object."""
    return _load_script_module("assemble_linux_bundle")


@pytest.fixture(scope="module")
def spec(inspect_mod: types.ModuleType) -> dict[str, Any]:
    """The parsed services bundle spec."""
    return dict(inspect_mod.load_spec(SPEC_PATH))


@pytest.fixture(scope="module")
def services_setup() -> types.ModuleType:
    """services/setup.py executed with the final setup() call stripped.

    Same pattern as test_core_runtime_dependencies.py: exposes the
    requirement groups, extras builders, and console scripts as data
    without building or installing anything.
    """
    source = SERVICES_SETUP.read_text(encoding="utf-8").replace(
        'setup(**build_services_setup_kwargs(package_source_dir="src"))',
        "",
    )
    module = types.ModuleType("services_setup_probe_p05")
    module.__file__ = str(SERVICES_SETUP)
    exec(compile(source, str(SERVICES_SETUP), "exec"), module.__dict__)
    return module


def module_exists(module: str) -> bool:
    """True when a module exists as a file or a package directory."""
    relpath = module.split("airunner_services.", 1)[1].replace(".", "/")
    return (SERVICES_SRC / f"{relpath}.py").is_file() or (
        SERVICES_SRC / relpath / "__init__.py"
    ).is_file()


def module_file(module: str) -> Path:
    """Map an airunner_services module to its checkout source file."""
    return SERVICES_SRC / (
        module.split("airunner_services.", 1)[1].replace(".", "/") + ".py"
    )


def _write_executable(path: Path) -> None:
    """Write a fake executable bit-bearing bundle entry point."""
    path.write_bytes(b"fake-elf-bundle-executable\n")
    path.chmod(0o755)


def _skeleton_bundle(bundle: Path, spec: dict[str, Any]) -> None:
    """Create the executable, bin dir, and _internal payload."""
    _write_executable(bundle / str(spec["bundle"]["executable"]))
    (bundle / str(spec["runtimes"]["bin_dir"])).mkdir(parents=True)
    (bundle / "_internal").mkdir(parents=True)
    (bundle / "_internal" / "base_library.zip").write_bytes(b"fake-zip")


def _stage_fixture_entry(bundle: Path, entry: dict[str, Any]) -> None:
    """Stage one synthetic payload file for a required data entry."""
    source = str(entry["source"])
    dest_dir = bundle / str(entry["dest"])
    dest_dir.mkdir(parents=True, exist_ok=True)
    if any(char in source for char in "*?["):
        filename = "probe.dat"
    else:
        filename = Path(source).name
    if filename.endswith(".dat"):
        content = SYNTHETIC_POLICY
    else:
        content = b"fixture-payload\n"
    (dest_dir / filename).write_bytes(content)


def make_bundle(
    root: Path,
    spec: dict[str, Any],
    assemble_mod: types.ModuleType,
    base: str = "testrev",
) -> Path:
    """Build a synthetic bundle tree from the spec, with a manifest.

    Every required [[data]] entry contributes one file (exact sources
    land as dest/basename, globs as dest/probe.dat); the policy payload
    is SYNTHETIC_POLICY. Returns the bundle directory.
    """
    bundle = root / "bundle"
    bundle.mkdir(parents=True, exist_ok=True)
    _skeleton_bundle(bundle, spec)
    for entry in spec.get("data", []):
        if entry.get("required", True):
            _stage_fixture_entry(bundle, entry)
    assemble_mod.write_manifest(bundle, spec, base)
    return bundle


def make_toc(spec: dict[str, Any], drop: frozenset[str]) -> str:
    """Render a synthetic PYZ-00.toc covering the spec's modules."""
    names = [entry["module"] for entry in spec.get("console_script", [])]
    names.extend(spec["code"].get("hidden_imports", []))
    for parent in spec["code"].get("collect_submodules", []):
        names.append(parent)
        names.append(f"{parent}.probe_child")
    lines = ["('/fake/work/PYZ-00.pyz',", " ["]
    for name in names:
        if name in drop:
            continue
        lines.append(f"  ('{name}', '/fake/src.py', 'PYMODULE'),")
    lines.append(" ])")
    return "\n".join(lines) + "\n"


def scrubbed_env() -> dict[str, str]:
    """Return the process env with repository lookups removed."""
    return {
        key: value for key, value in os.environ.items() if key != "PYTHONPATH"
    }


def write_warn(path: Path, dirty: bool) -> Path:
    """Write a synthetic PyInstaller warn file, clean or dirty."""
    text = WARN_CLEAN
    if dirty:
        text += (
            "missing module named torch - imported by "
            "airunner_services.fake (top-level)\n"
        )
    path.write_text(text, encoding="utf-8")
    return path


def write_toc(
    path: Path, spec: dict[str, Any], drop: frozenset[str] = frozenset()
) -> Path:
    """Write a synthetic PYZ-00.toc, optionally dropping modules."""
    path.write_text(make_toc(spec, drop), encoding="utf-8")
    return path
