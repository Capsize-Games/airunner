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
    "scripts/tests/test_cuda_source_recipe.py",
    "scripts/tests/test_cuda_wheel_handoff.py",
    "scripts/tests/test_apt_release_publisher.py",
    "scripts/tests/test_apt_daemon_health_probe.py",
    "scripts/tests/test_github_release_promotion.py",
    "services/tests/test_release_identity.py",
    "services/tests/test_debian_postinst_safety.py",
    "services/tests/test_release_core_bundle.py",
    "services/tests/test_core_input_readiness.py",
    "services/tests/test_dependency_notices.py",
    "services/tests/test_service_bootstrap.py",
    "services/tests/test_legacy_api_surface.py",
    "services/tests/test_loopback_auth.py",
    "services/tests/test_secret_storage.py",
    "services/tests/test_model_load_security.py",
    "services/tests/test_cross_distribution_versions.py",
    "services/tests/test_tool_sandbox_security.py",
    "services/tests/test_dependency_constraints.py",
    "services/tests/test_native_package_isolation.py",
    "services/tests/test_zimage_model_dir_config.py",
    "services/tests/test_third_party_notices.py",
    "services/tests/test_llm_request_for_action_parity.py",
    "services/tests/test_content_safety_gate.py",
    "services/tests/test_content_policy_mode.py",
    "services/tests/test_optional_policy_streaming.py",
    "services/tests/test_release_s04_packaged.py",
    "services/tests/test_download_security.py",
    "services/tests/test_security_package_pins.py",
    "services/tests/test_release_b02.py",
    "services/tests/test_import_boundaries.py",
    "services/tests/test_run_tests_optional_smoke.py",
)
_GATE_NEEDS = (
    "fetch-sidecars",
    "linux-candidate",
)
_REQUIRED_JOBS = _GATE_NEEDS + (
    "candidate-gate",
    "build-python-package",
    "build-debian-package",
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


def _write_test_sidecar_pin(
    root: Path, archive: Path, platform: str = "linux"
) -> tuple[Path, Path]:
    """Write an explicit synthetic trusted pin for one fixture archive."""
    pin = root / "native-sidecar-checksums.json"
    tag = root / "native-sidecar-version"
    records = {
        name: {
            "asset": f"runtime-sidecars-{name}.tar.gz",
            "sha256": _sha256_of(archive) if name == platform else None,
        }
        for name in ("linux", "windows")
    }
    pin.write_text(json.dumps({
        "tag": "v0.1.0",
        "source_commit": "0554185f27ac7db8f58e1ae8d59ba041e4118e62",
        "provenance_status": "verified",
        "archives": records,
    }), encoding="utf-8")
    tag.write_text("v0.1.0\n", encoding="utf-8")
    return pin, tag


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
