"""Bundle path and manifest helpers for AIRunner installers."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BundleSpec:
    """Static naming and dependency policy for one bundle target."""

    target_platform: str
    bundle_name: str
    install_extra: str

    @property
    def binary_suffix(self) -> str:
        """Return the executable suffix for this target."""
        return ".exe" if self.target_platform == "windows" else ""

    @property
    def launcher_name(self) -> str:
        """Return the staged launcher file name."""
        return f"airunner{self.binary_suffix}"


@dataclass(frozen=True)
class BundlePaths:
    """Canonical filesystem layout for one staged AIRunner bundle."""

    root: Path
    app_dir: Path
    app_site_packages: Path
    bin_dir: Path
    launcher_path: Path
    llama_server_path: Path
    whisper_server_path: Path
    python_dir: Path
    share_dir: Path
    airunner_share_dir: Path
    manifest_path: Path
    metadata_path: Path
    python_pins_path: Path
    runtime_pins_path: Path
    applications_dir: Path
    desktop_entry_path: Path
    icon_dir: Path
    icon_path: Path
    deployment_dir: Path


def default_install_extra(target_platform: str) -> str:
    """Return the default install extra for one bundle platform."""
    return "windows" if target_platform == "windows" else "desktop"


def build_bundle_spec(
    target_platform: str,
    bundle_name: str = "desktop",
    install_extra: str | None = None,
) -> BundleSpec:
    """Return the normalized bundle spec for one target."""
    if target_platform not in {"linux", "windows"}:
        raise ValueError(f"Unsupported target platform: {target_platform}")
    return BundleSpec(
        target_platform=target_platform,
        bundle_name=bundle_name,
        install_extra=install_extra or default_install_extra(target_platform),
    )


def build_bundle_paths(root: Path, spec: BundleSpec) -> BundlePaths:
    """Return the canonical staged paths for one bundle root."""
    share_dir = root / "share"
    airunner_share_dir = share_dir / "airunner"
    applications_dir = share_dir / "applications"
    icon_dir = share_dir / "icons" / "hicolor" / "64x64" / "apps"
    bin_dir = root / "bin"
    return BundlePaths(
        root=root,
        app_dir=root / "app",
        app_site_packages=root / "app" / "site-packages",
        bin_dir=bin_dir,
        launcher_path=bin_dir / spec.launcher_name,
        llama_server_path=bin_dir / f"llama-server{spec.binary_suffix}",
        whisper_server_path=bin_dir / f"whisper-server{spec.binary_suffix}",
        python_dir=root / "python",
        share_dir=share_dir,
        airunner_share_dir=airunner_share_dir,
        manifest_path=airunner_share_dir / "runtime_manifest.env",
        metadata_path=airunner_share_dir / "bundle_metadata.json",
        python_pins_path=airunner_share_dir / "python_runtime_pins.env",
        runtime_pins_path=airunner_share_dir / "runtime_pins.env",
        applications_dir=applications_dir,
        desktop_entry_path=applications_dir / "airunner.desktop",
        icon_dir=icon_dir,
        icon_path=icon_dir / "airunner.png",
        deployment_dir=root / "deployment",
    )


def bundle_archive_name(version: str, spec: BundleSpec) -> str:
    """Return the archive file name for one bundle."""
    extension = "zip" if spec.target_platform == "windows" else "tar.gz"
    return (
        f"airunner-{version}-{spec.target_platform}-"
        f"{spec.bundle_name}-bundle.{extension}"
    )


def relative_manifest_path(base_dir: Path, target_path: Path) -> str:
    """Return a manifest-friendly relative path between two locations."""
    return os.path.relpath(target_path, start=base_dir).replace(os.sep, "/")


def build_runtime_manifest(
    paths: BundlePaths,
    python_executable: Path,
) -> dict[str, str]:
    """Return the runtime manifest entries for one staged bundle."""
    manifest_dir = paths.manifest_path.parent
    return {
        "AIRUNNER_BUNDLE_ROOT": relative_manifest_path(manifest_dir, paths.root),
        "AIRUNNER_PYTHON": relative_manifest_path(
            manifest_dir,
            python_executable,
        ),
        "AIRUNNER_PYTHONPATH": relative_manifest_path(
            manifest_dir,
            paths.app_site_packages,
        ),
        "AIRUNNER_ENTRYPOINT": "airunner_native.launcher",
        "AIRUNNER_LLAMA_SERVER_BIN": relative_manifest_path(
            manifest_dir,
            paths.llama_server_path,
        ),
        "AIRUNNER_WHISPER_SERVER_BIN": relative_manifest_path(
            manifest_dir,
            paths.whisper_server_path,
        ),
    }


def file_sha256(path: Path) -> str:
    """Return the SHA256 digest for one file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()