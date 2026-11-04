from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from airunner_services.art.managers.stablediffusion.mixins.sd_memory_management_mixin import (
    SDMemoryManagementMixin,
)


class _Manager(SDMemoryManagementMixin):
    def __init__(self) -> None:
        self._pipe = SimpleNamespace(unet=object())
        self.logger = Mock()
        self._torch_compile_original_unet = None
        self._torch_compile_owner_pipe = None
        self._torch_compile_compiled_unet = None
        self._memory_settings_flags = {}
        self.torch_compile_applied = False
        self.torch_compile_status = "disabled"


def test_compile_preflight_failure_keeps_eager_unet(monkeypatch) -> None:
    import torch
    from airunner_services.art import triton_runtime

    manager = _Manager()
    eager = manager._pipe.unet
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(
        triton_runtime,
        "ensure_available",
        lambda: (False, "external CUDA tools are missing"),
    )

    assert manager._apply_torch_compile(True) is False
    assert manager._pipe.unet is eager
    assert manager.torch_compile_applied is False
    assert "external CUDA tools are missing" in manager.torch_compile_status
    assert (
        manager._memory_settings_flags["torch_compile_status"]
        == manager.torch_compile_status
    )
    manager.logger.warning.assert_called_once()


def test_compile_optin_wraps_and_disable_restores_unet(monkeypatch) -> None:
    import torch
    from airunner_services.art import triton_runtime

    manager = _Manager()
    eager = manager._pipe.unet
    compiled = SimpleNamespace(forward=lambda *_args, **_kwargs: "compiled")
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(
        triton_runtime, "ensure_available", lambda: (True, "ready")
    )
    monkeypatch.setattr(torch, "compile", lambda module: compiled)

    assert manager._apply_torch_compile(True) is True
    assert manager._pipe.unet is compiled
    assert manager.torch_compile_applied is True
    assert "first UNet forward" in manager.torch_compile_status
    assert (
        manager._memory_settings_flags["torch_compile_status"]
        == manager.torch_compile_status
    )

    assert manager._apply_torch_compile(False) is True
    assert manager._pipe.unet is eager
    assert manager.torch_compile_applied is False
    assert manager.torch_compile_status == "disabled"


def test_disable_after_pipeline_swap_keeps_new_pipelines_unet(monkeypatch) -> None:
    import torch
    from airunner_services.art import triton_runtime

    manager = _Manager()
    old_pipe = manager._pipe
    compiled = SimpleNamespace(forward=lambda *_args, **_kwargs: "compiled")
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(
        triton_runtime, "ensure_available", lambda: (True, "ready")
    )
    monkeypatch.setattr(torch, "compile", lambda _module: compiled)

    assert manager._apply_torch_compile(True) is True
    new_unet = object()
    manager._pipe = SimpleNamespace(unet=new_unet)

    assert manager._apply_torch_compile(False) is True
    assert manager._pipe.unet is new_unet
    assert old_pipe.unet is compiled
    assert manager._torch_compile_original_unet is None
    assert manager._torch_compile_owner_pipe is None


def test_retry_after_pipeline_swap_wraps_the_new_pipeline_unet(monkeypatch) -> None:
    import torch
    from airunner_services.art import triton_runtime

    manager = _Manager()
    compiled_modules = []

    def compile_module(module):
        compiled = SimpleNamespace(
            source=module, forward=lambda *_args, **_kwargs: "compiled"
        )
        compiled_modules.append(compiled)
        return compiled

    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(
        triton_runtime, "ensure_available", lambda: (True, "ready")
    )
    monkeypatch.setattr(torch, "compile", compile_module)
    assert manager._apply_torch_compile(True) is True

    new_eager = object()
    manager._pipe = SimpleNamespace(unet=new_eager)
    assert manager._apply_torch_compile(True) is True
    assert manager._pipe.unet is compiled_modules[1]
    assert compiled_modules[1].source is new_eager

    assert manager._apply_torch_compile(False) is True
    assert manager._pipe.unet is new_eager


def test_lazy_compiler_failure_falls_back_and_returns_eager_output(
    monkeypatch,
) -> None:
    import torch
    from airunner_services.art import triton_runtime

    class EagerModule:
        def forward(self, value):
            return f"eager:{value}"

        def __call__(self, value):
            return self.forward(value)

    class CompiledModule:
        def forward(self, _value):
            raise BackendCompilerFailed("compiler rejected graph")

    BackendCompilerFailed = type(
        "BackendCompilerFailed",
        (Exception,),
        {"__module__": "torch._dynamo.exc"},
    )
    manager = _Manager()
    eager = EagerModule()
    manager._pipe.unet = eager
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(
        triton_runtime, "ensure_available", lambda: (True, "ready")
    )
    monkeypatch.setattr(torch, "compile", lambda _module: CompiledModule())

    assert manager._apply_torch_compile(True) is True
    compiled = manager._pipe.unet
    assert compiled.forward("input") == "eager:input"
    assert manager._pipe.unet is eager
    assert manager.torch_compile_applied is False
    assert manager._memory_settings_flags["torch_compile_applied"] is None
    assert "eager UNet fallback is active" in manager.torch_compile_status


def test_lazy_forward_resource_failure_is_not_swallowed(monkeypatch) -> None:
    import torch
    from airunner_services.art import triton_runtime

    class CompiledModule:
        def forward(self, _value):
            raise RuntimeError("CUDA out of memory")

    manager = _Manager()
    eager = manager._pipe.unet
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(
        triton_runtime, "ensure_available", lambda: (True, "ready")
    )
    monkeypatch.setattr(torch, "compile", lambda _module: CompiledModule())

    assert manager._apply_torch_compile(True) is True
    with pytest.raises(RuntimeError, match="out of memory"):
        manager._pipe.unet.forward("input")
    assert manager._pipe.unet is not eager
    assert manager.torch_compile_applied is True


def test_wrapped_oom_does_not_fall_back_to_eager(monkeypatch) -> None:
    import torch
    from airunner_services.art import triton_runtime

    BackendCompilerFailed = type(
        "BackendCompilerFailed",
        (Exception,),
        {"__module__": "torch._dynamo.exc"},
    )
    OOMError = type(
        "OutOfMemoryError",
        (RuntimeError,),
        {"__module__": "torch.cuda"},
    )

    class CompiledModule:
        def forward(self, _value):
            try:
                raise OOMError("CUDA out of memory")
            except OOMError as oom:
                raise BackendCompilerFailed("compiler wrapper") from oom

    manager = _Manager()
    eager = manager._pipe.unet
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(
        triton_runtime, "ensure_available", lambda: (True, "ready")
    )
    monkeypatch.setattr(torch, "compile", lambda _module: CompiledModule())

    assert manager._apply_torch_compile(True) is True
    compiled = manager._pipe.unet
    with pytest.raises(BackendCompilerFailed, match="compiler wrapper"):
        compiled.forward("input")
    assert manager._pipe.unet is compiled
    assert manager._pipe.unet is not eager
    assert manager.torch_compile_applied is True


def test_compiler_exception_cycle_terminates_and_classifies() -> None:
    BackendCompilerFailed = type(
        "BackendCompilerFailed",
        (Exception,),
        {"__module__": "torch._inductor.exc"},
    )
    compiler_error = BackendCompilerFailed("compiler failed")
    related_error = RuntimeError("wrapped backend failure")
    compiler_error.__cause__ = related_error
    related_error.__context__ = compiler_error

    assert SDMemoryManagementMixin._is_compile_backend_failure(compiler_error)


def test_setup_oom_propagates_and_keeps_eager_unet(monkeypatch) -> None:
    import torch
    from airunner_services.art import triton_runtime

    manager = _Manager()
    eager = manager._pipe.unet
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(
        triton_runtime, "ensure_available", lambda: (True, "ready")
    )

    def raise_oom(_module):
        raise torch.OutOfMemoryError("CUDA out of memory during setup")

    monkeypatch.setattr(torch, "compile", raise_oom)
    with pytest.raises(torch.OutOfMemoryError, match="out of memory"):
        manager._apply_torch_compile(True)

    assert manager._pipe.unet is eager
    assert manager.torch_compile_applied is False
    assert "setup interrupted" in manager.torch_compile_status


def test_no_cuda_skips_toolchain_preflight(monkeypatch) -> None:
    import torch
    from airunner_services.art import triton_runtime

    manager = _Manager()
    eager = manager._pipe.unet
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    preflight = Mock()
    monkeypatch.setattr(triton_runtime, "ensure_available", preflight)

    assert manager._apply_torch_compile(True) is False
    assert manager._pipe.unet is eager
    preflight.assert_not_called()


def test_disabled_setting_does_not_run_preflight(monkeypatch) -> None:
    from airunner_services.art import triton_runtime

    manager = _Manager()
    preflight = Mock()
    monkeypatch.setattr(triton_runtime, "ensure_available", preflight)

    assert manager._apply_torch_compile(False) is True
    assert manager.torch_compile_status == "disabled"
    preflight.assert_not_called()
