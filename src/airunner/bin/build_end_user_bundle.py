#!/usr/bin/env python3
"""Build staged AIRunner end-user bundles with embedded Python."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from airunner.distribution.bundle_layout import BundlePaths
from airunner.distribution.bundle_layout import BundleSpec
from airunner.distribution.bundle_layout import build_bundle_paths
from airunner.distribution.bundle_layout import build_bundle_spec
from airunner.distribution.bundle_layout import build_runtime_manifest
from airunner.distribution.bundle_layout import bundle_archive_name
from airunner.distribution.bundle_layout import file_sha256
from airunner.distribution.bundle_layout import relative_manifest_path
from airunner.distribution.python_runtime_pins import EmbeddedPythonRuntime
from airunner.distribution.python_runtime_pins import get_embedded_python_runtime
from airunner.distribution.python_runtime_pins import pins_file_path


PACKAGE_ICON = Path("src/airunner/gui/images/icon64x64.png")
PACKAGE_LICENSE = Path("LICENSE")
PACKAGE_README = Path("README.md")


@dataclass(frozen=True)
class BuildConfig:
    """Normalized inputs for one staged bundle build."""

    repo_root: Path
    spec: BundleSpec
    launcher_binary: Path
    sidecar_root: Path
    output_root: Path
    dist_root: Path
    work_root: Path
    clean: bool
    dry_run: bool


class BundleBuilder:
    """Build one AIRunner bundle root plus its distributable archive."""

    def __init__(self, config: BuildConfig) -> None:
        """Store the bundle build configuration."""
        self.config = config
        self.runtime = get_embedded_python_runtime(config.spec.target_platform)
        self.version = read_airunner_version(config.repo_root)
        self.paths = build_bundle_paths(self.bundle_root(), config.spec)

    def build(self) -> Path:
        """Build the staged bundle and return the archive path."""
        self.prepare_directories()
        self.validate_prerequisites()
        self.stage_launcher()
        self.stage_sidecars()
        python_executable = self.stage_embedded_python()
        self.install_airunner(python_executable)
        self.stage_support_files()
        self.write_runtime_manifest(python_executable)
        self.write_bundle_metadata(python_executable)
        return self.create_archive()

    def bundle_root(self) -> Path:
        """Return the root directory for the staged bundle."""
        return (
            self.config.output_root
            / self.config.spec.target_platform
            / self.config.spec.bundle_name
        )

    def python_archive_path(self) -> Path:
        """Return the cached archive path for the pinned embedded runtime."""
        return self.work_dir() / self.runtime.asset_name

    def work_dir(self) -> Path:
        """Return the work directory used for downloads and extraction."""
        return (
            self.config.work_root
            / self.config.spec.target_platform
            / self.config.spec.bundle_name
        )

    def extracted_python_dir(self) -> Path:
        """Return the extraction directory for the embedded runtime archive."""
        return self.work_dir() / "python-runtime"

    def archive_output_path(self) -> Path:
        """Return the final archive path for this staged bundle."""
        return self.config.dist_root / bundle_archive_name(
            self.version,
            self.config.spec,
        )

    def prepare_directories(self) -> None:
        """Create or reset the build directories for one bundle."""
        if self.config.clean:
            self.remove_path(self.bundle_root())
            self.remove_path(self.work_dir())
        for path in self.directories_to_create():
            self.ensure_directory(path)

    def directories_to_create(self) -> tuple[Path, ...]:
        """Return the bundle directories that must exist before staging."""
        return (
            self.bundle_root(),
            self.work_dir(),
            self.config.dist_root,
            self.paths.app_site_packages,
            self.paths.bin_dir,
            self.paths.airunner_share_dir,
            self.paths.applications_dir,
            self.paths.icon_dir,
        )

    def validate_prerequisites(self) -> None:
        """Ensure the launcher and sidecar inputs exist before staging."""
        if self.config.dry_run:
            return
        for path in (self.config.launcher_binary, self.config.sidecar_root):
            if not path.exists():
                raise FileNotFoundError(f"Required input does not exist: {path}")

    def stage_launcher(self) -> None:
        """Copy the native AIRunner launcher into the bundle bin directory."""
        self.copy_file(self.config.launcher_binary, self.paths.launcher_path)

    def stage_sidecars(self) -> None:
        """Copy bundled llama.cpp and whisper.cpp sidecars into the bundle."""
        sidecar_bin = self.config.sidecar_root / "bin"
        self.copy_file(
            sidecar_bin / self.paths.llama_server_path.name,
            self.paths.llama_server_path,
        )
        self.copy_file(
            sidecar_bin / self.paths.whisper_server_path.name,
            self.paths.whisper_server_path,
        )
        pins_path = (
            self.config.sidecar_root
            / "share"
            / "airunner"
            / "runtime_pins.env"
        )
        self.copy_file(pins_path, self.paths.runtime_pins_path)

    def stage_embedded_python(self) -> Path:
        """Download, extract, and stage the pinned embedded Python runtime."""
        self.download_python_archive()
        self.extract_python_archive()
        if self.config.dry_run:
            return expected_python_executable_path(
                self.paths.python_dir,
                self.config.spec.target_platform,
            )
        self.copy_python_runtime()
        return find_python_executable(
            self.paths.python_dir,
            self.config.spec.target_platform,
        )

    def download_python_archive(self) -> None:
        """Download the pinned embedded Python runtime when it is missing."""
        if self.python_archive_path().exists():
            return
        if self.config.dry_run:
            print(f"+ download {self.runtime.download_url}")
            return
        urllib.request.urlretrieve(
            self.runtime.download_url,
            self.python_archive_path(),
        )

    def extract_python_archive(self) -> None:
        """Extract the pinned Python runtime into the work directory."""
        if self.extracted_python_dir().exists():
            return
        if self.config.dry_run:
            print(f"+ extract {self.python_archive_path()}")
            return
        self.ensure_directory(self.extracted_python_dir())
        with tarfile.open(self.python_archive_path(), "r:gz") as archive:
            archive.extractall(self.extracted_python_dir())

    def copy_python_runtime(self) -> None:
        """Copy the extracted Python runtime tree into the staged bundle."""
        source_dir = resolve_python_source(self.extracted_python_dir())
        self.copy_tree(source_dir, self.paths.python_dir)

    def install_airunner(self, python_executable: Path) -> None:
        """Install AIRunner and its dependencies into bundle-local packages."""
        self.run_python(python_executable, "-m", "ensurepip", "--upgrade")
        self.run_python(
            python_executable,
            "-m",
            "pip",
            "install",
            "--upgrade",
            "pip",
        )
        project_spec = build_project_spec(self.config.repo_root, self.config.spec)
        self.run_python(
            python_executable,
            "-m",
            "pip",
            "install",
            "--target",
            str(self.paths.app_site_packages),
            project_spec,
        )

    def stage_support_files(self) -> None:
        """Copy the docs, icon, desktop entry, and Linux deployment files."""
        self.copy_file(
            self.config.repo_root / PACKAGE_README,
            self.bundle_root() / "README.md",
        )
        self.copy_file(
            self.config.repo_root / PACKAGE_LICENSE,
            self.bundle_root() / "LICENSE",
        )
        self.copy_file(pins_file_path(), self.paths.python_pins_path)
        self.copy_file(self.desktop_entry_source(), self.paths.desktop_entry_path)
        self.copy_file(self.config.repo_root / PACKAGE_ICON, self.paths.icon_path)
        if self.config.spec.target_platform == "linux":
            self.copy_tree(
                self.config.repo_root / "deployment" / "systemd",
                self.paths.deployment_dir / "systemd",
            )

    def desktop_entry_source(self) -> Path:
        """Return the desktop entry template used for Linux bundles."""
        return self.config.repo_root / "packaging" / "linux" / "airunner.desktop"

    def write_runtime_manifest(self, python_executable: Path) -> None:
        """Write the manifest consumed by the native launcher in prod mode."""
        manifest = build_runtime_manifest(self.paths, python_executable)
        content = ["# Generated by build_end_user_bundle.py."]
        content.extend(f"{key}={value}" for key, value in manifest.items())
        self.write_text(self.paths.manifest_path, "\n".join(content) + "\n")

    def write_bundle_metadata(self, python_executable: Path) -> None:
        """Write pinned runtime and file integrity metadata for the bundle."""
        if self.config.dry_run:
            print(f"+ write {self.paths.metadata_path}")
            return
        metadata = build_bundle_metadata(
            self.bundle_root(),
            self.config.spec,
            self.runtime,
            self.version,
            self.paths,
            python_executable,
        )
        content = json.dumps(metadata, indent=2, sort_keys=True) + "\n"
        self.write_text(self.paths.metadata_path, content)

    def create_archive(self) -> Path:
        """Archive the staged bundle into the dist directory."""
        archive_path = self.archive_output_path()
        if self.config.dry_run:
            print(f"+ archive {self.bundle_root()} -> {archive_path}")
            return archive_path
        if self.config.spec.target_platform == "windows":
            return Path(
                shutil.make_archive(
                    str(archive_path.with_suffix("")),
                    "zip",
                    root_dir=self.bundle_root().parent,
                    base_dir=self.bundle_root().name,
                )
            )
        return Path(
            shutil.make_archive(
                str(archive_path).removesuffix(".tar.gz"),
                "gztar",
                root_dir=self.bundle_root().parent,
                base_dir=self.bundle_root().name,
            )
        )

    def run_python(self, python_executable: Path, *args: str) -> None:
        """Run one embedded-Python command unless the build is a dry run."""
        command = [str(python_executable), *args]
        if self.config.dry_run:
            print(f"+ {' '.join(command)}")
            return
        subprocess.run(command, check=True)

    def ensure_directory(self, path: Path) -> None:
        """Create one directory unless dry-run mode is enabled."""
        if self.config.dry_run:
            print(f"+ mkdir -p {path}")
            return
        path.mkdir(parents=True, exist_ok=True)

    def remove_path(self, path: Path) -> None:
        """Remove one filesystem path when clean mode is enabled."""
        if not path.exists() or self.config.dry_run:
            return
        if path.is_dir():
            shutil.rmtree(path)
            return
        path.unlink()

    def copy_file(self, source: Path, destination: Path) -> None:
        """Copy one file into the staged bundle."""
        if self.config.dry_run:
            print(f"+ cp {source} {destination}")
            return
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    def copy_tree(self, source: Path, destination: Path) -> None:
        """Copy one directory tree into the staged bundle."""
        if self.config.dry_run:
            print(f"+ cp -R {source} {destination}")
            return
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(source, destination)

    def write_text(self, path: Path, content: str) -> None:
        """Write one text file into the staged bundle."""
        if self.config.dry_run:
            print(f"+ write {path}")
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def read_airunner_version(repo_root: Path) -> str:
    """Read the AIRunner version directly from setup.py."""
    setup_text = (repo_root / "setup.py").read_text(encoding="utf-8")
    marker = 'version="'
    version_start = setup_text.index(marker) + len(marker)
    version_end = setup_text.index('"', version_start)
    return setup_text[version_start:version_end]


def build_project_spec(repo_root: Path, spec: BundleSpec) -> str:
    """Return the pip project spec used to install AIRunner into a bundle."""
    return f"{repo_root}[{spec.install_extra}]"


def resolve_python_source(extracted_dir: Path) -> Path:
    """Return the extracted directory that contains the Python runtime tree."""
    python_dir = extracted_dir / "python"
    if python_dir.is_dir():
        return python_dir
    entries = [entry for entry in extracted_dir.iterdir() if entry.is_dir()]
    if len(entries) == 1:
        return entries[0]
    return extracted_dir


def find_python_executable(bundle_python_dir: Path, target_platform: str) -> Path:
    """Locate the staged Python interpreter inside one bundle runtime tree."""
    if target_platform == "windows":
        names = ["python.exe"]
    else:
        names = ["python", "python3.13", "python3"]
    for name in names:
        matches = sorted(bundle_python_dir.rglob(name))
        if matches:
            return matches[0]
    raise FileNotFoundError(
        f"Unable to find bundled Python under {bundle_python_dir}"
    )


def expected_python_executable_path(
    bundle_python_dir: Path,
    target_platform: str,
) -> Path:
    """Return the expected staged Python interpreter path for one target."""
    if target_platform == "windows":
        return bundle_python_dir / "python.exe"
    return bundle_python_dir / "bin" / "python"


def build_file_record(bundle_root: Path, path: Path) -> dict[str, str | int]:
    """Return one relative-path metadata record for a bundle file."""
    return {
        "path": relative_manifest_path(bundle_root, path),
        "sha256": file_sha256(path),
        "size_bytes": path.stat().st_size,
    }


def build_bundle_metadata(
    bundle_root: Path,
    spec: BundleSpec,
    runtime: EmbeddedPythonRuntime,
    version: str,
    paths: BundlePaths,
    python_executable: Path,
) -> dict[str, object]:
    """Return the JSON metadata structure written into one bundle."""
    return {
        "airunner_version": version,
        "bundle_name": spec.bundle_name,
        "install_extra": spec.install_extra,
        "target_platform": spec.target_platform,
        "launcher": build_file_record(bundle_root, paths.launcher_path),
        "python": {
            "asset_name": runtime.asset_name,
            "download_url": runtime.download_url,
            "executable": relative_manifest_path(bundle_root, python_executable),
            "release_tag": runtime.release_tag,
            "version": runtime.version,
        },
        "runtime_manifest": relative_manifest_path(bundle_root, paths.manifest_path),
        "sidecars": {
            "llama_server": build_file_record(
                bundle_root,
                paths.llama_server_path,
            ),
            "whisper_server": build_file_record(
                bundle_root,
                paths.whisper_server_path,
            ),
        },
    }


def parse_args(argv: list[str]) -> BuildConfig:
    """Parse CLI arguments into a normalized bundle build config."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target-platform",
        choices=["linux", "windows"],
        required=True,
    )
    parser.add_argument("--bundle-name", default="desktop")
    parser.add_argument("--install-extra")
    parser.add_argument("--launcher-binary", required=True)
    parser.add_argument("--sidecar-root", required=True)
    parser.add_argument("--output-root", default="build/end-user-bundles")
    parser.add_argument("--dist-root", default="dist")
    parser.add_argument("--work-root", default="build/end-user-bundle-work")
    parser.add_argument("--clean", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    repo_root = Path(__file__).resolve().parents[3]
    spec = build_bundle_spec(
        args.target_platform,
        bundle_name=args.bundle_name,
        install_extra=args.install_extra,
    )
    return BuildConfig(
        repo_root=repo_root,
        spec=spec,
        launcher_binary=Path(args.launcher_binary).expanduser().resolve(),
        sidecar_root=Path(args.sidecar_root).expanduser().resolve(),
        output_root=(repo_root / args.output_root).resolve(),
        dist_root=(repo_root / args.dist_root).resolve(),
        work_root=(repo_root / args.work_root).resolve(),
        clean=args.clean,
        dry_run=args.dry_run,
    )


def main(argv: list[str] | None = None) -> int:
    """Build one AIRunner end-user bundle and print the archive path."""
    config = parse_args(argv or sys.argv[1:])
    archive_path = BundleBuilder(config).build()
    print(archive_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())