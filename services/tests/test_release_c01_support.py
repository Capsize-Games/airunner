"""Shared contracts and fixtures for the C01 release-gate suite."""

from __future__ import annotations

import hashlib
import json
import subprocess
import tarfile
from pathlib import Path
from typing import Any

import yaml

_ROOT = Path(__file__).resolve().parents[2]
_DISPATCH = _ROOT / ".github" / "workflows" / "pypi-dispatch.yml"
_EVAL = _ROOT / ".github" / "workflows" / "eval-tests.yml"
_GATE = _ROOT / "packaging" / "linux" / "candidate-gate.sh"
_STAGE = _ROOT / "packaging" / "linux" / "stage-sidecars.sh"
_SPEC = _ROOT / "packaging" / "linux" / "services-bundle-spec.toml"

_REQUIRED_TESTS = (
    "services/tests/test_content_safety_gate.py",
    "services/tests/test_model_load_security.py",
    "services/tests/test_loopback_auth.py",
    "services/tests/test_secret_storage.py",
    "services/tests/test_download_security.py",
    "services/tests/test_release_b02.py",
)
_GATE_NEEDS = (
    "provision-policy",
    "provision-policy-fixture",
    "fetch-sidecars",
    "linux-candidate",
)
_REQUIRED_JOBS = _GATE_NEEDS + (
    "candidate-gate",
    "build-python-package",
    "publish-release-assets",
)
_PUBLISH_MARKERS = (
    "pypi-publish",
    "gh-release",
    "twine",
    "butler",
    "itch",
    "secrets.",
    "github.token",
)
_BLOCKING_RESULTS = ("failure", "skipped", "cancelled", "")


def _load_yaml(path: Path) -> dict[str, Any]:
    """Return the parsed workflow mapping for one YAML file."""
    return dict(yaml.safe_load(path.read_text(encoding="utf-8")))


def _steps_text(job: dict[str, Any]) -> str:
    """Return the joined step text (name/uses/run/with) of one job."""
    steps = job.get("steps", [])
    keys = ("name", "uses", "run")
    runs = "\n".join(str(s.get(k, "")) for s in steps for k in keys)
    withs = "\n".join(str(s.get("with", "")) for s in steps)
    return runs + "\n" + withs


def _run_gate(*args: str) -> subprocess.CompletedProcess[str]:
    """Run the gate script with synthetic results; no side effects."""
    cmd = ["bash", str(_GATE), *args]
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def _run_stage(*args: str) -> subprocess.CompletedProcess[str]:
    """Run the stage script with synthetic inputs; no side effects."""
    cmd = ["bash", str(_STAGE), *args]
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def _release_checks(result: str = "success") -> list[str]:
    """Synthetic release checks with the candidate result overridable."""
    args: list[str] = []
    for job in _GATE_NEEDS:
        value = result if job == "linux-candidate" else "success"
        args += ["--check", f"{job}={value}"]
    return args


def _sha256_of(path: Path) -> str:
    """Return the hex SHA-256 of one file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_fake_manifest(bundle: Path) -> None:
    """Write a one-entry manifest over the fake bundle executable."""
    exe = bundle / "airunner-daemon"
    exe.write_bytes(b"fake-elf")
    manifest = {
        "bundle": "airunner-services",
        "tool": "pyinstaller==6.12.0",
        "entry": "airunner_services.daemon:main",
        "base": "c01fake",
        "files": [{"path": "airunner-daemon", "sha256": _sha256_of(exe)}],
    }
    (bundle / "bundle-manifest.json").write_text(json.dumps(manifest))


def _write_fake_tarball(root: Path) -> Path:
    """Write a nested sidecar tarball; return its path."""
    payload = root / "payload"
    (payload / "deep").mkdir(parents=True)
    (payload / "deep" / "llama-server").write_bytes(b"fake-llm")
    (payload / "whisper-server").write_bytes(b"fake-whisper")
    tarball = root / "sidecars.tar.gz"
    with tarfile.open(tarball, "w:gz") as tar:
        tar.add(payload / "deep" / "llama-server", arcname="n/llama-server")
        tar.add(payload / "whisper-server", arcname="whisper-server")
    return tarball


def _stage_fixture(root: Path) -> tuple[Path, Path]:
    """Build a fake bundle and tarball; return (bundle, tarball)."""
    bundle = root / "bundle"
    (bundle / "bin").mkdir(parents=True)
    _write_fake_manifest(bundle)
    return bundle, _write_fake_tarball(root)
