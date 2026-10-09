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
        "Upload Linux candidate bundle",
    )
    positions = [[i for i, n in enumerate(names) if w in n] for w in wants]
    assert all(len(found) == 1 for found in positions)
    flat = [found[0] for found in positions]
    assert flat == sorted(flat)


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
