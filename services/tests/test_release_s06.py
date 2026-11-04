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
import os
import re
import shutil
import subprocess
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
    TRUST_STORE_FILENAME,
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
    """Stage exact bytes, sidecar, and only the verified public key."""
    private, public = _keypair()
    _, other_public = _keypair()
    store = {_KEY_ID_A: public, _KEY_ID_B: other_public}
    artifact = _write_signed(work_dir, _valid_text(), private, _KEY_ID_A)
    store_path = _write_trust_store(work_dir, store)
    digest = _digest(artifact)
    out = work_dir / "staged" / "policy_terms.dat"

    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(
        stderr
    ):
        rc = main(_stage_args(artifact, store_path, digest, out))

    assert rc == 0
    assert out.read_bytes() == artifact.read_bytes()
    assert Path(str(out) + ".sig").read_bytes() == Path(
        str(artifact) + ".sig"
    ).read_bytes()
    staged_store = json.loads(
        (out.parent / TRUST_STORE_FILENAME).read_text(encoding="utf-8")
    )
    assert staged_store == {_KEY_ID_A: public.hex()}
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


def test_release_stage_tampered_signature_fails(work_dir: Path) -> None:
    """Edited sidecar bytes fail even when the artifact is intact."""
    private, public = _keypair()
    artifact = _write_signed(work_dir, _valid_text(), private, _KEY_ID_A)
    sidecar = Path(str(artifact) + ".sig")
    text = sidecar.read_text(encoding="utf-8")
    marker = "# signature: "
    head, _, tail = text.partition(marker)
    assert tail.strip()
    flipped = ("0" if tail[0] != "0" else "1") + tail[1:]
    sidecar.write_text(head + marker + flipped, encoding="utf-8")
    store_path = _write_trust_store(work_dir, {_KEY_ID_A: public})
    digest = _digest(artifact)
    out = work_dir / "staged.dat"

    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(
        stderr
    ):
        rc = main(_stage_args(artifact, store_path, digest, out))

    assert rc == 2
    assert not out.exists()
    for secret in _secret_strings({_KEY_ID_A: public}, digest):
        assert secret not in stdout.getvalue()
        assert secret not in stderr.getvalue()


def test_release_stage_swapped_sidecar_fails(work_dir: Path) -> None:
    """A valid signature over different bytes never stages."""
    private, public = _keypair()
    artifact_a = _write_signed(
        work_dir, _valid_text(), private, _KEY_ID_A, name="a.dat"
    )
    other = render_artifact({hash_token(_TERMS[0])})
    artifact_b = _write_signed(
        work_dir, other, private, _KEY_ID_A, name="b.dat"
    )
    Path(str(artifact_b) + ".sig").write_bytes(
        Path(str(artifact_a) + ".sig").read_bytes()
    )
    store_path = _write_trust_store(work_dir, {_KEY_ID_A: public})
    out = work_dir / "staged.dat"

    rc = main(_stage_args(artifact_b, store_path, _digest(artifact_b), out))

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


def _copy_packaged_runtime(
    package_root: Path, staged_artifact: Path
) -> Path:
    """Copy source package and stage outputs as packaged resources."""
    source = _PROJECT_ROOT / "services" / "src" / "airunner_services"
    package = package_root / "airunner_services"
    shutil.copytree(source, package)
    data_dir = package / "content_safety" / "data"
    shutil.copy2(staged_artifact, data_dir / "policy_terms.dat")
    shutil.copy2(
        Path(str(staged_artifact) + ".sig"),
        data_dir / "policy_terms.dat.sig",
    )
    shutil.copy2(
        staged_artifact.parent / TRUST_STORE_FILENAME,
        data_dir / TRUST_STORE_FILENAME,
    )
    return package_root


def _run_packaged_policy(
    package_root: Path,
    *,
    env_policy: Path,
    expect_valid: bool,
) -> subprocess.CompletedProcess[str]:
    """Load package resources in a fresh process using default trust keys."""
    code = """
import sys
sys.frozen = True
from airunner_services.content_safety.matcher import hash_token
from airunner_services.content_safety.policy_data import is_available, load_policy_hashes
from airunner_services.content_safety.policy_signature import TRUSTED_KEYS
hashes = load_policy_hashes(refresh=True)
expected = frozenset({hash_token('zorrb'), hash_token('quixnor')})
if EXPECT_VALID:
    assert hashes == expected
    assert tuple(TRUSTED_KEYS) == ('test-only-release-1',)
    assert is_available()
    print('verified')
else:
    assert hashes == frozenset()
    assert not is_available()
    print('closed')
""".replace("EXPECT_VALID", repr(expect_valid))
    env = os.environ.copy()
    env["PYTHONPATH"] = str(package_root)
    env["AIRUNNER_CONTENT_SAFETY_DATA"] = str(env_policy)
    # These cases exercise packaged signature verification, which is an
    # explicit application opt-in under the default-disabled policy mode.
    env["AIRUNNER_CONTENT_POLICY_MODE"] = "enforce"
    env["AIRUNNER_CONTENT_SAFETY_ENFORCE_SIGNED"] = "1"
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=package_root,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )


def _stage_synthetic_runtime_package(
    work_dir: Path,
) -> tuple[Path, Path, bytes]:
    """Create a staged package using a throwaway signer and extra key."""
    private, public = _keypair()
    _, other_public = _keypair()
    artifact = _write_signed(work_dir, _valid_text(), private, _KEY_ID_A)
    trust_store = _write_trust_store(
        work_dir, {_KEY_ID_A: public, _KEY_ID_B: other_public}
    )
    staged = work_dir / "staged" / "policy_terms.dat"
    assert main(_stage_args(artifact, trust_store, _digest(artifact), staged)) == 0

    # This alternate signed data proves packaged mode ignores the dev path.
    env_policy = _write_signed(
        work_dir, render_artifact({hash_token("neutral alternate")}),
        private, _KEY_ID_A, name="dev-override.dat",
    )
    package_root = _copy_packaged_runtime(work_dir / "runtime", staged)
    return package_root, env_policy, public


def test_staged_trust_resource_verifies_in_packaged_runtime(
    work_dir: Path,
) -> None:
    """Stage-to-runtime verification uses packaged keys with no injection."""
    package_root, env_policy, public = _stage_synthetic_runtime_package(work_dir)
    staged_store = json.loads(
        (
            package_root / "airunner_services" / "content_safety" / "data"
            / TRUST_STORE_FILENAME
        ).read_text(encoding="utf-8")
    )
    assert staged_store == {_KEY_ID_A: public.hex()}

    result = _run_packaged_policy(
        package_root, env_policy=env_policy, expect_valid=True
    )
    assert result.returncode == 0, result.stderr
    assert "verified" in result.stdout


@pytest.mark.parametrize("store_state", ["missing", "malformed", "untrusted"])
def test_packaged_runtime_trust_store_failures_deny(
    work_dir: Path, store_state: str
) -> None:
    """Missing, malformed, and non-matching stores deny without env fallback."""
    package_root, env_policy, other_public = _stage_synthetic_runtime_package(
        work_dir
    )
    store_path = (
        package_root / "airunner_services" / "content_safety" / "data"
        / TRUST_STORE_FILENAME
    )
    if store_state == "missing":
        store_path.unlink()
    elif store_state == "malformed":
        store_path.write_text("{not json", encoding="utf-8")
    else:
        store_path.write_text(
            json.dumps({_KEY_ID_B: other_public.hex()}), encoding="utf-8"
        )

    result = _run_packaged_policy(
        package_root, env_policy=env_policy, expect_valid=False
    )
    assert result.returncode == 0, result.stderr
    assert "closed" in result.stdout


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


def test_standard_workflow_does_not_provision_private_policy() -> None:
    """Standard service releases have no private corpus or key dependency."""
    workflow = _workflow()
    # NOTE: YAML 1.1 parses the `on` key as boolean True.
    assert "pull_request" not in workflow[True]
    jobs = workflow["jobs"]
    assert "provision-policy" not in jobs
    assert "provision-policy-fixture" not in jobs
    text = yaml.safe_dump(workflow)
    for marker in (
        "release-policy", "POLICY_ARTIFACT_URL", "POLICY_ARTIFACT_TOKEN",
        "POLICY_ARTIFACT_SHA256", "POLICY_TRUST_STORE_JSON",
        "policy-bundle-fragment", "policy-staged/",
    ):
        assert marker not in text


def test_workflow_build_and_candidate_omit_policy_by_default() -> None:
    """Default release artifacts do not depend on policy staging."""
    workflow = _workflow()
    job = workflow["jobs"]["build-python-package"]
    assert job["needs"] == ["candidate-gate"]
    assert "policy" not in _job_text(job).lower()
    candidate = workflow["jobs"]["linux-candidate"]
    candidate_text = _job_text(candidate)
    assert "policy-bundle-fragment" not in candidate_text
    assert "--policy-trust-store" not in candidate_text
    assert "provision-policy" not in candidate_text
