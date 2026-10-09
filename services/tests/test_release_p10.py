"""P10: opt-in update check with verified install handoff.

Wrong signatures/digests and incomplete downloads cannot reach P07;
network failure/cancel leaves the install usable. Synthetic fixtures
only, except one end-to-end test on the real ``upgrade.sh``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from airunner_services.downloads.update_check import (
    UpdateAvailable,
    UpdateCancelled,
    UpdateNetworkError,
    UpdateOffline,
    UpdateOptInRequired,
    download_update,
)
from airunner_services.downloads.update_install import (
    UpdateInstallError,
    install_verified_update,
)
from airunner_services.downloads.update_manifest import (
    UpdateManifestError,
    verify_manifest,
)
from test_release_p07_support import _data_db
from test_release_p07_support import _rows
from test_release_p07_upgrade import _bundle
from test_release_p07_upgrade import _installed
from test_release_p10_support import (
    ARTIFACT_NAME,
    CURRENT_VERSION,
    NEXT_VERSION,
    FakeTransport,
    _check,
    cancel_after,
    corrupted_case,
    fresh_keys,
    make_case,
    make_tarball,
    mutated_manifests,
    recording_installer,
    tampered_manifest,
)


@pytest.fixture(autouse=True)
def _online(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AIRUNNER_OFFLINE_MODE", "0")


def _current(prefix: Path) -> str:
    return (prefix / "versions" / "current").resolve().name


def test_check_requires_explicit_opt_in() -> None:
    """Without opt-in the transport is never contacted."""
    case = make_case()
    transport = FakeTransport(case)
    with pytest.raises(UpdateOptInRequired):
        _check(case, transport, opt_in=False)
    assert transport.log == []


def test_check_refused_while_offline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Offline mode (the default) denies the check before any fetch."""
    case = make_case()
    for value in ("1", None):
        if value is None:
            monkeypatch.delenv("AIRUNNER_OFFLINE_MODE")
        else:
            monkeypatch.setenv("AIRUNNER_OFFLINE_MODE", value)
        transport = FakeTransport(case)
        with pytest.raises(UpdateOffline):
            _check(case, transport)
        assert transport.log == []


def test_check_offer_tracks_current_version() -> None:
    """Current yields None; a newer version yields an offer."""
    assert _check(make_case(version=CURRENT_VERSION))[0] is None
    offer, transport = _check(make_case())
    assert isinstance(offer, UpdateAvailable)
    assert offer.version == NEXT_VERSION
    assert transport.log == ["manifest"]


def test_tampered_manifest_rejected() -> None:
    """One flipped manifest byte fails the exact-bytes signature."""
    bad = tampered_manifest(make_case())
    with pytest.raises(UpdateManifestError):
        verify_manifest(bad.manifest, bad.signature, trusted_keys=bad.store)
    with pytest.raises(UpdateManifestError):
        _check(bad)


def test_wrong_key_rejected() -> None:
    """Signatures from an untrusted key fail before any download."""
    case = make_case()
    _, other_store = fresh_keys()
    transport = FakeTransport(case)
    with pytest.raises(UpdateManifestError):
        _check(case, transport, store=other_store)
    assert transport.log == ["manifest"]


def test_schema_mismatch_rejected() -> None:
    """Bad format/version/artifacts fail despite a valid signature."""
    for raw, sig, store in mutated_manifests():
        with pytest.raises(UpdateManifestError):
            verify_manifest(raw, sig, trusted_keys=store)


def test_download_verifies_and_stages(tmp_path: Path) -> None:
    """A valid stream lands as a verified, installable artifact."""
    case = make_case()
    offer, _ = _check(case)
    assert offer is not None
    verified = download_update(offer, tmp_path / "staging")
    assert verified.version == NEXT_VERSION
    assert verified.path.read_bytes() == case.artifact


@pytest.mark.parametrize("corrupt", ["digest", "truncate"])
def test_corrupt_artifact_cannot_activate(
    tmp_path: Path, corrupt: str
) -> None:
    """Corrupt bytes fail; nothing installable remains."""
    case = make_case()
    bad = corrupted_case(case, corrupt)
    match = "digest" if corrupt == "digest" else "size"
    offer, _ = _check(bad)
    assert offer is not None
    with pytest.raises(UpdateManifestError, match=match):
        download_update(offer, tmp_path / "staging")
    assert list((tmp_path / "staging").iterdir()) == []


def test_manifest_failure_offers_nothing() -> None:
    """A failed manifest fetch offers nothing and stages nothing."""
    case = make_case()
    transport = FakeTransport(
        case, fail_manifest=UpdateNetworkError("synthetic outage")
    )
    with pytest.raises(UpdateNetworkError):
        _check(case, transport)
    assert transport.log == ["manifest"]


@pytest.mark.parametrize("interrupt", ["failure", "cancel"])
def test_interrupted_download_leaves_install_usable(
    tmp_path: Path, interrupt: str
) -> None:
    """Failure or cancellation keeps the current version usable."""
    prefix = _installed(tmp_path / "prefix", CURRENT_VERSION)
    case = make_case()
    fail_after = 1 if interrupt == "failure" else None
    transport = FakeTransport(case, fail_after=fail_after)
    offer, _ = _check(case, transport)
    assert offer is not None
    cancel = cancel_after(1) if interrupt == "cancel" else None
    with pytest.raises((UpdateNetworkError, UpdateCancelled)):
        download_update(offer, tmp_path / "staging", cancel=cancel)
    assert _current(prefix) == CURRENT_VERSION
    assert list((tmp_path / "staging").iterdir()) == []


def test_staged_swap_cannot_activate(tmp_path: Path) -> None:
    """Bytes swapped after download fail the install-time re-check."""
    offer, _ = _check(make_case())
    assert offer is not None
    verified = download_update(offer, tmp_path / "staging")
    swapped = bytearray(verified.path.read_bytes())
    swapped[0] ^= 0x01
    verified.path.write_bytes(bytes(swapped))
    install, calls = recording_installer()
    with pytest.raises(UpdateManifestError, match="digest"):
        install_verified_update(
            verified, prefix=tmp_path / "prefix", installer=install
        )
    assert calls == []


@pytest.mark.parametrize("artifact", ["plain", "tarball"])
def test_install_failure_reports_cleanly(
    tmp_path: Path, artifact: str
) -> None:
    """Bad bundles and failing installers raise; cause preserved."""
    src = _bundle(tmp_path / "bundle-src", NEXT_VERSION)
    good = make_tarball(src, tmp_path / ARTIFACT_NAME).read_bytes()
    data = good if artifact == "tarball" else make_case().artifact
    offer, _ = _check(make_case(artifact=data))
    assert offer is not None
    verified = download_update(offer, tmp_path / "staging")

    def boom(bundle: Path, prefix: Path) -> None:
        raise RuntimeError("synthetic installer crash")

    match = "synthetic" if artifact == "tarball" else "extraction"
    with pytest.raises(UpdateInstallError, match=match):
        install_verified_update(
            verified, prefix=tmp_path / "prefix", installer=boom
        )


def test_verified_handoff_activates_via_upgrade(
    tmp_path: Path,
) -> None:
    """The verified bundle activates through real P07 upgrade.sh."""
    prefix = _installed(tmp_path / "prefix", CURRENT_VERSION)
    db = prefix / "data" / "airunner.db"
    _data_db(db)
    src = _bundle(tmp_path / "bundle-src", NEXT_VERSION)
    tarball = make_tarball(src, tmp_path / ARTIFACT_NAME)
    offer, _ = _check(make_case(artifact=tarball.read_bytes()))
    assert offer is not None
    verified = download_update(offer, tmp_path / "staging")
    bundle = install_verified_update(verified, prefix=prefix)
    assert bundle.is_dir()
    assert _current(prefix) == NEXT_VERSION
    assert (prefix / "versions" / CURRENT_VERSION).is_dir()
    assert _rows(db, "conversations") == 1
    state = json.loads((prefix / "upgrade-state.json").read_text())
    assert (state["status"], state["previous"]) == ("ok", CURRENT_VERSION)
