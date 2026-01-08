from pathlib import Path
import zipfile

import pytest

from airunner.utils.zip_utils import UnsafeZipPathError, safe_extract_zip


def test_safe_extract_zip_blocks_path_traversal(tmp_path: Path):
    zip_path = tmp_path / "bad.zip"
    with zipfile.ZipFile(zip_path, "w") as z:
        z.writestr("../evil.txt", "pwnd")

    with zipfile.ZipFile(zip_path, "r") as z:
        with pytest.raises(UnsafeZipPathError):
            safe_extract_zip(z, tmp_path / "out")


def test_safe_extract_zip_allows_normal_paths(tmp_path: Path):
    zip_path = tmp_path / "ok.zip"
    with zipfile.ZipFile(zip_path, "w") as z:
        z.writestr("dir/file.txt", "hello")

    out_dir = tmp_path / "out"
    with zipfile.ZipFile(zip_path, "r") as z:
        safe_extract_zip(z, out_dir)

    assert (out_dir / "dir" / "file.txt").read_text() == "hello"
