"""P11: dependency/model license inventory and source manifest.

Proves release-planning/linux-v1/licenses.md exists, tracks every
bootstrap model and bundle sidecar, pins the P02 constraint lock by
hash, stages the legal files, states the no-blanket-permission
guardrail, and keeps unresolved provenance as explicit PENDING or
BLOCKER rows. CPU-only; standard library plus pytest.
"""

from __future__ import annotations

from test_release_p11_support import (
    LEGAL_FILES,
    REPO_ROOT,
    bootstrap_repo_ids,
    constraint_pins,
    constraints_sha256,
    licenses_text,
    load_notice_checker,
    load_spec,
    sidecar_names,
    sidecar_pin,
    staged_legal_sources,
)

_ISSUE = "https://github.com/Capsize-Games/airunner/issues/2113"
_PARENT = "https://github.com/Capsize-Games/airunner/issues/2083"
_W01 = "https://github.com/Capsize-Games/airunnerweb/issues/216"
_W01_PR = "https://github.com/Capsize-Games/airunnerweb/pull/221"
_S07 = "https://github.com/Capsize-Games/airunner/issues/2094"

_FORBIDDEN_CLAIMS = (
    "commercial use is permitted",
    "commercial use is automatically permitted",
    "approved for commercial use",
    "all rights cleared",
    "cleared for redistribution",
)


def test_manifest_exists_and_names_issue() -> None:
    """The evidence document exists and cites P11 and its parent."""
    text = licenses_text()
    assert _ISSUE in text
    assert _PARENT in text


def test_every_bootstrap_model_has_provenance_row() -> None:
    """Each catalogued model path appears in the inventory."""
    text = licenses_text()
    repo_ids = bootstrap_repo_ids()
    assert len(repo_ids) >= 4, repo_ids
    missing = sorted(rid for rid in repo_ids if rid not in text)
    assert missing == [], missing


def test_every_bundle_sidecar_has_provenance_row() -> None:
    """Each spec sidecar binary appears in the inventory."""
    text = licenses_text()
    names = sidecar_names(load_spec())
    assert len(names) >= 2, names
    for name in names:
        assert name in text, name


def test_sidecar_pin_tracked() -> None:
    """The doc records the authoritative sidecar tag verbatim."""
    pin = sidecar_pin()
    assert f"Sidecar pin (.github/native-sidecar-version): {pin}" in (
        licenses_text()
    )


def test_constraints_lock_pinned_by_hash_and_count() -> None:
    """The doc pins the lock by sha256; any regen fails here."""
    text = licenses_text()
    pins = constraint_pins()
    assert len(pins) > 300, len(pins)
    assert all(name and version for name, version in pins)
    assert constraints_sha256() in text
    assert f"Constraint pins: {len(pins)}" in text


def test_legal_sources_present_and_staged() -> None:
    """LICENSE/NOTICE/notices exist and the spec stages them."""
    for path in LEGAL_FILES:
        assert path.is_file(), path
    license_text = LEGAL_FILES[0].read_text(encoding="utf-8")
    assert "GNU GENERAL PUBLIC LICENSE" in license_text
    assert "Version 3" in license_text
    staged = staged_legal_sources(load_spec())
    for path in LEGAL_FILES:
        entry = staged.get(path.name)
        assert entry is not None, path.name
        assert entry.get("required") is True, path.name


def test_vendored_notice_gate_still_passes() -> None:
    """The THIRD_PARTY_NOTICES check has no open problems."""
    checker = load_notice_checker()
    assert checker.run_check(repo_root=REPO_ROOT) == []


def test_guardrail_present_and_no_blanket_claim() -> None:
    """The no-permission-claim guardrail holds; no clearance text."""
    text = licenses_text()
    assert "makes no blanket permission claim" in text
    for claim in _FORBIDDEN_CLAIMS:
        assert claim not in text, claim


def test_unresolved_blockers_explicit() -> None:
    """Open provenance (W01, S07, NC model, ...) stays flagged."""
    text = licenses_text()
    for marker in (_W01, _W01_PR, _S07):
        assert marker in text, marker
    for marker in ("sai-nc-community", "MPL-2.0", "bobross.wav"):
        assert marker in text, marker
    for index in range(1, 12):
        assert f"BLOCKER B-{index}" in text, index


def test_reviewer_operator_and_checklist_fields() -> None:
    """Checklist plus reviewer/operator PENDING fields exist."""
    text = licenses_text()
    assert "## 11. Acceptance checklist" in text
    assert "- Operator name: PENDING" in text
    assert "- Reviewer name: PENDING" in text
    assert "- Reviewer acceptance: PENDING" in text
