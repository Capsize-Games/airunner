"""The CORE candidate lock stays non-activatable while source review is pending."""

from __future__ import annotations

import json
import hashlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import check_core_input_readiness as readiness  # noqa: E402


def _make_complete_review_fixture(tmp_path: Path, *, flagged_builder: bool) -> Path:
    """Create a synthetic complete inventory to exercise readiness policy states."""
    manifest = json.loads(
        (ROOT / "package/core-input-readiness.json").read_text(encoding="utf-8")
    )
    inventory_path = manifest["dependency_review"]["path"]
    inventory = json.loads((ROOT / inventory_path).read_text(encoding="utf-8"))
    evidence_path = "release-planning/services/input-reviews/core-linux-reviewed-inputs.md"
    evidence = ROOT / evidence_path
    evidence_digest = hashlib.sha256(evidence.read_bytes()).hexdigest()
    for package in inventory["packages"]:
        package["source_review_status"] = "reviewed"
        package["review_evidence"] = {
            "record": evidence_path,
            "scope_id": "synthetic-test-fixture-only",
            "sha256": evidence_digest,
        }
        if package["origin_policy_status"] in {
            "pending-review",
            "pending-owner-exception",
            "owner-exception-recorded",
        }:
            package["origin_policy_status"] = "reviewed-no-flag"
    if flagged_builder:
        for package in inventory["packages"]:
            if package["name"] == "pyinstaller":
                package["origin_policy_status"] = "pending-owner-exception"

    inventory["source_reviewed_count"] = len(inventory["packages"])
    inventory["source_pending_count"] = 0
    inventory["origin_ready_count"] = sum(
        package["origin_policy_status"]
        in {"owner-controlled", "owner-exception-recorded", "reviewed-no-flag"}
        for package in inventory["packages"]
    )
    inventory["origin_pending_review_count"] = sum(
        package["origin_policy_status"] == "pending-review"
        for package in inventory["packages"]
    )
    inventory["origin_pending_exception_count"] = sum(
        package["origin_policy_status"] == "pending-owner-exception"
        for package in inventory["packages"]
    )
    inventory["next_source_intakes"] = []
    inventory["next_origin_reviews"] = [
        package["name"]
        for package in inventory["packages"]
        if package["origin_policy_status"] == "pending-review"
    ]
    inventory["status"] = (
        "complete"
        if inventory["source_pending_count"] == 0
        and inventory["origin_pending_review_count"] == 0
        and inventory["origin_pending_exception_count"] == 0
        else "incomplete"
    )
    inventory_bytes = (json.dumps(inventory, indent=2, sort_keys=True) + "\n").encode()
    manifest["dependency_review"].update(
        {
            "sha256": hashlib.sha256(inventory_bytes).hexdigest(),
            "status": inventory["status"],
            "source_reviewed_count": inventory["source_reviewed_count"],
            "source_pending_count": inventory["source_pending_count"],
            "origin_ready_count": inventory["origin_ready_count"],
            "origin_pending_review_count": inventory["origin_pending_review_count"],
            "origin_pending_exception_count": inventory[
                "origin_pending_exception_count"
            ],
        }
    )
    origin_by_name = {
        package["name"]: package["origin_policy_status"]
        for package in inventory["packages"]
    }
    for builder in manifest["builder_inputs"]:
        builder["source_policy_status"] = origin_by_name[builder["name"]]
    blockers = ["builder-origin-exception-pending"] if flagged_builder else []
    manifest["blockers"] = blockers
    manifest["readiness_status"] = "pending-review" if blockers else "ready"
    manifest["activation_allowed"] = not blockers

    for key in ("requirements", "lock"):
        source = ROOT / manifest[key]["path"]
        target = tmp_path / manifest[key]["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
    inventory_target = tmp_path / inventory_path
    inventory_target.parent.mkdir(parents=True, exist_ok=True)
    inventory_target.write_bytes(inventory_bytes)
    freeze_record = ROOT / manifest["builder_inputs"][0]["review_record"]
    freeze_target = tmp_path / manifest["builder_inputs"][0]["review_record"]
    freeze_target.parent.mkdir(parents=True, exist_ok=True)
    freeze_target.write_bytes(freeze_record.read_bytes())
    evidence_target = tmp_path / evidence_path
    evidence_target.parent.mkdir(parents=True, exist_ok=True)
    evidence_target.write_bytes(evidence.read_bytes())
    manifest_target = tmp_path / "package/core-input-readiness.json"
    manifest_target.parent.mkdir(parents=True, exist_ok=True)
    manifest_target.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_target


def test_candidate_record_matches_the_51_package_lock() -> None:
    result = readiness.check_readiness(
        ROOT, Path("package/core-input-readiness.json")
    )

    assert result["distribution_count"] == 51
    assert result["status"] == "pending-review"
    assert result["activation_allowed"] is False
    assert result["blockers"] == [
        "dependency-source-review-pending",
        "dependency-origin-review-pending",
        "builder-origin-exception-pending",
    ]
    assert result["dependency_review"] == {
        "status": "incomplete",
        "source_reviewed_count": 7,
        "source_pending_count": 44,
        "origin_ready_count": 2,
        "origin_pending_review_count": 47,
        "origin_pending_exception_count": 2,
    }


def test_activation_mode_fails_before_builder_install_or_freeze(capsys) -> None:
    code = readiness.main(
        [
            "--root",
            str(ROOT),
            "--manifest",
            "package/core-input-readiness.json",
            "--mode",
            "activate",
        ]
    )

    assert code == 2
    assert "exact dependency source/origin review is incomplete" in capsys.readouterr().err


def test_lock_digest_mismatch_is_rejected(tmp_path: Path) -> None:
    manifest = json.loads(
        (ROOT / "package/core-input-readiness.json").read_text(encoding="utf-8")
    )
    requirements = ROOT / manifest["requirements"]["path"]
    lock = ROOT / manifest["lock"]["path"]
    (tmp_path / "package").mkdir()
    (tmp_path / manifest["requirements"]["path"]).write_bytes(
        requirements.read_bytes()
    )
    (tmp_path / manifest["lock"]["path"]).write_bytes(lock.read_bytes() + b"# changed\n")
    (tmp_path / "package/core-input-readiness.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )

    with pytest.raises(readiness.ReadinessError, match="lock digest mismatch"):
        readiness.check_readiness(tmp_path, Path("package/core-input-readiness.json"))


def test_builder_exceptions_cannot_activate_an_unreviewed_graph(tmp_path: Path) -> None:
    manifest = json.loads(
        (ROOT / "package/core-input-readiness.json").read_text(encoding="utf-8")
    )
    inventory_path = manifest["dependency_review"]["path"]
    inventory = json.loads((ROOT / inventory_path).read_text(encoding="utf-8"))
    for package in inventory["packages"]:
        if package["name"] in {"pyinstaller", "pyinstaller-hooks-contrib"}:
            package["origin_policy_status"] = "owner-exception-recorded"
    inventory["origin_ready_count"] = 4
    inventory["origin_pending_exception_count"] = 0
    inventory_bytes = (json.dumps(inventory, indent=2, sort_keys=True) + "\n").encode()
    digest = hashlib.sha256(inventory_bytes).hexdigest()
    manifest["dependency_review"]["sha256"] = digest
    manifest["dependency_review"]["origin_ready_count"] = 4
    manifest["dependency_review"]["origin_pending_exception_count"] = 0
    for builder in manifest["builder_inputs"]:
        builder["source_policy_status"] = "owner-exception-recorded"
    manifest["readiness_status"] = "ready"
    manifest["activation_allowed"] = True
    manifest["blockers"] = []

    (tmp_path / "package").mkdir()
    for key in ("requirements", "lock"):
        source = ROOT / manifest[key]["path"]
        target = tmp_path / manifest[key]["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
    inventory_target = tmp_path / inventory_path
    inventory_target.parent.mkdir(parents=True, exist_ok=True)
    inventory_target.write_bytes(inventory_bytes)
    review_record = ROOT / manifest["builder_inputs"][0]["review_record"]
    review_copy = tmp_path / manifest["builder_inputs"][0]["review_record"]
    review_copy.parent.mkdir(parents=True, exist_ok=True)
    review_copy.write_bytes(review_record.read_bytes())
    evidence_path = "release-planning/services/input-reviews/core-linux-reviewed-inputs.md"
    evidence_copy_path = ROOT / evidence_path
    evidence_copy = tmp_path / evidence_path
    evidence_copy.parent.mkdir(parents=True, exist_ok=True)
    evidence_copy.write_bytes(evidence_copy_path.read_bytes())
    (tmp_path / "package/core-input-readiness.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )

    with pytest.raises(readiness.ReadinessError, match="blockers disagree"):
        readiness.check_readiness(tmp_path, Path("package/core-input-readiness.json"))


def test_reviewed_unflagged_graph_needs_no_owner_exceptions(tmp_path: Path) -> None:
    manifest_path = _make_complete_review_fixture(tmp_path, flagged_builder=False)

    result = readiness.check_readiness(tmp_path, manifest_path.relative_to(tmp_path))

    assert result["status"] == "ready"
    assert result["activation_allowed"] is True
    assert result["blockers"] == []
    assert result["dependency_review"]["source_pending_count"] == 0
    assert result["dependency_review"]["origin_pending_review_count"] == 0
    assert result["dependency_review"]["origin_pending_exception_count"] == 0


def test_flagged_builder_stays_blocked_after_other_reviews_complete(tmp_path: Path) -> None:
    manifest_path = _make_complete_review_fixture(tmp_path, flagged_builder=True)

    result = readiness.check_readiness(tmp_path, manifest_path.relative_to(tmp_path))

    assert result["status"] == "pending-review"
    assert result["activation_allowed"] is False
    assert result["blockers"] == ["builder-origin-exception-pending"]


def test_ci_preflight_precedes_each_pyinstaller_install_path() -> None:
    dispatch = (ROOT / ".github/workflows/pypi-dispatch.yml").read_text(
        encoding="utf-8"
    )
    evaluation = (ROOT / ".github/workflows/eval-tests.yml").read_text(
        encoding="utf-8"
    )

    candidate_check = dispatch.index(
        "Check CORE builder input readiness before installs"
    )
    candidate_install = dispatch.index("name: Install dependencies", candidate_check)
    assert candidate_check < candidate_install
    debian_check = dispatch.index(
        "Check CORE builder input readiness before installs", candidate_install
    )
    debian_install = dispatch.index("name: Install CORE freeze inputs", debian_check)
    assert debian_check < debian_install
    eval_check = evaluation.index("Check CORE builder input readiness before installs")
    eval_install = evaluation.index("name: Install Python dependencies", eval_check)
    assert eval_check < eval_install
