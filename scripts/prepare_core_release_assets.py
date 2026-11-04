"""Prepare the exact, tested CORE Debian assets for immutable release promotion."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import tarfile
from pathlib import Path

from core_upgrade_receipt import (
    CoreUpgradeReceiptError,
    validate_interrupted_upgrade_receipt,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(
    *, artifact_dir: Path, notices_dir: Path, output_dir: Path,
    source_sha: str, tag: str, workflow_run_id: int, workflow: str,
    candidate_run_id: int, candidate_attempt: int, candidate_run_receipt: Path,
) -> None:
    """Validate one prior candidate run and assemble immutable release assets."""
    _require_tag_identity(source_sha, tag)
    candidate, clean, upgrade = _read_candidate_records(artifact_dir)
    deb = _resolve_candidate_deb(artifact_dir, candidate)
    _require_acceptance(candidate, clean, upgrade, deb=deb, source_sha=source_sha)
    _require_candidate_run(
        candidate_run_receipt, run_id=candidate_run_id,
        attempt=candidate_attempt, source_sha=source_sha, tag=tag,
    )
    output_dir.mkdir(parents=True, exist_ok=False)
    staged = _stage_release_inputs(
        artifact_dir=artifact_dir, notices_dir=notices_dir,
        candidate_run_receipt=candidate_run_receipt, package=deb,
        output_dir=output_dir,
    )
    manifest = _build_release_manifest(
        candidate=candidate, clean=clean, upgrade=upgrade,
        source_sha=source_sha, tag=tag, workflow=workflow,
        promotion_run_id=workflow_run_id, candidate_run_id=candidate_run_id,
        candidate_attempt=candidate_attempt, staged=staged,
    )
    (output_dir / "airunner-core-release.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    _write_checksums(output_dir)


def validate_candidate_acceptance(artifact_dir: Path, source_sha: str) -> None:
    """Validate one candidate's exact package, clean-install and upgrade receipts."""
    candidate, clean, upgrade = _read_candidate_records(artifact_dir)
    deb = _resolve_candidate_deb(artifact_dir, candidate)
    _require_acceptance(candidate, clean, upgrade, deb=deb, source_sha=source_sha)


def _require_tag_identity(source_sha: str, tag: str) -> None:
    """Require a lowercase commit SHA and current service-version tag."""
    if not re.fullmatch(r"[0-9a-f]{40}", source_sha) or tag != f"v{_service_version(Path.cwd())}":
        raise ValueError("CORE release requires the exact annotated service version tag/source")


def _read_candidate_records(artifact_dir: Path) -> tuple[dict, dict, dict]:
    """Load candidate, clean-install and upgrade JSON records."""
    paths = (
        artifact_dir / "candidate.json",
        artifact_dir / "candidate-validation.json",
        artifact_dir / "candidate-upgrade-validation.json",
    )
    records = tuple(json.loads(path.read_text(encoding="utf-8")) for path in paths)
    if not all(isinstance(record, dict) for record in records):
        raise ValueError("CORE candidate validation records are invalid")
    return records


def _resolve_candidate_deb(artifact_dir: Path, candidate: dict) -> Path:
    """Resolve the regular amd64 package named by the candidate manifest."""
    name = candidate.get("debian_filename")
    if (
        not isinstance(name, str)
        or Path(name).name != name
        or not re.fullmatch(r"airunner_[0-9][A-Za-z0-9.+~:-]*_amd64\.deb", name)
    ):
        raise ValueError("CORE candidate package filename is invalid")
    package = artifact_dir / name
    if package.is_symlink() or not package.is_file():
        raise ValueError("CORE candidate package is missing or unsafe")
    return package


def _require_acceptance(
    candidate: dict, clean: dict, upgrade: dict, *, deb: Path, source_sha: str
) -> None:
    """Require exact package/source binding and successful acceptance statuses."""
    checks = (
        candidate.get("profile") == "linux-services-core",
        candidate.get("source_sha") == source_sha,
        candidate.get("build_status") == "passed",
        candidate.get("debian_sha256") == _sha(deb),
        candidate.get("requirements_sha256") == _sha(Path("package/requirements-linux-core.in")),
        candidate.get("lock_sha256") == _sha(Path("package/constraints-linux-core.txt")),
        clean.get("source_sha") == source_sha,
        clean.get("debian_sha256") == _sha(deb),
        clean.get("clean_install_smoke") == "passed",
        upgrade.get("source_sha") == source_sha,
        upgrade.get("debian_sha256") == _sha(deb),
        upgrade.get("upgrade_smoke") == "passed",
    )
    if not all(checks):
        raise ValueError("CORE build, clean-install, or upgrade evidence is incomplete")
    try:
        validate_interrupted_upgrade_receipt(
            upgrade, source_sha=source_sha, deb_sha256=_sha(deb)
        )
    except CoreUpgradeReceiptError as exc:
        raise ValueError("CORE interrupted-upgrade recovery evidence is incomplete") from exc


def _require_candidate_run(
    path: Path, *, run_id: int, attempt: int, source_sha: str, tag: str
) -> None:
    """Require the previous candidate workflow receipt to bind this release."""
    proof = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(proof, dict):
        raise ValueError("candidate run receipt is invalid")
    if (
        proof.get("run_id") != run_id
        or proof.get("run_attempt") != attempt
        or proof.get("source_sha") != source_sha
        or proof.get("tag") != tag
        or proof.get("run_conclusion") != "success"
    ):
        raise ValueError("candidate run receipt does not bind the requested source/tag")


def _stage_release_inputs(
    *, artifact_dir: Path, notices_dir: Path, candidate_run_receipt: Path,
    package: Path, output_dir: Path,
) -> dict[str, Path]:
    """Copy exact tested receipts and package, plus package notices archive."""
    staged = {
        "package": output_dir / package.name,
        "run": output_dir / "airunner-core-candidate-run.json",
        "clean": output_dir / "airunner-core-clean-install-validation.json",
        "upgrade": output_dir / "airunner-core-upgrade-validation.json",
        "notices": output_dir / "airunner-core-notices.tar.gz",
    }
    staged["package"].write_bytes(package.read_bytes())
    staged["run"].write_bytes(candidate_run_receipt.read_bytes())
    staged["clean"].write_bytes((artifact_dir / "candidate-validation.json").read_bytes())
    staged["upgrade"].write_bytes((artifact_dir / "candidate-upgrade-validation.json").read_bytes())
    _archive_notices(notices_dir, staged["notices"])
    return staged


def _archive_notices(notices_dir: Path, output_path: Path) -> None:
    """Write a deterministic archive from the package's legal-notices tree."""
    notice_root = notices_dir.resolve(strict=True)
    notice_files = [path for path in notice_root.rglob("*") if path.is_file()]
    if not notice_files or any(path.is_symlink() for path in notice_root.rglob("*")):
        raise ValueError("CORE package notices are missing or contain a symlink")
    with output_path.open("wb") as destination, gzip.GzipFile(
        filename="", fileobj=destination, mode="wb", mtime=0
    ) as compressed, tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as archive:
        for path in sorted(notice_files):
            relative = path.relative_to(notice_root)
            info = archive.gettarinfo(str(path), arcname=f"legal/{relative.as_posix()}")
            info.uid = info.gid = 0
            info.uname = info.gname = "root"
            info.mtime = 0
            with path.open("rb") as stream:
                archive.addfile(info, stream)


def _build_release_manifest(
    *, candidate: dict, clean: dict, upgrade: dict, source_sha: str, tag: str,
    workflow: str, promotion_run_id: int, candidate_run_id: int,
    candidate_attempt: int, staged: dict[str, Path],
) -> dict:
    """Bind release bytes and validation records to both workflow runs."""
    return {
        "schema_version": 1,
        "profile": "linux-services-core",
        "tag": tag,
        "source_sha": source_sha,
        "workflow": workflow,
        "promotion_workflow_run_id": promotion_run_id,
        "candidate_workflow_run_id": candidate_run_id,
        "candidate_run_attempt": candidate_attempt,
        "debian_filename": staged["package"].name,
        "debian_sha256": _sha(staged["package"]),
        "debian_version": candidate["debian_version"],
        "architecture": "amd64",
        "requirements_sha256": candidate["requirements_sha256"],
        "lock_sha256": candidate["lock_sha256"],
        "build_status": candidate["build_status"],
        "clean_install_smoke": clean["clean_install_smoke"],
        "upgrade_smoke": upgrade["upgrade_smoke"],
        "upgrade_validation_sha256": _sha(staged["upgrade"]),
        "clean_install_validation_sha256": _sha(staged["clean"]),
        "notices_path": "/usr/lib/airunner/legal",
        "notices_sha256": _sha(staged["notices"]),
        "candidate_run_receipt_sha256": _sha(staged["run"]),
        "scope": "frozen services CORE package; no model weights or full-ML inference runtime",
    }


def _write_checksums(output_dir: Path) -> None:
    """Write a sorted checksum entry for every staged asset."""
    checksum_paths = sorted(path for path in output_dir.iterdir() if path.is_file())
    (output_dir / "SHA256SUMS").write_text(
        "".join(f"{_sha(path)}  {path.name}\n" for path in checksum_paths),
        encoding="ascii",
    )


def _service_version(root: Path) -> str:
    match = re.search(
        r'^_RELEASE_VERSION\s*=\s*"([^"]+)"$',
        (root / "services/setup.py").read_text(encoding="utf-8"), re.MULTILINE,
    )
    if match is None:
        raise ValueError("services version is not a literal")
    return match.group(1)


def main() -> int:
    """Build the CORE release asset set from verified candidate inputs."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--notices-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--workflow-run-id", type=int, required=True)
    parser.add_argument("--candidate-run-id", type=int, required=True)
    parser.add_argument("--candidate-attempt", type=int, required=True)
    parser.add_argument("--candidate-run-receipt", type=Path, required=True)
    parser.add_argument("--workflow", required=True)
    args = parser.parse_args()
    prepare(
        artifact_dir=args.artifact_dir, notices_dir=args.notices_dir,
        output_dir=args.output_dir, source_sha=args.source_sha, tag=args.tag,
        workflow_run_id=args.workflow_run_id, workflow=args.workflow,
        candidate_run_id=args.candidate_run_id,
        candidate_attempt=args.candidate_attempt,
        candidate_run_receipt=args.candidate_run_receipt,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
