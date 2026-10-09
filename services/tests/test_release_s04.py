"""Release regression tests for S04 (policy signature verification).

Every token used here is synthetic and neutral. Signing keys are
throwaway Ed25519 keys generated at test time; no private key or
production data appears in this file or in any test asset.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.build_policy_terms import render_artifact  # noqa: E402

from airunner_services.content_safety import (  # noqa: E402
    check_text,
    hash_token,
    policy_data,
)
from airunner_services.content_safety.policy_data import (  # noqa: E402
    load_policy_hashes,
)
from airunner_services.content_safety.policy_signature import (  # noqa: E402
    ED25519_PUBLIC_KEY_BYTES,
    MAX_SIGNATURE_BYTES,
    SIGNATURE_FORMAT_ID,
    SIGNATURE_VERSION,
    TRUSTED_KEYS,
    PolicySignatureError,
    verify_policy_artifact,
)

_KEY_ID_A = "test-only-1"
_KEY_ID_B = "test-only-2"


@pytest.fixture
def work_dir() -> Iterator[Path]:
    """Create a scratch dir under the (gitignored) repo-local tmp/ tree."""
    base = _PROJECT_ROOT / "tmp" / "content_safety_tests"
    base.mkdir(parents=True, exist_ok=True)
    created = Path(tempfile.mkdtemp(prefix="s04_", dir=base))
    yield created
    shutil.rmtree(created, ignore_errors=True)


@pytest.fixture(autouse=True)
def _clean_policy_cache(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.delenv(policy_data.POLICY_DATA_ENV_VAR, raising=False)
    policy_data.reset_cache()
    yield
    policy_data.reset_cache()


def _keypair() -> tuple[Ed25519PrivateKey, bytes]:
    """Generate a throwaway test-only Ed25519 keypair."""
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes_raw()
    assert len(public) == ED25519_PUBLIC_KEY_BYTES
    return private, public


def _sign(private: Ed25519PrivateKey, key_id: str, data: bytes) -> bytes:
    """Render a sidecar signature file for the exact ``data`` bytes."""
    signature = private.sign(data).hex()
    text = (
        f"# format: {SIGNATURE_FORMAT_ID}\n"
        f"# key_id: {key_id}\n"
        f"# signature: {signature}\n"
    )
    return text.encode("utf-8")


def _write_signed(
    work_dir: Path, text: str, private: Ed25519PrivateKey, key_id: str
) -> Path:
    """Write artifact ``text`` plus its sidecar; return artifact path."""
    path = work_dir / "policy.dat"
    data = text.encode("utf-8")
    path.write_bytes(data)
    Path(str(path) + ".sig").write_bytes(_sign(private, key_id, data))
    return path


def _valid_text() -> str:
    return render_artifact({hash_token("zorrb"), hash_token("quixnor")})


def _verified(
    monkeypatch: pytest.MonkeyPatch,
    path: Path,
    store: dict[str, bytes],
) -> frozenset[str]:
    monkeypatch.setenv(policy_data.POLICY_DATA_ENV_VAR, str(path))
    return load_policy_hashes(
        refresh=True, verify_signature=True, trusted_keys=store
    )


def test_signed_fixture_loads_offline(
    work_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A validly signed synthetic fixture loads with no network."""
    private, public = _keypair()
    path = _write_signed(work_dir, _valid_text(), private, _KEY_ID_A)
    hashes = _verified(monkeypatch, path, {_KEY_ID_A: public})
    assert hashes == frozenset({hash_token("zorrb"), hash_token("quixnor")})
    assert check_text("zorrb") is False
    assert check_text("a totally unrelated neutral phrase") is True


def test_tampered_body_fails_verification(
    work_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A modified digest invalidates the detached signature."""
    private, public = _keypair()
    path = _write_signed(work_dir, _valid_text(), private, _KEY_ID_A)
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    for index, line in enumerate(lines):
        if line and not line.startswith("#") and line.strip():
            flipped = "0" if line[0] != "0" else "1"
            lines[index] = flipped + line[1:]
            break
    path.write_text("".join(lines), encoding="utf-8")
    with pytest.raises(PolicySignatureError):
        verify_policy_artifact(
            path.read_bytes(),
            Path(str(path) + ".sig").read_bytes(),
            trusted_keys={_KEY_ID_A: public},
        )
    assert _verified(monkeypatch, path, {_KEY_ID_A: public}) == frozenset()


def test_tampered_metadata_fails_verification(
    work_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Modified artifact metadata breaks the exact-bytes signature."""
    private, public = _keypair()
    path = _write_signed(work_dir, _valid_text(), private, _KEY_ID_A)
    text = path.read_text(encoding="utf-8").replace("# count: 2", "# count: 3")
    path.write_bytes(text.encode("utf-8"))
    with pytest.raises(PolicySignatureError):
        verify_policy_artifact(
            path.read_bytes(),
            Path(str(path) + ".sig").read_bytes(),
            trusted_keys={_KEY_ID_A: public},
        )
    assert _verified(monkeypatch, path, {_KEY_ID_A: public}) == frozenset()


def test_truncated_artifact_fails_verification(
    work_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A truncated artifact does not verify against the original."""
    private, public = _keypair()
    path = _write_signed(work_dir, _valid_text(), private, _KEY_ID_A)
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    path.write_text("".join(lines[:-1]), encoding="utf-8")
    with pytest.raises(PolicySignatureError):
        verify_policy_artifact(
            path.read_bytes(),
            Path(str(path) + ".sig").read_bytes(),
            trusted_keys={_KEY_ID_A: public},
        )
    assert _verified(monkeypatch, path, {_KEY_ID_A: public}) == frozenset()


def test_wrong_key_fails_verification(work_dir: Path) -> None:
    """Signatures from an untrusted key are rejected before parsing."""
    private_a, _ = _keypair()
    _, public_b = _keypair()
    data = _valid_text().encode("utf-8")
    unknown_id = _sign(private_a, _KEY_ID_A, data)
    with pytest.raises(PolicySignatureError):
        verify_policy_artifact(
            data, unknown_id, trusted_keys={_KEY_ID_B: public_b}
        )
    mislabeled = _sign(private_a, _KEY_ID_B, data)
    with pytest.raises(PolicySignatureError):
        verify_policy_artifact(
            data, mislabeled, trusted_keys={_KEY_ID_B: public_b}
        )


def test_missing_signature_fails_closed(
    work_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An artifact without a sidecar never loads on the verified path."""
    _, public = _keypair()
    path = work_dir / "policy.dat"
    path.write_text(_valid_text(), encoding="utf-8")
    with pytest.raises(PolicySignatureError):
        verify_policy_artifact(
            path.read_bytes(), b"", trusted_keys={_KEY_ID_A: public}
        )
    assert _verified(monkeypatch, path, {_KEY_ID_A: public}) == frozenset()


def test_signature_schema_mismatch_fails() -> None:
    """Malformed sidecars are rejected without touching the artifact."""
    assert SIGNATURE_VERSION == 1
    assert SIGNATURE_FORMAT_ID.endswith(f"/{SIGNATURE_VERSION}")
    _, public = _keypair()
    store = {_KEY_ID_A: public}
    data = _valid_text().encode("utf-8")
    private, _ = _keypair()
    valid = _sign(private, _KEY_ID_A, data).decode("utf-8")
    bad_format = valid.replace(
        f"# format: {SIGNATURE_FORMAT_ID}",
        "# format: airunner-policy-signature/99",
    )
    missing_field = "\n".join(
        line for line in valid.splitlines() if "# key_id:" not in line
    )
    bad_hex = valid.replace("# signature: ", "# signature: zz")
    cases = [
        bad_format.encode("utf-8"),
        missing_field.encode("utf-8"),
        bad_hex.encode("utf-8"),
        (valid + "not-a-comment\n").encode("utf-8"),
        (valid + "# signature: 00\n").encode("utf-8"),
        b"\xff\xfe not utf-8",
        b"x" * (MAX_SIGNATURE_BYTES + 1),
    ]
    for case in cases:
        with pytest.raises(PolicySignatureError):
            verify_policy_artifact(data, case, trusted_keys=store)


def test_bundled_trust_store_holds_public_keys_only() -> None:
    """Bundled trust entries are key IDs to 32-byte public keys."""
    assert isinstance(TRUSTED_KEYS, dict)
    for key_id, public_key in TRUSTED_KEYS.items():
        assert isinstance(key_id, str) and key_id
        assert isinstance(public_key, bytes)
        assert len(public_key) == ED25519_PUBLIC_KEY_BYTES


def test_unsigned_fixture_still_loads_unverified(
    work_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The default path keeps S03 semantics; S05 wires enforcement."""
    path = work_dir / "policy.dat"
    path.write_text(_valid_text(), encoding="utf-8")
    monkeypatch.setenv(policy_data.POLICY_DATA_ENV_VAR, str(path))
    assert load_policy_hashes(refresh=True) == frozenset(
        {hash_token("zorrb"), hash_token("quixnor")}
    )
