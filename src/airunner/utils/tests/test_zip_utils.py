from pathlib import Path
import re
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


def test_no_direct_extractall_usage_outside_zip_utils():
    repo_root = Path(__file__).resolve().parents[4]
    src_root = repo_root / "src"
    assert src_root.exists(), f"Expected src/ at {src_root}"

    extractall_re = re.compile(r"\bextractall\s*\(")
    offenders: list[str] = []

    for py_file in src_root.rglob("*.py"):
        rel = py_file.relative_to(repo_root).as_posix()
        if "/tests/" in rel or rel.endswith("/conftest.py") or rel.startswith("src/airunner/dev/"):
            continue
        if rel == "src/airunner/utils/zip_utils.py":
            continue
        try:
            text = py_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if extractall_re.search(text):
            offenders.append(rel)

    assert offenders == [], f"Direct extractall() usage found: {offenders}"
