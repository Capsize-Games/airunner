"""Tests for shared torch runtime flag helpers."""

from types import SimpleNamespace

from airunner.utils.memory.runtime_flags import apply_cudnn_benchmark


def test_apply_cudnn_benchmark_uses_persisted_setting(monkeypatch):
    import airunner.utils.memory.runtime_flags as runtime_flags

    previous = runtime_flags.torch.backends.cudnn.benchmark
    monkeypatch.setattr(runtime_flags.torch.cuda, "is_available", lambda: True)

    try:
        apply_cudnn_benchmark(
            SimpleNamespace(use_cudnn_benchmark=False)
        )
        assert runtime_flags.torch.backends.cudnn.benchmark is False

        apply_cudnn_benchmark(
            SimpleNamespace(use_cudnn_benchmark=True)
        )
        assert runtime_flags.torch.backends.cudnn.benchmark is True
    finally:
        runtime_flags.torch.backends.cudnn.benchmark = previous