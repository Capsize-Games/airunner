from pathlib import Path

from scripts import run_tests


def test_empty_optional_smoke_suite_skips_pytest_collection(
    tmp_path: Path, monkeypatch
) -> None:
    (tmp_path / "test_unrelated.py").write_text(
        "import unavailable_optional_runtime\n", encoding="utf-8"
    )
    called = False

    def fail_if_run(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("pytest should not collect unrelated tests")

    monkeypatch.setattr(run_tests, "run_command", fail_if_run)

    result = run_tests._run_optional_smoke_suite(
        ["python", "-m", "pytest", str(tmp_path), "-m", "stt_runtime_smoke"],
        "STT runtime smoke tests",
        tmp_path,
        "stt_runtime_smoke",
    )

    assert result == 0
    assert called is False


def test_declared_optional_smoke_marker_runs_pytest(
    tmp_path: Path, monkeypatch
) -> None:
    (tmp_path / "test_smoke.py").write_text(
        "import pytest\n@pytest.mark.stt_runtime_smoke\ndef test_smoke(): pass\n",
        encoding="utf-8",
    )
    observed = {}

    def run(*args, **kwargs):
        observed["args"] = args
        observed["kwargs"] = kwargs
        return 0

    monkeypatch.setattr(run_tests, "run_command", run)

    result = run_tests._run_optional_smoke_suite(
        ["python", "-m", "pytest", str(tmp_path), "-m", "stt_runtime_smoke"],
        "STT runtime smoke tests",
        tmp_path,
        "stt_runtime_smoke",
    )

    assert result == 0
    assert observed["args"][0][0] == "python"


def test_marker_import_alias_runs_pytest(tmp_path: Path) -> None:
    (tmp_path / "optional_test.py").write_text(
        "import pytest as pt\n@pt.mark.stt_runtime_smoke\ndef test_smoke(): pass\n",
        encoding="utf-8",
    )
    assert run_tests._has_pytest_marker(tmp_path, "stt_runtime_smoke")


def test_dynamic_marker_assignment_falls_back_to_pytest(tmp_path: Path) -> None:
    (tmp_path / "test_dynamic.py").write_text(
        "import pytest\npytestmark = getattr(pytest.mark, marker_name)\n",
        encoding="utf-8",
    )
    assert run_tests._has_pytest_marker(tmp_path, "stt_runtime_smoke")


def test_unparseable_test_file_falls_back_to_pytest(tmp_path: Path) -> None:
    (tmp_path / "test_broken.py").write_text("def test_invalid(:\n", encoding="utf-8")
    assert run_tests._has_pytest_marker(tmp_path, "stt_runtime_smoke")


def test_dynamic_conftest_collection_hook_falls_back_to_pytest(
    tmp_path: Path,
) -> None:
    (tmp_path / "conftest.py").write_text(
        "def pytest_collection_modifyitems(session, config, items): pass\n",
        encoding="utf-8",
    )
    assert run_tests._has_pytest_marker(tmp_path, "stt_runtime_smoke")

