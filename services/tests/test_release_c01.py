"""Regression tests for release issue C01.

Proves the Linux v1 candidate pipeline gates promotion on the
required deterministic checks and artifact completeness: the
candidate job runs the required set, assembles and verifies one
bundle, and never publishes; the gate blocks any required
failed/skipped/cancelled/missing result; publish paths need the
gate; the PR pipeline runs the same set secret-free.

No GUI/model, network, or live DB: YAML/TOML assertions read the
real contracts, and both scripts run on synthetic fixtures only.
"""

from __future__ import annotations

import json
import subprocess
import tomllib
from pathlib import Path

import pytest
import test_release_c01_support as c01


def test_candidate_job_runs_required_checks() -> None:
    """The candidate runs every required safety/auth/download check."""
    jobs = c01._load_yaml(c01._DISPATCH)["jobs"]
    text = c01._steps_text(jobs["linux-candidate"])
    for required in c01._REQUIRED_TESTS:
        assert required in text, f"candidate omits {required}"
    assert "continue-on-error" not in text


def test_candidate_assembles_verifies_and_uploads() -> None:
    """The candidate assembles, stages, verifies, and uploads."""
    jobs = c01._load_yaml(c01._DISPATCH)["jobs"]
    job = jobs["linux-candidate"]
    assert set(job["needs"]) == {"provision-policy", "fetch-sidecars"}
    text = c01._steps_text(job)
    for marker in (
        "scripts/assemble_linux_bundle.py",
        "packaging/linux/stage-sidecars.sh",
        "scripts/inspect_linux_bundle.py",
        "runtime-sidecars-linux.tar.gz",
        "policy-bundle-fragment",
        "llama-server",
        "whisper-server",
        "upload-artifact",
        "linux-candidate",
    ):
        assert marker in text, f"candidate omits {marker}"


def test_candidate_stages_sidecars_before_verifying() -> None:
    """Sidecars stage after the freeze and before verification."""
    jobs = c01._load_yaml(c01._DISPATCH)["jobs"]
    steps = jobs["linux-candidate"]["steps"]
    names = [str(step.get("name", "")) for step in steps]
    wants = (
        "Assemble candidate bundle",
        "Stage sidecars",
        "Verify candidate manifest",
        "Upload Linux candidate archive",
    )
    positions = [[i for i, n in enumerate(names) if w in n] for w in wants]
    assert all(len(found) == 1 for found in positions)
    flat = [found[0] for found in positions]
    assert flat == sorted(flat)


def test_release_archives_verified_candidate_before_upload_and_promotion() -> None:
    """The exact SHA-bound bundle archive is uploaded, then rechecked."""
    jobs = c01._load_yaml(c01._DISPATCH)["jobs"]
    candidate_steps = jobs["linux-candidate"]["steps"]
    names = [str(step.get("name", "")) for step in candidate_steps]
    assert names.index("Verify candidate manifest") < names.index(
        "Package verified Linux candidate"
    ) < names.index("Upload Linux candidate archive")
    assemble = next(
        step for step in candidate_steps
        if step.get("name") == "Assemble candidate bundle"
    )
    assert '--base "${{ github.sha }}"' in assemble["run"]
    upload = next(
        step for step in candidate_steps
        if step.get("name") == "Upload Linux candidate archive"
    )
    assert "*.tar.gz" in upload["with"]["path"]

    publish = jobs["publish-release-assets"]
    publish_steps = publish["steps"]
    publish_names = [str(step.get("name", "")) for step in publish_steps]
    assert publish_names.index("Download verified Linux candidate archive") < (
        publish_names.index("Verify candidate and checksum final release assets")
    )
    assert publish_names.index(
        "Verify candidate and checksum final release assets"
    ) < publish_names.index("Upload release assets")
    verify = next(
        step for step in publish_steps
        if step.get("name") == "Verify candidate and checksum final release assets"
    )
    assert "linux_candidate_artifact.py verify" in verify["run"]
    assert "linux_candidate_artifact.py checksums" in verify["run"]
    assert "${{ github.sha }}" in verify["env"]["RELEASE_SOURCE_SHA"]
    upload_release = next(
        step for step in publish_steps
        if step.get("name") == "Upload release assets"
    )
    assert "linux-candidate/*" in upload_release["with"]["files"]
    assert "SHA256SUMS" in upload_release["with"]["files"]


def test_promotion_checks_tag_source_and_existing_assets_before_side_effects() -> None:
    """Tag/version identity and collision checks precede protected actions."""
    jobs = c01._load_yaml(c01._DISPATCH)["jobs"]
    provision_steps = jobs["provision-policy"]["steps"]
    provision_names = [str(step.get("name", "")) for step in provision_steps]
    assert provision_names.index("Verify promotion tag and source identity") < (
        provision_names.index("Retrieve and stage signed policy artifact")
    )

    candidate_steps = jobs["linux-candidate"]["steps"]
    candidate_names = [str(step.get("name", "")) for step in candidate_steps]
    assert candidate_names.index("Verify promotion tag and source identity") < (
        candidate_names.index("Install dependencies")
    )
    candidate_checkout = candidate_steps[0]["with"]
    assert candidate_checkout["fetch-depth"] == 0

    package_steps = jobs["build-python-package"]["steps"]
    package_names = [str(step.get("name", "")) for step in package_steps]
    assert package_names.index("Verify promotion tag and source identity") < (
        package_names.index("Build packages")
    )
    assert package_names.index("Recheck promotion tag before PyPI upload") < (
        package_names.index("Publish package")
    )

    release_steps = jobs["publish-release-assets"]["steps"]
    release_names = [str(step.get("name", "")) for step in release_steps]
    assert release_names.index(
        "Preflight immutable release asset identities"
    ) < release_names.index("Upload release assets")
    preflight = next(
        step for step in release_steps
        if step.get("name") == "Preflight immutable release asset identities"
    )
    assert "GITHUB_TOKEN" in preflight["env"]
    assert "--check-release-assets" in preflight["run"]
    assert "--github-token" not in preflight["run"]


def test_candidate_creation_publishes_nothing() -> None:
    """The candidate job has no publish step, secret, or environment."""
    jobs = c01._load_yaml(c01._DISPATCH)["jobs"]
    job = jobs["linux-candidate"]
    assert "environment" not in job
    text = c01._steps_text(job).lower()
    for marker in c01._PUBLISH_MARKERS:
        assert marker not in text, f"candidate leaks {marker}"


def test_gate_passes_every_required_result() -> None:
    """The gate runs always and reports every need to the script."""
    jobs = c01._load_yaml(c01._DISPATCH)["jobs"]
    job = jobs["candidate-gate"]
    assert job["if"] == "always()"
    assert list(job["needs"]) == list(c01._GATE_NEEDS)
    text = c01._steps_text(job)
    assert "packaging/linux/candidate-gate.sh" in text
    for need in job["needs"]:
        assert f"needs.{need}.result" in text, f"gate omits {need}"


def test_no_continue_on_error_on_required_path() -> None:
    """No required release job tolerates a failed step."""
    jobs = c01._load_yaml(c01._DISPATCH)["jobs"]
    for name in c01._REQUIRED_JOBS:
        job = jobs[name]
        assert job.get("continue-on-error") in (None, False), name
        for step in job.get("steps", []):
            assert step.get("continue-on-error") in (
                None,
                False,
            ), f"{name}/{step.get('name')}"


def test_publish_paths_need_candidate_gate() -> None:
    """Both publish paths require an exactly-green gate result."""
    jobs = c01._load_yaml(c01._DISPATCH)["jobs"]
    build = jobs["build-python-package"]
    assert "candidate-gate" in build["needs"]
    assert "needs.candidate-gate.result == 'success'" in build["if"]
    assets = jobs["publish-release-assets"]
    assert "candidate-gate" in assets["needs"]


def test_pypi_publish_requires_explicit_dispatch_opt_in() -> None:
    """A published GitHub release never publishes to PyPI implicitly."""
    workflow = c01._load_yaml(c01._DISPATCH)
    triggers = workflow.get("on", workflow.get(True, {}))
    opt_in = triggers["workflow_dispatch"]["inputs"]["publish_pypi"]
    assert opt_in["type"] == "boolean"
    assert opt_in["default"] is False

    steps = workflow["jobs"]["build-python-package"]["steps"]
    publishers = [
        step for step in steps
        if "pypa/gh-action-pypi-publish" in str(step.get("uses", ""))
    ]
    assert len(publishers) == 1
    assert publishers[0]["if"] == (
        "github.event_name == 'workflow_dispatch' && inputs.publish_pypi == true"
    )


def test_all_release_checkouts_use_the_tested_source_ref() -> None:
    """Release jobs use the tag SHA; manual runs use their selected SHA."""
    jobs = c01._load_yaml(c01._DISPATCH)["jobs"]
    expected_ref = "${{ github.sha }}"
    for job_name, job in jobs.items():
        for step in job.get("steps", []):
            if str(step.get("uses", "")).startswith("actions/checkout@"):
                assert step.get("with", {}).get("ref") == expected_ref, job_name


def test_pr_pipeline_runs_required_set_secret_free() -> None:
    """The PR contracts run the required set with no secrets."""
    text = c01._EVAL.read_text(encoding="utf-8")
    assert "secrets." not in text
    assert "continue-on-error:" not in text
    jobs = c01._load_yaml(c01._EVAL)["jobs"]
    steps = jobs["runtime-contract-tests"]["steps"]
    runs = "\n".join(str(step.get("run", "")) for step in steps)
    for required in c01._REQUIRED_TESTS:
        assert required in runs, f"PR pipeline omits {required}"


def test_bundle_spec_covers_expected_components() -> None:
    """The spec names the manifest, entry, sidecars, and payloads."""
    spec = tomllib.loads(c01._SPEC.read_text(encoding="utf-8"))
    assert spec["bundle"]["executable"] == "airunner-daemon"
    assert set(spec["manifest"]["required_fields"]) >= {
        "bundle",
        "tool",
        "entry",
        "base",
        "files",
    }
    primary = [e for e in spec["console_script"] if e.get("primary")]
    assert [e["name"] for e in primary] == ["airunner-daemon"]
    assert {r["name"] for r in spec["runtime"]} == {
        "llama-server",
        "whisper-server",
    }
    assert spec["exclusions"]["patterns"] != []
    assert spec["qt"]["required"] is False


def test_gate_allows_green_release() -> None:
    """All-success on release promotes the candidate."""
    proc = c01._run_gate("--event", "release", *c01._release_checks())
    assert proc.returncode == 0, proc.stderr
    assert "promotion allowed" in proc.stdout


@pytest.mark.parametrize("result", c01._BLOCKING_RESULTS)
def test_gate_blocks_non_success_result(result: str) -> None:
    """Any failed/skipped/cancelled/missing result blocks release."""
    proc = c01._run_gate("--event", "release", *c01._release_checks(result))
    assert proc.returncode != 0
    assert "promotion blocked" in proc.stderr


def test_gate_blocks_missing_check() -> None:
    """An unreported required check blocks promotion."""
    args: list[str] = ["--event", "release"]
    for job in c01._GATE_NEEDS:
        if job != "fetch-sidecars":
            args += ["--check", f"{job}=success"]
    proc = c01._run_gate(*args)
    assert proc.returncode != 0
    assert "no result reported for fetch-sidecars" in proc.stderr


@pytest.mark.parametrize(
    ("candidate", "allowed"), [("success", True), ("failure", False)]
)
def test_gate_dispatch_needs_green_candidate(
    candidate: str, allowed: bool
) -> None:
    """Dispatch ignores release-only skips, requires the candidate."""
    proc = c01._run_gate(
        "--event",
        "workflow_dispatch",
        "--check",
        "provision-policy=skipped",
        "--check",
        "provision-policy-fixture=success",
        "--check",
        "fetch-sidecars=skipped",
        "--check",
        f"linux-candidate={candidate}",
    )
    assert (proc.returncode == 0) == allowed, proc.stderr


def test_gate_rejects_bad_invocation() -> None:
    """Unknown events, no checks, and bad flags all fail closed."""
    bad_event = c01._run_gate("--event", "push", *c01._release_checks())
    assert bad_event.returncode != 0
    assert c01._run_gate("--event", "release").returncode != 0
    assert c01._run_gate("--event").returncode != 0
    assert c01._run_gate("--bogus", "x").returncode != 0


def test_stage_sidecars_extends_manifest(tmp_path: Path) -> None:
    """Staging installs sidecars and extends the manifest, sorted."""
    bundle, tarball = c01._stage_fixture(tmp_path)
    proc = c01._run_stage(
        "--tarball",
        str(tarball),
        "--bundle",
        str(bundle),
        "--",
        "llama-server",
        "whisper-server",
    )
    assert proc.returncode == 0, proc.stderr
    manifest = json.loads((bundle / "bundle-manifest.json").read_text())
    paths = [entry["path"] for entry in manifest["files"]]
    assert paths == sorted(paths)
    assert {"bin/llama-server", "bin/whisper-server"} <= set(paths)
    assert (bundle / "bin" / "llama-server").is_file()


def test_stage_sidecars_fails_closed(tmp_path: Path) -> None:
    """Missing binaries, bundles, and bad names all exit non-zero."""
    bundle, tarball = c01._stage_fixture(tmp_path)
    cases = [
        ["--bundle", str(bundle), "--", "nope"],
        ["--bundle", str(tmp_path / "absent"), "--", "llama-server"],
        ["--bundle", str(bundle)],
        ["--bundle", str(bundle), "--", "../evil"],
    ]
    for argv in cases:
        proc = c01._run_stage("--tarball", str(tarball), *argv)
        assert proc.returncode != 0, argv


@pytest.mark.parametrize("script", [c01._GATE, c01._STAGE])
def test_scripts_pass_shell_syntax(script: Path) -> None:
    """Both release scripts parse under bash -n."""
    proc = subprocess.run(["bash", "-n", str(script)], capture_output=True)
    assert proc.returncode == 0, proc.stderr
