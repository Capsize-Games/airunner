"""Dependency-free startup environment helpers for AIRunner entrypoints."""

from __future__ import annotations

import os


CUDA_MALLOC_ASYNC_ALLOCATOR = "backend:cudaMallocAsync"


def configure_early_torch_allocator_environment() -> None:
    """Set allocator env vars before any torch import occurs.

    The headless service copy additionally set ``TOKENIZERS_PARALLELISM``;
    that flag is safe and desirable for every entrypoint, so it is included
    here in the canonical implementation.
    """
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
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
