"""
Unit tests for airunner.utils.memory.clear_memory
Covers all code paths, including import errors and fallback logic.
"""

import pytest
from unittest.mock import patch
from airunner.utils.memory.clear_memory import clear_memory


def test_clear_memory_with_torch():
    with patch("airunner.utils.memory.clear_memory.torch") as torch_mock:
        torch_mock.cuda.is_available.return_value = True
        clear_memory(device=0)
        torch_mock.cuda.set_device.assert_called_once_with(0)
        torch_mock.cuda.empty_cache.assert_called_once()
        torch_mock.cuda.reset_max_memory_allocated.assert_called_once_with(
            device=0
        )
        torch_mock.cuda.reset_max_memory_cached.assert_called_once_with(
            device=0
        )
        torch_mock.cuda.synchronize.assert_called_once_with(device=0)


def test_clear_memory_no_torch(monkeypatch):
    # Simulate torch not available
    with patch("airunner.utils.memory.clear_memory.torch", None):
        # Should not raise
        clear_memory(device=0)


def test_clear_memory_runtimeerror(capfd):
    import importlib

    clear_memory_mod = importlib.import_module(
        "airunner.utils.memory.clear_memory"
    )

    class DummyCuda:
        def is_available(self):
            return True

        def set_device(self, device):
            pass

        def empty_cache(self):
            raise RuntimeError("fail")

        def reset_max_memory_allocated(self, device):
            pass

        def reset_max_memory_cached(self, device):
            pass

        def synchronize(self, device):
            pass

    old_torch = getattr(clear_memory_mod, "torch", None)
    clear_memory_mod.torch = type("DummyTorch", (), {"cuda": DummyCuda()})()
    try:
        clear_memory_mod.clear_memory()
        out, err = capfd.readouterr()
        assert (
            "Failed to clear memory" in out or "Failed to clear memory" in err
        )
    finally:
        if old_torch is not None:
            clear_memory_mod.torch = old_torch
        else:
            delattr(clear_memory_mod, "torch")
