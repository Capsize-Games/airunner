"""Release regression tests for P05 policy packaging enforcement.

Proves bundle assembly fails closed (exit 2, content-free, writes
nothing) on an absent/empty/unsigned policy set, that the inspector
rejects synthetic frozen payloads when asked, and that trust-store
verification rejects data signed outside the release process.

Every token here is synthetic and neutral. Signing keys are
throwaway Ed25519 keys generated at test time; no private key,
production term, or production data appears in this file.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import sys
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
_SPEC_PATH = _REPO_ROOT / "packaging" / "linux" / "services-bundle-spec.toml"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import assemble_linux_bundle as assemble_mod  # noqa: E402
import inspect_linux_bundle as inspect_mod  # noqa: E402

_KEY_ID = "test-only-p05-release"
_OTHER_KEY_ID = "test-only-p05-other"
_TOKENS = ["zqxj-fake-one", "wubbl-fake-two"]


def _digests() -> list[str]:
    """Return fixture digests for the synthetic tokens, sorted."""
    return sorted(hashlib.sha256(t.encode()).hexdigest() for t in _TOKENS)


def _artifact_text(digests: list[str]) -> str:
    """Render a strictly versioned artifact for ``digests``."""
    block = "".join(f"{digest}\n" for digest in sorted(set(digests)))
    block_sha = hashlib.sha256(block.encode("utf-8")).hexdigest()
    return (
        "# format: airunner-policy-data/1\n"
        "# normalization: v1\n"
        f"# count: {len(digests)}\n"
        f"# sha256: {block_sha}\n" + block
    )


def _sign(private: Ed25519PrivateKey, key_id: str, data: bytes) -> bytes:
    """Render a sidecar signature file for the exact ``data`` bytes."""
    return (
        "# format: airunner-policy-signature/1\n"
        f"# key_id: {key_id}\n"
        f"# signature: {private.sign(data).hex()}\n"
    ).encode("utf-8")


def _write_staged(
    root: Path,
    text: str,
    private: Ed25519PrivateKey | None,
    key_id: str = _KEY_ID,
) -> Path:
    """Write staged .dat (plus .sig when keyed); return .dat path."""
    staged = root / "staged"
    staged.mkdir(parents=True, exist_ok=True)
    path = staged / "policy_terms.dat"
    data = text.encode("utf-8")
    path.write_bytes(data)
    if private is not None:
        path.with_name(path.name + ".sig").write_bytes(
            _sign(private, key_id, data)
        )
    return path


def _shard() -> dict:
    """Return a minimal spec shard selecting staged/*.dat."""
    return {
        "data": [
            {
                "source": "staged/*.dat",
                "dest": "policy/data",
                "stage": "collect",
                "required": True,
            }
        ]
    }


def _trust_store(root: Path, key_id: str, public: bytes) -> Path:
    """Write a JSON trust store; return its path."""
    path = root / "trust-store.json"
    path.write_text(json.dumps({key_id: public.hex()}), encoding="utf-8")
    return path


def test_gate_absent_set_fails(tmp_path: Path) -> None:
    """No staged .dat is a packaging error, never shipped silently."""
    problems = assemble_mod.gate_staged_policy(_shard(), tmp_path)
    assert problems
    assert any("absent" in problem for problem in problems)


def test_gate_unsigned_set_fails(tmp_path: Path) -> None:
    """A valid but unsigned set never reaches the freeze."""
    _write_staged(tmp_path, _artifact_text(_digests()), None)
    problems = assemble_mod.gate_staged_policy(_shard(), tmp_path)
    assert any("unsigned or synthetic-only" in p for p in problems)


def test_gate_tampered_sidecar_fails(tmp_path: Path) -> None:
    """A truncated sidecar fails the form check."""
    private = Ed25519PrivateKey.generate()
    path = _write_staged(tmp_path, _artifact_text(_digests()), private)
    sidecar = path.with_name(path.name + ".sig")
    sidecar.write_bytes(sidecar.read_bytes()[:-10])
    problems = assemble_mod.gate_staged_policy(_shard(), tmp_path)
    assert problems


def test_gate_trust_store_rejects_tampered_signature(
    tmp_path: Path,
) -> None:
    """A well-formed but forged signature fails trust verification."""
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes_raw()
    path = _write_staged(tmp_path, _artifact_text(_digests()), private)
    sidecar = path.with_name(path.name + ".sig")
    raw = bytearray(sidecar.read_bytes())
    raw[-2] = ord("0") if raw[-2] != ord("0") else ord("1")
    sidecar.write_bytes(bytes(raw))
    store = _trust_store(tmp_path, _KEY_ID, public)
    problems = assemble_mod.gate_staged_policy(
        _shard(), tmp_path, trust_store=store
    )
    assert any("unsigned or synthetic-only" in p for p in problems)


def test_gate_errors_are_content_free(tmp_path: Path) -> None:
    """Gate problems never carry tokens, digests, or key material."""
    _write_staged(tmp_path, _artifact_text(_digests()), None)
    problems = assemble_mod.gate_staged_policy(_shard(), tmp_path)
    assert problems
    reported = "\n".join(problems)
    for secret in (*_TOKENS, *_digests()):
        assert secret not in reported


def test_gate_trust_store_rejects_synthetic_key(tmp_path: Path) -> None:
    """Well-formed data signed outside the store is synthetic-only."""
    private = Ed25519PrivateKey.generate()
    _write_staged(tmp_path, _artifact_text(_digests()), private)
    assert assemble_mod.gate_staged_policy(_shard(), tmp_path) == []
    other_private = Ed25519PrivateKey.generate()
    other_public = other_private.public_key().public_bytes_raw()
    store = _trust_store(tmp_path, _OTHER_KEY_ID, other_public)
    problems = assemble_mod.gate_staged_policy(
        _shard(), tmp_path, trust_store=store
    )
    assert any("unsigned or synthetic-only" in p for p in problems)


def test_gate_trust_store_accepts_release_key(tmp_path: Path) -> None:
    """Data signed by a trusted release key passes the full gate."""
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes_raw()
    _write_staged(tmp_path, _artifact_text(_digests()), private)
    store = _trust_store(tmp_path, _KEY_ID, public)
    assert assemble_mod.gate_staged_policy(
        _shard(), tmp_path, trust_store=store
    ) == []


def test_assemble_main_fails_closed_on_checkout(tmp_path: Path) -> None:
    """Real assembly from the checkout exits 2 and writes nothing."""
    dist = tmp_path / "dist"
    work = tmp_path / "work"
    stderr = io.StringIO()
    with contextlib.redirect_stderr(stderr):
        rc = assemble_mod.main(
            [
                "--spec",
                str(_SPEC_PATH),
                "--distpath",
                str(dist),
                "--workpath",
                str(work),
                "--base",
                "testrev",
            ]
        )
    assert rc == 2
    assert not dist.exists()
    assert not work.exists()
    assert "POLICY" in stderr.getvalue()


def _write_frozen(
    root: Path, text: str, private: Ed25519PrivateKey | None
) -> Path:
    """Stage a frozen _internal payload tree; return the bundle dir."""
    bundle = root / "bundle"
    payload = bundle / "_internal" / "policy" / "data"
    payload.mkdir(parents=True, exist_ok=True)
    path = payload / "policy_terms.dat"
    data = text.encode("utf-8")
    path.write_bytes(data)
    if private is not None:
        path.with_name(path.name + ".sig").write_bytes(
            _sign(private, _KEY_ID, data)
        )
    return bundle


def test_inspect_payload_rejects_synthetic_frozen(tmp_path: Path) -> None:
    """The opt-in frozen check rejects unsigned synthetic payloads."""
    bundle = _write_frozen(tmp_path, "synthetic-test-policy-fixture\n", None)
    problems = inspect_mod.verify_policy_payload(bundle, _shard())
    assert problems


def test_inspect_payload_accepts_wellformed_frozen(tmp_path: Path) -> None:
    """The opt-in frozen check passes a well-formed signed payload."""
    private = Ed25519PrivateKey.generate()
    bundle = _write_frozen(tmp_path, _artifact_text(_digests()), private)
    assert inspect_mod.verify_policy_payload(bundle, _shard()) == []
