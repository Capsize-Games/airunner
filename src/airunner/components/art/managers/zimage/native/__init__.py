"""
Native Z-Image implementation without diffusers dependency.

This module provides a ComfyUI-compatible implementation of the Z-Image
model that supports FP8 scaled checkpoints with minimal memory usage.
"""

from airunner.components.art.managers.zimage.native.fp8_ops import (
    QuantizedTensor,
    TensorCoreFP8Layout,
    FP8Linear,
    load_fp8_state_dict_entry,
    is_fp8_scaled_checkpoint,
)
from airunner.components.art.managers.zimage.native.nextdit_model import (
    NextDiT,
    ZIMAGE_CONFIG,
    create_zimage_transformer,
)
from airunner.components.art.managers.zimage.native.flow_match_scheduler import (
    FlowMatchEulerScheduler,
    FlowMatchHeunScheduler,
)
from airunner.components.art.managers.zimage.native.attention import (
    JointAttention,
    RMSNorm,
    optimized_attention,
    optimized_attention_masked,
)
from airunner.components.art.managers.zimage.native.feedforward import (
    FeedForward,
)
from airunner.components.art.managers.zimage.native.transformer_block import (
    JointTransformerBlock,
    FinalLayer,
)
from airunner.components.art.managers.zimage.native.embedders import (
    TimestepEmbedder,
    EmbedND,
    apply_rope,
)
from airunner.components.art.managers.zimage.native.zimage_text_encoder import (
    ZImageTextEncoder,
    ZImageTokenizer,
    SimpleTextEncoder,
)
from airunner.components.art.managers.zimage.native.zimage_native_pipeline import (
    ZImageNativePipeline,
)
from airunner.components.art.managers.zimage.native.zimage_native_wrapper import (
    NativePipelineWrapper,
)
from airunner.components.art.managers.zimage.native.native_lora import (
    NativeLoraLoader,
    load_lora_into_transformer,
    load_lora_state_dict,
)

__all__ = [
    # FP8 Operations
    "QuantizedTensor",
    "TensorCoreFP8Layout",
    "FP8Linear",
    "load_fp8_state_dict_entry",
    "is_fp8_scaled_checkpoint",
    # Model
    "NextDiT",
    "ZIMAGE_CONFIG",
    "create_zimage_transformer",
    # Scheduler
    "FlowMatchEulerScheduler",
    "FlowMatchHeunScheduler",
    # Attention
    "JointAttention",
    "RMSNorm",
    "optimized_attention",
    "optimized_attention_masked",
    # Feedforward
    "FeedForward",
    # Transformer Block
    "JointTransformerBlock",
    "FinalLayer",
    # Embedders
    "TimestepEmbedder",
    "EmbedND",
    "apply_rope",
    # Text Encoder
    "ZImageTextEncoder",
    "ZImageTokenizer",
    "SimpleTextEncoder",
    # Pipeline
    "ZImageNativePipeline",
    "NativePipelineWrapper",
    # LoRA
    "NativeLoraLoader",
    "load_lora_into_transformer",
    "load_lora_state_dict",
]
