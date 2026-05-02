"""Unit tests for AIRunner bundle layout helpers."""

from pathlib import Path

from airunner.distribution.bundle_layout import build_bundle_paths
from airunner.distribution.bundle_layout import build_bundle_spec
from airunner.distribution.bundle_layout import build_runtime_manifest
from airunner.distribution.bundle_layout import bundle_archive_name
from airunner.distribution.bundle_layout import file_sha256
from airunner.distribution.bundle_layout import relative_manifest_path
from airunner.distribution.python_runtime_pins import get_embedded_python_runtime


def test_get_embedded_python_runtime_linux() -> None:
    """Linux bundle pins should target the pinned standalone runtime."""
    runtime = get_embedded_python_runtime("linux")
    assert runtime.version == "3.13.13"
    assert runtime.asset_name.endswith("x86_64-unknown-linux-gnu-install_only.tar.gz")
    assert runtime.download_url.endswith(runtime.asset_name)


def test_get_embedded_python_runtime_windows() -> None:
    """Windows bundle pins should target the pinned standalone runtime."""
    runtime = get_embedded_python_runtime("windows")
    assert runtime.version == "3.13.13"
    assert runtime.asset_name.endswith("x86_64-pc-windows-msvc-install_only.tar.gz")
    assert runtime.download_url.endswith(runtime.asset_name)


def test_build_bundle_paths_linux(tmp_path: Path) -> None:
    """Linux bundle paths should land under the staged bundle root."""
    spec = build_bundle_spec("linux")
    paths = build_bundle_paths(tmp_path / "bundle", spec)
    assert paths.launcher_path == tmp_path / "bundle" / "bin" / "airunner"
    assert paths.desktop_entry_path == (
        tmp_path / "bundle" / "share" / "applications" / "airunner.desktop"
    )


def test_runtime_manifest_uses_relative_bundle_paths(tmp_path: Path) -> None:
    """Runtime manifest values should stay relative to the manifest file."""
    spec = build_bundle_spec("linux")
    paths = build_bundle_paths(tmp_path / "bundle", spec)
    python_executable = paths.python_dir / "bin" / "python"
    manifest = build_runtime_manifest(paths, python_executable)
    assert manifest["AIRUNNER_BUNDLE_ROOT"] == "../.."
    assert manifest["AIRUNNER_PYTHON"] == "../../python/bin/python"
    assert manifest["AIRUNNER_PYTHONPATH"] == "../../app/site-packages"
    assert manifest["AIRUNNER_LLAMA_SERVER_BIN"] == "../../bin/llama-server"


def test_bundle_archive_name_changes_by_platform() -> None:
    """Bundle archive naming should follow the platform convention."""
    linux_spec = build_bundle_spec("linux")
    windows_spec = build_bundle_spec("windows")
    assert bundle_archive_name("5.6.1", linux_spec).endswith(".tar.gz")
    assert bundle_archive_name("5.6.1", windows_spec).endswith(".zip")


def test_relative_manifest_path_normalizes_separators(tmp_path: Path) -> None:
    """Manifest paths should always use forward slashes."""
    base_dir = tmp_path / "share" / "airunner"
    target_path = tmp_path / "python" / "bin" / "python"
    assert relative_manifest_path(base_dir, target_path) == "../../python/bin/python"


def test_file_sha256_reads_binary_content(tmp_path: Path) -> None:
    """SHA256 helper should hash the file contents exactly once."""
    sample = tmp_path / "sample.bin"
    sample.write_bytes(b"airunner")
    assert file_sha256(sample) == (
        "bec75f0f47784269ffbf2965827d5d66f959aec9748457f7e08056d615cac4a9"
    )