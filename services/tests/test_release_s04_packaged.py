"""Release regression tests for packaged-mode policy enforcement.

Packaged/production mode verifies the staged sidecar over the exact
packaged bytes against the provisioned trust store at load, locks
the development path override, and fails closed to the empty set
with no fallback to the other source. An empty set still denies
with the actionable installation/policy message.

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

from airunner_services import content_safety_gate as gate  # noqa: E402
from airunner_services.content_safety import (  # noqa: E402
    check_text,
    hash_token,
    policy_data,
)
from airunner_services.content_safety.matcher import (  # noqa: E402
    REASON_POLICY_UNAVAILABLE,
)
from airunner_services.content_safety.policy_data import (  # noqa: E402
    is_packaged_mode,
    load_policy_hashes,
)
from airunner_services.content_safety import policy_signature  # noqa: E402
from airunner_services.content_safety.policy_signature import (  # noqa: E402
    ED25519_PUBLIC_KEY_BYTES,
    SIGNATURE_FORMAT_ID,
)

_KEY_ID_A = "test-only-packaged-1"
_KEY_ID_B = "test-only-packaged-2"

_SAFE = "a calm neutral landscape"


@pytest.fixture
def work_dir() -> Iterator[Path]:
    """Create a scratch dir under the (gitignored) repo-local tmp/ tree."""
    base = _PROJECT_ROOT / "tmp" / "content_safety_tests"
    base.mkdir(parents=True, exist_ok=True)
    created = Path(tempfile.mkdtemp(prefix="s04p_", dir=base))
    yield created
    shutil.rmtree(created, ignore_errors=True)


@pytest.fixture(autouse=True)
def _clean_policy_cache(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("AIRUNNER_CONTENT_POLICY_MODE", "enforce")
    monkeypatch.delenv(policy_data.POLICY_DATA_ENV_VAR, raising=False)
    monkeypatch.delenv(
        policy_data.PACKAGED_ENFORCE_ENV_VAR, raising=False
    )
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


def _artifact(token: str) -> bytes:
    """Render a one-entry synthetic artifact for ``token``."""
    return render_artifact({hash_token(token)}).encode("utf-8")


def _enable_packaged(
    monkeypatch: pytest.MonkeyPatch,
    data: bytes | None,
    sig: bytes | None,
    store: dict[str, bytes],
) -> None:
    """Simulate packaged mode with synthetic resources and public keys."""
    monkeypatch.setenv(policy_data.PACKAGED_ENFORCE_ENV_VAR, "1")
    monkeypatch.setattr(policy_data, "_read_packaged_bytes", lambda: data)
    monkeypatch.setattr(
        policy_data, "_read_packaged_signature", lambda: sig
    )
    monkeypatch.setattr(
        policy_signature, "load_bundled_trusted_keys", lambda: store
    )


def _write_env_file(
    work_dir: Path,
    token: str,
    private: Ed25519PrivateKey,
    key_id: str,
) -> Path:
    """Write a signed dev-hook file for ``token``; return its path."""
    path = work_dir / "env-policy.dat"
    data = _artifact(token)
    path.write_bytes(data)
    Path(str(path) + ".sig").write_bytes(_sign(private, key_id, data))
    return path


def test_packaged_mode_defaults_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ordinary checkouts stay on the development path by default."""
    assert is_packaged_mode() is False
    for value in ("1", "true", "YES", " on "):
        monkeypatch.setenv(policy_data.PACKAGED_ENFORCE_ENV_VAR, value)
        assert is_packaged_mode() is True
    for value in ("0", "false", "NO", " off "):
        monkeypatch.setenv(policy_data.PACKAGED_ENFORCE_ENV_VAR, value)
        assert is_packaged_mode() is False
        monkeypatch.delenv(policy_data.PACKAGED_ENFORCE_ENV_VAR)
    assert is_packaged_mode() is False


@pytest.mark.parametrize("value", ["", "tru", "2"])
def test_invalid_signed_policy_setting_is_rejected(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv(policy_data.PACKAGED_ENFORCE_ENV_VAR, value)
    with pytest.raises(policy_data.SignedPolicyConfigurationError):
        is_packaged_mode()


def test_signed_policy_mode_is_not_automatic_for_frozen_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Packaging does not require an application policy corpus by itself."""
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    assert is_packaged_mode() is False
    monkeypatch.setenv(policy_data.PACKAGED_ENFORCE_ENV_VAR, "1")
    assert is_packaged_mode() is True


def test_packaged_mode_loads_verified_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The enforced path loads the staged set with no flag needed."""
    private, public = _keypair()
    data = _artifact("zorrb")
    _enable_packaged(
        monkeypatch, data, _sign(private, _KEY_ID_A, data),
        {_KEY_ID_A: public},
    )
    hashes = load_policy_hashes(refresh=True)
    assert hashes == frozenset({hash_token("zorrb")})
    assert policy_data.is_available() is True
    assert check_text("zorrb") is False
    assert check_text(_SAFE) is True


def test_packaged_mode_sig_tamper_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tampered staged bytes deny with the policy-unavailable reason."""
    private, public = _keypair()
    data = _artifact("zorrb")
    _enable_packaged(
        monkeypatch, data + b"\n", _sign(private, _KEY_ID_A, data),
        {_KEY_ID_A: public},
    )
    assert load_policy_hashes(refresh=True) == frozenset()
    assert policy_data.is_available() is False
    result = gate.evaluate_prompt_fields({"prompt": _SAFE})
    assert result.allowed is False
    assert result.reason == REASON_POLICY_UNAVAILABLE
    assert result.field is None
    assert gate.rejection_message(result) == gate.GENERIC_POLICY_ERROR_MESSAGE


def test_packaged_mode_ignores_env_repoint(
    work_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The dev/test hook cannot swap the enforced set in packaged mode."""
    private_a, public_a = _keypair()
    private_b, _ = _keypair()
    staged = _artifact("zorrb")
    _enable_packaged(
        monkeypatch, staged, _sign(private_a, _KEY_ID_A, staged),
        {_KEY_ID_A: public_a},
    )
    env_path = _write_env_file(work_dir, "quixnor", private_b, _KEY_ID_B)
    monkeypatch.setenv(policy_data.POLICY_DATA_ENV_VAR, str(env_path))
    hashes = load_policy_hashes(refresh=True)
    assert hashes == frozenset({hash_token("zorrb")})
    assert hash_token("quixnor") not in hashes


def test_packaged_mode_has_no_env_fallback(
    work_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A broken staged set never falls back to the dev/test hook file."""
    private_a, _ = _keypair()
    private_b, public_b = _keypair()
    staged = _artifact("zorrb")
    _enable_packaged(
        monkeypatch, staged + b"\n", _sign(private_a, _KEY_ID_A, staged),
        {_KEY_ID_B: public_b},
    )
    env_path = _write_env_file(work_dir, "quixnor", private_b, _KEY_ID_B)
    monkeypatch.setenv(policy_data.POLICY_DATA_ENV_VAR, str(env_path))
    assert load_policy_hashes(refresh=True) == frozenset()
    assert policy_data.is_available() is False


def test_packaged_mode_ignores_explicit_trust_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Packaged mode never accepts caller-supplied trust keys."""
    private_a, public_a = _keypair()
    _, public_b = _keypair()
    data = _artifact("zorrb")
    _enable_packaged(
        monkeypatch, data, _sign(private_a, _KEY_ID_A, data),
        {_KEY_ID_B: public_b},
    )

    assert load_policy_hashes(
        refresh=True, trusted_keys={_KEY_ID_A: public_a}
    ) == frozenset()
    assert policy_data.is_available() is False


def test_packaged_mode_missing_data_denies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Absent staged bytes deny with the policy-unavailable reason."""
    _, public = _keypair()
    _enable_packaged(monkeypatch, None, None, {_KEY_ID_A: public})
    assert load_policy_hashes(refresh=True) == frozenset()
    assert policy_data.is_available() is False
    result = gate.evaluate_prompt_fields({"prompt": _SAFE})
    assert result.allowed is False
    assert result.reason == REASON_POLICY_UNAVAILABLE
    assert gate.rejection_message(result) == (
        gate.GENERIC_POLICY_ERROR_MESSAGE
    )


def test_packaged_mode_empty_data_denies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verified-but-empty staged bytes still deny generation."""
    private, public = _keypair()
    _enable_packaged(
        monkeypatch, b"", _sign(private, _KEY_ID_A, b""),
        {_KEY_ID_A: public},
    )
    assert load_policy_hashes(refresh=True) == frozenset()
    assert policy_data.is_available() is False
