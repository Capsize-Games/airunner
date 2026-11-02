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
import re
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
    assert set(job["needs"]) == {"fetch-sidecars"}
    text = c01._steps_text(job)
    for marker in (
        "scripts/assemble_linux_bundle.py",
        "packaging/linux/stage-sidecars.sh",
        "scripts/inspect_linux_bundle.py",
        "runtime-sidecars-linux.tar.gz",
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
    stage = next(
        step for step in steps if step.get("name") == "Stage sidecars and extend manifest"
    )
    assert "--checksums .github/native-sidecar-checksums.json" in stage["run"]
    assert "--tag-file .github/native-sidecar-version" in stage["run"]
    assert "--platform linux" in stage["run"]


def test_release_archives_are_verified_before_draft_promotion() -> None:
    """The exact SHA-bound bundle is checked before draft assets are attached."""
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
    ) < publish_names.index("Create draft, attach all assets, and publish immutable release")
    verify = next(
        step for step in publish_steps
        if step.get("name") == "Verify candidate and checksum final release assets"
    )
    assert "linux_candidate_artifact.py verify" in verify["run"]
    assert "linux_candidate_artifact.py checksums" in verify["run"]
    assert "${{ github.sha }}" in verify["env"]["RELEASE_SOURCE_SHA"]
    promotion = next(
        step for step in publish_steps
        if step.get("name") == "Create draft, attach all assets, and publish immutable release"
    )
    assert promotion["env"]["GITHUB_TOKEN"] == "${{ github.token }}"
    assert "--promote-release-assets" in promotion["run"]
    assert "gh release upload" not in promotion["run"]


def test_debian_build_and_asset_share_candidate_gate_identity() -> None:
    """The .deb is built after candidate gates and attached without replacement."""
    jobs = c01._load_yaml(c01._DISPATCH)["jobs"]
    build = jobs["build-debian-package"]
    assert set(build["needs"]) == {"candidate-gate", "build-python-package"}
    assert build["if"] == "github.event_name == 'workflow_dispatch' && inputs.promote_release == true"
    assert build["runs-on"] == "ubuntu-26.04"
    text = c01._steps_text(build)
    assert "scripts/check_release_identity.py" in text
    assert "constraints-linux-core.txt" in text
    assert "AIRUNNER_CORE_PYTHON" in text
    assert "--no-build-isolation" in text
    assert "services-core-bundle-spec.toml" in (
        c01._ROOT / "debian/rules"
    ).read_text(encoding="utf-8")
    assert "dpkg-buildpackage --build=binary --no-sign" in text
    assert "packaging/apt/release_manifest.py" in text
    assert "GITHUB_RUN_ID" in text
    assert "actions/upload-artifact" in text
    assert "publish.sh" not in text
    assert "ssh " not in text

    release_job = jobs["publish-release-assets"]
    assert "build-debian-package" in release_job["needs"]
    release_steps = release_job["steps"]
    download = next(
        step for step in release_steps
        if step.get("name") == "Download Debian package and source manifest"
    )
    assert download["with"]["name"] == "debian-release"
    assert download["with"]["path"] == "release-assets/debian"
    promotion = next(
        step for step in release_steps
        if step.get("name") == "Create draft, attach all assets, and publish immutable release"
    )
    assert "--asset-dir release-assets/debian" in promotion["run"]
    assert "--promote-release-assets" in promotion["run"]
    checksum = next(
        step for step in release_steps
        if step.get("name") == "Verify candidate and checksum final release assets"
    )
    assert "release-assets/debian" in checksum["run"]


def test_release_workflows_pin_every_action_to_a_commit() -> None:
    """Release and contract workflows use immutable action refs."""
    for workflow_path in (c01._DISPATCH, c01._EVAL):
        workflow = c01._load_yaml(workflow_path)
        for job in workflow["jobs"].values():
            for step in job.get("steps", []):
                uses = step.get("uses")
                if uses:
                    assert re.fullmatch(r"[^@]+@[0-9a-f]{40}", uses), uses


def test_promotion_checks_tag_source_and_existing_assets_before_side_effects() -> None:
    """Tag/version identity and collision checks precede protected actions."""
    jobs = c01._load_yaml(c01._DISPATCH)["jobs"]
    workflow_text = c01._steps_text(jobs["linux-candidate"])
    assert "POLICY_ARTIFACT_URL" not in workflow_text
    assert "POLICY_TRUST_STORE_JSON" not in workflow_text

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

    debian_steps = jobs["build-debian-package"]["steps"]
    debian_names = [str(step.get("name", "")) for step in debian_steps]
    assert debian_names.index("Verify promotion tag and source identity") < (
        debian_names.index("Build and bind the Debian package")
    )

    release_steps = jobs["publish-release-assets"]["steps"]
    release_names = [str(step.get("name", "")) for step in release_steps]
    promotion = next(
        step for step in release_steps
        if step.get("name") == "Create draft, attach all assets, and publish immutable release"
    )
    assert "GITHUB_TOKEN" in promotion["env"]
    assert "--promote-release-assets" in promotion["run"]
    assert "--github-token" not in promotion["run"]

    verify = jobs["verify-published-release"]
    assert verify["if"] == "github.event_name == 'release'"
    verify_text = c01._steps_text(verify)
    assert "--verify-published-release" in verify_text
    assert "gh release upload" not in verify_text
    assert "contents" not in verify["permissions"] or verify["permissions"]["contents"] == "read"


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
    assert list(job["needs"]) == list(c01._GATE_NEEDS)
    assert job["if"] == "always() && github.event_name == 'workflow_dispatch'"
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
    debian = jobs["build-debian-package"]
    assert "candidate-gate" in debian["needs"]
    assert "build-python-package" in debian["needs"]


def test_pypi_publish_requires_explicit_dispatch_opt_in() -> None:
    """A published GitHub release never publishes to PyPI implicitly."""
    workflow = c01._load_yaml(c01._DISPATCH)
    triggers = workflow.get("on", workflow.get(True, {}))
    opt_in = triggers["workflow_dispatch"]["inputs"]["publish_pypi"]
    assert opt_in["type"] == "boolean"
    assert opt_in["default"] is False
    promotion = triggers["workflow_dispatch"]["inputs"]["promote_release"]
    assert promotion["type"] == "boolean"
    assert promotion["default"] is False

    steps = workflow["jobs"]["build-python-package"]["steps"]
    publishers = [
        step for step in steps
        if "pypa/gh-action-pypi-publish" in str(step.get("uses", ""))
    ]
    assert len(publishers) == 1
    assert publishers[0]["if"] == (
        "github.event_name == 'workflow_dispatch' && inputs.publish_pypi == true"
    )


def test_release_event_only_verifies_and_never_builds_or_appends_assets() -> None:
    jobs = c01._load_yaml(c01._DISPATCH)["jobs"]
    assert jobs["verify-published-release"]["if"] == "github.event_name == 'release'"
    for name in ("linux-candidate", "build-debian-package", "fetch-sidecars", "publish-release-assets"):
        assert "github.event_name == 'workflow_dispatch'" in jobs[name]["if"]
    promotion = c01._steps_text(jobs["publish-release-assets"])
    assert "--promote-release-assets" in promotion
    verification = c01._steps_text(jobs["verify-published-release"])
    assert "--verify-published-release" in verification
    assert "upload-artifact" not in verification


def test_package_dispatch_input_is_validated_as_data_before_build() -> None:
    jobs = c01._load_yaml(c01._DISPATCH)["jobs"]
    steps = jobs["build-python-package"]["steps"]
    names = [str(step.get("name", "")) for step in steps]
    assert names.index("Validate requested package selection") < names.index("Build packages")
    build = next(step for step in steps if step.get("name") == "Build packages")
    assert "for pkg in \"${packages[@]}\"" in build["run"]
    assert "${{ inputs.packages" not in build["run"]


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
    checksums, tag_file = c01._write_test_sidecar_pin(tmp_path, tarball)
    proc = c01._run_stage(
        "--tarball",
        str(tarball),
        "--checksums",
        str(checksums),
        "--tag-file",
        str(tag_file),
        "--platform",
        "linux",
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
    checksums, tag_file = c01._write_test_sidecar_pin(tmp_path, tarball)
    pin_args = [
        "--checksums", str(checksums), "--tag-file", str(tag_file),
        "--platform", "linux",
    ]
    cases = [
        ["--bundle", str(bundle), "--", "nope"],
        ["--bundle", str(tmp_path / "absent"), "--", "llama-server"],
        ["--bundle", str(bundle)],
        ["--bundle", str(bundle), "--", "../evil"],
    ]
    for argv in cases:
        proc = c01._run_stage("--tarball", str(tarball), *pin_args, *argv)
        assert proc.returncode != 0, argv


def test_candidate_stage_rejects_checksum_mismatch_before_bundle_changes(
    tmp_path: Path,
) -> None:
    """A wrong archive digest cannot add binaries or change its manifest."""
    bundle, tarball = c01._stage_fixture(tmp_path)
    checksums, tag_file = c01._write_test_sidecar_pin(tmp_path, tarball)
    metadata = json.loads(checksums.read_text())
    metadata["archives"]["linux"]["sha256"] = "f" * 64
    checksums.write_text(json.dumps(metadata))
    before = (bundle / "bundle-manifest.json").read_bytes()
    proc = c01._run_stage(
        "--tarball", str(tarball), "--bundle", str(bundle),
        "--checksums", str(checksums), "--tag-file", str(tag_file),
        "--platform", "linux", "--", "llama-server", "whisper-server",
    )
    assert proc.returncode != 0
    assert "SHA-256 mismatch" in proc.stderr
    assert (bundle / "bundle-manifest.json").read_bytes() == before
    assert list((bundle / "bin").iterdir()) == []


@pytest.mark.parametrize("script", [c01._GATE, c01._STAGE])
def test_scripts_pass_shell_syntax(script: Path) -> None:
    """Both release scripts parse under bash -n."""
    proc = subprocess.run(["bash", "-n", str(script)], capture_output=True)
    assert proc.returncode == 0, proc.stderr
