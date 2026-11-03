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
CORE_CI_LOCK = Path("package/constraints-linux-core-ci.txt")
CORE_CI_MANIFEST = Path("package/linux-core-ci-artifact-sources.json")
EXPECTED_TOOLS = {
    "iniconfig": "2.3.0",
    "pluggy": "1.7.0",
    "pytest": "9.1.1",
    "pytest-timeout": "2.4.0",
    "responses": "0.26.3",
}
EXPECTED_TOOL_SUPPORT = {
    "certifi": "2026.10.23",
    "charset-normalizer": "3.5.2",
    "idna": "3.20",
    "pygments": "2.21.0",
    "requests": "2.34.2",
    "urllib3": "2.8.0",
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
    expected_closure = EXPECTED_TOOLS | EXPECTED_TOOL_SUPPORT
    assert manifest["selected_count"] == len(expected_closure)
    assert manifest["selected_lock_sha256"] == hashlib.sha256(
        lock_path.read_bytes()
    ).hexdigest()

    pins = _lock_rows(lock_path)
    assert {name: version for name, (version, _digest) in pins.items()} == expected_closure
    rows = manifest["artifact_sources"]
    assert len(rows) == len(expected_closure)
    assert {row["name"]: row["version"] for row in rows} == expected_closure
    for row in rows:
        name = re.sub(r"[-_.]+", "-", row["name"]).lower()
        version, digest = pins[name]
        assert row["sha256"] == digest
        assert row["wheel_tags"]
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
    support = source_review["runtime_support"]
    assert support["evidence"] == (
        "package/core-input-readiness.json and "
        "release-planning/services/input-reviews/core-linux-dependency-inventory.json"
    )
    assert {row["name"]: row["version"] for row in support["packages"]} == EXPECTED_TOOL_SUPPORT
    for row in support["packages"]:
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


def test_packaging_core_manifest_projects_only_reviewed_core_wheels() -> None:
    """Clean artifact probes receive a 51-wheel projection of the CORE graph."""
    lock_path = ROOT / CORE_CI_LOCK
    manifest = json.loads((ROOT / CORE_CI_MANIFEST).read_text(encoding="utf-8"))
    readiness = json.loads(
        (ROOT / "package/core-input-readiness.json").read_text(encoding="utf-8")
    )
    assert manifest["schema_version"] == 1
    assert manifest["status"] == "candidate-only; not activated"
    assert manifest["selected_count"] == 51
    assert manifest["selected_lock_sha256"] == hashlib.sha256(
        lock_path.read_bytes()
    ).hexdigest()
    assert manifest["source_review"]["upstream_lock"] == "package/constraints-linux-core.txt"
    assert manifest["source_review"]["upstream_lock_sha256"] == readiness["lock"]["sha256"]
    assert manifest["source_review"]["readiness_record"] == "package/core-input-readiness.json"
    pins = _lock_rows(lock_path)
    assert len(pins) == 51
    rows = manifest["artifact_sources"]
    assert len(rows) == 51
    assert {row["name"]: row["version"] for row in rows} == {
        name: version for name, (version, _digest) in pins.items()
    }
    for row in rows:
        version, digest = pins[row["name"]]
        assert row["version"] == version
        assert row["sha256"] == digest
        assert row["source"]["sha256"] == digest
        assert row["filename"].endswith(".whl")


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
            cleanup = script.index('rm -rf -- "$wheelhouse" "$tools"')
            assert script.index("python -m pip check") < cleanup
            assert '"$wheelhouse/staging-receipt.json"' in script
            assert '"$tools/staging-receipt.json"' in script
            assert '"$wheelhouse/requirements.txt"' in script
            assert '"$tools/requirements.txt"' in script
            assert "capacity-before-staging.txt" in script
            assert "capacity-after-wheelhouse-cleanup.txt" in script
            _step(job, "Upload runtime input and capacity audit" if workflow_path.endswith("eval-tests.yml") and job_name == "runtime-contract-tests" else "Upload runtime smoke input and capacity audit" if workflow_path.endswith("eval-tests.yml") else "Upload Linux candidate input and capacity audit")
            if workflow_path.endswith("pypi-dispatch.yml"):
                assert "package/linux-builder-tools-artifact-sources.json" in script
                assert str(BUILDER_LOCK) in script
                assert '"$builder/staging-receipt.json"' in script
                assert '"$builder/requirements.txt"' in script
                assert 'rm -rf -- "$wheelhouse" "$tools" "$builder"' in script
                assert "capacity-before-freeze.txt" in _step(job, "Record available capacity before freeze")["run"]
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


def test_packaging_workflows_use_reviewed_tools_and_setuptools_backend() -> None:
    """Build jobs avoid unpinned frontends and use the reviewed backend lock."""
    workflows = {
        ".github/workflows/eval-tests.yml": "packaging-gates",
        ".github/workflows/pypi-dispatch.yml": "build-python-package",
    }
    for workflow_path, job_name in workflows.items():
        job = _workflow(workflow_path)["jobs"][job_name]
        all_run_text = "\n".join(
            str(step.get("run", "")) for step in job["steps"]
        )
        assert "pip install --upgrade pip" not in all_run_text
        assert "pip install build" not in all_run_text
        assert "python -m build" not in all_run_text
        assert "build_python_distributions.py" in all_run_text
        if workflow_path.endswith("eval-tests.yml"):
            assert str(CORE_CI_MANIFEST) in all_run_text
            assert str(CORE_CI_LOCK) in all_run_text
            assert str(TOOLS_MANIFEST) in all_run_text
            assert str(TOOLS_LOCK) in all_run_text
            assert "--locked-dependency-requirements" in all_run_text
            assert "--locked-dependency-wheelhouse" in all_run_text
        else:
            assert "package/linux-builder-tools-artifact-sources.json" in all_run_text
            assert str(BUILDER_LOCK) in all_run_text
            assert str(CORE_CI_MANIFEST) in all_run_text
            assert str(CORE_CI_LOCK) in all_run_text
            assert "--locked-dependency-requirements" in all_run_text
            assert "--locked-dependency-wheelhouse" in all_run_text
        assert "--require-hashes" in all_run_text
        assert "--no-index" in all_run_text
        assert "--no-deps" in all_run_text


def test_direct_backend_builder_limits_package_and_declared_backend() -> None:
    """The direct helper only invokes the backend declared by both projects."""
    source = (ROOT / "scripts/build_python_distributions.py").read_text(
        encoding="utf-8"
    )
    assert 'choices=("services", "native")' in source
    assert "from setuptools import build_meta" in source
    assert "build_meta.build_wheel" in source
    assert "build_meta.build_sdist" in source
    assert "python -m build" not in source
    for package in ("pyproject.toml", "services/pyproject.toml", "native/pyproject.toml"):
        assert 'requires = ["setuptools==84.2.1", "wheel"]' in (
            ROOT / package
        ).read_text(encoding="utf-8")
