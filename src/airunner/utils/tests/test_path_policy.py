"""Unit tests for local path policy helpers."""

import pytest

from airunner.utils.path_policy import (
    PathPolicyError,
    normalize_local_path,
    resolve_existing_directory,
    resolve_existing_file,
)


def test_normalize_local_path_rejects_remote_uri():
    with pytest.raises(PathPolicyError):
        normalize_local_path(
            "https://example.com/file.txt",
            label="Test path",
        )


def test_resolve_existing_file_enforces_approved_roots(tmp_path):
    allowed_root = tmp_path / "allowed"
    allowed_root.mkdir()
    inside_file = allowed_root / "inside.txt"
    inside_file.write_text("ok")
    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("no")

    resolved = resolve_existing_file(
        str(inside_file),
        allowed_roots=(str(allowed_root),),
    )

    assert resolved == str(inside_file.resolve())
    with pytest.raises(PathPolicyError):
        resolve_existing_file(
            str(outside_file),
            allowed_roots=(str(allowed_root),),
        )


def test_resolve_existing_directory_enforces_approved_roots(tmp_path):
    allowed_root = tmp_path / "allowed"
    allowed_root.mkdir()
    inside_dir = allowed_root / "inside"
    inside_dir.mkdir()
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()

    resolved = resolve_existing_directory(
        str(inside_dir),
        allowed_roots=(str(allowed_root),),
    )

    assert resolved == str(inside_dir.resolve())
    with pytest.raises(PathPolicyError):
        resolve_existing_directory(
            str(outside_dir),
            allowed_roots=(str(allowed_root),),
        )