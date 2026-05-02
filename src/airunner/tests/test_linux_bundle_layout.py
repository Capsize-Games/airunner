"""Tests for Linux bundle layout interpreter resolution."""

from pathlib import Path

from airunner.linux_bundle_layout import build_linux_bundle_layout


def test_build_linux_bundle_layout_preserves_symlinked_venv_python(
    tmp_path: Path,
) -> None:
    """Symlinked venv/bin/python should remain the chosen interpreter path."""
    bundle_root = tmp_path / "bundle"
    venv_bin = bundle_root / "venv" / "bin"
    venv_bin.mkdir(parents=True)
    system_python = tmp_path / "python3.13"
    system_python.write_text("#!/bin/sh\n", encoding="utf-8")
    system_python.chmod(0o755)
    (venv_bin / "python").symlink_to(system_python)

    layout = build_linux_bundle_layout(bundle_root=bundle_root)

    assert layout.bundle_root == bundle_root.resolve()
    assert layout.python_executable == venv_bin / "python"
    assert layout.bin_dir == venv_bin