"""Unit tests for the safetensors header validation helpers.

The helpers were extracted to keep _read_validated_safetensors_header
within the long-function threshold. These tests pin each validation
rule with synthetic shards instead of real model files.
"""

import json
import struct
from pathlib import Path

import pytest

from airunner_services.art.managers.zimage.zimage_resource_budget import (
    _read_safetensors_header_json,
    _read_validated_safetensors_header,
    _validate_tensor_layout,
    _validate_tensor_spec,
)


def _write_shard(path: Path, header: dict, payload: bytes) -> Path:
    encoded = json.dumps(header).encode()
    path.write_bytes(struct.pack("<Q", len(encoded)) + encoded + payload)
    return path


def _shard(header, payload_len=0):
    return _write_shard(
        Path("/tmp/test_shard.safetensors"), header, b"x" * payload_len
    )


def test_validate_tensor_spec_happy_path():
    spec = {"dtype": "F32", "shape": [2, 2], "data_offsets": [0, 16]}
    got = _validate_tensor_spec(Path("s"), "t", spec, 16)
    assert got == ("t", "F32", [2, 2], 0, 16)


def test_validate_tensor_spec_rejects_bad_dtype():
    spec = {"dtype": "NOPE", "shape": [1], "data_offsets": [0, 4]}
    with pytest.raises(ValueError, match="Invalid tensor header"):
        _validate_tensor_spec(Path("s"), "t", spec, 4)


def test_validate_tensor_spec_rejects_size_mismatch():
    spec = {"dtype": "F32", "shape": [4], "data_offsets": [0, 8]}
    with pytest.raises(ValueError, match="byte-size mismatch"):
        _validate_tensor_spec(Path("s"), "t", spec, 16)


def test_validate_tensor_spec_rejects_non_dict_spec():
    with pytest.raises(ValueError, match="Invalid tensor header entry"):
        _validate_tensor_spec(Path("s"), "t", "not-a-dict", 0)


def test_validate_tensor_layout_happy_path():
    tensors = [("a", "F32", [1], 0, 4), ("b", "F32", [1], 4, 8)]
    _validate_tensor_layout(Path("s"), tensors, 8)


def test_validate_tensor_layout_rejects_gap():
    tensors = [("a", "F32", [1], 0, 4), ("b", "F32", [1], 6, 10)]
    with pytest.raises(ValueError, match="payload layout"):
        _validate_tensor_layout(Path("s"), tensors, 10)


def test_read_header_json_roundtrip(tmp_path):
    header = {"__metadata__": {}, "t": {"dtype": "F32", "shape": [1], "data_offsets": [0, 4]}}
    shard = _write_shard(tmp_path / "s.safetensors", header, b"1234")
    parsed, payload_bytes = _read_safetensors_header_json(shard)
    assert parsed["t"]["dtype"] == "F32"
    assert payload_bytes == 4


def test_read_header_json_rejects_truncated_size(tmp_path):
    shard = tmp_path / "s.safetensors"
    shard.write_bytes(struct.pack("<Q", 9999) + b"short")
    with pytest.raises(ValueError, match="Truncated safetensors header"):
        _read_safetensors_header_json(shard)


def test_read_validated_header_end_to_end(tmp_path):
    header = {
        "__metadata__": {"format": "test"},
        "a": {"dtype": "F32", "shape": [1], "data_offsets": [0, 4]},
        "b": {"dtype": "F16", "shape": [2], "data_offsets": [4, 8]},
    }
    shard = _write_shard(tmp_path / "s.safetensors", header, b"12345678")
    tensors = _read_validated_safetensors_header(shard)
    assert tensors == [("a", "F32", [1], 4), ("b", "F16", [2], 4)]


def test_read_validated_header_rejects_bad_metadata_object(tmp_path):
    shard = _write_shard(tmp_path / "s.safetensors", [1, 2], b"")
    with pytest.raises(ValueError, match="Invalid safetensors header object"):
        _read_validated_safetensors_header(shard)
