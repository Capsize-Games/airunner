"""Contracts for CPU/CUDA native runtime selection and profile verification."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from airunner_services.runtimes.native_backend_profiles import (
    CUDA_PROFILE,
    PROFILE_SCHEMA,
    NativeBackendUnavailable,
    select_native_backend,
)


def _write_profile(root: Path, *, status: str = "verified") -> Path:
    """Build a small verified-format profile tree with no executable use."""
    (root / "bin").mkdir(parents=True)
    (root / "lib").mkdir()
    files = {
        "bin/llama-server": (b"fixture server", 0o755),
        "bin/llama-server-cuda": (
            b'#!/bin/sh\nserver_dir="$(cd -- "$(dirname -- "$0")" && pwd)"\n'
            b'export LD_LIBRARY_PATH="$server_dir/../lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"\n'
            b'cd /\nexec "$server_dir/llama-server" "$@"\n',
            0o755,
        ),
        "lib/libcudart.so.12": (b"fixture library", 0o644),
    }
    rows = []
    for name, (content, mode) in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        path.chmod(mode)
        rows.append(
            {
                "path": name,
                "sha256": hashlib.sha256(content).hexdigest(),
                "mode": mode,
            }
        )
    manifest = {
        "schema": PROFILE_SCHEMA,
        "status": status,
        "profile": CUDA_PROFILE,
        "artifact_id": "fixture-artifact-001",
        "platform": "linux-x86_64",
        "abi": "ubuntu-24.04",
        "compute_capability": "12.0",
        "source": {
            "repository": "fixture",
            "commit": "a" * 40,
            "tree": "d" * 40,
        },
        "producer": {"commit": "b" * 40, "recipe_sha256": "c" * 64},
        "entrypoint": "bin/llama-server-cuda",
        "files": rows,
    }
    manifest_path = root / "profile-manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    manifest_path.chmod(0o644)
    return root


def test_auto_keeps_genuine_cpu_request_on_legacy_binary(
    tmp_path, monkeypatch
):
    cpu = tmp_path / "llama-server"
    cpu.write_text("diagnostic")
    monkeypatch.delenv("AIRUNNER_LLAMA_BACKEND", raising=False)
    selection = select_native_backend(
        n_gpu_layers=0,
        requested="auto",
        cpu_executable=str(cpu),
    )
    assert selection.profile == "cpu"
    assert selection.executable == str(cpu)
    assert selection.verified is False
    assert selection.metadata()["actual_device"] is None


def test_explicit_cpu_backend_overrides_gpu_layers_intentionally(
    tmp_path, monkeypatch
):
    cpu = tmp_path / "diagnostic-server"
    cpu.write_text("fixture executable")
    cpu.chmod(0o755)
    monkeypatch.setenv("AIRUNNER_LLAMA_SERVER_BIN", str(cpu))
    selection = select_native_backend(
        n_gpu_layers=-1,
        requested="cpu",
        cpu_executable=str(cpu),
    )
    assert selection.profile == "cpu"
    assert selection.executable == str(cpu)
    assert selection.artifact_id == "explicit-cpu-executable"
    assert selection.device is None


def test_gpu_intent_does_not_fall_back_when_profile_is_missing(tmp_path):
    with pytest.raises(NativeBackendUnavailable, match="profile"):
        select_native_backend(
            n_gpu_layers=-1,
            requested="auto",
            bundle_root=tmp_path,
            device_probe=lambda: None,
        )


def test_cuda_intent_fails_actionably_when_device_is_unsupported(tmp_path):
    root = _write_profile(tmp_path / "profile")
    with pytest.raises(NativeBackendUnavailable, match="compute capability"):
        select_native_backend(
            n_gpu_layers=-1,
            requested="cuda-sm120a",
            cuda_profile_root=root,
            device_probe=lambda: (_ for _ in ()).throw(
                NativeBackendUnavailable(
                    "compute capability 12.0 GPU required"
                )
            ),
        )


def test_cuda_selection_checks_verified_tree_and_uses_confined_wrapper(
    tmp_path,
):
    root = _write_profile(tmp_path / "profile")
    selection = select_native_backend(
        n_gpu_layers=-1,
        requested="cuda-sm120a",
        cuda_profile_root=root,
        device_probe=lambda: "CUDA1",
    )
    assert selection.profile == "cuda-sm120a"
    assert selection.executable == str(root / "bin/llama-server-cuda")
    assert selection.device == "CUDA1"
    assert selection.verified is True
    assert (
        selection.manifest_sha256
        == hashlib.sha256(
            (root / "profile-manifest.json").read_bytes()
        ).hexdigest()
    )
    assert selection.fit == "off"
    assert selection.metadata()["offloaded_layers"] is None


def test_settings_resolver_separates_backend_from_gguf_tuning(
    tmp_path, monkeypatch
):
    from types import SimpleNamespace

    from airunner_services.runtimes import (
        llama_cpp_runtime_settings as settings_module,
    )
    from airunner_services.runtimes import native_backend_profiles

    bundle_root = tmp_path / "bundle"
    root = _write_profile(
        bundle_root / "share/airunner/native-runtimes/cuda-sm120a"
    )
    model = tmp_path / "model.gguf"
    model.write_bytes(b"GGUF fixture")
    monkeypatch.setenv("AIRUNNER_LLAMA_BACKEND", "auto")
    monkeypatch.setenv("AIRUNNER_BUNDLE_ROOT", str(bundle_root))
    monkeypatch.delenv("CUDA_VISIBLE_DEVICES", raising=False)
    monkeypatch.setattr(native_backend_profiles, "_DEVICE_PROBE_SUCCEEDED_AT", 0.0)
    monkeypatch.setattr(native_backend_profiles, "_DEVICE_PROBE_DEVICE", None)
    monkeypatch.setattr(
        native_backend_profiles, "_probe_sm120a_device", lambda: "CUDA0"
    )
    settings = settings_module.resolve_llama_cpp_runtime_settings(
        llm_settings=SimpleNamespace(use_gpu=True),
        path_settings=SimpleNamespace(base_path=str(tmp_path)),
        runtime_profile="qwen-parameters",
        selected_model_id="custom",
        selected_model_path=str(model),
        selected_n_ctx=32768,
        selected_n_gpu_layers=-1,
    )
    assert settings.backend_profile == "cuda-sm120a"
    assert settings.runtime_profile == "qwen-parameters"
    assert settings.n_ctx == 32768
    assert settings.n_gpu_layers == -1
    assert settings.executable == str(root / "bin/llama-server-cuda")


def test_deeply_nested_manifest_returns_typed_unavailable(tmp_path):
    root = _write_profile(tmp_path / "profile")
    (root / "profile-manifest.json").write_text('{"nested":' * 1100 + '0' + '}' * 1100)
    with pytest.raises(NativeBackendUnavailable, match="malformed"):
        select_native_backend(
            n_gpu_layers=-1,
            requested="cuda-sm120a",
            cuda_profile_root=root,
            device_probe=lambda: "CUDA0",
        )


def test_launcher_pins_cuda_device_and_disables_auto_fit(tmp_path):
    from airunner_services.runtimes.llama_cpp_runtime_settings import (
        LlamaCppRuntimeSettings,
    )
    from airunner_services.runtimes.sidecar_launcher import SidecarLauncher

    model = tmp_path / "model.gguf"
    model.write_bytes(b"GGUF fixture")
    launcher = SidecarLauncher(
        LlamaCppRuntimeSettings(
            executable="/verified/profile/bin/llama-server-cuda",
            host="127.0.0.1",
            port=8011,
            model_path=str(model),
            model_id="custom",
            runtime_profile="qwen-parameters",
            n_ctx=32768,
            n_gpu_layers=-1,
            startup_timeout_seconds=1,
            requested_device="CUDA1",
            fit="off",
        )
    )
    command = launcher.command()
    assert command[command.index("--device") + 1] == "CUDA1"
    assert command[command.index("--fit") + 1] == "off"


@pytest.mark.parametrize(
    "mutation",
    [
        "candidate",
        "hash",
        "path_escape",
        "unexpected_file",
        "wrapper_escape",
    ],
)
def test_cuda_profile_rejects_unverified_or_tampered_tree(tmp_path, mutation):
    root = _write_profile(
        tmp_path / "profile",
        status="candidate" if mutation == "candidate" else "verified",
    )
    manifest_path = root / "profile-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    if mutation == "hash":
        (root / "lib/libcudart.so.12").write_bytes(b"tampered")
    elif mutation == "path_escape":
        manifest["files"][0]["path"] = "../outside"
        manifest_path.write_text(json.dumps(manifest))
    elif mutation == "unexpected_file":
        (root / "lib/unlisted.so").write_bytes(b"extra")
    elif mutation == "wrapper_escape":
        wrapper = root / "bin/llama-server-cuda"
        wrapper.write_text("#!/bin/sh\nexec /tmp/other-server\n")
        wrapper.chmod(0o755)
    with pytest.raises(NativeBackendUnavailable):
        select_native_backend(
            n_gpu_layers=-1,
            requested="cuda-sm120a",
            cuda_profile_root=root,
            device_probe=lambda: None,
        )


def test_verified_profile_hash_cache_invalidates_when_a_file_changes(
    tmp_path, monkeypatch
):
    from airunner_services.runtimes import native_backend_profiles

    root = _write_profile(tmp_path / "profile")
    selection_args = {
        "n_gpu_layers": -1,
        "requested": "cuda-sm120a",
        "cuda_profile_root": root,
        "device_probe": lambda: None,
    }
    original_hash = native_backend_profiles._sha256_file
    calls = []

    def record_hash(path):
        calls.append(path)
        return original_hash(path)

    native_backend_profiles._PROFILE_CACHE.clear()
    monkeypatch.setattr(native_backend_profiles, "_sha256_file", record_hash)
    select_native_backend(**selection_args)
    first_count = len(calls)
    select_native_backend(**selection_args)
    assert len(calls) == first_count
    (root / "lib/libcudart.so.12").write_bytes(b"tampered")
    with pytest.raises(NativeBackendUnavailable):
        select_native_backend(**selection_args)
    assert len(calls) > first_count


@pytest.mark.parametrize(
    "kind", ["extra_dir", "fifo", "symlink_dir", "unsafe_manifest_mode"]
)
def test_cuda_profile_rejects_unlisted_or_unsafe_tree_entries(tmp_path, kind):
    root = _write_profile(tmp_path / "profile")
    if kind == "extra_dir":
        (root / "unexpected").mkdir()
    elif kind == "fifo":
        os.mkfifo(root / "unexpected.fifo")
    elif kind == "symlink_dir":
        external = tmp_path / "external-lib"
        shutil.move(root / "lib", external)
        (root / "lib").symlink_to(external, target_is_directory=True)
    else:
        (root / "profile-manifest.json").chmod(0o600)
    with pytest.raises(NativeBackendUnavailable):
        select_native_backend(
            n_gpu_layers=-1,
            requested="cuda-sm120a",
            cuda_profile_root=root,
            device_probe=lambda: None,
        )


@pytest.mark.parametrize("target_kind", ["bundle", "profile"])
def test_cuda_root_rejects_symlinked_configured_path(tmp_path, target_kind):
    root = _write_profile(tmp_path / "real-profile")
    alias = tmp_path / "profile-alias"
    alias.symlink_to(root, target_is_directory=True)
    options = (
        {"bundle_root": alias.parent}
        if target_kind == "bundle"
        else {"cuda_profile_root": alias}
    )
    if target_kind == "bundle":
        bundle = tmp_path / "real-bundle"
        bundle_profile = bundle / "share/airunner/native-runtimes/cuda-sm120a"
        _write_profile(bundle_profile)
        bundle_alias = tmp_path / "bundle-alias"
        bundle_alias.symlink_to(bundle, target_is_directory=True)
        options = {"bundle_root": bundle_alias}
    with pytest.raises(NativeBackendUnavailable, match="symlink"):
        select_native_backend(
            n_gpu_layers=-1,
            requested="cuda-sm120a",
            device_probe=lambda: None,
            **options,
        )


def test_cuda_root_rejects_symlinked_ancestor_component(tmp_path):
    real_parent = tmp_path / "real-parent"
    root = _write_profile(real_parent / "profile")
    alias_parent = tmp_path / "alias-parent"
    alias_parent.symlink_to(real_parent, target_is_directory=True)
    with pytest.raises(NativeBackendUnavailable, match="symlink"):
        select_native_backend(
            n_gpu_layers=-1,
            requested="cuda-sm120a",
            cuda_profile_root=alias_parent / "profile",
            device_probe=lambda: None,
        )


def test_cuda_device_index_uses_pci_order_before_selecting_sm120(
    tmp_path, monkeypatch
):
    from airunner_services.runtimes import native_backend_profiles

    monkeypatch.setattr(
        native_backend_profiles.platform, "system", lambda: "Linux"
    )
    monkeypatch.setattr(
        native_backend_profiles.platform, "machine", lambda: "x86_64"
    )
    monkeypatch.delenv("CUDA_VISIBLE_DEVICES", raising=False)
    monkeypatch.setattr(
        native_backend_profiles.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(
            stdout="0000:02:00.0, 12.0\n0000:01:00.0, 8.9\n"
        ),
    )
    assert native_backend_profiles._probe_sm120a_device() == "CUDA1"


def test_cuda_device_probe_rejects_visibility_remapping(monkeypatch):
    from airunner_services.runtimes import native_backend_profiles

    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "1")
    monkeypatch.setattr(
        native_backend_profiles.subprocess,
        "run",
        lambda *_args, **_kwargs: pytest.fail(
            "driver queried under remapping"
        ),
    )
    with pytest.raises(NativeBackendUnavailable, match="CUDA_VISIBLE_DEVICES"):
        native_backend_profiles._probe_sm120a_device()


def test_cuda_launcher_sets_pci_device_order(monkeypatch, tmp_path):
    from airunner_services.runtimes.llama_cpp_runtime_settings import (
        LlamaCppRuntimeSettings,
    )
    from airunner_services.runtimes.sidecar_launcher import SidecarLauncher

    monkeypatch.delenv("CUDA_VISIBLE_DEVICES", raising=False)
    layout = SimpleNamespace(
        ensure_exists=lambda: None,
        as_environment=lambda: {"AIRUNNER_RUNTIME_ROOT": str(tmp_path)},
    )
    monkeypatch.setattr(
        "airunner_services.runtimes.sidecar_launcher.build_runtime_directory_layout",
        lambda: layout,
    )
    launcher = SidecarLauncher(
        LlamaCppRuntimeSettings(
            executable="/bundle/cuda/bin/llama-server-cuda",
            host="127.0.0.1",
            port=8011,
            model_path=str(tmp_path / "model.gguf"),
            model_id="custom",
            runtime_profile="default",
            n_ctx=4096,
            n_gpu_layers=-1,
            startup_timeout_seconds=1,
            backend_profile="cuda-sm120a",
        )
    )
    assert launcher._environment()["CUDA_DEVICE_ORDER"] == "PCI_BUS_ID"


def test_cuda_profile_rejects_symlinked_tree_member(tmp_path):
    root = _write_profile(tmp_path / "profile")
    target = tmp_path / "outside"
    target.write_bytes(b"outside")
    member = root / "lib/libcudart.so.12"
    member.unlink()
    member.symlink_to(target)
    with pytest.raises(NativeBackendUnavailable):
        select_native_backend(
            n_gpu_layers=-1,
            requested="cuda-sm120a",
            cuda_profile_root=root,
            device_probe=lambda: None,
        )


def test_client_and_registry_survive_missing_gpu_artifact_until_use(
    tmp_path, monkeypatch
):
    import sys
    from types import SimpleNamespace

    from airunner_services.runtimes import llama_cpp_runtime_settings
    from airunner_services.runtimes import native_backend_profiles
    from airunner_services.runtimes.contracts import RuntimeAction, RuntimeKind
    from airunner_services.runtimes.registry import RuntimeRegistry
    from airunner_services.runtimes.sidecar_llm_client import (
        register_sidecar_llm_client,
    )

    monkeypatch.setenv("AIRUNNER_LLAMA_BACKEND", "auto")
    monkeypatch.setenv("AIRUNNER_LLAMA_N_GPU_LAYERS", "-1")
    monkeypatch.setenv("AIRUNNER_BUNDLE_ROOT", str(tmp_path))
    monkeypatch.delenv("AIRUNNER_LLAMA_CUDA_PROFILE_ROOT", raising=False)
    monkeypatch.setattr(
        llama_cpp_runtime_settings,
        "_load_llm_settings",
        lambda: SimpleNamespace(use_gpu=True),
    )
    monkeypatch.setattr(
        llama_cpp_runtime_settings,
        "_load_path_settings",
        lambda: SimpleNamespace(base_path=str(tmp_path)),
    )
    verify_calls = []
    original_verify = native_backend_profiles._verify_cuda_profile

    def verify(root):
        verify_calls.append(root)
        return original_verify(root)

    monkeypatch.setattr(
        native_backend_profiles, "_verify_cuda_profile", verify
    )
    monkeypatch.setattr(
        native_backend_profiles,
        "_probe_sm120a_device",
        lambda: pytest.fail("driver probed before profile verification"),
    )

    registry = RuntimeRegistry()
    register_sidecar_llm_client(registry)
    client = registry.resolve(RuntimeKind.LLM, "local")
    health = client.healthcheck()
    assert health.status.value == "stopped"
    assert health.metadata["backend_profile"] == "cuda-sm120a"
    assert health.metadata["backend_selection_deferred"] is True
    assert health.metadata["backend_profile_verified"] is False
    assert "backend_executable" not in health.metadata
    assert client._launcher._process is None
    assert verify_calls == []
    assert not any(
        name == "llama_cpp" or name.startswith("llama_cpp.")
        for name in sys.modules
    )

    response = client.invoke(
        SimpleNamespace(
            runtime=RuntimeKind.LLM,
            action=RuntimeAction.INVOKE,
            request_id="gpu-required",
            payload={"messages": [{"role": "user", "content": "hello"}]},
        )
    )
    assert response.status.value == "failed"
    assert response.error.code == "native_backend_unavailable"
    assert "missing, malformed, or unverified" in response.error.message
    assert len(verify_calls) == 1
    assert client._launcher._process is None
    health_after_attempt = client.healthcheck()
    assert health_after_attempt.status.value == "failed"
    assert health_after_attempt.metadata["backend_unavailable"] is True


def test_llm_invoke_returns_typed_backend_unavailable_failure(tmp_path):
    from types import SimpleNamespace

    from airunner_services.runtimes.contracts import RuntimeAction, RuntimeKind
    from airunner_services.runtimes.llama_cpp_runtime_settings import (
        LlamaCppRuntimeSettings,
    )
    from airunner_services.runtimes.sidecar_llm_client import SidecarLLMClient

    model = tmp_path / "model.gguf"
    model.write_bytes(b"GGUF fixture")
    settings = LlamaCppRuntimeSettings(
        executable="llama-server",
        host="127.0.0.1",
        port=8011,
        model_path=str(model),
        model_id="custom",
        runtime_profile="default",
        n_ctx=4096,
        n_gpu_layers=0,
        startup_timeout_seconds=1,
    )

    def unavailable(*_args, **_kwargs):
        raise NativeBackendUnavailable(
            "CUDA SM120a runtime profile is missing; install a verified profile"
        )

    client = SidecarLLMClient(settings=settings, settings_resolver=unavailable)
    response = client.invoke(
        SimpleNamespace(
            runtime=RuntimeKind.LLM,
            action=RuntimeAction.INVOKE,
            request_id="gpu-required",
            payload={"messages": [{"role": "user", "content": "hello"}]},
        )
    )
    assert response.status.value == "failed"
    assert response.error.code == "native_backend_unavailable"
    assert "verified profile" in response.error.message


def test_backend_artifact_identity_participates_in_binding_identity(tmp_path):
    from dataclasses import replace

    from airunner_services.runtimes.llama_cpp_runtime_settings import (
        LlamaCppRuntimeSettings,
    )
    from airunner_services.runtimes.sidecar_llm_client import SidecarLLMClient

    model = tmp_path / "model.gguf"
    model.write_bytes(b"GGUF fixture")
    settings = LlamaCppRuntimeSettings(
        executable="/bundle/cuda-sm120a/bin/llama-server-cuda",
        host="127.0.0.1",
        port=8011,
        model_path=str(model),
        model_id="qwen3.5-9b",
        runtime_profile="qwen-parameters",
        n_ctx=32768,
        n_gpu_layers=-1,
        startup_timeout_seconds=1,
        backend_profile="cuda-sm120a",
        backend_artifact_id="artifact-a",
        backend_manifest_sha256="d" * 64,
        backend_profile_verified=True,
    )
    original = SidecarLLMClient._backend_identity(
        settings, None, settings.runtime_profile
    )
    replacement = SidecarLLMClient._backend_identity(
        replace(settings, backend_artifact_id="artifact-b"),
        None,
        settings.runtime_profile,
    )
    assert original != replacement


def test_sidecar_health_reports_selected_profile_not_actual_offload(tmp_path):
    from airunner_services.runtimes.contracts import RuntimeHealthStatus
    from airunner_services.runtimes.llama_cpp_runtime_settings import (
        LlamaCppRuntimeSettings,
    )
    from airunner_services.runtimes.sidecar_llm_client import SidecarLLMClient

    model = tmp_path / "model.gguf"
    model.write_bytes(b"GGUF fixture")
    settings = LlamaCppRuntimeSettings(
        executable="/bundle/cuda-sm120a/bin/llama-server-cuda",
        host="127.0.0.1",
        port=8011,
        model_path=str(model),
        model_id="qwen3.5-9b",
        runtime_profile="qwen-parameters",
        n_ctx=32768,
        n_gpu_layers=-1,
        startup_timeout_seconds=1,
        backend_profile="cuda-sm120a",
        backend_artifact_id="fixture-artifact-001",
        backend_manifest_sha256="d" * 64,
        backend_profile_verified=True,
        requested_device="CUDA0",
        fit="off",
    )

    class Launcher:
        endpoint = settings.endpoint

        @staticmethod
        def health_status():
            return RuntimeHealthStatus.READY, "ready"

    health = SidecarLLMClient(
        settings=settings, launcher=Launcher()
    ).healthcheck()
    assert health.metadata["backend_profile"] == "cuda-sm120a"
    assert health.metadata["backend_artifact_id"] == "fixture-artifact-001"
    assert health.metadata["backend_manifest_sha256"] == "d" * 64
    assert health.metadata["requested_device"] == "CUDA0"
    assert health.metadata["actual_device"] is None
    assert health.metadata["offloaded_layers"] is None


def test_runtime_health_entry_propagates_selection_metadata():
    from airunner_services.llm.local_capability_runtime import runtime_entry
    from airunner_services.runtimes.contracts import (
        RuntimeDescriptor,
        RuntimeHealth,
        RuntimeHealthStatus,
        RuntimeKind,
        RuntimeMode,
        TransportKind,
    )

    health = RuntimeHealth(
        descriptor=RuntimeDescriptor(
            runtime=RuntimeKind.LLM,
            provider="local",
            mode=RuntimeMode.SIDECAR,
            transport=TransportKind.HTTP,
        ),
        status=RuntimeHealthStatus.READY,
        metadata={
            "backend_profile": "cuda-sm120a",
            "backend_executable": "/private/bundle/bin/llama-server-cuda",
            "model_path": "/private/models/secret.gguf",
            "actual_device": None,
            "backend_selection_deferred": True,
        },
    )
    entry = runtime_entry(health, failed=False)
    assert entry["metadata"]["backend_profile"] == "cuda-sm120a"
    assert entry["metadata"]["actual_device"] is None
    assert entry["metadata"]["backend_binary"] == "llama-server-cuda"
    assert "backend_executable" not in entry["metadata"]
    assert "model_path" not in entry["metadata"]
    from airunner_services.api.routes.llm_local_routes import (
        LocalRuntimeHealth,
    )

    wire_health = LocalRuntimeHealth.model_validate(entry)
    assert wire_health.metadata["backend_profile"] == "cuda-sm120a"
    assert wire_health.metadata["actual_device"] is None
    assert wire_health.metadata["backend_selection_deferred"] is True
