"""Smoke tests for AIRunner's native launcher runtime planning."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from airunner_native.repo_paths import resolve_repo_root


REPO_ROOT = resolve_repo_root(Path(__file__))
LINUX_LAUNCHER = REPO_ROOT / "build" / "airunner-launcher" / "airunner"
LAUNCHER_SOURCE_ROOT = REPO_ROOT / "native" / "airunner_launcher" / "src"


def _launcher_build_is_stale() -> bool:
    """Return whether the checked-in launcher binary predates the sources."""
    if not LINUX_LAUNCHER.exists() or not LAUNCHER_SOURCE_ROOT.exists():
        return False
    source_mtime = max(
        path.stat().st_mtime_ns
        for path in LAUNCHER_SOURCE_ROOT.rglob("*")
        if path.is_file()
    )
    return LINUX_LAUNCHER.stat().st_mtime_ns < source_mtime


def launcher_path() -> Path:
    """Return the built Linux launcher path or skip when unavailable."""
    if LINUX_LAUNCHER.exists() and not _launcher_build_is_stale():
        return LINUX_LAUNCHER
    if _launcher_build_is_stale():
        pytest.skip("native launcher build is stale")
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


def run_python_module(module_name: str) -> subprocess.CompletedProcess[str]:
    """Run one Python launcher module directly under the repo venv."""
    env = dict(**os.environ)
    env["PYTHONPATH"] = expected_repo_pythonpath()
    env["AIRUNNER_TEST_NO_GUI_LAUNCH"] = "1"
    env.pop("AIRUNNER_ALLOW_GUI_TEST_LAUNCH", None)
    return subprocess.run(
        [str(repo_python()), "-m", module_name],
        capture_output=True,
        check=False,
        cwd=REPO_ROOT,
        env=env,
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


def expected_repo_source_roots() -> list[Path]:
    """Return checkout source roots in launcher PYTHONPATH order."""
    return [
        REPO_ROOT / "api" / "src",
        REPO_ROOT / "gui" / "src",
        REPO_ROOT / "model" / "src",
        REPO_ROOT / "shared" / "src",
        REPO_ROOT / "services" / "src",
        REPO_ROOT / "native" / "src",
    ]


def expected_repo_pythonpath() -> str:
    """Return the checkout PYTHONPATH used by dev launcher flows."""
    return os.pathsep.join(str(path) for path in expected_repo_source_roots())


def parse_pythonpath(value: str) -> list[Path]:
    """Split one PYTHONPATH string into concrete path entries."""
    return [Path(entry) for entry in value.split(os.pathsep) if entry]


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
                "AIRUNNER_ENTRYPOINT=airunner_native.launcher",
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
    assert [path.resolve() for path in parse_pythonpath(plan["pythonpath"])] == [
        path.resolve() for path in expected_repo_source_roots()
    ]


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


@pytest.mark.fast
def test_native_python_launcher_module_executes_main_guard() -> None:
    """python -m airunner_native.launcher should execute main()."""
    result = run_python_module("airunner_native.launcher")

    assert result.returncode != 0
    assert "GUI AIRunner startup is disabled during automated tests." in (
        result.stderr + result.stdout
    )


@pytest.mark.fast
def test_launcher_headless_mode_delegates_before_gui_startup(
    monkeypatch,
) -> None:
    """Headless mode should bypass desktop bootstrap entirely."""
    import airunner_native.launcher as launcher

    captured: dict[str, object] = {}

    def fake_headless(argv=None):
        captured["argv"] = list(argv or [])
        return 17

    def fail_desktop(_: float) -> int:
        raise AssertionError("desktop launcher should not run")

    monkeypatch.setenv("AIRUNNER_HEADLESS", "1")
    monkeypatch.setattr(launcher, "_run_headless_launcher", fake_headless)
    monkeypatch.setattr(launcher, "_run_desktop_launcher", fail_desktop)

    assert launcher.main(["--port", "9000"]) == 17
    assert captured["argv"] == ["--port", "9000"]


@pytest.mark.fast
def test_compat_python_launcher_module_executes_main_guard() -> None:
    """python -m airunner.launcher should continue to hit the native main."""
    result = run_python_module("airunner.launcher")

    assert result.returncode != 0
    assert "GUI AIRunner startup is disabled during automated tests." in (
        result.stderr + result.stdout
    )


@pytest.mark.fast
def test_facehugger_activate_kwargs_include_expected_desktop_paths() -> None:
    """Desktop privacy activation should whitelist repo and app paths."""
    import airunner_native.launcher as launcher

    kwargs = launcher._facehugger_activate_kwargs()
    directories = kwargs["darklock_os_whitelisted_directories"]

    assert kwargs["activate_shadowlogger"] is True
    assert kwargs["darklock_os_allow_network"] is True
    assert launcher.AIRUNNER_BASE_PATH in directories
    assert str(REPO_ROOT / "gui" / "src") in directories
    assert str(REPO_ROOT / "services" / "src") in directories
    assert str(REPO_ROOT / "native" / "src") in directories
    assert "/usr/share/zoneinfo/" in directories