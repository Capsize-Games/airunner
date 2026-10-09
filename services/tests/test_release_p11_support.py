"""Shared paths and parsers for the P11 license-inventory tests.

Single concern: locate the P11 evidence document and the release
sources it must track (bundle spec, constraint lock, model catalog,
sidecar pin, legal files), and parse them with the standard library
only. CPU-only; no model, network, or database side effects.
"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import sys
import tomllib
import types
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
LICENSES_MD = REPO_ROOT / "release-planning" / "linux-v1" / "licenses.md"
SPEC_PATH = REPO_ROOT / "packaging" / "linux" / "services-bundle-spec.toml"
CONSTRAINTS_PATH = (
    REPO_ROOT / "package" / "constraints-linux-nvidia-cu129.txt"
)
BOOTSTRAP_PATH = (
    REPO_ROOT
    / "services"
    / "src"
    / "airunner_services"
    / "bootstrap"
    / "model_bootstrap_data.py"
)
PIN_PATH = REPO_ROOT / ".github" / "native-sidecar-version"
LICENSE_PATH = REPO_ROOT / "LICENSE"
NOTICE_PATH = REPO_ROOT / "NOTICE"
THIRD_PARTY_PATH = REPO_ROOT / "THIRD_PARTY_NOTICES.md"

LEGAL_FILES = (LICENSE_PATH, NOTICE_PATH, THIRD_PARTY_PATH)


def read_text(path: Path) -> str:
    """Return the UTF-8 text of a repository file."""
    return path.read_text(encoding="utf-8")


def licenses_text() -> str:
    """Return the P11 evidence document text."""
    return read_text(LICENSES_MD)


def load_spec() -> dict[str, Any]:
    """Return the parsed services bundle spec."""
    with SPEC_PATH.open("rb") as handle:
        return dict(tomllib.load(handle))


def sidecar_names(spec: dict[str, Any]) -> list[str]:
    """Return the [[runtime]] sidecar names from the spec."""
    names: list[str] = []
    for entry in spec.get("runtime", []):
        names.append(str(entry["name"]))
    return names


def staged_legal_sources(spec: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Map root-staged legal sources to their spec entries."""
    staged: dict[str, dict[str, Any]] = {}
    for entry in spec.get("data", []):
        if str(entry.get("stage")) != "root":
            continue
        if str(entry.get("dest")) != "legal":
            continue
        staged[str(entry["source"])] = dict(entry)
    return staged


def constraint_pins() -> list[tuple[str, str]]:
    """Return (name, version) for every lock pin line."""
    pins: list[tuple[str, str]] = []
    for line in read_text(CONSTRAINTS_PATH).splitlines():
        head = line.split("\\", 1)[0].strip()
        if "==" not in head or head.startswith("#"):
            continue
        name, version = head.split("==", 1)
        pins.append((name.strip(), version.strip()))
    return pins


def constraints_sha256() -> str:
    """Return the hex SHA256 of the constraint lock file."""
    return hashlib.sha256(CONSTRAINTS_PATH.read_bytes()).hexdigest()


def sidecar_pin() -> str:
    """Return the authoritative native-sidecar tag."""
    lines = [ln for ln in read_text(PIN_PATH).splitlines() if ln.strip()]
    assert len(lines) == 1, lines
    return lines[0].strip()


def bootstrap_repo_ids() -> set[str]:
    """Return every model "path" literal in the bootstrap catalog.

    Parsed by AST so the test never imports the services stack
    (which needs airunner_common installed); mirrors the P05
    re-derive-literals-from-source pattern.
    """
    tree = ast.parse(read_text(BOOTSTRAP_PATH))
    found: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        found.update(_dict_path_values(node))
    return found


def _dict_path_values(node: ast.Dict) -> set[str]:
    """Return "path" string values from one dict literal."""
    values: set[str] = set()
    for key, value in zip(node.keys, node.values):
        if not isinstance(key, ast.Constant) or key.value != "path":
            continue
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            values.add(value.value)
    return values


def load_notice_checker() -> types.ModuleType:
    """Load scripts/check_third_party_notices.py in isolation."""
    path = REPO_ROOT / "scripts" / "check_third_party_notices.py"
    spec = importlib.util.spec_from_file_location(
        "release_p11_check_notices", path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
