"""Service-owned torch runtime flag helpers."""

try:
    import torch
except ImportError:
    torch = None


def apply_cudnn_benchmark(memory_settings) -> None:
    """Apply the persisted cuDNN benchmark preference when possible."""
    if torch is None or not hasattr(torch, "backends"):
        return

    enabled = bool(getattr(memory_settings, "use_cudnn_benchmark", True))
    try:
        torch.backends.cudnn.benchmark = enabled and torch.cuda.is_available()
    except Exception:
        return


__all__ = ["apply_cudnn_benchmark"]