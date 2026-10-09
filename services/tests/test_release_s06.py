"""Release regression tests for S06 (trusted release provisioning).

The release stage (``scripts/build_policy_terms.py --stage-release``)
verifies an already-compiled artifact plus its detached sidecar against
an expected digest and an owner-provisioned trust store, then stages
the exact bytes. Absent, invalid, empty, or synthetic-only data fails
with exit code 2 and writes nothing.

Every token used here is synthetic and neutral. Signing keys are
throwaway Ed25519 keys generated at test time; no private key,
production term, or production data appears in this file.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import re
import shutil
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest
import yaml
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.build_policy_terms import (  # noqa: E402
    PolicyBuildError,
    load_release_trust_store,
    main,
    render_artifact,
    stage_release_artifact,
)

from airunner_services.content_safety import (  # noqa: E402
    hash_token,
)
from airunner_services.content_safety.policy_signature import (  # noqa: E402
    ED25519_PUBLIC_KEY_BYTES,
    SIGNATURE_FORMAT_ID,
)

_KEY_ID_A = "test-only-release-1"
_KEY_ID_B = "test-only-release-2"

_TERMS = ["zorrb", "quixnor"]
_PINNED_USES_RE = re.compile(r"^[^@\s]+@[0-9a-f]{40}$")


@pytest.fixture
def work_dir() -> Iterator[Path]:
    """Create a scratch dir under the (gitignored) repo-local tmp/ tree."""
    base = _PROJECT_ROOT / "tmp" / "content_safety_tests"
    base.mkdir(parents=True, exist_ok=True)
    created = Path(tempfile.mkdtemp(prefix="s06_", dir=base))
    yield created
    shutil.rmtree(created, ignore_errors=True)


def _keypair() -> tuple[Ed25519PrivateKey, bytes]:
    """Generate a throwaway test-only Ed25519 keypair."""
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes_raw()
    assert len(public) == ED25519_PUBLIC_KEY_BYTES
    return private, public


def _sign(private: Ed25519PrivateKey, key_id: str, data: bytes) -> bytes:
    """Render a sidecar signature file for the exact ``data`` bytes."""
    text = (
        f"# format: {SIGNATURE_FORMAT_ID}\n"
        f"# key_id: {key_id}\n"
        f"# signature: {private.sign(data).hex()}\n"
    )
    return text.encode("utf-8")


def _valid_text() -> str:
    return render_artifact({hash_token(term) for term in _TERMS})


def _write_signed(
    work_dir: Path,
    text: str,
    private: Ed25519PrivateKey,
    key_id: str,
    name: str = "policy_terms.dat",
) -> Path:
    """Write artifact ``text`` plus its sidecar; return artifact path."""
    path = work_dir / name
    data = text.encode("utf-8")
    path.write_bytes(data)
    Path(str(path) + ".sig").write_bytes(_sign(private, key_id, data))
    return path


def _write_trust_store(work_dir: Path, store: dict[str, bytes]) -> Path:
    """Write a JSON trust store for ``store``; return its path."""
    path = work_dir / "trust-store.json"
    path.write_text(
        json.dumps({key: value.hex() for key, value in store.items()}),
        encoding="utf-8",
    )
    return path


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stage_args(artifact: Path, store: Path, digest: str, out: Path):
    return [
        "--stage-release",
        "--artifact",
        str(artifact),
        "--trust-store",
        str(store),
        "--expected-sha256",
        digest,
        "--output",
        str(out),
    ]


def _secret_strings(store: dict[str, bytes], digest: str) -> list[str]:
    """Return every string that must never reach output or errors."""
    secrets = list(_TERMS)
    secrets.extend(hash_token(term) for term in _TERMS)
    secrets.extend(public.hex() for public in store.values())
    secrets.append(digest)
    return secrets


def test_release_stage_success_stages_exact_bytes(
    work_dir: Path,
) -> None:
    """A verified artifact stages byte-identically with counts only."""
    private, public = _keypair()
    store = {_KEY_ID_A: public}
    artifact = _write_signed(work_dir, _valid_text(), private, _KEY_ID_A)
    store_path = _write_trust_store(work_dir, store)
    digest = _digest(artifact)
    out = work_dir / "staged.dat"

    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(
        stderr
    ):
        rc = main(_stage_args(artifact, store_path, digest, out))

    assert rc == 0
    assert out.read_bytes() == artifact.read_bytes()
    printed = stdout.getvalue()
    assert "hashes staged: 2" in printed
    assert f"key id: {_KEY_ID_A}" in printed
    for secret in _secret_strings(store, digest):
        assert secret not in printed
        assert secret not in stderr.getvalue()


def test_release_stage_absent_artifact_fails(work_dir: Path) -> None:
    """A missing artifact fails without writing anything."""
    _, public = _keypair()
    store_path = _write_trust_store(work_dir, {_KEY_ID_A: public})
    out = work_dir / "staged.dat"

    rc = main(
        _stage_args(
            work_dir / "does_not_exist.dat",
            store_path,
            "0" * 64,
            out,
        )
    )

    assert rc == 2
    assert not out.exists()


def test_release_stage_digest_mismatch_fails(work_dir: Path) -> None:
    """A wrong expected digest fails without writing anything."""
    private, public = _keypair()
    artifact = _write_signed(work_dir, _valid_text(), private, _KEY_ID_A)
    store_path = _write_trust_store(work_dir, {_KEY_ID_A: public})
    out = work_dir / "staged.dat"

    rc = main(_stage_args(artifact, store_path, "0" * 64, out))

    assert rc == 2
    assert not out.exists()


def test_release_stage_tampered_body_fails(work_dir: Path) -> None:
    """Edited bytes fail the signature even when the digest matches."""
    private, public = _keypair()
    artifact = _write_signed(work_dir, _valid_text(), private, _KEY_ID_A)
    lines = artifact.read_text(encoding="utf-8").splitlines(keepends=True)
    for index, line in enumerate(lines):
        if line.strip() and not line.startswith("#"):
            flipped = "0" if line[0] != "0" else "1"
            lines[index] = flipped + line[1:]
            break
    artifact.write_text("".join(lines), encoding="utf-8")
    store_path = _write_trust_store(work_dir, {_KEY_ID_A: public})
    out = work_dir / "staged.dat"

    rc = main(_stage_args(artifact, store_path, _digest(artifact), out))

    assert rc == 2
    assert not out.exists()


def test_release_stage_invalid_artifact_fails(work_dir: Path) -> None:
    """A versioned artifact with a bad inner digest is rejected."""
    private, public = _keypair()
    text = (
        "# format: airunner-policy-data/1\n"
        "# normalization: v1\n"
        "# count: 1\n"
        "# sha256: " + "0" * 64 + "\n" + hash_token(_TERMS[0]) + "\n"
    )
    artifact = _write_signed(work_dir, text, private, _KEY_ID_A)
    store_path = _write_trust_store(work_dir, {_KEY_ID_A: public})
    out = work_dir / "staged.dat"

    rc = main(_stage_args(artifact, store_path, _digest(artifact), out))

    assert rc == 2
    assert not out.exists()


def test_release_stage_missing_sidecar_fails(work_dir: Path) -> None:
    """Unsigned synthetic-only data never stages in release mode."""
    _, public = _keypair()
    artifact = work_dir / "policy_terms.dat"
    artifact.write_text(_valid_text(), encoding="utf-8")
    store_path = _write_trust_store(work_dir, {_KEY_ID_A: public})
    out = work_dir / "staged.dat"

    rc = main(_stage_args(artifact, store_path, _digest(artifact), out))

    assert rc == 2
    assert not out.exists()


def test_release_stage_untrusted_key_fails(work_dir: Path) -> None:
    """Data signed outside the release trust store is synthetic-only."""
    private_b, _ = _keypair()
    _, public_a = _keypair()
    artifact = _write_signed(work_dir, _valid_text(), private_b, _KEY_ID_B)
    store_path = _write_trust_store(work_dir, {_KEY_ID_A: public_a})
    out = work_dir / "staged.dat"

    rc = main(_stage_args(artifact, store_path, _digest(artifact), out))

    assert rc == 2
    assert not out.exists()


def test_release_stage_empty_artifact_fails(work_dir: Path) -> None:
    """An empty digest set is a build error, never staged silently."""
    private, public = _keypair()
    text = (
        "# format: airunner-policy-data/1\n"
        "# normalization: v1\n"
        "# count: 0\n"
        "# sha256: "
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855\n"
    )
    artifact = _write_signed(work_dir, text, private, _KEY_ID_A)
    store_path = _write_trust_store(work_dir, {_KEY_ID_A: public})
    out = work_dir / "staged.dat"

    rc = main(_stage_args(artifact, store_path, _digest(artifact), out))

    assert rc == 2
    assert not out.exists()


def test_release_stage_malformed_inputs_fail(work_dir: Path) -> None:
    """Missing flags, bad digests, and bad trust stores all fail."""
    private, public = _keypair()
    artifact = _write_signed(work_dir, _valid_text(), private, _KEY_ID_A)
    good_store = _write_trust_store(work_dir, {_KEY_ID_A: public})
    digest = _digest(artifact)
    out = work_dir / "staged.dat"

    assert main(["--stage-release", "--output", str(out)]) == 2
    assert main(_stage_args(artifact, good_store, "zz", out)) == 2
    assert not out.exists()

    bad_stores = [
        "{not json",
        json.dumps({}),
        json.dumps([]),
        json.dumps({_KEY_ID_A: "zz"}),
        json.dumps({_KEY_ID_A: "00"}),
        json.dumps({_KEY_ID_A: "0" * 62}),
        json.dumps({_KEY_ID_A: 42}),
        json.dumps({"": public.hex()}),
    ]
    for index, payload in enumerate(bad_stores):
        store_path = work_dir / f"bad-store-{index}.json"
        store_path.write_text(payload, encoding="utf-8")
        with pytest.raises(PolicyBuildError):
            load_release_trust_store(store_path)
        rc = main(_stage_args(artifact, store_path, digest, out))
        assert rc == 2
    assert not out.exists()


def test_release_stage_errors_are_content_free(work_dir: Path) -> None:
    """Failure output never carries terms, hashes, keys, or digests."""
    private_b, _ = _keypair()
    _, public_a = _keypair()
    artifact = _write_signed(work_dir, _valid_text(), private_b, _KEY_ID_B)
    store = {_KEY_ID_A: public_a}
    store_path = _write_trust_store(work_dir, store)
    digest = _digest(artifact)
    secrets = _secret_strings(store, digest)

    cases = [
        _stage_args(artifact, store_path, "0" * 64, work_dir / "a.dat"),
        _stage_args(artifact, store_path, digest, work_dir / "b.dat"),
        _stage_args(
            work_dir / "missing.dat",
            store_path,
            digest,
            work_dir / "c.dat",
        ),
    ]
    for args in cases:
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout):
            with contextlib.redirect_stderr(stderr):
                assert main(args) == 2
        for secret in secrets:
            assert secret not in stdout.getvalue()
            assert secret not in stderr.getvalue()


def test_stage_release_artifact_returns_key_and_count(
    work_dir: Path,
) -> None:
    """The stage helper reports the signing key ID and hash count."""
    private, public = _keypair()
    artifact = _write_signed(work_dir, _valid_text(), private, _KEY_ID_A)

    data, key_id, count = stage_release_artifact(
        artifact=artifact,
        trust_store={_KEY_ID_A: public},
        expected_sha256=_digest(artifact),
    )

    assert data == artifact.read_bytes()
    assert key_id == _KEY_ID_A
    assert count == len(_TERMS)


# ---------------------------------------------------------------------------
# Trusted workflow wiring (static checks over pypi-dispatch.yml)
# ---------------------------------------------------------------------------


def _workflow() -> dict:
    """Return the parsed PyPI dispatch workflow."""
    path = _PROJECT_ROOT / ".github" / "workflows" / "pypi-dispatch.yml"
    with path.open(encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle)
    assert isinstance(loaded, dict)
    return loaded


def _job_text(job: dict) -> str:
    return yaml.safe_dump(job, default_flow_style=False)


def _uses_entries(job: dict) -> list[str]:
    return [step["uses"] for step in job.get("steps", []) if "uses" in step]


def _run_blocks(job: dict) -> list[str]:
    return [step["run"] for step in job.get("steps", []) if "run" in step]


def test_workflow_trusted_job_is_release_only() -> None:
    """Provisioning needs the release event plus the protected env."""
    workflow = _workflow()
    # NOTE: YAML 1.1 parses the `on` key as boolean True.
    assert "pull_request" not in workflow[True]
    job = workflow["jobs"]["provision-policy"]
    assert job["if"] == "github.event_name == 'release'"
    assert job["environment"] == "release-policy"
    assert job["permissions"] == {"contents": "read"}
    checkout = job["steps"][0]
    assert checkout["with"]["ref"] == ("${{ github.event.release.tag_name }}")
    assert checkout["with"]["persist-credentials"] is False


def test_workflow_trusted_actions_are_pinned() -> None:
    """Secret-adjacent steps use immutable action SHAs, not tags."""
    workflow = _workflow()
    jobs = workflow["jobs"]
    entries = _uses_entries(jobs["provision-policy"])
    entries.extend(
        uses
        for uses in _uses_entries(jobs["build-python-package"])
        if "download-artifact" in uses
    )
    assert entries
    for uses in entries:
        assert _PINNED_USES_RE.match(uses), f"unpinned action: {uses}"


def test_workflow_trusted_job_hides_secrets() -> None:
    """No shell tracing, env dumps, or general artifact uploads."""
    workflow = _workflow()
    job = workflow["jobs"]["provision-policy"]
    runs = "\n".join(_run_blocks(job))
    assert "set -x" not in runs
    assert "printenv" not in runs
    assert "echo" not in runs
    uploads = [
        step
        for step in job["steps"]
        if "upload-artifact" in step.get("uses", "")
    ]
    assert len(uploads) == 1
    assert uploads[0]["with"]["name"] == "policy-bundle-fragment"
    assert uploads[0]["with"]["retention-days"] == 1
    assert uploads[0]["with"]["if-no-files-found"] == "error"


def test_workflow_fixture_job_is_secret_free() -> None:
    """The fixture job validates wiring without env or secrets."""
    workflow = _workflow()
    job = workflow["jobs"]["provision-policy-fixture"]
    assert "environment" not in job
    text = _job_text(job)
    assert "secrets." not in text
    assert "services/tests/test_release_s06.py" in text


def test_workflow_build_consumes_verified_fragment() -> None:
    """Releases build on the staged fragment; dispatches skip it."""
    workflow = _workflow()
    job = workflow["jobs"]["build-python-package"]
    assert "provision-policy" in job["needs"]
    assert "needs.provision-policy.result == 'success'" in job["if"]
    assert "needs.provision-policy.result == 'skipped'" in job["if"]
    guarded = [
        step
        for step in job["steps"]
        if step.get("if") == "needs.provision-policy.result == 'success'"
    ]
    assert len(guarded) == 2
    assert "policy-bundle-fragment" in _job_text(guarded[0])
    assert "content_safety/data/policy_terms.dat" in _job_text(guarded[1])


def test_packaging_ships_the_detached_sidecar() -> None:
    """The staged .sig rides the sdist -> wheel path with the .dat."""
    setup_text = (_PROJECT_ROOT / "services" / "setup.py").read_text(
        encoding="utf-8"
    )
    manifest_text = (_PROJECT_ROOT / "services" / "MANIFEST.in").read_text(
        encoding="utf-8"
    )
    assert '"data/*.dat.sig"' in setup_text
    assert "data/*.dat.sig" in manifest_text
