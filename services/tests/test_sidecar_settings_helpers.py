"""Unit tests for the sidecar settings-resolution helpers.

_resolve_via_settings_resolver, _resolve_fallback_settings, and
_bind_selected_model were extracted to keep
_resolve_settings_unchecked within the long-function threshold.
These tests pin the kwarg forwarding, the fallback chain, and the
model-binding mismatch errors.
"""

from unittest.mock import MagicMock

import pytest

from airunner_services.runtimes.sidecar_llm_client import (
    SidecarLLMClient,
)


def _make_client(resolver=None):
    client = SidecarLLMClient.__new__(SidecarLLMClient)
    client._uses_default_settings_resolver = False
    client._settings_resolver = resolver or MagicMock(return_value="s")
    return client


def test_via_resolver_forwards_selection_kwargs():
    resolver = MagicMock(return_value="s")
    client = _make_client(resolver)
    out = client._resolve_via_settings_resolver(
        "profile", {"model_id": "m1", "n_ctx": 8}
    )
    assert out == "s"
    resolver.assert_called_once_with(
        "profile", selected_model_id="m1", selected_n_ctx=8
    )


def test_fallback_prefers_profile_call():
    resolver = MagicMock(return_value="s")
    client = _make_client(resolver)
    assert client._resolve_fallback_settings("profile") == "s"
    resolver.assert_called_once_with("profile")


def test_fallback_drops_to_bare_call_on_type_error():
    calls = []

    def resolver(*args):
        calls.append(args)
        if args:
            raise TypeError("legacy signature")
        return "s"

    client = _make_client(resolver)
    assert client._resolve_fallback_settings("profile") == "s"
    assert calls == [("profile",), ()]


def test_bind_rejects_missing_selected_path():
    client = _make_client()
    resolved = MagicMock(model_path="/m/x.gguf", model_id=None)
    with pytest.raises(RuntimeError, match="cannot bind"):
        client._bind_selected_model(resolved, {}, "default")


def test_bind_rejects_mismatched_paths(tmp_path):
    client = _make_client()
    a = tmp_path / "a.gguf"
    a.write_bytes(b"")
    b = tmp_path / "b.gguf"
    b.write_bytes(b"")
    resolved = MagicMock(model_path=str(b), model_id=None, n_ctx=1, n_gpu_layers=1)
    with pytest.raises(RuntimeError, match="does not match"):
        client._bind_selected_model(
            resolved, {"model_path": str(a)}, "default"
        )


def test_bind_overrides_selection_fields(tmp_path):
    from airunner_services.runtimes.sidecar_llm_client import (
        LlamaCppRuntimeSettings,
    )

    client = _make_client()
    path = tmp_path / "m.gguf"
    path.write_bytes(b"")
    real = LlamaCppRuntimeSettings(
        executable="/bin/x",
        host="127.0.0.1",
        port=8080,
        model_path=str(path),
        model_id=None,
        runtime_profile=None,
        n_ctx=1,
        n_gpu_layers=1,
        startup_timeout_seconds=30.0,
        n_batch=512,
        flash_attn=False,
        cache_type_k=None,
        cache_type_v=None,
        repeat_last_n=64,
        backend_profile=None,
        backend_artifact_id=None,
        backend_manifest_sha256=None,
        backend_profile_verified=False,
        requested_device="cpu",
        fit=False,
        backend_selection_deferred=False,
    )
    bound = client._bind_selected_model(
        real, {"model_path": str(path), "model_id": "sel", "n_ctx": 9}, None
    )
    assert bound.model_id == "sel"
    assert bound.n_ctx == 9
    assert bound.runtime_profile == "default"
