import torch
from safetensors.torch import save_file

from airunner.components.art.managers.zimage.native.zimage_text_encoder import (
    _resolve_transformers_weights_override,
)


def test_prefers_sharded_index_for_nonstandard_merged_metadata(tmp_path):
    model_dir = tmp_path / "text_encoder"
    model_dir.mkdir()

    save_file(
        {"weight": torch.zeros(1)},
        str(model_dir / "model.safetensors"),
        metadata={"merged_from": "model.safetensors.index.json"},
    )
    (model_dir / "model.safetensors.index.json").write_text("{}")

    assert (
        _resolve_transformers_weights_override(str(model_dir))
        == "model.safetensors.index.json"
    )


def test_keeps_single_file_when_metadata_is_transformers_compatible(tmp_path):
    model_dir = tmp_path / "text_encoder"
    model_dir.mkdir()

    save_file(
        {"weight": torch.zeros(1)},
        str(model_dir / "model.safetensors"),
        metadata={"format": "pt"},
    )
    (model_dir / "model.safetensors.index.json").write_text("{}")

    assert _resolve_transformers_weights_override(str(model_dir)) is None


def test_returns_none_without_sharded_index(tmp_path):
    model_dir = tmp_path / "text_encoder"
    model_dir.mkdir()

    save_file(
        {"weight": torch.zeros(1)},
        str(model_dir / "model.safetensors"),
        metadata={"merged_from": "model.safetensors.index.json"},
    )

    assert _resolve_transformers_weights_override(str(model_dir)) is None