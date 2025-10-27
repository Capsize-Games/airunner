"""Pytest configuration for LLM component tests.

Provides cleanup to prevent resource leaks and hangs when running
multiple tests together.
"""

import gc
import pytest


@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Clean up resources after each test to prevent hangs.

    LlamaIndex, embeddings, and other AI libraries can leak resources
    (threads, CUDA memory, file handles) between tests. This fixture
    ensures cleanup happens after each test.
    """
    yield

    # Force garbage collection to clean up any lingering objects
    gc.collect()

    # Try to clean up CUDA cache if torch is loaded
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except (ImportError, AttributeError):
        pass


@pytest.fixture(scope="module", autouse=True)
def cleanup_after_module():
    """Clean up resources after each test module.

    More aggressive cleanup between test modules to prevent
    resource accumulation.
    """
    yield

    # Force garbage collection
    gc.collect()

    # Clear CUDA cache
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
    except (ImportError, AttributeError):
        pass
