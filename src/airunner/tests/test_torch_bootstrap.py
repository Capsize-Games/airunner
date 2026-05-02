"""Tests for early PyTorch allocator bootstrap behavior."""

from __future__ import annotations

import importlib
import os

import airunner_startup_env


def test_configure_early_torch_allocator_environment_sets_defaults(
    monkeypatch,
) -> None:
    """Default allocator env should be present before any torch import."""
    monkeypatch.delenv("PYTORCH_ALLOC_CONF", raising=False)
    monkeypatch.delenv("PYTORCH_CUDA_ALLOC_CONF", raising=False)

    airunner_startup_env.configure_early_torch_allocator_environment()

    assert os.environ["PYTORCH_ALLOC_CONF"] == "backend:cudaMallocAsync"
    assert os.environ["PYTORCH_CUDA_ALLOC_CONF"] == "backend:cudaMallocAsync"


def test_configure_early_torch_allocator_environment_preserves_existing_value(
    monkeypatch,
) -> None:
    """Existing allocator selections should not be overwritten."""
    monkeypatch.setenv("PYTORCH_ALLOC_CONF", "backend:native")
    monkeypatch.delenv("PYTORCH_CUDA_ALLOC_CONF", raising=False)

    airunner_startup_env.configure_early_torch_allocator_environment()

    assert os.environ["PYTORCH_ALLOC_CONF"] == "backend:native"
    assert os.environ["PYTORCH_CUDA_ALLOC_CONF"] == "backend:native"


def test_airunner_package_import_bootstraps_allocator_env(
    monkeypatch,
) -> None:
    """Importing the AIRunner package should establish allocator env vars."""
    monkeypatch.delenv("PYTORCH_ALLOC_CONF", raising=False)
    monkeypatch.delenv("PYTORCH_CUDA_ALLOC_CONF", raising=False)

    import airunner

    importlib.reload(airunner)

    assert os.environ["PYTORCH_ALLOC_CONF"] == "backend:cudaMallocAsync"
    assert os.environ["PYTORCH_CUDA_ALLOC_CONF"] == "backend:cudaMallocAsync"