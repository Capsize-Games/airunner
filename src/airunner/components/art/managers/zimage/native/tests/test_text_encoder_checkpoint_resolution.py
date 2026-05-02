from unittest.mock import MagicMock, patch

import torch
from safetensors.torch import save_file

from airunner.components.art.managers.zimage.native.zimage_text_encoder import (
    ZImageTextEncoder,
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


def test_8bit_cpu_offload_sets_bitsandbytes_flag():
    with patch(
        "airunner.components.art.managers.zimage.native.zimage_text_encoder.AutoConfig.from_pretrained",
        return_value=MagicMock(),
    ), patch(
        "airunner.components.art.managers.zimage.native.zimage_text_encoder.AutoModel.from_pretrained",
        return_value=MagicMock(),
    ) as mock_model, patch(
        "airunner.components.art.managers.zimage.native.zimage_text_encoder.ZImageTokenizer",
        return_value=MagicMock(),
    ):
        ZImageTextEncoder(
            model_path="text-encoder",
            tokenizer_path="tokenizer",
            quantization="8bit",
            device_map="auto",
            max_memory={0: "1GiB", "cpu": "32GiB"},
            enable_cpu_offload=True,
        )

    quantization_config = mock_model.call_args.kwargs["quantization_config"]
    assert quantization_config.load_in_8bit is True
    assert quantization_config.llm_int8_enable_fp32_cpu_offload is True