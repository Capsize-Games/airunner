"""Install handoff for verified update bundles (release P10).

Stage 3 of the update flow: :func:`install_verified_update`
re-verifies the staged bytes, extracts the tarball, and hands the
bundle to P07 activation (``packaging/linux/upgrade.sh``) or an
injected installer. It accepts only a :class:`VerifiedUpdate`,
so an unverified, swapped, or truncated artifact cannot reach
the installer.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import tarfile
from collections.abc import Callable
from pathlib import Path

from airunner_services.downloads.update_check import (
    UpdateCheckError,
    VerifiedUpdate,
)
from airunner_services.downloads.update_manifest import match_artifact

UPGRADE_SCRIPT_ENV_VAR = "AIRUNNER_UPGRADE_SH"
UPGRADE_TIMEOUT_SECONDS = 300
MAX_EXTRACT_MULTIPLE = 8


class UpdateInstallError(UpdateCheckError):
    """A verified bundle failed extraction or installer handoff."""


def _run_installer(
    run: Callable[[Path, Path], None], bundle: Path, prefix: Path
) -> None:
    """Run the installer; wrap unexpected failures."""
    try:
        run(bundle, prefix)
    except UpdateCheckError:
        raise
    except Exception as exc:
        raise UpdateInstallError(f"installer failed: {exc}") from exc


def install_verified_update(
    verified: VerifiedUpdate,
    *,
    prefix: str | Path,
    installer: Callable[[Path, Path], None] | None = None,
) -> Path:
    """Re-verify, extract, and hand the bundle to P07 activation.

    Default installer is ``upgrade.sh``; return the bundle directory.
    """
    size, hexdigest = _digest_file(verified.path)
    match_artifact(size, hexdigest, verified.artifact)
    bundle = _extract_bundle(verified)
    run = installer if installer is not None else _run_upgrade
    _run_installer(run, bundle, Path(prefix))
    return bundle


def _digest_file(path: Path) -> tuple[int, str]:
    """Return ``(size, sha256)`` streaming over ``path``."""
    try:
        handle = path.open("rb")
    except OSError as exc:
        raise UpdateInstallError(
            f"verified artifact unreadable: {exc}"
        ) from exc
    digest = hashlib.sha256()
    total = 0
    with handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            total += len(chunk)
            digest.update(chunk)
    return total, digest.hexdigest()


def _extract_member(
    archive: tarfile.TarFile,
    member: tarfile.TarInfo,
    dest: Path,
    total: int,
    budget: int,
) -> int:
    """Extract one member; return the running size total."""
    target = _check_member(member, dest)
    total += member.size
    if total > budget:
        raise UpdateInstallError("bundle exceeds size budget")
    if member.isdir():
        target.mkdir(parents=True, exist_ok=True)
    else:
        _write_member(archive, member, target)
    return total


def _extract_bundle(verified: VerifiedUpdate) -> Path:
    """Extract the verified tarball into a fresh bundle directory."""
    dest = verified.path.parent / "bundle"
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    budget = verified.artifact.size * MAX_EXTRACT_MULTIPLE
    try:
        total = 0
        with tarfile.open(verified.path, "r:gz") as archive:
            for member in archive.getmembers():
                total = _extract_member(archive, member, dest, total, budget)
    except UpdateInstallError:
        raise
    except Exception as exc:
        raise UpdateInstallError(f"bundle extraction failed: {exc}") from exc
    return dest


def _check_member(member: tarfile.TarInfo, dest: Path) -> Path:
    """Return the extraction target for one safe tar member."""
    if not member.isreg() and not member.isdir():
        raise UpdateInstallError(f"unsupported entry: {member.name}")
    if not member.name or member.name.startswith("/"):
        raise UpdateInstallError(f"unsafe entry: {member.name!r}")
    target = (dest / member.name).resolve()
    if not target.is_relative_to(dest.resolve()):
        raise UpdateInstallError(f"escaping entry: {member.name}")
    return target


def _write_member(
    archive: tarfile.TarFile, member: tarfile.TarInfo, target: Path
) -> None:
    """Write one regular tar member, preserving executability."""
    target.parent.mkdir(parents=True, exist_ok=True)
    reader = archive.extractfile(member)
    if reader is None:
        raise UpdateInstallError(f"unreadable entry: {member.name}")
    target.write_bytes(reader.read())
    if member.mode & 0o111:
        target.chmod(0o755)


def _run_upgrade(bundle: Path, prefix: Path) -> None:
    """Activate ``bundle`` under ``prefix`` via P07 ``upgrade.sh``."""
    script = _upgrade_script_path()
    proc = subprocess.run(
        [str(script), "--bundle", str(bundle), "--prefix", str(prefix)],
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"},
        timeout=UPGRADE_TIMEOUT_SECONDS,
    )
    if proc.returncode != 0:
        raise UpdateInstallError(f"upgrade.sh failed: {proc.stderr.strip()}")


def _upgrade_script_path() -> Path:
    """Locate ``packaging/linux/upgrade.sh`` for this checkout."""
    override = os.environ.get(UPGRADE_SCRIPT_ENV_VAR)
    if override:
        return Path(override)
    root = Path(__file__).resolve().parents[4]
    candidate = root / "packaging" / "linux" / "upgrade.sh"
    if not candidate.is_file():
        raise UpdateInstallError(
            "upgrade.sh not found; pass installer= explicitly"
        )
    return candidate
