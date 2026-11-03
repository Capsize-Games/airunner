"""Assemble the Linux v1 services directory bundle (release P05).

Implements the P04-selected recipe (directory-mode PyInstaller) at full
application scale from packaging/linux/services-bundle-spec.toml: freeze
the daemon entry point, stage legal notices beside the executable,
write the P04 bundle manifest, then gate the result through
inspect_linux_bundle (manifest hashes, required resources, exclusion
scan, warn-file gate, frozen-module presence).

Run from the repo root in an isolated venv with the P02 linux-release
profile installed from its validated hash lock. Lock generation is pending;
the candidate workflow fails closed until that lock exists.

    venv/bin/python scripts/assemble_linux_bundle.py --dry-run
    venv/bin/python scripts/assemble_linux_bundle.py \\
        --distpath /tmp/bundle/dist --workpath /tmp/bundle/work

--dry-run resolves every data glob and prints the exact PyInstaller
command without executing it. stdlib only; safe to run with no
repository on PYTHONPATH.

Content policy data is optional and omitted from the standard bundle.
Applications that choose signed policy data can request strict build
validation with --require-signed-policy and --policy-trust-store.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import sys
import types
from pathlib import Path
from typing import Any

# Re-exported so this CLI keeps the single-file module API intact.
from linux_bundle_assemble import (
    build_command,
    expand_data,
    prune_bundle,
    resolve_base_rev,
    run_freeze,
    stage_root_files,
    write_entry_script,
    write_manifest,
)
from dependency_notices import collect_dependency_notices
from stage_espeak_native_payload import stage_espeak_payload, _validate_payload
from postgresql_runtime_payload import (
    PostgreSQLPayloadError,
    stage_runtime_payload,
    validate_staged_runtime,
    validate_staged_supplement,
    validate_build_host,
)
from verify_warning_source_reviews import verify_warning_source_reviews

_REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SPEC = (
    Path(__file__).resolve().parent.parent
    / "packaging"
    / "linux"
    / "services-bundle-spec.toml"
)


def _load_sibling_module(module_name: str, file_name: str) -> types.ModuleType:
    """Load one sibling script by file location into sys.modules."""
    path = Path(__file__).resolve().with_name(file_name)
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load sibling module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _load_inspect_module() -> types.ModuleType:
    """Load the sibling inspect script without touching sys.path."""
    _load_sibling_module("linux_bundle_checks", "linux_bundle_checks.py")
    _load_sibling_module("linux_bundle_gates", "linux_bundle_gates.py")
    return _load_sibling_module(
        "linux_bundle_inspect", "inspect_linux_bundle.py"
    )


def _build_paths(workpath: Path, executable: str) -> tuple[Path, list[Path]]:
    """Locate the freeze gate inputs under the PyInstaller workdir."""
    build_dir = workpath / executable
    warn_file = build_dir / f"warn-{executable}.txt"
    return warn_file, sorted(build_dir.glob("*.toc"))


def _assemble_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse the assemble CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, default=None)
    parser.add_argument("--distpath", type=Path, default=None)
    parser.add_argument("--workpath", type=Path, default=None)
    parser.add_argument("--base", default=None)
    parser.add_argument("--pyinstaller", default="pyinstaller")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--require-sidecars", action="store_true")
    parser.add_argument("--espeak-payload", type=Path, default=None)
    parser.add_argument("--postgresql-runtime-inputs", type=Path, default=None)
    parser.add_argument("--postgresql-build-supplement-inputs", type=Path, default=None)
    parser.add_argument("--policy-trust-store", type=Path, default=None)
    parser.add_argument("--require-signed-policy", action="store_true")
    return parser.parse_args(argv)


def _report_spec_errors(errors: list[str]) -> bool:
    """Print spec errors; True when the spec is unusable."""
    for error in errors:
        print(f"SPEC: {error}", file=sys.stderr)
    return bool(errors)


def _staged_policy_files(
    spec: dict[str, Any], repo_root: Path
) -> list[Path]:
    """Resolve staged policy .dat files from the spec data entries."""
    staged: list[Path] = []
    for entry in spec.get("data", []):
        if not str(entry.get("source", "")).endswith(".dat"):
            continue
        matches = sorted(repo_root.glob(str(entry["source"])))
        staged.extend(path for path in matches if path.is_file())
    return staged


def _verify_policy_trust(
    staged: list[Path], trust_store: Path
) -> list[str]:
    """Verify staged files against the trust store; problems or [].

    Reuses the S06 staging verifier with the self-computed digest, so
    only the signature-against-trust-store check is meaningful here.
    """
    try:
        stage_mod = _load_sibling_module(
            "bundle_policy_stage", "build_policy_terms.py"
        )
        store = stage_mod.load_release_trust_store(Path(trust_store))
    except (ImportError, OSError, ValueError):
        return ["release policy trust store is unusable"]
    problems: list[str] = []
    for path in staged:
        try:
            data = path.read_bytes()
        except OSError:
            return ["release policy data set is absent"]
        try:
            stage_mod.stage_release_artifact(
                artifact=path,
                trust_store=store,
                expected_sha256=hashlib.sha256(data).hexdigest(),
            )
        except ValueError:
            problems.append(
                "release policy data is unsigned or synthetic-only"
            )
    return problems


def gate_staged_policy(
    spec: dict[str, Any],
    repo_root: Path,
    trust_store: Path | None = None,
) -> list[str]:
    """Fail-closed release gate over the staged policy set.

    Returns content-free problems ([]) when every staged .dat is
    present, strictly versioned, non-empty, and accompanied by a
    well-formed detached signature. With ``trust_store`` each
    signature is additionally verified against those release keys,
    which rejects data signed outside the release process. Writes
    nothing; the caller maps a non-empty return to exit code 2.
    """
    staged = _staged_policy_files(spec, repo_root)
    if not staged:
        return ["release policy data set is absent"]
    checker = _load_inspect_module()
    problems: list[str] = []
    for path in staged:
        problems.extend(checker.check_policy_file(path))
    if problems or trust_store is None:
        return problems
    problems.extend(_verify_policy_trust(staged, trust_store))
    return problems


def _report_policy_errors(problems: list[str]) -> bool:
    """Print policy gate problems; True when packaging must stop."""
    for problem in problems:
        print(f"POLICY: {problem}", file=sys.stderr)
    return bool(problems)


def _output_paths(
    args: argparse.Namespace, spec: dict[str, Any]
) -> tuple[Path, Path]:
    """Resolve output dirs and pre-check every data glob.

    Records the resolved dirs back onto args for later steps.
    """
    args.workpath = args.workpath or (_REPO_ROOT / "build" / "bundle-work")
    args.distpath = args.distpath or (_REPO_ROOT / "build" / "bundle-dist")
    # Resolve every data glob before touching the toolchain: a
    # declaration that matches nothing is a recipe bug (P04 rule).
    for entry in spec.get("data", []):
        expand_data(entry, _REPO_ROOT)
    return args.workpath, args.distpath


def _print_dry_run(base: str, entry_script: Path, command: list[str]) -> None:
    """Print the resolved base, entry, and freeze command."""
    print("base:", base)
    print("entry:", entry_script)
    print("command:")
    print("  " + " ".join(str(part) for part in command))


def _freeze_cmd(
    spec: dict[str, Any],
    workpath: Path,
    distpath: Path,
    pyinstaller: str,
    include_content_policy: bool = False,
) -> tuple[Path, list[str]]:
    """Return the entry path and exact freeze command for the spec."""
    entry_script = workpath / "_bundle_entry.py"
    command = build_command(
        spec, _REPO_ROOT, entry_script, distpath, workpath, pyinstaller,
        include_content_policy=include_content_policy,
    )
    return entry_script, command


def _freeze_tree(
    spec: dict[str, Any],
    workpath: Path,
    distpath: Path,
    command: list[str],
    pyinstaller: str,
    espeak_payload: Path | None = None,
    postgresql_runtime_inputs: Path | None = None,
    postgresql_build_supplement_inputs: Path | None = None,
) -> Path:
    """Freeze the bundle and stage root payloads; return its dir."""
    write_entry_script(
        workpath,
        str(spec["bundle"]["entry_module"]),
        str(spec["bundle"]["entry_function"]),
    )
    run_freeze(command, pyinstaller)
    bundle_dir = distpath / str(spec["bundle"]["executable"])
    if not bundle_dir.is_dir():
        raise SystemExit(f"pyinstaller produced no bundle dir: {bundle_dir}")
    _finish_tree(
        spec, bundle_dir, espeak_payload, postgresql_runtime_inputs,
        postgresql_build_supplement_inputs,
    )
    return bundle_dir


def _finish_tree(
    spec: dict[str, Any],
    bundle_dir: Path,
    espeak_payload: Path | None = None,
    postgresql_runtime_inputs: Path | None = None,
    postgresql_build_supplement_inputs: Path | None = None,
) -> None:
    """Stage root payloads, prune hook data, then collect locked notices."""
    (bundle_dir / spec["runtimes"]["bin_dir"]).mkdir(exist_ok=True)
    stage_root_files(spec, _REPO_ROOT, bundle_dir)
    pruned = prune_bundle(bundle_dir, spec)
    print(f"pruned {len(pruned)} hook-collected paths")
    if espeak_payload is not None:
        stage_espeak_payload(espeak_payload, bundle_dir)
    stage_runtime_payload(
        postgresql_runtime_inputs, bundle_dir, spec, _REPO_ROOT,
        postgresql_build_supplement_inputs,
    )
    if spec.get("dependency_notices", {}).get("required", False):
        collect_dependency_notices(spec, _REPO_ROOT, bundle_dir)


def _write_bundle_manifest(
    bundle_dir: Path, spec: dict[str, Any], base: str
) -> dict[str, Any]:
    """Write the manifest and print its summary; return it."""
    manifest = write_manifest(bundle_dir, spec, base)
    print(f"wrote {bundle_dir / spec['manifest']['filename']}")
    print(f"  {len(manifest['files'])} files, base {base}")
    return manifest


def _report_gate(result: Any, bundle_dir: Path) -> int:
    """Print gate warnings and problems; return the exit code."""
    for warning in result.warnings:
        print(f"WARN: {warning}")
    for problem in result.problems:
        print(f"FAIL: {problem}")
    if result.failed:
        return 1
    print(f"OK: {bundle_dir} assembled and inspected")
    return 0


def _inspect_frozen(
    inspect: types.ModuleType,
    spec: dict[str, Any],
    bundle_dir: Path,
    args: argparse.Namespace,
) -> int:
    """Gate the frozen bundle through the inspector; exit code."""
    executable = str(spec["bundle"]["executable"])
    warn_file, toc_paths = _build_paths(args.workpath, executable)
    result = inspect.inspect_bundle(
        bundle_dir,
        spec,
        warn_file=warn_file if warn_file.is_file() else None,
        toc_paths=toc_paths,
        require_sidecars=args.require_sidecars,
        require_signed_policy=(
            args.require_signed_policy or args.policy_trust_store is not None
        ),
    )
    return _report_gate(result, bundle_dir)


def main(argv: list[str] | None = None) -> int:
    """Assemble the bundle, then gate it through the inspector."""
    args = _assemble_args(argv)
    inspect = _load_inspect_module()
    spec = inspect.load_spec(args.spec or DEFAULT_SPEC)
    if _report_spec_errors(inspect.spec_errors(spec)):
        return 2
    validate_policy = args.require_signed_policy or args.policy_trust_store is not None
    if validate_policy and args.policy_trust_store is None:
        print("POLICY: --require-signed-policy requires --policy-trust-store", file=sys.stderr)
        return 2
    if validate_policy and not args.dry_run:
        problems = gate_staged_policy(
            spec, _REPO_ROOT, args.policy_trust_store
        )
        if _report_policy_errors(problems):
            return 2
    workpath, distpath = _output_paths(args, spec)
    base = resolve_base_rev(_REPO_ROOT, args.base)
    entry_script, command = _freeze_cmd(
        spec, workpath, distpath, args.pyinstaller, validate_policy
    )
    if args.dry_run:
        _print_dry_run(base, entry_script, command)
        return 0
    if args.espeak_payload is None and spec.get("native_speech", {}).get("required", False):
        print("SPEECH: full bundle requires --espeak-payload from the reviewed native build", file=sys.stderr)
        return 2
    if args.espeak_payload is not None:
        try:
            _validate_payload(
                args.espeak_payload, _REPO_ROOT / "packaging/espeak/source-lock.json", _REPO_ROOT
            )
        except (OSError, ValueError) as exc:
            print(f"SPEECH: {exc}", file=sys.stderr)
            return 2
    postgresql_mode = spec.get("postgresql_runtime", {}).get("mode")
    if postgresql_mode == "locked-ubuntu-debs":
        if args.postgresql_runtime_inputs is None:
            print("POSTGRESQL: full bundle requires staged reviewed Ubuntu libpq inputs", file=sys.stderr)
            return 2
        if args.postgresql_build_supplement_inputs is None:
            print("POSTGRESQL: full bundle requires staged glibc build compatibility inputs", file=sys.stderr)
            return 2
        try:
            validate_build_host()
            validate_staged_runtime(args.postgresql_runtime_inputs, _REPO_ROOT)
            validate_staged_supplement(args.postgresql_build_supplement_inputs, _REPO_ROOT)
        except (OSError, PostgreSQLPayloadError) as exc:
            print(f"POSTGRESQL: {exc}", file=sys.stderr)
            return 2
    elif postgresql_mode == "disabled":
        if args.postgresql_runtime_inputs is not None or args.postgresql_build_supplement_inputs is not None:
            print("POSTGRESQL: SQLite-only bundle cannot accept PostgreSQL inputs", file=sys.stderr)
            return 2
    else:
        print("POSTGRESQL: bundle spec must explicitly select a runtime policy", file=sys.stderr)
        return 2
    evidence = spec.get("warn_allowlist", {}).get("source_evidence")
    if evidence:
        problems = verify_warning_source_reviews(_REPO_ROOT / evidence)
        if problems:
            for problem in problems:
                print(f"SOURCE REVIEW: {problem}", file=sys.stderr)
            return 2
    bundle_dir = _freeze_tree(
        spec,
        workpath,
        distpath,
        command,
        args.pyinstaller,
        args.espeak_payload,
        args.postgresql_runtime_inputs,
        args.postgresql_build_supplement_inputs,
    )
    _write_bundle_manifest(bundle_dir, spec, base)
    return _inspect_frozen(inspect, spec, bundle_dir, args)


if __name__ == "__main__":
    raise SystemExit(main())
