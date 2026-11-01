"""Fail closed while required sibling distributions await source review."""

from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path
from typing import Any
import tomllib


MANIFEST = Path("release-planning/services/release-inputs.json")
HISTORICAL_CONSTRAINTS = Path(
    "package/constraints-linux-nvidia-cu129-historical-desktop.txt"
)
PACKAGE_METADATA = (Path("services/setup.py"), Path("native/setup.py"))
_REVIEWED_STATUS = "reviewed"
_APPROVED_ACTIVATION = "approved"
EXPECTED_INPUTS = {
    "airunner-common": "Capsize-Games/airunner-common",
    "facehuggershield": "Capsize-Games/facehuggershield",
    "airunner-tts-vendor": "Capsize-Games/airunner-tts-vendor",
}
EXPECTED_PROFILE_EXTRAS = (
    "llm-native",
    "stt-native",
    "art-python",
    "tts-python-core",
    "llm_weather",
    "search",
    "nvidia",
    "linux",
)
EXPECTED_PROFILE_EXCLUDES = (
    "airunner-tts-vendor",
    "facehuggershield",
)
_VENDOR_DISTRIBUTION = "airunner-tts-vendor"


def _source_refs(text: str, repository: str) -> list[str | None]:
    """Collect raw checkout refs, preserving absent and mutable ref values."""
    lines = text.splitlines()
    refs: list[str | None] = []
    for index, line in enumerate(lines):
        repository_match = re.fullmatch(
            rf"\s*repository:\s*(['\"]?){re.escape(repository)}\1\s*(?:#.*)?",
            line,
        )
        if not repository_match:
            continue

        step_end = index + 1
        while step_end < len(lines) and not re.match(
            r"^\s{6}-\s", lines[step_end]
        ):
            step_end += 1
        ref: str | None = None
        for candidate in lines[index + 1 : step_end]:
            match = re.fullmatch(
                r"\s*ref:\s*(.*?)\s*(?:#.*)?", candidate
            )
            if match:
                raw_ref = match.group(1).strip()
                if len(raw_ref) >= 2 and raw_ref[0] == raw_ref[-1] and raw_ref[0] in "'\"":
                    raw_ref = raw_ref[1:-1]
                ref = raw_ref.lower()
                break
        refs.append(ref)
    return refs


def _has_constraint(text: str, package: str, version: str) -> bool:
    pattern = rf"(?m)^{re.escape(package)}=={re.escape(version)}(?:\s|\\|$)"
    return re.search(pattern, text) is not None


def _has_requirement(text: str, package: str, requirement: str) -> bool:
    pattern = rf"{re.escape(package)}{re.escape(requirement)}(?:[\"' ,\]])"
    return re.search(pattern, text) is not None


def _assignment_values(tree: ast.Module) -> dict[str, ast.expr]:
    """Index top-level assignment expressions without executing setup.py."""
    values: dict[str, ast.expr] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    values[target.id] = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            values[node.target.id] = node.value
    return values


def _returned_dict(tree: ast.Module, name: str) -> dict[str, ast.expr] | None:
    """Read a function's literal returned mapping from its AST."""
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name != name:
            continue
        for child in ast.walk(node):
            if isinstance(child, ast.Return) and isinstance(child.value, ast.Dict):
                result: dict[str, ast.expr] = {}
                for key, value in zip(child.value.keys, child.value.values):
                    if isinstance(key, ast.Constant) and isinstance(key.value, str):
                        result[key.value] = value
                return result
    return None


def _resolved_strings(
    expression: ast.expr,
    assignments: dict[str, ast.expr],
    seen: set[str] | None = None,
) -> set[str]:
    """Collect string literals through named requirement-list assignments."""
    visited = set() if seen is None else seen
    found = {
        node.value
        for node in ast.walk(expression)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    for node in ast.walk(expression):
        if not isinstance(node, ast.Name) or node.id in visited:
            continue
        assignment = assignments.get(node.id)
        if assignment is None:
            continue
        visited.add(node.id)
        found.update(_resolved_strings(assignment, assignments, visited))
    return found


def _profile_errors(root: Path, profile: Any) -> list[str]:
    """Bind the deferred vendor decision to the actual release profile."""
    errors: list[str] = []
    try:
        spec = tomllib.loads(
            (root / "packaging/linux/services-bundle-spec.toml").read_text(
                encoding="utf-8"
            )
        )
        setup_tree = ast.parse(
            (root / "services/setup.py").read_text(encoding="utf-8")
        )
        workflow_text = (root / ".github/workflows/pypi-dispatch.yml").read_text(
            encoding="utf-8"
        )
    except (OSError, tomllib.TOMLDecodeError, SyntaxError) as exc:
        return [f"cannot verify release profile binding: {exc}"]

    profile_name = profile.get("services_extra") if isinstance(profile, dict) else None
    aggregates = profile.get("aggregates") if isinstance(profile, dict) else None
    active_lock = profile.get("active_lock") if isinstance(profile, dict) else None
    excludes = profile.get("excludes") if isinstance(profile, dict) else None
    if (
        profile_name != "linux-release"
        or aggregates != list(EXPECTED_PROFILE_EXTRAS)
        or excludes != list(EXPECTED_PROFILE_EXCLUDES)
    ):
        errors.append("manifest release profile is not the expected linux-release profile")
    spec_profile = spec.get("profile", {})
    if (
        spec_profile.get("services_extra") != profile_name
        or spec_profile.get("aggregates") != aggregates
        or spec_profile.get("excludes") != excludes
        or spec.get("bundle", {}).get("constraints") != active_lock
    ):
        errors.append("bundle specification does not match the manifest release profile")
    escaped_profile = re.escape(str(profile_name))
    if not re.search(
        rf'-e\s+"\./services\[{escaped_profile},development\]"',
        workflow_text,
    ):
        errors.append("release workflow does not install the manifest service profile")
    if not active_lock or workflow_text.count(str(active_lock)) < 2:
        errors.append("release workflow does not bind both lock uses to the active lock")

    assignments = _assignment_values(setup_tree)
    declared_extras = assignments.get("LINUX_RELEASE_EXTRAS")
    if not isinstance(declared_extras, (ast.Tuple, ast.List)):
        errors.append("services/setup.py lacks the literal linux-release aggregate list")
        actual_extras: list[str] = []
    else:
        actual_extras = [
            element.value
            for element in declared_extras.elts
            if isinstance(element, ast.Constant) and isinstance(element.value, str)
        ]
        if actual_extras != list(EXPECTED_PROFILE_EXTRAS):
            errors.append("services/setup.py linux-release aggregates drifted")

    base_extras = _returned_dict(setup_tree, "_base_extras_require")
    aggregate_extras = _returned_dict(setup_tree, "_aggregate_extras_require")
    if base_extras is None or aggregate_extras is None:
        errors.append("services/setup.py release aggregate definitions are not statically inspectable")
        base_extras = base_extras or {}
        aggregate_extras = aggregate_extras or {}
    setup_kwargs = _returned_dict(setup_tree, "build_services_setup_kwargs")
    install_requires = (
        setup_kwargs.get("install_requires") if setup_kwargs is not None else None
    )
    if install_requires is None or any(
        _VENDOR_DISTRIBUTION in value
        for value in _resolved_strings(install_requires, assignments)
    ):
        errors.append("base service requirements activate the quarantined TTS vendor")
    release_expr = aggregate_extras.get("linux-release")
    if not (
        isinstance(release_expr, ast.Call)
        and isinstance(release_expr.func, ast.Name)
        and release_expr.func.id == "_aggregate_extra"
        and any(
            isinstance(argument, ast.Starred)
            and isinstance(argument.value, ast.Name)
            and argument.value.id == "LINUX_RELEASE_EXTRAS"
            for argument in release_expr.args
        )
    ):
        errors.append("services/setup.py does not build linux-release from its declared aggregate list")

    for extra_name in actual_extras:
        expression = base_extras.get(extra_name)
        if expression is None:
            errors.append(f"linux-release aggregate is missing extra {extra_name}")
            continue
        requirement_strings = _resolved_strings(expression, assignments)
        if any(_VENDOR_DISTRIBUTION in value for value in requirement_strings):
            errors.append(
                f"linux-release extra {extra_name} activates the quarantined TTS vendor"
            )

    legacy_extras = (
        "tts-python",
        "openvoice",
        "melotts",
        "openvoice_cn",
        "openvoice_jp",
        "openvoice_kr",
        "openvoice_tw",
        "gruut_support",
    )
    for extra_name in legacy_extras:
        expression = base_extras.get(extra_name)
        if expression is None or not any(
            _VENDOR_DISTRIBUTION in value
            for value in _resolved_strings(expression, assignments)
        ):
            errors.append(
                f"legacy opt-in extra {extra_name} no longer records its quarantined vendor dependency"
            )

    return errors


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
    release_profile = manifest.get("release_profile")
    inputs = manifest.get("inputs")
    if not isinstance(inputs, list) or not inputs:
        return errors + ["release input manifest has no inputs"]

    identities = {
        item.get("distribution"): item.get("repository")
        for item in inputs
        if isinstance(item, dict)
    }
    for distribution, repository in EXPECTED_INPUTS.items():
        if distribution not in identities:
            errors.append(f"mandatory release input is missing: {distribution}")
        elif identities[distribution] != repository:
            errors.append(
                f"{distribution}: repository must be {repository}"
            )
    for distribution in identities.keys() - EXPECTED_INPUTS.keys():
        errors.append(f"unrecognized release input: {distribution}")

    try:
        if not (root / workflow).is_file():
            return errors + [f"workflow does not exist: {workflow}"]
        historical_lock_path = Path(
            release_profile.get("historical_lock", "")
            if isinstance(release_profile, dict)
            else ""
        )
        if historical_lock_path != HISTORICAL_CONSTRAINTS:
            errors.append("manifest does not identify the preserved historical lock")
        historical_constraints_text = (root / historical_lock_path).read_text(
            encoding="utf-8"
        )
        package_text = {
            path: (root / path).read_text(encoding="utf-8")
            for path in PACKAGE_METADATA
        }
    except OSError as exc:
        return errors + [f"cannot read release pin source: {exc}"]

    profile_errors = _profile_errors(root, release_profile)
    errors.extend(profile_errors)
    profile_is_safe = not profile_errors
    active_lock_path = Path(
        release_profile.get("active_lock", "")
        if isinstance(release_profile, dict)
        else ""
    )
    lock_status = (
        release_profile.get("lock_status")
        if isinstance(release_profile, dict)
        else None
    )
    active_lock_text = ""
    if lock_status == "generation_pending":
        if active_lock_path.exists():
            errors.append(
                "pending-release-lock: active lock path already exists while "
                "manifest says generation is pending"
            )
        errors.append(
            "pending-release-lock: linux-release hash lock generation and "
            "validation remain pending"
        )
    elif lock_status == "ready":
        try:
            active_lock_text = (root / active_lock_path).read_text(
                encoding="utf-8"
            )
        except OSError as exc:
            errors.append(f"active release lock is unavailable: {exc}")
        if active_lock_text:
            if "./services[linux-release]" not in active_lock_text:
                errors.append("active release lock provenance does not name linux-release")
            if re.search(
                rf"(?m)^{re.escape(_VENDOR_DISTRIBUTION)}==", active_lock_text
            ):
                errors.append("active release lock includes the quarantined TTS vendor")
    else:
        errors.append("manifest release lock status must be generation_pending or ready")
    constraints_text = (
        active_lock_text if lock_status == "ready" else historical_constraints_text
    )

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
        if not re.fullmatch(r"[0-9a-fA-F]{40}", revision):
            errors.append(
                f"{distribution}: source revision must be a full 40-character SHA"
            )
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
                if any(
                    ref is None or not re.fullmatch(r"[0-9a-f]{40}", ref)
                    for ref in refs
                ):
                    errors.append(
                        f"{distribution}: sibling checkout in {source_workflow} "
                        "has a missing or mutable source ref"
                    )
            elif expected_count is not None and (
                len(refs) != expected_count
                or any(
                    ref is None
                    or not re.fullmatch(r"[0-9a-f]{40}", ref)
                    or ref != revision.lower()
                    for ref in refs
                )
            ):
                errors.append(
                    f"{distribution}: workflow source refs do not match "
                    f"manifest revision {revision} ({source_workflow}: "
                    f"found {len(refs)}, expected {expected_count})"
                )
        for source_workflow in expected_source_refs:
            if not (root / source_workflow).is_file():
                errors.append(
                    f"{distribution}: manifest source workflow is missing: "
                    f"{source_workflow}"
                )

        release_profile_name = (
            release_profile.get("services_extra")
            if isinstance(release_profile, dict)
            else None
        )
        profile_excludes = (
            release_profile.get("excludes", [])
            if isinstance(release_profile, dict)
            else []
        )
        is_deferred_input = (
            item.get("status") == "deferred"
            and item.get("activation") == "quarantined"
            and item.get("deferred_from_profile")
            == release_profile_name
            and distribution in profile_excludes
            and profile_is_safe
        )
        is_pending_common_refresh = (
            distribution == "airunner-common"
            and lock_status == "generation_pending"
            and not _has_constraint(
                historical_constraints_text, distribution, version
            )
        )
        if (
            not is_deferred_input
            and not is_pending_common_refresh
            and not _has_constraint(constraints_text, distribution, version)
        ):
            errors.append(
                f"{distribution}: constraints do not pin exactly {version}"
            )
        requirement_matches = [
            path for path, text in package_text.items()
            if _has_requirement(text, distribution, requirement)
        ]
        # The vendor is a service-only extra; common is required by both
        # shipped packages. Shield stays pinned in explicit compatibility
        # extras while deferred from the default linux-release profile.
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

        if is_deferred_input:
            pass
        elif (
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
