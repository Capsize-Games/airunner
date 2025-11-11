"""
GGUF operations for quantized model loading.

Based on stable-diffusion-webui-forge's implementation with adaptations for Airunner.
Provides ParameterGGUF wrapper for lazy dequantization of GGUF tensors.
"""

import torch
import gguf
from typing import Optional


# Mapping from GGUF quantization types to gguf Python package classes
QUANTS_MAPPING = {
    gguf.GGMLQuantizationType.Q2_K: gguf.Q2_K,
    gguf.GGMLQuantizationType.Q3_K: gguf.Q3_K,
    gguf.GGMLQuantizationType.Q4_0: gguf.Q4_0,
    gguf.GGMLQuantizationType.Q4_K: gguf.Q4_K,
    gguf.GGMLQuantizationType.Q4_1: gguf.Q4_1,
    gguf.GGMLQuantizationType.Q5_0: gguf.Q5_0,
    gguf.GGMLQuantizationType.Q5_1: gguf.Q5_1,
    gguf.GGMLQuantizationType.Q5_K: gguf.Q5_K,
    gguf.GGMLQuantizationType.Q6_K: gguf.Q6_K,
    gguf.GGMLQuantizationType.Q8_0: gguf.Q8_0,
    gguf.GGMLQuantizationType.BF16: gguf.BF16,
}


class ParameterGGUF(torch.nn.Parameter):
    """
    Torch Parameter subclass that wraps GGUF quantized tensors.

    Stores quantization metadata and provides lazy dequantization via baking.
    The parameter stays in quantized form until explicitly baked, reducing
    memory usage during model loading.

    Attributes:
        gguf_cls: Quantization class from gguf package (Q4_K, Q8_0, etc.)
        real_shape: Actual shape of the unquantized tensor
        computation_dtype: Target dtype for computation (default: torch.float16)
        baked: Whether the tensor has been dequantized

    Example:
        >>> reader = gguf.GGUFReader("model.gguf")
        >>> for tensor in reader.tensors:
        ...     param = ParameterGGUF(tensor)
        ...     # Later, before inference:
        ...     param.gguf_cls.bake(param)  # Dequantize in-place
    """

    def __init__(
        self, tensor=None, requires_grad: bool = False, no_init: bool = False
    ):
        """
        Initialize GGUF parameter wrapper.

        Args:
            tensor: GGUF tensor from GGUFReader
            requires_grad: Whether parameter requires gradients (always False for inference)
            no_init: Skip initialization (for internal use)
        """
        super().__init__()
        if no_init:
            return

        self.gguf_cls = QUANTS_MAPPING.get(tensor.tensor_type, None)
        # GGUF stores shapes in reverse order
        self.real_shape = torch.Size(reversed(list(tensor.shape)))
        self.computation_dtype = torch.float16
        self.baked = False

    @property
    def shape(self) -> torch.Size:
        """Return the actual unquantized shape (not the quantized data shape)."""
        return self.real_shape

    def __new__(
        cls, tensor=None, requires_grad: bool = False, no_init: bool = False
    ):
        """
        Create new Parameter instance with quantized tensor data.

        This is called before __init__ to create the actual torch.Tensor storage.
        """
        return super().__new__(
            cls,
            (
                torch.tensor(tensor.data)
                if tensor is not None
                else torch.tensor([])
            ),
            requires_grad=requires_grad,
        )

    def dequantize_as_pytorch_parameter(self) -> torch.nn.Parameter:
        """
        Explicitly dequantize and return as standard Parameter.

        This is an alternative to in-place baking when you need a fresh Parameter.

        Returns:
            Standard torch.nn.Parameter with dequantized data
        """
        if self.gguf_cls is not None:
            self.gguf_cls.bake(self)
        return torch.nn.Parameter(dequantize_tensor(self), requires_grad=False)

    def copy_with_data(self, data: torch.Tensor) -> "ParameterGGUF":
        """
        Create a copy with different data but same metadata.

        Used when moving tensors between devices.

        Args:
            data: New tensor data

        Returns:
            New ParameterGGUF with copied metadata
        """
        new = ParameterGGUF(no_init=True)
        new.data = data
        new.gguf_cls = self.gguf_cls
        new.real_shape = self.real_shape
        new.computation_dtype = self.computation_dtype
        new.baked = self.baked
        return new

    def to(self, *args, **kwargs) -> "ParameterGGUF":
        """
        Move tensor to device/dtype, preserving GGUF metadata.

        Overrides torch.Tensor.to() to maintain ParameterGGUF type.
        """
        return self.copy_with_data(self.data.to(*args, **kwargs))

    def pin_memory(self, device=None) -> "ParameterGGUF":
        """Pin memory for faster CPU->GPU transfer, preserving metadata."""
        return self.copy_with_data(
            torch.Tensor.pin_memory(self, device=device)
        )


def dequantize_tensor(tensor: torch.Tensor) -> torch.Tensor:
    """
    Dequantize a tensor if it's a ParameterGGUF, otherwise return as-is.

    Args:
        tensor: Input tensor (may be ParameterGGUF or regular Tensor)

    Returns:
        Dequantized tensor or original tensor
    """
    if tensor is None:
        return None

    if not hasattr(tensor, "gguf_cls"):
        return tensor

    gguf_cls = tensor.gguf_cls

    if gguf_cls is None:
        return tensor

    return gguf_cls.dequantize_pytorch(tensor)


def state_dict_dtype(state_dict: dict) -> str:
    """
    Detect the dtype/quantization of a state dict.

    Checks for GGUF, BitsAndBytes quantization, or standard dtypes.

    Args:
        state_dict: Model state dictionary

    Returns:
        String identifier: 'gguf', 'nf4', 'fp4', or torch dtype
    """
    for k, v in state_dict.items():
        if hasattr(v, "gguf_cls"):
            return "gguf"
        if "bitsandbytes__nf4" in k:
            return "nf4"
        if "bitsandbytes__fp4" in k:
            return "fp4"

    # Count dtypes to find most common
    dtype_counts = {}
    for tensor in state_dict.values():
        dtype = tensor.dtype
        dtype_counts[dtype] = dtype_counts.get(dtype, 0) + 1

    if not dtype_counts:
        return torch.float32

    return max(dtype_counts, key=dtype_counts.get)


def bake_gguf_model(model: torch.nn.Module) -> torch.nn.Module:
    """
    Dequantize all GGUF parameters in a model in-place.

    This should be called once after model loading and before inference.
    After baking, parameters are standard torch tensors at computation_dtype.

    Args:
        model: PyTorch model with potentially quantized parameters

    Returns:
        Same model (modified in-place) for chaining

    Example:
        >>> model = load_flux_transformer(state_dict)
        >>> bake_gguf_model(model)  # Dequantize before inference
        >>> output = model(input_latents)
    """
    # Skip if already baked
    if getattr(model, "gguf_baked", False):
        return model

    # Dequantize each GGUF parameter
    for p in model.parameters():
        gguf_cls = getattr(p, "gguf_cls", None)
        if gguf_cls is not None:
            gguf_cls.bake(p)

    # Mark as baked to avoid redundant work
    model.gguf_baked = True
    return model


def load_gguf_state_dict(
    path: str, device: Optional[torch.device] = None
) -> dict:
    """
    Load a GGUF file into a state dict with ParameterGGUF wrappers.

    Args:
        path: Path to .gguf file
        device: Target device (default: CPU)

    Returns:
        State dict with ParameterGGUF tensors

    Example:
        >>> state_dict = load_gguf_state_dict("flux_q4_k_s.gguf")
        >>> model.load_state_dict(state_dict, strict=False)
        >>> bake_gguf_model(model)
    """
    if device is None:
        device = torch.device("cpu")

    reader = gguf.GGUFReader(path)
    state_dict = {}

    for tensor in reader.tensors:
        tensor_name = str(tensor.name)
        state_dict[tensor_name] = ParameterGGUF(tensor)

    return state_dict


def print_gguf_stats(state_dict: dict) -> None:
    """
    Print statistics about GGUF quantization in a state dict.

    Useful for debugging and understanding memory usage.

    Args:
        state_dict: State dict potentially containing GGUF parameters
    """
    quant_counts = {}
    total_params = 0
    gguf_params = 0

    for k, v in state_dict.items():
        if hasattr(v, "gguf_cls") and v.gguf_cls is not None:
            quant_type = v.gguf_cls.__name__
            quant_counts[quant_type] = quant_counts.get(quant_type, 0) + 1
            gguf_params += v.real_shape.numel()
        total_params += v.numel() if hasattr(v, "numel") else 0

    if gguf_params > 0:
        print(f"\n=== GGUF Quantization Statistics ===")
        print(f"Total parameters: {total_params:,}")
        print(
            f"GGUF parameters: {gguf_params:,} ({gguf_params/total_params*100:.1f}%)"
        )
        print(f"\nQuantization types:")
        for qtype, count in sorted(quant_counts.items()):
            print(f"  {qtype}: {count} tensors")
        print(f"=====================================\n")
