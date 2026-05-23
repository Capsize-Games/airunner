"""Regression coverage for package-scoped test surfaces."""

from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys


def _load_run_tests_module():
    repo_root = Path(__file__).resolve().parents[4]
    module_path = (
        repo_root / "gui" / "src" / "airunner" / "bin" / "run_tests.py"
    )
    spec = spec_from_file_location("airunner_gui_run_tests", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


run_tests = _load_run_tests_module()


def test_build_gui_package_test_command() -> None:
    """GUI package mode should target the safe default GUI suite."""
    cmd, description, env = run_tests._build_package_test_command("gui")

    assert description == "GUI package test surface (safe default suite)"
    assert cmd[:3] == [sys.executable, "-m", "pytest"]
    assert str(run_tests.REPO_ROOT / "gui" / "src") in cmd
    assert f"--ignore={run_tests.GUI_COMPONENTS_ROOT / 'eval'}" in cmd
    assert env["AIRUNNER_SKIP_GUI_TESTS"] == "1"


def test_run_package_tests_uses_selected_surface(monkeypatch) -> None:
    """Package mode should hand the selected surface to run_command."""
    captured: dict[str, object] = {}

    def fake_run_command(cmd, description, env=None):
        captured["cmd"] = cmd
        captured["description"] = description
        captured["env"] = env
        return 0

    monkeypatch.setattr(run_tests, "run_command", fake_run_command)

    exit_code = run_tests.run_package_tests("services", verbose=True)

    assert exit_code == 0
    assert captured["description"] == "Service package test surface"
    assert "-v" in captured["cmd"]
    assert str(run_tests.REPO_ROOT / "services" / "src") in captured["cmd"]
    assert captured["env"]["AIRUNNER_SKIP_GUI_TESTS"] == "1"


def test_main_routes_package_mode(monkeypatch) -> None:
    """CLI parsing should route package mode to run_package_tests."""
    called: dict[str, object] = {}

    def fake_run_package_tests(package: str, verbose: bool = False) -> int:
        called["package"] = package
        called["verbose"] = verbose
        return 0

    monkeypatch.setattr(run_tests, "run_package_tests", fake_run_package_tests)

    exit_code = run_tests.main(["--package", "native", "--verbose"])

    assert exit_code == 0
    assert called == {"package": "native", "verbose": True}


def test_main_rejects_component_package_combo(capsys) -> None:
    """Package mode should reject the component-only test selector."""
    exit_code = run_tests.main(["--package", "gui", "--component", "llm"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "--package cannot be combined with --component" in captured.out