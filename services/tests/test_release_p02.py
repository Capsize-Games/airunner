"""Release issue P02: NVIDIA profile defined, hashed, documented.

Static analysis only (no installs/network/GPU/models/databases);
install plus ``pip check`` evidence is in the lock header. The daemon
closure case additionally proves services base imports without the ML
profile (torch stays optional); the walker lives in
startup_closure_support.py.
"""

from __future__ import annotations

import re
import types
from pathlib import Path

from packaging.markers import default_environment
from packaging.requirements import Requirement

from startup_closure_support import startup_closure

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ROOT_SETUP = _PROJECT_ROOT / "setup.py"
_SERVICES_SETUP = _PROJECT_ROOT / "services" / "setup.py"
_NATIVE_SETUP = _PROJECT_ROOT / "native" / "setup.py"
_LOCK_PATH = _PROJECT_ROOT / "package" / "constraints-linux-nvidia-cu129.txt"
_IMPORT_TO_DIST = {"PIL": "pillow", "yaml": "pyyaml"}
_LINUX_ENV = {**default_environment(), "platform_system": "Linux"}
_LINUX_ENV["python_version"] = "3.13"
_PIN_LINE = re.compile(r"^([A-Za-z0-9_.\-]+)==([^\s\\;]+)")
_SERVICES_SETUP_CALL = "\nsetup(**build_services_setup_kwargs"
_NATIVE_SETUP_CALL = "\nsetup(**build_native_setup_kwargs"
_PACKAGE_ROOTS = {
    "airunner": _PROJECT_ROOT / "src" / "airunner",
    "airunner_services": _PROJECT_ROOT / "services" / "src"
    / "airunner_services",
    "airunner_native": _PROJECT_ROOT / "native" / "src" / "airunner_native",
}


def _load_setup_module(path: Path, setup_call: str) -> types.ModuleType:
    """Execute a setup.py without running its final setup() call."""
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        'Path("README.md")', f'Path(r"{_PROJECT_ROOT / "README.md"}")'
    )
    text = text[: text.rindex(setup_call)]
    module = types.ModuleType(f"p02_{path.parent.name}")
    module.__file__ = str(path)
    exec(compile(text, str(path), "exec"), module.__dict__)
    return module


def _normalise(name: str) -> str:
    """Normalize a distribution name for comparison."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _declared_dists(requirements: list[str]) -> set[str]:
    """Normalized distribution names declared by requirement strings."""
    return {_normalise(Requirement(raw).name) for raw in requirements}


def _profile_inputs() -> list[str]:
    """All requirement strings of the locked release profile."""
    root = _load_setup_module(_ROOT_SETUP, "\nsetup(")
    services = _load_setup_module(_SERVICES_SETUP, _SERVICES_SETUP_CALL)
    native = _load_setup_module(_NATIVE_SETUP, _NATIVE_SETUP_CALL)
    kwargs = services.build_services_setup_kwargs(package_source_dir="src")
    return [
        *root.GUI_REQUIREMENTS,
        *root.ML_REQUIREMENTS,
        *kwargs["install_requires"],
        *services.build_services_extras_require()["desktop"],
        *native.NATIVE_BASE_REQUIREMENTS,
    ]


def _lock_pins() -> dict[str, str]:
    """Map normalized distribution name to locked version."""
    lines = _LOCK_PATH.read_text(encoding="utf-8").splitlines()
    matches = (_PIN_LINE.match(line) for line in lines)
    return {_normalise(m.group(1)): m.group(2) for m in matches if m}


def test_release_profile_is_defined() -> None:
    """Profile extras exist with the cu129 torch line and no CPU docs."""
    root = _load_setup_module(_ROOT_SETUP, "\nsetup(")
    assert root.ML_REQUIREMENTS == [
        "torch==2.13.0+cu129",
        "torchvision==0.28.0+cu129",
        "torchaudio==2.11.0+cu129",
    ]
    text = _ROOT_SETUP.read_text(encoding="utf-8")
    assert '"nvidia": ML_REQUIREMENTS' in text
    services = _load_setup_module(_SERVICES_SETUP, _SERVICES_SETUP_CALL)
    desktop = services.build_services_extras_require()["desktop"]
    names = _declared_dists(desktop)
    assert "torch" in names
    assert "nvidia-cuda-runtime-cu12" in names
    assert not ({"pyside6", "shiboken6"} & names)
    for path in (_ROOT_SETUP, _SERVICES_SETUP):
        profile = path.read_text(encoding="utf-8")
        assert "whl/cpu" not in profile
        assert "download.pytorch.org/whl/cu129" in profile


def test_lock_covers_profile_requirements() -> None:
    """Every profile requirement is locked to a satisfying version."""
    local_roots = {"airunner", "airunner-services", "airunner-native"}
    pins = _lock_pins()
    assert pins, "lock file has no pins"
    for raw in _profile_inputs():
        req = Requirement(raw)
        if req.marker is not None and not req.marker.evaluate(_LINUX_ENV):
            continue
        name = _normalise(req.name)
        if name in local_roots:
            continue
        assert name in pins, f"{raw} is missing from the lock"
        assert req.specifier.contains(pins[name], prereleases=True), (
            f"locked {name}=={pins[name]} violates {raw}"
        )


def test_lock_entries_are_unique_hashed_pins() -> None:
    """Lock holds exact pins with hashes and no bare local paths."""
    hashed: dict[str, bool] = {}
    current = ""
    for line in _LOCK_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if line.startswith((" ", "\t", "-")):
            if stripped.startswith("--hash=sha256:"):
                hashed[current] = True
            continue
        match = _PIN_LINE.match(line)
        assert match, f"non-pin top-level line in lock: {line!r}"
        current = _normalise(match.group(1))
        assert current not in hashed, f"duplicate pin for {current}"
        hashed[current] = False
    assert hashed, "lock file has no pins"
    assert all(hashed.values()), sorted(n for n, d in hashed.items() if not d)


def test_lock_records_provenance() -> None:
    """Lock header records inputs, indexes, scope, and evidence."""
    lines = _LOCK_PATH.read_text(encoding="utf-8").splitlines()
    first = next(i for i, line in enumerate(lines) if _PIN_LINE.match(line))
    header = "\n".join(lines[:first])
    for token in (
        "./[nvidia]", "./services[desktop]", "./native",
        "https://pypi.org/simple", "https://download.pytorch.org/whl/cu129",
        "Linux", "pip check", "uv pip compile",
    ):
        assert token in header, f"provenance header lacks {token!r}"


def test_base_startup_imports_are_declared() -> None:
    """Startup closures import only their declared distributions."""
    services = _load_setup_module(_SERVICES_SETUP, _SERVICES_SETUP_CALL)
    kwargs = services.build_services_setup_kwargs(package_source_dir="src")
    native = _load_setup_module(_NATIVE_SETUP, _NATIVE_SETUP_CALL)
    daemon_allowed = _declared_dists(kwargs["install_requires"])
    native_allowed = _declared_dists(native.NATIVE_BASE_REQUIREMENTS)
    svc = _PROJECT_ROOT / "services" / "src" / "airunner_services"
    gui = _PROJECT_ROOT / "src" / "airunner"
    nat = _PROJECT_ROOT / "native" / "src" / "airunner_native"
    cases = (
        ("daemon", daemon_allowed, [("airunner_services", svc / "daemon.py")]),
        ("gui", _declared_dists(_profile_inputs()), [
            ("airunner", gui / "launcher.py"), ("airunner", gui / "main.py")]),
        ("native", native_allowed, [("airunner_native", nat / "launcher.py")]),
    )
    for label, allowed, entries in cases:
        imports = startup_closure(_PACKAGE_ROOTS, entries)
        mapped = {_IMPORT_TO_DIST.get(n, _normalise(n)) for n in imports}
        assert mapped <= allowed and imports, (label, sorted(mapped - allowed))
