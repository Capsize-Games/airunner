"""Contracts for hash-staged V4 runtime and deterministic CI tools."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
RUNTIME_LOCK = "package/constraints-linux-nvidia-cu129-linux-release.txt"
TOOLS_LOCK = Path("package/constraints-linux-ci-tools.txt")
TOOLS_MANIFEST = Path("package/linux-ci-tools-artifact-sources.json")
BUILDER_LOCK = Path("package/constraints-linux-builder-tools.txt")
BUILDER_MANIFEST = Path("package/linux-builder-tools-artifact-sources.json")
EXPECTED_TOOLS = {
    "iniconfig": "2.3.0",
    "pluggy": "1.7.0",
    "pytest": "9.1.1",
    "pytest-timeout": "2.4.0",
    "responses": "0.26.3",
}
EXPECTED_BUILDER_TOOLS = {
    "altgraph": "0.17.5",
    "packaging": "26.3",
    "pyinstaller": "6.12.0",
    "pyinstaller-hooks-contrib": "2026.9",
    "setuptools": "84.2.1",
    "wheel": "0.48.0",
}


def _workflow(path: str) -> dict:
    """Read workflow YAML while preserving its jobs mapping."""
    return yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))


def _step(job: dict, name: str) -> dict:
    """Return one named workflow step or fail with a useful assertion."""
    return next(step for step in job["steps"] if step.get("name") == name)


def _lock_rows(path: Path) -> dict[str, tuple[str, str]]:
    """Parse exact pins and one SHA-256 from this small hash lock."""
    text = path.read_text(encoding="utf-8")
    rows: dict[str, tuple[str, str]] = {}
    pattern = re.compile(
        r"(?m)^([A-Za-z0-9_.-]+)==([^\s\\]+)\s+\\\n"
        r"\s+--hash=sha256:([0-9a-f]{64})$"
    )
    for name, version, digest in pattern.findall(text):
        normalized = re.sub(r"[-_.]+", "-", name).lower()
        assert normalized not in rows, f"duplicate test-tool pin: {name}"
        rows[normalized] = (version, digest)
    assert rows, "test-tool lock has no parsed pins"
    return rows


def test_ci_tools_manifest_is_bound_to_exact_hash_lock() -> None:
    """Manifest and pip lock describe the same five wheel-only inputs."""
    lock_path = ROOT / TOOLS_LOCK
    manifest_path = ROOT / TOOLS_MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 1
    assert manifest["status"] == "candidate-only; not activated"
    assert manifest["selected_count"] == len(EXPECTED_TOOLS)
    assert manifest["selected_lock_sha256"] == hashlib.sha256(
        lock_path.read_bytes()
    ).hexdigest()

    pins = _lock_rows(lock_path)
    assert {name: version for name, (version, _digest) in pins.items()} == EXPECTED_TOOLS
    rows = manifest["artifact_sources"]
    assert len(rows) == len(EXPECTED_TOOLS)
    assert {row["name"]: row["version"] for row in rows} == EXPECTED_TOOLS
    for row in rows:
        name = re.sub(r"[-_.]+", "-", row["name"]).lower()
        version, digest = pins[name]
        assert row["sha256"] == digest
        assert row["wheel_tags"] == ["py3-none-any"]
        assert row["source"]["kind"] == "https"
        assert row["source"]["url"].startswith(
            "https://files.pythonhosted.org/packages/"
        )
        assert row["filename"].endswith(".whl")
        assert row["version"] == version
        assert row["size_bytes"] == row["source"]["size_bytes"] > 0

    source_review = manifest["source_review"]
    assert source_review["status"].startswith(
        "bounded review of exact upstream tags"
    )
    reviewed = source_review["packages"]
    assert {row["name"]: row["version"] for row in reviewed} == EXPECTED_TOOLS
    for row in reviewed:
        assert re.fullmatch(r"[0-9a-f]{40}", row["upstream_commit"])
        assert row["wheel_license_matches_pinned_source"] is True
        assert re.fullmatch(r"[0-9a-f]{64}", row["wheel_license_sha256"])
        assert row["wheel_record_entries"] > 0
        assert row["wheel_sha256"] == next(
            item["sha256"] for item in rows if item["name"] == row["name"]
        )


def test_builder_tools_manifest_is_bound_to_exact_hash_lock() -> None:
    """The separate PyInstaller layer contains only reviewed exact wheels."""
    lock_path = ROOT / BUILDER_LOCK
    manifest = json.loads((ROOT / BUILDER_MANIFEST).read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 1
    assert manifest["status"] == "candidate-only; not activated"
    assert manifest["selected_count"] == len(EXPECTED_BUILDER_TOOLS)
    assert manifest["selected_lock_sha256"] == hashlib.sha256(
        lock_path.read_bytes()
    ).hexdigest()
    pins = _lock_rows(lock_path)
    assert {name: version for name, (version, _digest) in pins.items()} == EXPECTED_BUILDER_TOOLS
    rows = manifest["artifact_sources"]
    assert {row["name"]: row["version"] for row in rows} == EXPECTED_BUILDER_TOOLS
    assert len(rows) == len(EXPECTED_BUILDER_TOOLS)
    for row in rows:
        name = re.sub(r"[-_.]+", "-", row["name"]).lower()
        version, digest = pins[name]
        assert row["version"] == version
        assert row["sha256"] == digest
        assert row["filename"].endswith(".whl")
        assert row["source"]["kind"] == "https"
        assert row["source"]["url"].startswith(
            "https://files.pythonhosted.org/packages/"
        )
        assert row["size_bytes"] == row["source"]["size_bytes"] > 0
    assert "CORE source and license review" in manifest["source_review"]["status"]


def test_runtime_ci_jobs_install_only_staged_hash_locked_inputs() -> None:
    """Hybrid contracts, smoke, and Linux candidate use the same staged graph."""
    workflows = {
        ".github/workflows/eval-tests.yml": [
            "runtime-contract-tests",
            "runtime-smoke",
        ],
        ".github/workflows/pypi-dispatch.yml": ["linux-candidate"],
    }
    for workflow_path, job_names in workflows.items():
        jobs = _workflow(workflow_path)["jobs"]
        for job_name in job_names:
            job = jobs[job_name]
            install = _step(job, "Install Python dependencies" if workflow_path.endswith("eval-tests.yml") else "Install dependencies")
            script = install["run"]
            assert "scripts/stage_linux_release_artifacts.py" in script
            assert "package/linux-release-v4-artifact-sources.json" in script
            assert RUNTIME_LOCK in script
            assert "package/linux-ci-tools-artifact-sources.json" in script
            assert str(TOOLS_LOCK) in script
            assert "--require-hashes" in script
            assert "--no-index" in script
            assert "--no-deps" in script
            assert "python -m pip check" in script
            assert "pip install --upgrade" not in script
            assert "'./services[linux-release]'" in script
            assert "./services[linux-release,development]" not in script
            if workflow_path.endswith("pypi-dispatch.yml"):
                assert "package/linux-builder-tools-artifact-sources.json" in script
                assert str(BUILDER_LOCK) in script
            assert "download.pytorch.org/whl/cpu" not in script
            assert job["permissions"]["actions"] == "read"
            assert "GITHUB_TOKEN" in install.get("env", {})


def test_cpu_tensor_contract_uses_reviewed_cuda_wheel_with_devices_hidden() -> None:
    """CPU execution evidence does not imply CPU-wheel or GPU support."""
    workflow = _workflow(".github/workflows/eval-tests.yml")
    job = workflow["jobs"]["runtime-contract-tests"]
    step = _step(job, "Run runtime contract tests")
    assert step["env"]["CUDA_VISIBLE_DEVICES"] == ""
    install = _step(job, "Install Python dependencies")["run"]
    assert "torch.tensor([1.0, 2.0], device=\"cpu\")" in install
    assert "torch.cuda.is_available() is False" in install
    assert "torch==2.13.0+cpu" not in install
