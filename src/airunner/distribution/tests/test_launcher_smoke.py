"""Smoke tests for AIRunner's native launcher runtime planning."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[4]
LINUX_LAUNCHER = REPO_ROOT / "build" / "airunner-launcher" / "airunner"


def launcher_path() -> Path:
    """Return the built Linux launcher path or skip when unavailable."""
    if LINUX_LAUNCHER.exists():
        return LINUX_LAUNCHER
    pytest.skip("native launcher is not built")


def repo_python() -> Path:
    """Return the repo-local Python interpreter used by launcher tests."""
    for path in (
        REPO_ROOT / "venv" / "bin" / "python",
        REPO_ROOT / ".venv" / "bin" / "python",
    ):
        if path.exists():
            return path
    pytest.skip("repo-local venv Python is missing")


def run_launcher(*args: str) -> subprocess.CompletedProcess[str]:
    """Run the native launcher and capture its output."""
    return subprocess.run(
        [str(launcher_path()), *args],
        capture_output=True,
        check=False,
        text=True,
    )


def parse_plan(output: str) -> dict[str, str]:
    """Parse launcher plan output into a normalized key-value mapping."""
    values: dict[str, str] = {}
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key] = value.strip().strip('"')
    return values


def create_prod_manifest(
    tmp_path: Path,
    pythonpath: str = "../../app/site-packages",
) -> Path:
    """Create one minimal prod bundle layout and return its manifest path."""
    bundle_root = tmp_path / "bundle"
    (bundle_root / "app" / "site-packages").mkdir(parents=True)
    (bundle_root / "bin").mkdir(parents=True)
    (bundle_root / "python" / "bin").mkdir(parents=True)
    (bundle_root / "share" / "airunner").mkdir(parents=True)
    (bundle_root / "python" / "bin" / "python").symlink_to(repo_python())
    for name in ("llama-server", "whisper-server"):
        (bundle_root / "bin" / name).write_text("binary", encoding="utf-8")
    manifest = bundle_root / "share" / "airunner" / "runtime_manifest.env"
    manifest.write_text(
        "\n".join(
            [
                "AIRUNNER_BUNDLE_ROOT=../..",
                "AIRUNNER_PYTHON=../../python/bin/python",
                f"AIRUNNER_PYTHONPATH={pythonpath}",
                "AIRUNNER_ENTRYPOINT=airunner.launcher",
                "AIRUNNER_LLAMA_SERVER_BIN=../../bin/llama-server",
                "AIRUNNER_WHISPER_SERVER_BIN=../../bin/whisper-server",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return manifest


@pytest.mark.fast
def test_launcher_dev_dry_run_uses_repo_venv() -> None:
    """Dev dry-run should resolve the repository root and venv Python."""
    result = run_launcher(
        "--mode",
        "dev",
        "--repo-root",
        str(REPO_ROOT),
        "--dry-run",
    )
    assert result.returncode == 0
    plan = parse_plan(result.stdout)
    assert plan["mode"] == "dev"
    assert Path(plan["repo_root"]).resolve() == REPO_ROOT
    assert Path(plan["python"]).resolve() == repo_python().resolve()
    assert Path(plan["pythonpath"]).resolve() == (REPO_ROOT / "src")


@pytest.mark.fast
def test_launcher_prod_dry_run_uses_manifest_bundle(tmp_path: Path) -> None:
    """Prod dry-run should resolve bundle paths relative to the manifest."""
    manifest = create_prod_manifest(tmp_path)
    result = run_launcher(
        "--mode",
        "prod",
        "--manifest",
        str(manifest),
        "--dry-run",
    )
    assert result.returncode == 0
    bundle_root = manifest.parents[2]
    plan = parse_plan(result.stdout)
    assert plan["mode"] == "prod"
    assert Path(plan["manifest"]).resolve() == manifest
    assert Path(plan["bundle_root"]).resolve() == bundle_root
    assert Path(plan["python"]).resolve() == repo_python().resolve()
    assert Path(plan["pythonpath"]).resolve() == (
        bundle_root / "app" / "site-packages"
    )


@pytest.mark.fast
def test_launcher_diagnose_reports_missing_pythonpath(tmp_path: Path) -> None:
    """Diagnose mode should print validation errors for broken prod paths."""
    manifest = create_prod_manifest(tmp_path, "../../app/missing-site-packages")
    result = run_launcher(
        "--mode",
        "prod",
        "--manifest",
        str(manifest),
        "--diagnose",
    )
    assert result.returncode == 2
    assert "mode=prod" in result.stdout
    assert "configured AIRUNNER_PYTHONPATH does not exist" in result.stderr