"""Unit tests for the E5 model-identity extraction helpers.

_inventory_model_files, _verify_reviewed_metadata, and
_hash_runtime_files were extracted to keep
verify_e5_model_directory within the long-function threshold. These
tests pin the symlink/missing/unexpected rejections and the hash
binding with synthetic directories.
"""

import hashlib
from pathlib import Path

import pytest

from airunner_services.runtimes.e5_model_identity import (
    E5ModelIdentityError,
    _hash_runtime_files,
    _inventory_model_files,
    _verify_reviewed_metadata,
)


def _entry(tmp_path, name, content=b"data"):
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def _expectations(tmp_path, names):
    out = {}
    for name in names:
        data = (tmp_path / name).read_bytes()
        out[name] = (len(data), hashlib.sha256(data).hexdigest())
    return out


def test_inventory_happy_path_returns_files(tmp_path):
    _entry(tmp_path, "a.bin")
    required = _expectations(tmp_path, ["a.bin"])
    assert _inventory_model_files(tmp_path, required, {}) == {"a.bin"}


def test_inventory_rejects_symlink(tmp_path):
    target = _entry(tmp_path, "real.bin")
    (tmp_path / "link.bin").symlink_to(target)
    required = _expectations(tmp_path, ["real.bin", "link.bin"])
    with pytest.raises(E5ModelIdentityError, match="symlink is not allowed"):
        _inventory_model_files(tmp_path, required, {})


def test_inventory_rejects_missing_required(tmp_path):
    required = {"gone.bin": (0, "x")}
    with pytest.raises(E5ModelIdentityError, match="required E5 files are missing"):
        _inventory_model_files(tmp_path, required, {})


def test_inventory_rejects_unexpected_file(tmp_path):
    _entry(tmp_path, "a.bin")
    _entry(tmp_path, "stray.txt")
    required = _expectations(tmp_path, ["a.bin"])
    with pytest.raises(E5ModelIdentityError, match="unexpected E5 files"):
        _inventory_model_files(tmp_path, required, {})


def test_hash_runtime_files_binds_digests(tmp_path):
    _entry(tmp_path, "a.bin", b"one")
    _entry(tmp_path, "b.bin", b"two")
    required = _expectations(tmp_path, ["a.bin", "b.bin"])
    hashed = _hash_runtime_files(tmp_path, required, {}, set(required))
    assert [name for name, _ in hashed] == ["a.bin", "b.bin"]
    assert hashed[0][1] == required["a.bin"][1]


def test_hash_runtime_files_rejects_tampered_size(tmp_path):
    _entry(tmp_path, "a.bin", b"one")
    required = {"a.bin": (99, "deadbeef")}
    with pytest.raises(E5ModelIdentityError, match="size mismatch"):
        _hash_runtime_files(tmp_path, required, {}, {"a.bin"})


def test_verify_reviewed_metadata_noop_when_absent(tmp_path):
    _verify_reviewed_metadata(tmp_path, set())


def test_hash_skips_absent_optional(tmp_path):
    _entry(tmp_path, "a.bin", b"one")
    required = _expectations(tmp_path, ["a.bin"])
    optional = {"opt.bin": (3, "x")}
    hashed = _hash_runtime_files(tmp_path, required, optional, {"a.bin"})
    assert [name for name, _ in hashed] == ["a.bin"]
