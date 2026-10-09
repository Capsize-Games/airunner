"""Assemble the Linux v1 services directory bundle (release P05).

Implements the P04-selected recipe (directory-mode PyInstaller) at full
application scale from packaging/linux/services-bundle-spec.toml: freeze
the daemon entry point, stage legal notices beside the executable,
write the P04 bundle manifest, then gate the result through
inspect_linux_bundle (manifest hashes, required resources, exclusion
scan, warn-file gate, frozen-module presence).

Run from the repo root in an isolated venv with the P02 profile
installed (package/constraints-linux-nvidia-cu129.txt)::

    venv/bin/python scripts/assemble_linux_bundle.py --dry-run
    venv/bin/python scripts/assemble_linux_bundle.py \\
        --distpath /tmp/bundle/dist --workpath /tmp/bundle/work

--dry-run resolves every data glob and prints the exact PyInstaller
command without executing it. stdlib only; safe to run with no
repository on PYTHONPATH.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
import types
from pathlib import Path
from typing import Any

# Re-exported so this CLI keeps the single-file module API intact.
from linux_bundle_assemble import (
    build_command,
    expand_data,
    resolve_base_rev,
    run_freeze,
    stage_root_files,
    write_entry_script,
    write_manifest,
)

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
    return parser.parse_args(argv)


def _report_spec_errors(errors: list[str]) -> bool:
    """Print spec errors; True when the spec is unusable."""
    for error in errors:
        print(f"SPEC: {error}", file=sys.stderr)
    return bool(errors)


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
) -> tuple[Path, list[str]]:
    """Return the entry path and exact freeze command for the spec."""
    entry_script = workpath / "_bundle_entry.py"
    command = build_command(
        spec, _REPO_ROOT, entry_script, distpath, workpath, pyinstaller
    )
    return entry_script, command


def _freeze_tree(
    spec: dict[str, Any],
    workpath: Path,
    distpath: Path,
    command: list[str],
    pyinstaller: str,
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
    (bundle_dir / spec["runtimes"]["bin_dir"]).mkdir(exist_ok=True)
    stage_root_files(spec, _REPO_ROOT, bundle_dir)
    return bundle_dir


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
    )
    return _report_gate(result, bundle_dir)


def main(argv: list[str] | None = None) -> int:
    """Assemble the bundle, then gate it through the inspector."""
    args = _assemble_args(argv)
    inspect = _load_inspect_module()
    spec = inspect.load_spec(args.spec or DEFAULT_SPEC)
    if _report_spec_errors(inspect.spec_errors(spec)):
        return 2
    workpath, distpath = _output_paths(args, spec)
    base = resolve_base_rev(_REPO_ROOT, args.base)
    entry_script, command = _freeze_cmd(
        spec, workpath, distpath, args.pyinstaller
    )
    if args.dry_run:
        _print_dry_run(base, entry_script, command)
        return 0
    bundle_dir = _freeze_tree(
        spec, workpath, distpath, command, args.pyinstaller
    )
    manifest = _write_bundle_manifest(bundle_dir, spec, base)
    return _inspect_frozen(inspect, spec, bundle_dir, args)


if __name__ == "__main__":
    raise SystemExit(main())
