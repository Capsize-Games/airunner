"""
FP8 Quantized Tensor Operations for Z-Image.

This module provides FP8 scaled weight handling compatible with ComfyUI's
checkpoint format. It implements a QuantizedTensor class that stores weights
in FP8 format with per-layer scale values for accurate dequantization.

Based on ComfyUI's comfy/quant_ops.py implementation.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)

# Registry for layout-specific operation handlers
_LAYOUT_REGISTRY: Dict[Any, Dict[str, Any]] = {}
_GENERIC_UTILS: Dict[Any, Any] = {}


def register_layout_op(torch_op: Any, layout_type: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator to register a layout-specific operation handler.
    
    Args:
        torch_op: PyTorch operation (e.g., torch.ops.aten.linear.default)
        layout_type: Layout type string (e.g., "TensorCoreFP8Layout")
    """
    def decorator(handler_func: Callable[..., Any]) -> Callable[..., Any]:
        """Register a handler function for a specific op/layout.

        Args:
            handler_func: The function that handles this op for the layout.

        Returns:
            The original handler function (unchanged).
        """
        if torch_op not in _LAYOUT_REGISTRY:
            _LAYOUT_REGISTRY[torch_op] = {}
        _LAYOUT_REGISTRY[torch_op][layout_type] = handler_func
        return handler_func
    return decorator


def register_generic_util(torch_op: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator to register a generic utility that works for all layouts.
    
    Args:
        torch_op: PyTorch operation (e.g., torch.ops.aten.detach.default)
    """
    def decorator(handler_func: Callable[..., Any]) -> Callable[..., Any]:
        """Register a generic utility handler for all layouts.

        Args:
            handler_func: The utility function to register.

        Returns:
            The original handler function.
        """
        _GENERIC_UTILS[torch_op] = handler_func
        return handler_func
    return decorator


def _get_layout_from_args(args: tuple) -> Optional[str]:
    """Extract layout type from operation arguments."""
    for arg in args:
        if isinstance(arg, QuantizedTensor):
            return arg._layout_type
        elif isinstance(arg, (list, tuple)):
            for item in arg:
                if isinstance(item, QuantizedTensor):
                    return item._layout_type
    return None


def _move_layout_params_to_device(
    params: Dict[str, Any], device: torch.device
) -> Dict[str, Any]:
    """Move layout parameters to target device."""
    new_params = {}
    for k, v in params.items():
        if isinstance(v, torch.Tensor):
            new_params[k] = v.to(device=device)
        else:
            new_params[k] = v
    return new_params


def _copy_layout_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """Create a copy of layout parameters."""
    new_params = {}
    for k, v in params.items():
        if isinstance(v, torch.Tensor):
            new_params[k] = v.clone()
        else:
            new_params[k] = v
    return new_params


class TensorCoreFP8Layout:
    """
    FP8 tensor layout for TensorCore operations.
    
    Storage format:
    - qdata: FP8 tensor (torch.float8_e4m3fn)
    - scale: Scalar tensor (float32) for dequantization
    - orig_dtype: Original dtype before quantization
    """
    
    @classmethod
    def quantize(
        cls,
        tensor: torch.Tensor,
        scale: Optional[torch.Tensor] = None,
        dtype: torch.dtype = torch.float8_e4m3fn,
        stochastic_rounding: int = 0,
        inplace_ops: bool = False,
    ) -> Tuple[torch.Tensor, Dict[str, Any]]:
        """
        Quantize a tensor to FP8 format.
        
        Args:
            tensor: Input tensor to quantize
            scale: Optional scale factor (computed if not provided)
            dtype: FP8 dtype (default: torch.float8_e4m3fn)
            stochastic_rounding: Seed for stochastic rounding (0 = disabled)
            inplace_ops: Whether to modify tensor in-place
            
        Returns:
            Tuple of (quantized_tensor, layout_params)
        """
        orig_dtype = tensor.dtype
        
        if isinstance(scale, str) and scale == "recalculate":
            scale = torch.amax(tensor.abs()) / torch.finfo(dtype).max
        
        if scale is not None:
            if not isinstance(scale, torch.Tensor):
                scale = torch.tensor(scale)
            scale = scale.to(device=tensor.device, dtype=torch.float32)
            
            if inplace_ops:
                tensor *= (1.0 / scale).to(tensor.dtype)
            else:
                tensor = tensor * (1.0 / scale).to(tensor.dtype)
        else:
            scale = torch.ones((), device=tensor.device, dtype=torch.float32)
        
        # Clamp to FP8 range and convert
        lp_amax = torch.finfo(dtype).max
        tensor = torch.clamp(tensor, min=-lp_amax, max=lp_amax)
        tensor = tensor.to(dtype, memory_format=torch.contiguous_format)
        
        layout_params = {
            'scale': scale,
            'orig_dtype': orig_dtype
        }
        return tensor, layout_params
    
    @staticmethod
    def dequantize(
        qdata: torch.Tensor,
        scale: torch.Tensor,
        orig_dtype: torch.dtype,
        **kwargs
    ) -> torch.Tensor:
        """
        Dequantize FP8 tensor back to original dtype.
        
        Args:
            qdata: FP8 quantized data
            scale: Scale factor for dequantization
            orig_dtype: Target dtype for output
            
        Returns:
            Dequantized tensor
        """
        plain_tensor = qdata.to(orig_dtype)
        # Ensure scale is in correct dtype to avoid type promotion
        scale_typed = scale.to(orig_dtype)
        plain_tensor = plain_tensor * scale_typed
        return plain_tensor
    
    @classmethod
    def get_plain_tensors(
        cls, qtensor: 'QuantizedTensor'
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """Get raw data and scale from a QuantizedTensor."""
        return qtensor._qdata, qtensor._layout_params['scale']


# Layout registry
LAYOUTS = {
    "TensorCoreFP8Layout": TensorCoreFP8Layout,
}


class QuantizedTensor(torch.Tensor):
    """
    Universal quantized tensor that supports FP8 scaled weights.
    
    This tensor subclass uses a pluggable layout system to support
    quantized formats while maintaining PyTorch compatibility.
    
    Attributes:
        _qdata: The quantized tensor data (FP8)
        _layout_type: Layout type string
        _layout_params: Dict with layout-specific params (scale, orig_dtype)
    """
    
    @staticmethod
    def __new__(
        cls,
        qdata: torch.Tensor,
        layout_type: str,
        layout_params: Dict[str, Any]
    ) -> 'QuantizedTensor':
        """Create a quantized tensor wrapper."""
        return torch.Tensor._make_wrapper_subclass(
            cls,
            qdata.shape,
            device=qdata.device,
            dtype=qdata.dtype,
            requires_grad=False
        )
    
    def __init__(
        self,
        qdata: torch.Tensor,
        layout_type: str,
        layout_params: Dict[str, Any]
    ):
        """
        Initialize the quantized tensor.
        
        Args:
            qdata: The quantized data tensor
            layout_type: Layout type string
            layout_params: Dictionary with layout-specific parameters
        """
        self._qdata = qdata
        self._layout_type = layout_type
        self._layout_params = layout_params
    
    def __repr__(self) -> str:
        layout_name = self._layout_type
        param_str = ", ".join(
            f"{k}={v}" for k, v in list(self._layout_params.items())[:2]
        )
        return f"QuantizedTensor(shape={self.shape}, layout={layout_name}, {param_str})"
    
    @property
    def layout_type(self) -> str:
        """Get the layout type."""
        return self._layout_type
    
    def __tensor_flatten__(self) -> Tuple[list, dict]:
        """
        Tensor flattening protocol for proper device movement.
        """
        inner_tensors = ["_qdata"]
        ctx = {
            "layout_type": self._layout_type,
        }
        
        tensor_params = {}
        non_tensor_params = {}
        for k, v in self._layout_params.items():
            if isinstance(v, torch.Tensor):
                tensor_params[k] = v
            else:
                non_tensor_params[k] = v
        
        ctx["tensor_param_keys"] = list(tensor_params.keys())
        ctx["non_tensor_params"] = non_tensor_params
        
        for k, v in tensor_params.items():
            attr_name = f"_layout_param_{k}"
            object.__setattr__(self, attr_name, v)
            inner_tensors.append(attr_name)
        
        return inner_tensors, ctx
    
    @staticmethod
    def __tensor_unflatten__(
        inner_tensors: dict,
        ctx: dict,
        outer_size: tuple,
        outer_stride: tuple
    ) -> 'QuantizedTensor':
        """
        Tensor unflattening protocol for proper device movement.
        """
        layout_type = ctx["layout_type"]
        layout_params = dict(ctx["non_tensor_params"])
        
        for key in ctx["tensor_param_keys"]:
            attr_name = f"_layout_param_{key}"
            layout_params[key] = inner_tensors[attr_name]
        
        return QuantizedTensor(inner_tensors["_qdata"], layout_type, layout_params)
    
    @classmethod
    def from_float(
        cls,
        tensor: torch.Tensor,
        layout_type: str,
        **quantize_kwargs
    ) -> 'QuantizedTensor':
        """
        Create a quantized tensor from a float tensor.
        
        Args:
            tensor: Input float tensor
            layout_type: Target layout type
            **quantize_kwargs: Additional arguments for quantization
            
        Returns:
            QuantizedTensor instance
        """
        qdata, layout_params = LAYOUTS[layout_type].quantize(
            tensor, **quantize_kwargs
        )
        return cls(qdata, layout_type, layout_params)
    
    @classmethod
    def from_fp8_with_scale(
        cls,
        fp8_tensor: torch.Tensor,
        scale: torch.Tensor,
        orig_dtype: torch.dtype = torch.bfloat16
    ) -> 'QuantizedTensor':
        """
        Create a quantized tensor from pre-quantized FP8 data with scale.
        
        This is the primary method for loading ComfyUI FP8 checkpoints.
        
        Args:
            fp8_tensor: Pre-quantized FP8 tensor
            scale: Per-layer scale factor
            orig_dtype: Original dtype for dequantization
            
        Returns:
            QuantizedTensor instance
        """
        layout_params = {
            'scale': scale,
            'orig_dtype': orig_dtype
        }
        return cls(fp8_tensor, "TensorCoreFP8Layout", layout_params)
    
    def dequantize(self) -> torch.Tensor:
        """
        Dequantize the tensor back to original dtype.
        
        Returns:
            Dequantized float tensor
        """
        return LAYOUTS[self._layout_type].dequantize(
            self._qdata, **self._layout_params
        )
    
    @classmethod
    def __torch_dispatch__(cls, func, types, args=(), kwargs=None):
        """
        PyTorch dispatch hook for automatic dequantization.
        
        This handles operations on QuantizedTensors by either:
        1. Using a registered handler for the operation
        2. Falling back to dequantization
        """
        kwargs = kwargs or {}
        
        # Check generic utilities first (detach, clone, to, etc.)
        if func in _GENERIC_UTILS:
            return _GENERIC_UTILS[func](func, args, kwargs)
        
        # Check layout-specific handlers (linear, matmul, etc.)
        layout_type = _get_layout_from_args(args)
        if layout_type and func in _LAYOUT_REGISTRY:
            handler = _LAYOUT_REGISTRY[func].get(layout_type)
            if handler:
                return handler(func, args, kwargs)
        
        # Fallback to dequantization
        if isinstance(args[0] if args else None, QuantizedTensor):
            logger.debug(
                f"QuantizedTensor: Unhandled op {func}, falling back to dequant"
            )
        return cls._dequant_and_fallback(func, args, kwargs)
    
    @classmethod
    def _dequant_and_fallback(cls, func: Callable, args: tuple, kwargs: dict) -> Any:
        """Dequantize all quantized tensors and run the operation."""
        def dequant_arg(arg: Any) -> Any:
            """Recursively dequantizes QuantizedTensor instances in nested structures.

            Args:
                arg: The argument to dequantize.

            Returns:
                The same structure with QuantizedTensor objects converted to tensors.
            """
            if isinstance(arg, QuantizedTensor):
                return arg.dequantize()
            elif isinstance(arg, (list, tuple)):
                return type(arg)(dequant_arg(a) for a in arg)
            return arg
        
        new_args = dequant_arg(args)
        new_kwargs = dequant_arg(kwargs)
        return func(*new_args, **new_kwargs)
    
    def data_ptr(self) -> int:
        """Get raw data pointer."""
        return self._qdata.data_ptr()
    
    def is_pinned(self) -> bool:
        """Check if tensor is pinned."""
        return self._qdata.is_pinned()
    
    def is_contiguous(self, *arg: Any, **kwargs: Any) -> bool:
        """Check if tensor is contiguous."""
        return self._qdata.is_contiguous(*arg, **kwargs)
    
    def storage(self) -> Any:
        """Get tensor storage."""
        return self._qdata.storage()


# =============================================================================
# Generic Utilities (Layout-Agnostic Operations)
# =============================================================================

@register_generic_util(torch.ops.aten.detach.default)
def generic_detach(func: Callable, args: tuple, kwargs: dict) -> Any:
    """Detach operation - creates a detached copy."""
    qt = args[0]
    if isinstance(qt, QuantizedTensor):
        new_qdata = qt._qdata.detach()
        new_params = _copy_layout_params(qt._layout_params)
        return QuantizedTensor(new_qdata, qt._layout_type, new_params)
    return func(*args, **kwargs)


@register_generic_util(torch.ops.aten.clone.default)
def generic_clone(func: Callable, args: tuple, kwargs: dict) -> Any:
    """Clone operation - creates a deep copy."""
    qt = args[0]
    if isinstance(qt, QuantizedTensor):
        new_qdata = qt._qdata.clone()
        new_params = _copy_layout_params(qt._layout_params)
        return QuantizedTensor(new_qdata, qt._layout_type, new_params)
    return func(*args, **kwargs)


@register_generic_util(torch.ops.aten._to_copy.default)
def generic_to_copy(func: Callable, args: tuple, kwargs: dict) -> Any:
    """Device/dtype transfer operation."""
    qt = args[0]
    if isinstance(qt, QuantizedTensor):
        target_device = kwargs.get('device', None)
        target_dtype = kwargs.get('dtype', None)
        
        if target_device is not None:
            new_qdata = qt._qdata.to(device=target_device)
            new_params = _move_layout_params_to_device(
                qt._layout_params, target_device
            )
            if target_dtype is not None:
                new_params["orig_dtype"] = target_dtype
            return QuantizedTensor(new_qdata, qt._layout_type, new_params)
    return func(*args, **kwargs)


@register_generic_util(torch.ops.aten.to.dtype_layout)
def generic_to_dtype_layout(func: Callable, args: tuple, kwargs: dict) -> Any:
    """Handle .to(device) calls using dtype_layout variant."""
    qt = args[0]
    if isinstance(qt, QuantizedTensor):
        target_device = kwargs.get('device', None)
        target_dtype = kwargs.get('dtype', None)
        
        if target_device is not None:
            new_qdata = qt._qdata.to(device=target_device)
            new_params = _move_layout_params_to_device(
                qt._layout_params, target_device
            )
            if target_dtype is not None:
                new_params["orig_dtype"] = target_dtype
            return QuantizedTensor(new_qdata, qt._layout_type, new_params)
    return func(*args, **kwargs)


# =============================================================================
# FP8 Layout-Specific Operations
# =============================================================================

@register_layout_op(torch.ops.aten.linear.default, "TensorCoreFP8Layout")
def fp8_linear(func: Callable, args: tuple, kwargs: dict) -> Any:
    """
    FP8-optimized linear operation.
    
    Uses torch._scaled_mm for TensorCore-accelerated FP8 matmul when possible.
    """
    input_tensor = args[0]
    weight = args[1]
    bias = args[2] if len(args) > 2 else None
    
    if isinstance(input_tensor, QuantizedTensor) and isinstance(weight, QuantizedTensor):
        plain_input, scale_a = TensorCoreFP8Layout.get_plain_tensors(input_tensor)
        plain_weight, scale_b = TensorCoreFP8Layout.get_plain_tensors(weight)
        
        out_dtype = kwargs.get("out_dtype")
        if out_dtype is None:
            out_dtype = input_tensor._layout_params['orig_dtype']
        
        weight_t = plain_weight.t()
        
        tensor_2d = False
        if len(plain_input.shape) == 2:
            tensor_2d = True
            plain_input = plain_input.unsqueeze(1)
        
        input_shape = plain_input.shape
        if len(input_shape) != 3:
            # Fall back to dequantization for non-standard shapes
            return None
        
        try:
            output = torch._scaled_mm(
                plain_input.reshape(-1, input_shape[2]).contiguous(),
                weight_t,
                bias=bias,
                scale_a=scale_a,
                scale_b=scale_b,
                out_dtype=out_dtype,
            )
            
            if isinstance(output, tuple):  # Torch 2.4 compatibility
                output = output[0]
            
            if not tensor_2d:
                output = output.reshape((-1, input_shape[1], weight.shape[0]))
            
            return output
            
        except Exception as e:
            logger.warning(f"FP8 _scaled_mm failed: {e}, falling back to dequant")
    
    # Fallback: dequantize and run regular linear
    if isinstance(weight, QuantizedTensor):
        weight = weight.dequantize()
    if isinstance(input_tensor, QuantizedTensor):
        input_tensor = input_tensor.dequantize()
    
    return F.linear(input_tensor, weight, bias)


@register_layout_op(torch.ops.aten.mm.default, "TensorCoreFP8Layout")
def fp8_mm(func: Callable, args: tuple, kwargs: dict) -> Any:
    """FP8-optimized matrix multiplication."""
    input_tensor = args[0]
    weight = args[1]
    
    if isinstance(input_tensor, QuantizedTensor) and isinstance(weight, QuantizedTensor):
        plain_input, scale_a = TensorCoreFP8Layout.get_plain_tensors(input_tensor)
        plain_weight, scale_b = TensorCoreFP8Layout.get_plain_tensors(weight)
        
        out_dtype = input_tensor._layout_params['orig_dtype']
        
        try:
            output = torch._scaled_mm(
                plain_input.contiguous(),
                plain_weight,
                bias=None,
                scale_a=scale_a,
                scale_b=scale_b,
                out_dtype=out_dtype,
            )
            
            if isinstance(output, tuple):
                output = output[0]
            return output
            
        except Exception as e:
            logger.warning(f"FP8 mm failed: {e}, falling back to dequant")
    
    # Fallback
    a = list(args)
    if isinstance(args[0], QuantizedTensor):
        a[0] = args[0].dequantize()
    if isinstance(args[1], QuantizedTensor):
        a[1] = args[1].dequantize()
    return func(*a, **kwargs)


@register_layout_op(torch.ops.aten.t.default, "TensorCoreFP8Layout")
def fp8_transpose(func: Callable, args: tuple, kwargs: dict) -> Any:
    """Transpose operation for FP8 tensors."""
    input_tensor = args[0]
    if isinstance(input_tensor, QuantizedTensor):
        new_qdata = input_tensor._qdata.t()
        return QuantizedTensor(
            new_qdata,
            input_tensor._layout_type,
            input_tensor._layout_params
        )
    return func(*args, **kwargs)


@register_layout_op(torch.ops.aten.view.default, "TensorCoreFP8Layout")
def fp8_view(func: Callable, args: tuple, kwargs: dict) -> Any:
    """View operation for FP8 tensors."""
    input_tensor = args[0]
    if isinstance(input_tensor, QuantizedTensor):
        new_shape = args[1] if len(args) > 1 else kwargs.get('size')
        new_qdata = input_tensor._qdata.view(*new_shape) if isinstance(new_shape, (list, tuple)) else input_tensor._qdata.view(new_shape)
        return QuantizedTensor(
            new_qdata,
            input_tensor._layout_type,
            input_tensor._layout_params
        )
    return func(*args, **kwargs)


# =============================================================================
# FP8 Linear Layer
# =============================================================================

class FP8Linear(nn.Module):
    """
    Linear layer that supports FP8 quantized weights.
    
    This layer can hold FP8 weights with per-layer scale factors and
    automatically dequantizes during forward pass for compatibility.
    
    The FP8 weight is stored as `fp8_weight_storage` to avoid nn.Module's
    special handling of 'weight'. Access via `.weight` property is provided
    for compatibility with LoRA loaders.
    """
    
    def __init__(
        self,
        in_features: int,
        out_features: int,
        bias: bool = True,
        device: Optional[torch.device] = None,
        dtype: Optional[torch.dtype] = None,
        compute_dtype: Optional[torch.dtype] = None,
    ):
        """
        Initialize FP8 linear layer.
        
        Args:
            in_features: Input feature dimension
            out_features: Output feature dimension  
            bias: Whether to include bias
            device: Target device
            dtype: Compute dtype (for activations) - deprecated, use compute_dtype
            compute_dtype: Compute dtype (for activations)
        """
        super().__init__()
        
        self.in_features = in_features
        self.out_features = out_features
        self.compute_dtype = compute_dtype or dtype or torch.bfloat16
        
        # Use unique name to avoid nn.Module intercepting 'weight'
        self.fp8_weight_storage: Optional[QuantizedTensor] = None
        self._has_bias = bias
        # Optional merged weight for LoRA (set by native_lora._merge_fp8_linear_weights)
        self._merged_weight: Optional[torch.Tensor] = None
        
        if bias:
            self.register_buffer(
                '_bias',
                torch.zeros(out_features, device=device, dtype=self.compute_dtype)
            )
    
    @property
    def weight(self) -> Optional[QuantizedTensor]:
        """Get the FP8 quantized weight (for LoRA compatibility)."""
        return self.fp8_weight_storage
    
    @weight.setter
    def weight(self, value: Optional[QuantizedTensor]):
        """Set the FP8 quantized weight."""
        self.fp8_weight_storage = value
    
    @property
    def bias(self) -> Optional[torch.Tensor]:
        """Get bias tensor."""
        return self._bias if self._has_bias and hasattr(self, '_bias') else None
    
    @bias.setter  
    def bias(self, value: Optional[torch.Tensor]):
        """Set bias tensor."""
        if value is not None and self._has_bias:
            if hasattr(self, '_bias'):
                self._bias.copy_(value)
            else:
                self.register_buffer('_bias', value)
    
    def set_fp8_weight(
        self,
        fp8_weight: torch.Tensor,
        scale: torch.Tensor,
        orig_dtype: torch.dtype = torch.bfloat16
    ):
        """
        Set the FP8 quantized weight with scale.
        
        Args:
            fp8_weight: FP8 tensor (torch.float8_e4m3fn)
            scale: Per-layer scale factor
            orig_dtype: Original dtype for dequantization
        """
        self.fp8_weight_storage = QuantizedTensor.from_fp8_with_scale(
            fp8_weight, scale, orig_dtype
        )
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass with automatic FP8 handling.
        
        Args:
            x: Input tensor
            
        Returns:
            Output tensor
        """
        if self.fp8_weight_storage is None:
            raise RuntimeError("Weight not set. Call set_fp8_weight first.")
        
        # If a LoRA merge has been staged, prefer it; otherwise dequantize FP8 weight
        if self._merged_weight is not None:
            weight = self._merged_weight.to(x.dtype)
        else:
            weight = self.fp8_weight_storage.dequantize().to(x.dtype)
        
        bias = self._bias if self._has_bias and hasattr(self, '_bias') else None
        if bias is not None:
            bias = bias.to(x.dtype)
        
        return F.linear(x, weight, bias)


# =============================================================================
# Checkpoint Loading Utilities
# =============================================================================

class UnscaledFP8Linear(nn.Module):
    """
    Linear layer that stores weights in FP8 format without scale factors.
    
    Weights are stored as FP8 (8 bits per param = ~50% memory savings).
    During forward pass, weights are cast to compute dtype on-the-fly.
    This is memory efficient - FP8 weights stay FP8 until needed.
    
    LoRA support: LoRA weights (A and B matrices) are stored separately
    and applied additively during forward pass. This allows enabling/disabling
    LoRA without reloading the base model. Memory overhead is minimal since
    LoRA matrices are small (rank << hidden_dim).
    """
    
    def __init__(
        self,
        in_features: int,
        out_features: int,
        bias: bool = True,
        device: Optional[torch.device] = None,
        compute_dtype: torch.dtype = torch.bfloat16,
    ):
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.compute_dtype = compute_dtype
        self._has_bias = bias
        
        # Register FP8 weight as buffer (not parameter) to avoid grad issues
        self.register_buffer('fp8_weight', None)
        if bias:
            self.register_buffer('bias', torch.zeros(out_features, device=device, dtype=compute_dtype))
        else:
            self.register_buffer('bias', None)
        
        # Additive LoRA storage - stored separately, applied during forward
        # Dict[adapter_name] -> {"down": Tensor, "up": Tensor, "alpha": float, "scale": float, "enabled": bool}
        self._lora_layers: Dict[str, Dict[str, Any]] = {}
    
    def set_weight(self, fp8_weight: torch.Tensor, bias: Optional[torch.Tensor] = None):
        """Set the FP8 weight tensor."""
        self.fp8_weight = fp8_weight
        if bias is not None and self._has_bias:
            self.bias = bias.to(self.compute_dtype)
    
    def add_lora(
        self,
        adapter_name: str,
        down_weight: torch.Tensor,
        up_weight: torch.Tensor,
        alpha: Optional[float] = None,
        scale: float = 1.0,
    ) -> None:
        """Add LoRA weights to this layer (non-destructive).
        
        LoRA weights are stored separately and applied during forward pass.
        This allows toggling LoRA on/off without reloading the model.
        
        Args:
            adapter_name: Unique name for this LoRA adapter
            down_weight: LoRA down/A weight [rank, in_features]
            up_weight: LoRA up/B weight [out_features, rank]
            alpha: LoRA alpha (defaults to rank if not provided)
            scale: LoRA scale factor (0.0-1.0+)
        """
        rank = down_weight.shape[0]
        if alpha is None:
            alpha = float(rank)
        
        # Store on same device as base weight, keep in compute dtype for efficiency
        device = self.fp8_weight.device if self.fp8_weight is not None else down_weight.device
        self._lora_layers[adapter_name] = {
            "down": down_weight.to(device=device, dtype=self.compute_dtype),
            "up": up_weight.to(device=device, dtype=self.compute_dtype),
            "alpha": alpha,
            "rank": rank,
            "scale": scale,
            "enabled": True,
        }
    
    def remove_lora(self, adapter_name: str) -> bool:
        """Remove a LoRA adapter from this layer.
        
        Args:
            adapter_name: Name of the adapter to remove
            
        Returns:
            True if removed, False if not found
        """
        if adapter_name in self._lora_layers:
            del self._lora_layers[adapter_name]
            return True
        return False
    
    def remove_all_loras(self) -> int:
        """Remove all LoRA adapters from this layer.
        
        Returns:
            Number of adapters removed
        """
        count = len(self._lora_layers)
        self._lora_layers.clear()
        return count
    
    def set_lora_enabled(self, adapter_name: str, enabled: bool) -> bool:
        """Enable or disable a specific LoRA adapter.
        
        Args:
            adapter_name: Name of the adapter
            enabled: Whether to enable or disable
            
        Returns:
            True if found and updated, False if not found
        """
        if adapter_name in self._lora_layers:
            self._lora_layers[adapter_name]["enabled"] = enabled
            return True
        return False
    
    def set_all_loras_enabled(self, enabled: bool) -> None:
        """Enable or disable all LoRA adapters."""
        for lora_data in self._lora_layers.values():
            lora_data["enabled"] = enabled
    
    def set_lora_scale(self, adapter_name: str, scale: float) -> bool:
        """Set the scale for a specific LoRA adapter.
        
        Args:
            adapter_name: Name of the adapter
            scale: New scale value
            
        Returns:
            True if found and updated, False if not found
        """
        if adapter_name in self._lora_layers:
            self._lora_layers[adapter_name]["scale"] = scale
            return True
        return False
    
    def get_lora_names(self) -> List[str]:
        """Get names of all loaded LoRA adapters."""
        return list(self._lora_layers.keys())
    
    def has_lora(self, adapter_name: str) -> bool:
        """Check if a LoRA adapter is loaded."""
        return adapter_name in self._lora_layers
    
    def _compute_lora_delta(self) -> Optional[torch.Tensor]:
        """Compute the combined LoRA delta from all enabled adapters.
        
        Returns:
            Combined delta tensor or None if no enabled LoRAs
        """
        if not self._lora_layers:
            return None
        
        delta = None
        for adapter_name, lora_data in self._lora_layers.items():
            if not lora_data["enabled"]:
                continue
            
            down = lora_data["down"]
            up = lora_data["up"]
            alpha = lora_data["alpha"]
            rank = lora_data["rank"]
            scale = lora_data["scale"]
            
            # LoRA formula: delta = scale * (alpha/rank) * (up @ down)
            lora_scale = scale * (alpha / rank)
            adapter_delta = lora_scale * (up @ down)
            
            if delta is None:
                delta = adapter_delta
            else:
                delta = delta + adapter_delta
        
        return delta
    
    # Legacy method for backwards compatibility - now uses additive approach
    def merge_lora_weight(self, merged_weight: torch.Tensor):
        """Legacy method - prefer add_lora() for non-destructive LoRA.
        
        This method is kept for backwards compatibility but now logs a warning.
        """
        logger.warning(
            "merge_lora_weight() is deprecated. Use add_lora() for non-destructive LoRA."
        )
        # Convert merged weight back to FP8
        lp_amax = torch.finfo(torch.float8_e4m3fn).max
        clamped = torch.clamp(merged_weight, min=-lp_amax, max=lp_amax)
        self.fp8_weight = clamped.to(torch.float8_e4m3fn)
    
    def get_dequantized_weight(self) -> torch.Tensor:
        """Get the weight as compute dtype tensor."""
        return self.fp8_weight.to(self.compute_dtype)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward with on-the-fly FP8 -> compute_dtype conversion and LoRA.
        
        LoRA is applied additively: output = x @ (W + delta).T + bias
        This is mathematically equivalent to: output = x @ W.T + x @ delta.T + bias
        """
        # Cast FP8 weight to compute dtype
        weight = self.fp8_weight.to(self.compute_dtype)
        
        # Apply LoRA delta if any enabled adapters exist
        lora_delta = self._compute_lora_delta()
        if lora_delta is not None:
            weight = weight + lora_delta
        
        return F.linear(x, weight, self.bias)
    
    def extra_repr(self) -> str:
        """Return a short textual description for module debugging.

        Includes basic shape and LoRA counts for quick inspection in debug logs.
        """
        lora_count = len(self._lora_layers)
        enabled_count = sum(1 for l in self._lora_layers.values() if l["enabled"])
        lora_str = f", loras={enabled_count}/{lora_count}" if lora_count > 0 else ""
        return f'in={self.in_features}, out={self.out_features}, fp8=True{lora_str}'


def load_fp8_state_dict_entry(
    tensor: torch.Tensor,
    scale_tensor: Optional[torch.Tensor],
    target_dtype: torch.dtype = torch.bfloat16
) -> torch.Tensor | QuantizedTensor:
    """
    Load a tensor from FP8 checkpoint, handling scale if present.
    
    Args:
        tensor: The weight tensor (may be FP8 or float)
        scale_tensor: Optional scale tensor for FP8 weights
        target_dtype: Target dtype if not FP8
        
    Returns:
        QuantizedTensor if FP8 with scale, else regular tensor
    """
    if tensor.dtype == torch.float8_e4m3fn and scale_tensor is not None:
        return QuantizedTensor.from_fp8_with_scale(
            tensor, scale_tensor, target_dtype
        )
    elif tensor.dtype == torch.float8_e4m3fn:
        # FP8 without scale - convert directly
        return tensor.to(target_dtype)
    else:
        return tensor.to(target_dtype)


def is_fp8_scaled_checkpoint(state_dict: Dict[str, torch.Tensor]) -> bool:
    """
    Check if a state dict is from an FP8 scaled checkpoint.
    
    Args:
        state_dict: Model state dictionary
        
    Returns:
        True if checkpoint contains FP8 scaled weights
    """
    has_fp8 = False
    has_scale = False
    
    for key, tensor in state_dict.items():
        if tensor.dtype == torch.float8_e4m3fn:
            has_fp8 = True
        if 'scale_weight' in key:
            has_scale = True
        if has_fp8 and has_scale:
            return True
    
    return has_fp8 and has_scale
