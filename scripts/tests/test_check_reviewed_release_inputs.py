"""Contract tests for the fail-closed sibling-input review gate."""

from __future__ import annotations

import shutil
from pathlib import Path

from scripts.check_reviewed_release_inputs import inspect_release_inputs


ROOT = Path(__file__).resolve().parents[2]


def test_quarantined_inputs_fail_closed_without_pin_errors() -> None:
    errors = inspect_release_inputs(
        ROOT, Path(".github/workflows/eval-tests.yml")
    )

    assert errors == [
        "pending-source-review: quarantined release inputs: "
        "airunner-common, airunner-tts-vendor, facehuggershield"
    ]


def test_sibling_checkout_ref_must_match_manifest(tmp_path: Path) -> None:
    required_paths = [
        Path("release-planning/services/release-inputs.json"),
        Path("package/constraints-linux-nvidia-cu129.txt"),
        Path("services/setup.py"),
        Path("native/setup.py"),
        Path(".github/workflows/eval-tests.yml"),
        Path(".github/workflows/pypi-dispatch.yml"),
    ]
    for relative in required_paths:
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, destination)

    workflow_path = tmp_path / ".github/workflows/eval-tests.yml"
    workflow = workflow_path.read_text(encoding="utf-8")
    workflow_path.write_text(
        workflow.replace(
            "544a553dc565a91407d9654358e8b4bc3b480b94",
            "1111111111111111111111111111111111111111",
            1,
        ),
        encoding="utf-8",
    )

    errors = inspect_release_inputs(
        tmp_path, Path(".github/workflows/pypi-dispatch.yml")
    )

    assert any(
        "airunner-common: workflow source refs do not match" in error
        for error in errors
    )
    assert any(error.startswith("pending-source-review:") for error in errors)


def test_release_workflow_gates_precede_dependency_execution() -> None:
    eval_workflow = (ROOT / ".github/workflows/eval-tests.yml").read_text(
        encoding="utf-8"
    )
    release_workflow = (ROOT / ".github/workflows/pypi-dispatch.yml").read_text(
        encoding="utf-8"
    )

    def job_slice(text: str, job: str, following: str) -> str:
        start = text.index(f"  {job}:")
        return text[start : text.index(f"  {following}:", start)]

    for job, next_job in (
        ("runtime-contract-tests", "runtime-smoke"),
        ("runtime-smoke", "packaging-gates"),
        ("packaging-gates", None),
    ):
        section = (
            job_slice(eval_workflow, job, next_job)
            if next_job
            else eval_workflow[eval_workflow.index(f"  {job}:") :]
        )
        gate = section.index("check_reviewed_release_inputs.py")
        if job == "runtime-contract-tests":
            assert gate < section.index("Checkout facehuggershield source")
        if job == "runtime-smoke":
            assert gate < section.index("Checkout facehuggershield source")
        if job == "packaging-gates":
            assert gate < section.index("Install source-gate test tools")
            assert gate < section.index("Build candidate wheels")

    for job, next_job in (
        ("linux-candidate", "candidate-gate"),
        ("build-python-package", "fetch-sidecars"),
    ):
        section = job_slice(release_workflow, job, next_job)
        gate = section.index("check_reviewed_release_inputs.py")
        assert gate < section.index("Install dependencies")
