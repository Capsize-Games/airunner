"""Contract tests for the fail-closed sibling-input review gate."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from scripts.check_reviewed_release_inputs import inspect_release_inputs


ROOT = Path(__file__).resolve().parents[2]
_GATE_FILES = [
    Path("release-planning/services/release-inputs.json"),
    Path("package/constraints-linux-nvidia-cu129-historical-desktop.txt"),
    Path("packaging/linux/services-bundle-spec.toml"),
    Path("services/setup.py"),
    Path("native/setup.py"),
    Path(".github/workflows/eval-tests.yml"),
    Path(".github/workflows/pypi-dispatch.yml"),
]


def _copy_gate_tree(destination_root: Path) -> None:
    for relative in _GATE_FILES:
        destination = destination_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, destination)


def test_quarantined_inputs_fail_closed_without_pin_errors() -> None:
    errors = inspect_release_inputs(
        ROOT, Path(".github/workflows/eval-tests.yml")
    )

    assert errors == [
        "pending-release-lock: linux-release hash lock generation and "
        "validation remain pending",
        "pending-source-review: quarantined release inputs: "
        "airunner-common, facehuggershield",
    ]


def test_deferred_vendor_cannot_be_added_to_release_profile(tmp_path: Path) -> None:
    _copy_gate_tree(tmp_path)
    setup_path = tmp_path / "services/setup.py"
    setup = setup_path.read_text(encoding="utf-8")
    setup = setup.replace('"tts-python-core",', '"tts-python",', 1)
    setup_path.write_text(setup, encoding="utf-8")

    errors = inspect_release_inputs(
        tmp_path, Path(".github/workflows/pypi-dispatch.yml")
    )

    assert any("linux-release aggregates drifted" in error for error in errors)
    assert any("activates the quarantined TTS vendor" in error for error in errors)
    assert any("airunner-tts-vendor" in error for error in errors if error.startswith("pending-source-review:"))

def test_sibling_checkout_ref_must_match_manifest(tmp_path: Path) -> None:
    _copy_gate_tree(tmp_path)

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


def test_manifest_cannot_omit_a_mandatory_distribution(tmp_path: Path) -> None:
    _copy_gate_tree(tmp_path)
    manifest_path = tmp_path / "release-planning/services/release-inputs.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["inputs"] = [
        item
        for item in manifest["inputs"]
        if item["distribution"] != "facehuggershield"
    ]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    errors = inspect_release_inputs(
        tmp_path, Path(".github/workflows/pypi-dispatch.yml")
    )

    assert "mandatory release input is missing: facehuggershield" in errors


def test_quoted_mutable_unregistered_checkout_is_rejected(tmp_path: Path) -> None:
    _copy_gate_tree(tmp_path)
    workflow_path = tmp_path / ".github/workflows/pypi-dispatch.yml"
    with workflow_path.open("a", encoding="utf-8") as workflow:
        workflow.write(
            "\n      - name: Unregistered vendor source\n"
            "        uses: actions/checkout@v4\n"
            "        with:\n"
            '          repository: "Capsize-Games/airunner-tts-vendor"\n'
            "          ref: master\n"
        )

    errors = inspect_release_inputs(
        tmp_path, Path(".github/workflows/pypi-dispatch.yml")
    )

    assert any("unregistered sibling source checkout" in error for error in errors)
    assert any("missing or mutable source ref" in error for error in errors)


def test_checkout_without_ref_is_rejected(tmp_path: Path) -> None:
    _copy_gate_tree(tmp_path)
    workflow_path = tmp_path / ".github/workflows/pypi-dispatch.yml"
    with workflow_path.open("a", encoding="utf-8") as workflow:
        workflow.write(
            "\n      - name: Vendor source without pin\n"
            "        uses: actions/checkout@v4\n"
            "        with:\n"
            "          repository: Capsize-Games/airunner-tts-vendor\n"
        )

    errors = inspect_release_inputs(
        tmp_path, Path(".github/workflows/pypi-dispatch.yml")
    )

    assert any("unregistered sibling source checkout" in error for error in errors)
    assert any("missing or mutable source ref" in error for error in errors)


def test_short_manifest_revision_is_rejected(tmp_path: Path) -> None:
    _copy_gate_tree(tmp_path)
    manifest_path = tmp_path / "release-planning/services/release-inputs.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    vendor = next(
        item
        for item in manifest["inputs"]
        if item["distribution"] == "airunner-tts-vendor"
    )
    vendor["revision"] = "d9228"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    errors = inspect_release_inputs(
        tmp_path, Path(".github/workflows/pypi-dispatch.yml")
    )

    assert any(
        "airunner-tts-vendor: source revision must be a full 40-character SHA"
        in error
        for error in errors
    )


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
