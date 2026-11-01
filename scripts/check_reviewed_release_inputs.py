"""Fail closed while required sibling distributions await source review."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


MANIFEST = Path("release-planning/services/release-inputs.json")
CONSTRAINTS = Path("package/constraints-linux-nvidia-cu129.txt")
PACKAGE_METADATA = (Path("services/setup.py"), Path("native/setup.py"))
_REVIEWED_STATUS = "reviewed"
_APPROVED_ACTIVATION = "approved"


def _source_refs(text: str, repository: str) -> list[str]:
    """Collect checkout refs paired with one repository in workflow YAML."""
    lines = text.splitlines()
    refs: list[str] = []
    for index, line in enumerate(lines):
        if line.strip() != f"repository: {repository}":
            continue
        for candidate in lines[index + 1 :]:
            if candidate.startswith("      - "):
                break
            match = re.match(r"\s*ref:\s*([0-9a-fA-F]{5,40})\s*(?:#.*)?$", candidate)
            if match:
                refs.append(match.group(1).lower())
                break
    return refs


def _has_constraint(text: str, package: str, version: str) -> bool:
    pattern = rf"(?m)^{re.escape(package)}=={re.escape(version)}(?:\s|\\|$)"
    return re.search(pattern, text) is not None


def _has_requirement(text: str, package: str, requirement: str) -> bool:
    pattern = rf"{re.escape(package)}{re.escape(requirement)}(?:[\"' ,\]])"
    return re.search(pattern, text) is not None


def inspect_release_inputs(root: Path, workflow: Path) -> list[str]:
    """Return pin/provenance errors and pending review gates."""
    errors: list[str] = []
    manifest_path = root / MANIFEST
    try:
        manifest: dict[str, Any] = json.loads(
            manifest_path.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot read release input manifest: {exc}"]

    if manifest.get("schema_version") != 1:
        errors.append("unsupported release input manifest schema")
    inputs = manifest.get("inputs")
    if not isinstance(inputs, list) or not inputs:
        return errors + ["release input manifest has no inputs"]

    try:
        if not (root / workflow).is_file():
            return errors + [f"workflow does not exist: {workflow}"]
        constraints_text = (root / CONSTRAINTS).read_text(encoding="utf-8")
        package_text = {
            path: (root / path).read_text(encoding="utf-8")
            for path in PACKAGE_METADATA
        }
    except OSError as exc:
        return errors + [f"cannot read release pin source: {exc}"]

    pending: list[str] = []
    workflow_dir = root / ".github/workflows"
    workflow_files = sorted(
        path
        for suffix in ("*.yml", "*.yaml")
        for path in workflow_dir.glob(suffix)
    )
    seen_distributions: set[str] = set()
    for item in inputs:
        if not isinstance(item, dict):
            errors.append("release input entry must be an object")
            continue
        distribution = item.get("distribution")
        repository = item.get("repository")
        revision = item.get("revision")
        version = item.get("version")
        requirement = item.get("requirement")
        if not all(isinstance(value, str) and value for value in (
            distribution, repository, revision, version, requirement
        )):
            errors.append("release input entry is missing its identity or pin")
            continue
        if distribution in seen_distributions:
            errors.append(f"duplicate release input: {distribution}")
            continue
        seen_distributions.add(distribution)
        if not re.fullmatch(r"[0-9a-fA-F]{5,40}", revision):
            errors.append(f"{distribution}: invalid source revision format")
        expected_source_refs = item.get("workflow_source_refs", {})
        if not isinstance(expected_source_refs, dict):
            errors.append(
                f"{distribution}: workflow_source_refs must be an object"
            )
            expected_source_refs = {}
        for source_path in workflow_files:
            source_workflow = source_path.relative_to(root).as_posix()
            refs = _source_refs(
                source_path.read_text(encoding="utf-8"), repository
            )
            expected_count = expected_source_refs.get(source_workflow)
            if refs and expected_count is None:
                errors.append(
                    f"{distribution}: unregistered sibling source checkout in "
                    f"{source_workflow}"
                )
            elif expected_count is not None and (
                len(refs) != expected_count
                or any(ref != revision.lower() for ref in refs)
            ):
                errors.append(
                    f"{distribution}: workflow source refs do not match "
                    f"manifest revision {revision} ({source_workflow}: "
                    f"found {len(refs)}, expected {expected_count})"
                )
        for source_workflow, expected_count in expected_source_refs.items():
            if not (root / source_workflow).is_file():
                errors.append(
                    f"{distribution}: manifest source workflow is missing: "
                    f"{source_workflow}"
                )

        if not _has_constraint(constraints_text, distribution, version):
            errors.append(
                f"{distribution}: constraints do not pin exactly {version}"
            )
        requirement_matches = [
            path for path, text in package_text.items()
            if _has_requirement(text, distribution, requirement)
        ]
        # The vendor is an optional service extra, while common/shield are
        # runtime requirements in both shipped Python distributions.
        required_metadata_files = (
            (Path("services/setup.py"),)
            if distribution == "airunner-tts-vendor"
            else PACKAGE_METADATA
        )
        missing_metadata = [
            path for path in required_metadata_files
            if path not in requirement_matches
        ]
        if missing_metadata:
            errors.append(
                f"{distribution}: package requirement pin missing/mismatched "
                f"in {', '.join(map(str, missing_metadata))}"
            )

        if (
            item.get("status") != _REVIEWED_STATUS
            or item.get("activation") != _APPROVED_ACTIVATION
        ):
            pending.append(distribution)
        else:
            review_record = item.get("review_record")
            if (
                not isinstance(review_record, str)
                or not review_record
                or not (root / review_record).is_file()
            ):
                errors.append(
                    f"{distribution}: reviewed input requires a repository "
                    "review_record file"
                )

    if pending:
        errors.append(
            "pending-source-review: quarantined release inputs: "
            + ", ".join(sorted(pending))
        )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument("--workflow", type=Path, required=True)
    args = parser.parse_args()
    errors = inspect_release_inputs(args.root, args.workflow)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("Release input review and pin checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
