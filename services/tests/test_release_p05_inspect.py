"""P05 bundle inspection tests (manifest, resources, exclusions).

Proves scripts/inspect_linux_bundle.py accepts a well-formed synthetic
bundle and rejects tampered, incomplete, unmanifested, excluded, Qt,
and non-executable trees. CPU-only; bundles are synthetic tmp trees.
"""

from __future__ import annotations

import json
import re
import types
from pathlib import Path
from typing import Any

from test_release_p05_support import (
    assemble_mod,
    bundle_data_dir,
    inspect_mod,
    make_bundle,
    spec,
    write_toc,
    write_warn,
)

__all__ = ["assemble_mod", "inspect_mod", "spec"]


def test_inspect_clean_bundle_passes(
    tmp_path: Path,
    inspect_mod: types.ModuleType,
    assemble_mod: types.ModuleType,
    spec: dict[str, Any],
) -> None:
    bundle = make_bundle(tmp_path, spec, assemble_mod)
    warn = write_warn(tmp_path / "warn.txt", dirty=False)
    toc = write_toc(tmp_path / "PYZ-00.toc", spec)
    result = inspect_mod.inspect_bundle(
        bundle, spec, warn_file=warn, toc_paths=[toc]
    )
    assert result.problems == []
    # Release-provided sidecars are absent from the synthetic tree:
    # warnings, not failures.
    assert any("llama-server" in w for w in result.warnings)
    assert any("whisper-server" in w for w in result.warnings)


def test_inspect_manifest_matches_p04_contract(
    tmp_path: Path,
    assemble_mod: types.ModuleType,
    spec: dict[str, Any],
) -> None:
    """The written manifest carries the P04 identity and file hashes."""
    bundle = make_bundle(tmp_path, spec, assemble_mod, base="rev123")
    manifest = json.loads(
        (bundle / str(spec["manifest"]["filename"])).read_text(
            encoding="utf-8"
        )
    )
    assert manifest["bundle"] == spec["bundle"]["name"]
    assert manifest["tool"] == spec["bundle"]["tool"]
    assert manifest["entry"] == spec["bundle"]["entry"]
    assert manifest["base"] == "rev123"
    assert manifest["files"]
    for entry in manifest["files"]:
        assert set(entry) == {"path", "sha256"}
        assert re.fullmatch(r"[0-9a-f]{64}", entry["sha256"])


def test_inspect_detects_tampered_file(
    tmp_path: Path,
    inspect_mod: types.ModuleType,
    assemble_mod: types.ModuleType,
    spec: dict[str, Any],
) -> None:
    bundle = make_bundle(tmp_path, spec, assemble_mod)
    target = bundle / "legal" / "NOTICE"
    target.write_bytes(target.read_bytes() + b"tampered")
    result = inspect_mod.inspect_bundle(bundle, spec)
    assert any("legal/NOTICE" in problem for problem in result.problems)


def test_inspect_detects_silently_dropped_payload(
    tmp_path: Path,
    inspect_mod: types.ModuleType,
    assemble_mod: types.ModuleType,
    spec: dict[str, Any],
) -> None:
    """A payload missing from both tree and manifest still fails: the
    spec requires it, so a consistent-but-incomplete freeze is caught."""
    bundle = make_bundle(tmp_path, spec, assemble_mod)
    dropped = bundle_data_dir(
        bundle, "airunner_services", "database", "alembic", "versions"
    )
    for path in dropped.iterdir():
        path.unlink()
    assemble_mod.write_manifest(bundle, spec, "testrev")
    result = inspect_mod.inspect_bundle(bundle, spec)
    assert any("versions" in problem for problem in result.problems)


def test_inspect_detects_unmanifested_file(
    tmp_path: Path,
    inspect_mod: types.ModuleType,
    assemble_mod: types.ModuleType,
    spec: dict[str, Any],
) -> None:
    bundle = make_bundle(tmp_path, spec, assemble_mod)
    (bundle / "stray.txt").write_text("unmanifested", encoding="utf-8")
    result = inspect_mod.inspect_bundle(bundle, spec)
    assert any("stray.txt" in problem for problem in result.problems)


def test_inspect_detects_excluded_payload(
    tmp_path: Path,
    inspect_mod: types.ModuleType,
    assemble_mod: types.ModuleType,
    spec: dict[str, Any],
) -> None:
    """Models, secrets, and caches fail even when duly manifested."""
    bundle = make_bundle(tmp_path, spec, assemble_mod)
    (bundle / "models").mkdir()
    (bundle / "models" / "weights.gguf").write_bytes(b"fake-weights")
    (bundle / ".env").write_text("TOKEN=fake\n", encoding="utf-8")
    cache = bundle / "pkg" / "__pycache__"
    cache.mkdir(parents=True)
    (cache / "mod.pyc").write_bytes(b"fake-bytecode")
    assemble_mod.write_manifest(bundle, spec, "testrev")
    result = inspect_mod.inspect_bundle(bundle, spec)
    assert any("weights.gguf" in p for p in result.problems)
    assert any(".env" in p for p in result.problems)
    assert any("mod.pyc" in p for p in result.problems)


def test_inspect_detects_qt_payload(
    tmp_path: Path,
    inspect_mod: types.ModuleType,
    assemble_mod: types.ModuleType,
    spec: dict[str, Any],
) -> None:
    """Any Qt marker path fails the services-only bundle."""
    bundle = make_bundle(tmp_path, spec, assemble_mod)
    qt_dir = bundle / "_internal" / "PySide6" / "Qt" / "plugins"
    qt_dir.mkdir(parents=True)
    (qt_dir / "libqxcb.so").write_bytes(b"fake-qt")
    assemble_mod.write_manifest(bundle, spec, "testrev")
    result = inspect_mod.inspect_bundle(bundle, spec)
    assert any("Qt payload" in p for p in result.problems)


def test_inspect_reports_qt_file_once(
    tmp_path: Path,
    inspect_mod: types.ModuleType,
    assemble_mod: types.ModuleType,
    spec: dict[str, Any],
) -> None:
    """A Qt file matching several markers is one problem, not many."""
    bundle = make_bundle(tmp_path, spec, assemble_mod)
    payload = bundle / "_internal" / "PySide6" / "libQt6Core.so.6"
    payload.parent.mkdir(parents=True, exist_ok=True)
    payload.write_bytes(b"fake-qt")
    assemble_mod.write_manifest(bundle, spec, "testrev")
    result = inspect_mod.inspect_bundle(bundle, spec)
    assert sum("Qt payload" in p for p in result.problems) == 1


def test_inspect_tolerates_reviewed_ca_bundle(
    tmp_path: Path,
    inspect_mod: types.ModuleType,
    assemble_mod: types.ModuleType,
    spec: dict[str, Any],
) -> None:
    """The reviewed certifi CA bundle passes despite *.pem."""
    bundle = make_bundle(tmp_path, spec, assemble_mod)
    ca_dir = bundle / "_internal" / "certifi"
    ca_dir.mkdir(parents=True, exist_ok=True)
    (ca_dir / "cacert.pem").write_bytes(b"fake-ca-bundle")
    assemble_mod.write_manifest(bundle, spec, "testrev")
    result = inspect_mod.inspect_bundle(bundle, spec)
    assert result.problems == []


def test_inspect_still_rejects_unreviewed_pem(
    tmp_path: Path,
    inspect_mod: types.ModuleType,
    assemble_mod: types.ModuleType,
    spec: dict[str, Any],
) -> None:
    """The allowlist is exact-path: another *.pem still fails."""
    bundle = make_bundle(tmp_path, spec, assemble_mod)
    key_dir = bundle / "_internal" / "app"
    key_dir.mkdir(parents=True, exist_ok=True)
    (key_dir / "server.pem").write_bytes(b"fake-key")
    assemble_mod.write_manifest(bundle, spec, "testrev")
    result = inspect_mod.inspect_bundle(bundle, spec)
    assert any("server.pem" in p for p in result.problems)


def test_inspect_requires_native_extensions(
    tmp_path: Path,
    inspect_mod: types.ModuleType,
    assemble_mod: types.ModuleType,
    spec: dict[str, Any],
) -> None:
    """A missing extension .so fails even with a clean manifest."""
    bundle = make_bundle(tmp_path, spec, assemble_mod)
    for path in (bundle / "_internal").glob("libzim*.so"):
        path.unlink()
    assemble_mod.write_manifest(bundle, spec, "testrev")
    result = inspect_mod.inspect_bundle(bundle, spec)
    assert any("native extension libzim" in p for p in result.problems)


def test_inspect_requires_nested_extension_submodule(
    tmp_path: Path,
    inspect_mod: types.ModuleType,
    assemble_mod: types.ModuleType,
    spec: dict[str, Any],
) -> None:
    """A missing dotted extension .so fails with its full name."""
    bundle = make_bundle(tmp_path, spec, assemble_mod)
    nested = bundle / "_internal" / "scipy" / "_cyutility.fake-ext.so"
    assert nested.is_file()
    nested.unlink()
    assemble_mod.write_manifest(bundle, spec, "testrev")
    result = inspect_mod.inspect_bundle(bundle, spec)
    assert any(
        "native extension scipy._cyutility" in p
        for p in result.problems
    )


def test_inspect_requires_frozen_import_sources(
    tmp_path: Path,
    inspect_mod: types.ModuleType,
    assemble_mod: types.ModuleType,
    spec: dict[str, Any],
) -> None:
    """A dropped import-scan source fails even with a clean manifest."""
    bundle = make_bundle(tmp_path, spec, assemble_mod)
    marker = bundle / "_internal" / "transformers" / "models"
    for path in marker.rglob("__init__.py"):
        path.unlink()
    assemble_mod.write_manifest(bundle, spec, "testrev")
    result = inspect_mod.inspect_bundle(bundle, spec)
    assert any("import-scan source" in p for p in result.problems)


def test_inspect_requires_executable_bit(
    tmp_path: Path,
    inspect_mod: types.ModuleType,
    assemble_mod: types.ModuleType,
    spec: dict[str, Any],
) -> None:
    bundle = make_bundle(tmp_path, spec, assemble_mod)
    exe = bundle / str(spec["bundle"]["executable"])
    exe.chmod(0o644)
    result = inspect_mod.inspect_bundle(bundle, spec)
    assert any("not executable" in p for p in result.problems)
