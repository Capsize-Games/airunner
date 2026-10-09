"""Bundle assembly steps for the Linux services bundle (P05).

Single concern: pure build steps behind the assemble CLI (freeze
command construction, entry trampoline, data staging, manifest
hashing). No repository imports; stdlib only.
"""

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

_ENTRY_TEMPLATE = '''"""Frozen entry trampoline (generated at bundle time)."""

import os
import sys
from pathlib import Path


def _bundle_root() -> None:
    """Default AIRUNNER_BUNDLE_ROOT at the frozen bundle root."""
    if os.environ.get("AIRUNNER_BUNDLE_ROOT"):
        return
    if not getattr(sys, "frozen", False):
        return
    internal = getattr(sys, "_MEIPASS", "")
    if internal:
        os.environ["AIRUNNER_BUNDLE_ROOT"] = str(
            Path(internal).resolve().parent
        )


_bundle_root()

from {module} import {function}

{function}()
'''


def expand_data(
    entry: dict[str, Any], repo_root: Path
) -> list[tuple[Path, str]]:
    """Expand one [[data]] entry into (file, bundle dest dir) pairs."""
    matches = sorted(repo_root.glob(str(entry["source"])))
    files = [path for path in matches if path.is_file()]
    if entry.get("required", True) and not files:
        raise SystemExit(
            f"data source matches no file: {entry['source']} "
            "(P04 data-file rule: declare the payload or drop it)"
        )
    return [(path, str(entry["dest"]).rstrip("/")) for path in files]


def _tool_args(
    pyinstaller: str, bundle: dict[str, Any], distpath: Path, workpath: Path
) -> list[str]:
    """Return the tool-level PyInstaller flags for this bundle."""
    command = [pyinstaller, "--onedir", "--noconfirm", "--clean"]
    command.extend(["--name", str(bundle["executable"])])
    command.extend(["--distpath", str(distpath)])
    command.extend(["--workpath", str(workpath), "--specpath", str(workpath)])
    return command


def _data_args(spec: dict[str, Any], repo_root: Path) -> list[str]:
    """Return the --add-data flags for collect-staged entries."""
    args: list[str] = []
    for entry in spec.get("data", []):
        if str(entry.get("stage")) != "collect":
            continue
        for path, dest in expand_data(entry, repo_root):
            args.extend(["--add-data", f"{path}:{dest}"])
    return args


def _code_args(spec: dict[str, Any]) -> list[str]:
    """Return the code-inclusion flags for the spec [code] table."""
    args: list[str] = []
    for package in spec["code"].get("collect_data", []):
        args.extend(["--collect-data", package])
    for module in spec["code"].get("hidden_imports", []):
        args.extend(["--hidden-import", module])
    for package in spec["code"].get("collect_submodules", []):
        args.extend(["--collect-submodules", package])
    for dist in spec["code"].get("copy_metadata", []):
        args.extend(["--copy-metadata", dist])
    return args


def build_command(
    spec: dict[str, Any],
    repo_root: Path,
    entry_script: Path,
    distpath: Path,
    workpath: Path,
    pyinstaller: str,
) -> list[str]:
    """Return the exact PyInstaller command for this spec."""
    command = _tool_args(pyinstaller, spec["bundle"], distpath, workpath)
    for extra in ("services/src", "native/src"):
        command.extend(["--paths", str(repo_root / extra)])
    command.extend(_data_args(spec, repo_root))
    command.extend(_code_args(spec))
    command.append(str(entry_script))
    return command


def write_entry_script(workpath: Path, module: str, function: str) -> Path:
    """Write the frozen entry trampoline into the build workdir."""
    workpath.mkdir(parents=True, exist_ok=True)
    entry = workpath / "_bundle_entry.py"
    entry.write_text(
        _ENTRY_TEMPLATE.format(module=module, function=function),
        encoding="utf-8",
    )
    return entry


def resolve_base_rev(repo_root: Path, override: str | None) -> str:
    """Return the manifest build identity (git rev or --base)."""
    if override:
        return override
    proc = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    if proc.returncode == 0 and proc.stdout.strip():
        return proc.stdout.strip()
    raise SystemExit(
        "cannot resolve git HEAD for the manifest; pass --base explicitly"
    )


def stage_root_files(
    spec: dict[str, Any], repo_root: Path, bundle_dir: Path
) -> None:
    """Copy stage=root payloads (legal notices) beside the executable."""
    for entry in spec.get("data", []):
        if str(entry.get("stage")) != "root":
            continue
        for path, dest in expand_data(entry, repo_root):
            target_dir = bundle_dir / dest
            target_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target_dir / path.name)


def _manifest_entries(
    bundle_dir: Path, manifest_name: str
) -> list[dict[str, str]]:
    """Return sorted (path, sha256) entries for every bundle file."""
    entries: list[dict[str, str]] = []
    paths = sorted(
        p.relative_to(bundle_dir)
        for p in bundle_dir.rglob("*")
        if p.is_file() and p.name != manifest_name
    )
    for path in paths:
        digest = hashlib.sha256()
        with (bundle_dir / path).open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        entries.append({"path": path.as_posix(), "sha256": digest.hexdigest()})
    return entries


def write_manifest(
    bundle_dir: Path, spec: dict[str, Any], base: str
) -> dict[str, Any]:
    """Hash every bundle file and write bundle-manifest.json."""
    manifest_name = spec["manifest"]["filename"]
    entries = _manifest_entries(bundle_dir, manifest_name)
    manifest = {
        "bundle": spec["bundle"]["name"],
        "tool": spec["bundle"]["tool"],
        "entry": spec["bundle"]["entry"],
        "base": base,
        "files": entries,
    }
    (bundle_dir / manifest_name).write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def run_freeze(command: list[str], pyinstaller: str) -> None:
    """Execute PyInstaller or fail with an actionable message."""
    if shutil.which(pyinstaller) is None:
        raise SystemExit(
            f"pyinstaller executable not found: {pyinstaller!r}; "
            "install the pinned tool into the isolated build "
            "environment first"
        )
    env = dict(os.environ)
    # NLTK's import guard breaks PyInstaller hook collection; the daemon
    # runs with it disabled (daemon.py), so the freeze does too. Scoped
    # to the subprocess: this process needs its sibling imports as-is.
    env.setdefault("NLTK_DISABLE_IMPORT_SECURITY", "1")
    proc = subprocess.run(command, env=env)
    if proc.returncode != 0:
        raise SystemExit(f"pyinstaller exited with status {proc.returncode}")
