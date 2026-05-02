import os
import time
from pathlib import Path

from airunner.utils.download_temp_cleanup import (
    cleanup_stale_download_dir,
    cleanup_stale_download_dirs,
)


def _set_tree_mtime(path: Path, timestamp: float) -> None:
    for current_root, dirnames, filenames in os.walk(path):
        current_path = Path(current_root)
        os.utime(current_path, (timestamp, timestamp))

        for dirname in dirnames:
            os.utime(current_path / dirname, (timestamp, timestamp))

        for filename in filenames:
            os.utime(current_path / filename, (timestamp, timestamp))


def test_cleanup_stale_download_dir_removes_old_directory(tmp_path: Path):
    temp_dir = tmp_path / "model" / ".downloading"
    temp_dir.mkdir(parents=True)
    (temp_dir / "partial.bin").write_bytes(b"abc")

    old_timestamp = time.time() - (48 * 60 * 60)
    _set_tree_mtime(temp_dir, old_timestamp)

    removed = cleanup_stale_download_dir(temp_dir, max_age_seconds=60 * 60)

    assert removed is True
    assert not temp_dir.exists()


def test_cleanup_stale_download_dir_keeps_recent_directory(tmp_path: Path):
    temp_dir = tmp_path / "model" / ".downloading"
    temp_dir.mkdir(parents=True)
    (temp_dir / "partial.bin").write_bytes(b"abc")

    removed = cleanup_stale_download_dir(temp_dir, max_age_seconds=48 * 60 * 60)

    assert removed is False
    assert temp_dir.exists()


def test_cleanup_stale_download_dirs_removes_only_stale_entries(tmp_path: Path):
    stale_dir = tmp_path / "art" / "models" / "Z-Image Turbo" / "txt2img" / ".downloading"
    fresh_dir = tmp_path / "text" / "models" / "llm" / "demo" / ".downloading"

    stale_dir.mkdir(parents=True)
    fresh_dir.mkdir(parents=True)
    (stale_dir / "old.part").write_bytes(b"old")
    (fresh_dir / "new.part").write_bytes(b"new")

    old_timestamp = time.time() - (72 * 60 * 60)
    _set_tree_mtime(stale_dir, old_timestamp)

    removed = cleanup_stale_download_dirs(tmp_path, max_age_seconds=2 * 60 * 60)

    assert stale_dir in removed
    assert not stale_dir.exists()
    assert fresh_dir.exists()