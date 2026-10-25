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

