"""Unit tests for the shard tensor estimator helper.

_estimate_shard_tensors was extracted to keep
estimate_quantized_component within the long-function threshold.
These tests pin the quantizable classification, the index/header
mismatch error, and the byte math with synthetic shards.
"""

import json
import struct
from pathlib import Path

import pytest

from airunner_services.art.managers.zimage.zimage_resource_budget import (
    _estimate_shard_tensors,
)


def _write_shard(tmp_path, header, payload_len):
    encoded = json.dumps(header).encode()
    payload = b"x" * payload_len
    path = tmp_path / "s.safetensors"
    path.write_bytes(struct.pack("<Q", len(encoded)) + encoded + payload)
    return path


def test_quantizable_weight_uses_factor(tmp_path):
    header = {
        "w.weight": {"dtype": "F32", "shape": [4, 4], "data_offsets": [0, 64]},
    }
    shard = _write_shard(tmp_path, header, 64)
    weight_map = {"w.weight": "s.safetensors"}
    source, estimated, count = _estimate_shard_tensors(
        shard, "s.safetensors", weight_map, 0.5, None
    )
    assert source == 64
    assert estimated == 8  # 16 params * 0.5 bytes
    assert count == 1


def test_embedding_excluded_from_quantization(tmp_path):
    header = {
        "embed_tokens.weight": {"dtype": "F32", "shape": [4, 4], "data_offsets": [0, 64]},
    }
    shard = _write_shard(tmp_path, header, 64)
    weight_map = {"embed_tokens.weight": "s.safetensors"}
    _, estimated, _ = _estimate_shard_tensors(
        shard, "s.safetensors", weight_map, 0.5, None
    )
    assert estimated == 64  # source dtype bytes, not quantized


def test_non_rank_two_weight_not_quantized(tmp_path):
    header = {
        "bias.weight": {"dtype": "F32", "shape": [16], "data_offsets": [0, 64]},
    }
    shard = _write_shard(tmp_path, header, 64)
    weight_map = {"bias.weight": "s.safetensors"}
    _, estimated, _ = _estimate_shard_tensors(
        shard, "s.safetensors", weight_map, 0.5, None
    )
    assert estimated == 64


def test_without_factor_uses_source_bytes(tmp_path):
    header = {
        "w.weight": {"dtype": "F32", "shape": [4, 4], "data_offsets": [0, 64]},
    }
    shard = _write_shard(tmp_path, header, 64)
    weight_map = {"w.weight": "s.safetensors"}
    _, estimated, _ = _estimate_shard_tensors(
        shard, "s.safetensors", weight_map, None, None
    )
    assert estimated == 64


def test_target_dtype_override_applies_to_floats(tmp_path):
    header = {
        "head": {"dtype": "F32", "shape": [4], "data_offsets": [0, 16]},
    }
    shard = _write_shard(tmp_path, header, 16)
    weight_map = {"head": "s.safetensors"}
    _, estimated, _ = _estimate_shard_tensors(
        shard, "s.safetensors", weight_map, None, 2
    )
    assert estimated == 8  # 4 elems * 2 bytes


def test_index_mismatch_raises(tmp_path):
    header = {
        "a": {"dtype": "F32", "shape": [1], "data_offsets": [0, 4]},
    }
    shard = _write_shard(tmp_path, header, 4)
    weight_map = {"other": "s.safetensors"}
    with pytest.raises(ValueError, match="index/header mismatch"):
        _estimate_shard_tensors(shard, "s.safetensors", weight_map, None, None)
