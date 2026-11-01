"""Contract tests for the fail-closed sibling-input review gate."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

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
    Path(".github/workflows/docker-release.yml"),
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
    assert any(
        "linux-release extra tts-python activates excluded dependency airunner-tts-vendor"
        in error
        for error in errors
    )
    assert any("airunner-tts-vendor" in error for error in errors if error.startswith("pending-source-review:"))


@pytest.mark.parametrize(
    ("relative_path", "anchor", "expected_error"),
    [
        (
            "services/setup.py",
            'CORE_REQUIREMENTS = [\n',
            "base service requirements activate excluded dependency facehuggershield",
        ),
        (
            "services/setup.py",
            'LLM_NATIVE_REQUIREMENTS = [\n',
            "linux-release extra llm-native activates excluded dependency facehuggershield",
        ),
        (
            "native/setup.py",
            'NATIVE_BASE_REQUIREMENTS = [\n',
            "native base requirements activate excluded dependency facehuggershield",
        ),
    ],
)
def test_reviewed_manifest_cannot_activate_profile_exclusions(
    tmp_path: Path,
    relative_path: str,
    anchor: str,
    expected_error: str,
) -> None:
    _copy_gate_tree(tmp_path)
    setup_path = tmp_path / relative_path
    setup = setup_path.read_text(encoding="utf-8")
    assert anchor in setup
    setup_path.write_text(
        setup.replace(anchor, anchor + '    "facehuggershield==1.0.0",\n', 1),
        encoding="utf-8",
    )

    manifest_path = tmp_path / "release-planning/services/release-inputs.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for item in manifest["inputs"]:
        item["status"] = "reviewed"
        item["activation"] = "approved"
        item["review_record"] = f"review-records/{item['distribution']}.md"
        review_record = tmp_path / item["review_record"]
        review_record.parent.mkdir(parents=True, exist_ok=True)
        review_record.write_text("Reviewed fixture.\n", encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    errors = inspect_release_inputs(
        tmp_path, Path(".github/workflows/pypi-dispatch.yml")
    )

    assert any(expected_error in error for error in errors)

def test_sibling_checkout_ref_must_match_manifest(tmp_path: Path) -> None:
    _copy_gate_tree(tmp_path)

    manifest = json.loads(
        (tmp_path / "release-planning/services/release-inputs.json").read_text(
            encoding="utf-8"
        )
    )
    common = next(
        item for item in manifest["inputs"]
        if item["distribution"] == "airunner-common"
    )
    workflow_path = tmp_path / ".github/workflows/eval-tests.yml"
    workflow = workflow_path.read_text(encoding="utf-8")
    workflow_path.write_text(
        workflow.replace(
            common["revision"],
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
    assert not any(error.startswith("pending-source-review:") for error in errors)


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


def test_deferred_shield_must_remain_excluded_from_release_profile(
    tmp_path: Path,
) -> None:
    _copy_gate_tree(tmp_path)
    manifest_path = tmp_path / "release-planning/services/release-inputs.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["release_profile"]["excludes"].remove("facehuggershield")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    errors = inspect_release_inputs(
        tmp_path, Path(".github/workflows/pypi-dispatch.yml")
    )

    assert any(
        "manifest release profile is not the expected linux-release profile" in error
        for error in errors
    )


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
        if job in {"runtime-contract-tests", "runtime-smoke"}:
            assert gate < section.index("Checkout airunner-common source")
            assert "Checkout facehuggershield source" not in section
            assert ".ci-sources/facehuggershield" not in section
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

    docker_release = (ROOT / ".github/workflows/docker-release.yml").read_text(
        encoding="utf-8"
    )
    docker_job = docker_release[docker_release.index("  build-and-push:"):]
    gate = docker_job.index("check_reviewed_release_inputs.py")
    assert gate < docker_job.index("Set up Docker Buildx")
    assert gate < docker_job.index("Log in to GitHub Container Registry")
    assert gate < docker_job.index("Build ${{ matrix.name }} image")
    assert "ref: ${{ github.event.workflow_run.head_sha || github.sha }}" in docker_job


def test_docker_release_preflight_reports_current_lock_and_source_blockers() -> None:
    errors = inspect_release_inputs(
        ROOT, Path(".github/workflows/docker-release.yml")
    )

    assert errors == [
        "pending-release-lock: linux-release hash lock generation and "
        "validation remain pending",
    ]
