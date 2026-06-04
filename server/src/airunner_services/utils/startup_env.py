"""Service-owned startup environment helpers."""

from __future__ import annotations

import os


CUDA_MALLOC_ASYNC_ALLOCATOR = "backend:cudaMallocAsync"


def configure_early_torch_allocator_environment() -> None:
    """Set PyTorch allocator env vars before any torch import occurs."""
    os.environ.setdefault(
        "PYTORCH_ALLOC_CONF",
        CUDA_MALLOC_ASYNC_ALLOCATOR,
    )
    os.environ.setdefault(
        "PYTORCH_CUDA_ALLOC_CONF",
        os.environ["PYTORCH_ALLOC_CONF"],
    )


__all__ = [
    "CUDA_MALLOC_ASYNC_ALLOCATOR",
    "configure_early_torch_allocator_environment",
]
