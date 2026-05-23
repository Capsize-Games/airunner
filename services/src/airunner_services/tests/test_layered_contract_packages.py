"""Boundary tests for the extracted API and model contract packages."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _run_import_probe() -> subprocess.CompletedProcess[str]:
    repo_root = _repo_root()
    code = f"""
import json
import sys

sys.path.insert(0, {str(repo_root / 'shared' / 'src')!r})
sys.path.insert(0, {str(repo_root / 'model' / 'src')!r})
sys.path.insert(0, {str(repo_root / 'api' / 'src')!r})

import airunner_api.downloads
import airunner_api.application_data
import airunner_api.bootstrap
import airunner_model.contracts
import airunner_model.llm.provider_config
import airunner_model.model_management
import airunner_model.model_management.mixins
import airunner_model.model_management.mixins.memory_tracking_mixin
import airunner_model.model_management.mixins.model_loading_mixin
import airunner_model.model_management.mixins.model_selection_mixin
import airunner_model.model_management.mixins.model_state_mixin
import airunner_model.model_management.model_resource_manager
import airunner_model.model_management.canvas_memory_tracker
import airunner_model.model_management.hardware_profiler
import airunner_model.model_management.memory_allocator
import airunner_model.model_management.model_manager_interface
import airunner_model.model_management.model_registry
import airunner_model.model_management.quantization_strategy
import airunner_model.model_management.types
import airunner_model.runtimes.art_daemon_runtime_settings
import airunner_model.runtimes.base
import airunner_model.runtimes.bundled_runtime_paths
import airunner_model.runtimes.llama_cpp_runtime_settings
import airunner_model.runtimes.registry
import airunner_model.runtimes.runtime_layout
import airunner_model.runtimes.sidecar_art_client
import airunner_model.runtimes.sidecar_launcher
import airunner_model.runtimes.sidecar_llm_client
import airunner_model.runtimes.sidecar_stt_client
import airunner_model.runtimes.sidecar_stt_launcher
import airunner_model.runtimes.sidecar_tts_client
import airunner_model.runtimes.tts_daemon_runtime_settings
import airunner_model.runtimes.whisper_cpp_runtime_settings
import airunner_api.messages
import airunner_api.privacy

loaded = sorted(
    name
    for name in sys.modules
    if name.startswith('airunner') or name.startswith('airunner_')
)
print(json.dumps(loaded))
"""
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )


def test_api_and_model_contracts_import_without_gui_or_services() -> None:
    result = _run_import_probe()

    assert result.returncode == 0, result.stderr
    loaded = json.loads(result.stdout)

    assert "airunner_api" in loaded
    assert "airunner_api.application_data" in loaded
    assert "airunner_api.bootstrap" in loaded
    assert "airunner_api.downloads" in loaded
    assert "airunner_api.messages" in loaded
    assert "airunner_api.privacy" in loaded
    assert "airunner_model" in loaded
    assert "airunner_model.contracts" in loaded
    assert "airunner_model.llm.provider_config" in loaded
    assert "airunner_model.model_management" in loaded
    assert "airunner_model.model_management.mixins" in loaded
    assert "airunner_model.model_management.mixins.memory_tracking_mixin" in loaded
    assert "airunner_model.model_management.mixins.model_loading_mixin" in loaded
    assert "airunner_model.model_management.mixins.model_selection_mixin" in loaded
    assert "airunner_model.model_management.mixins.model_state_mixin" in loaded
    assert "airunner_model.model_management.canvas_memory_tracker" in loaded
    assert "airunner_model.model_management.hardware_profiler" in loaded
    assert "airunner_model.model_management.memory_allocator" in loaded
    assert "airunner_model.model_management.model_manager_interface" in loaded
    assert "airunner_model.model_management.model_resource_manager" in loaded
    assert "airunner_model.model_management.model_registry" in loaded
    assert "airunner_model.model_management.quantization_strategy" in loaded
    assert "airunner_model.model_management.types" in loaded
    assert "airunner_model.runtimes.art_daemon_runtime_settings" in loaded
    assert "airunner_model.runtimes.base" in loaded
    assert "airunner_model.runtimes.bundled_runtime_paths" in loaded
    assert "airunner_model.runtimes.llama_cpp_runtime_settings" in loaded
    assert "airunner_model.runtimes.registry" in loaded
    assert "airunner_model.runtimes.runtime_layout" in loaded
    assert "airunner_model.runtimes.sidecar_art_client" in loaded
    assert "airunner_model.runtimes.sidecar_launcher" in loaded
    assert "airunner_model.runtimes.sidecar_llm_client" in loaded
    assert "airunner_model.runtimes.sidecar_stt_client" in loaded
    assert "airunner_model.runtimes.sidecar_stt_launcher" in loaded
    assert "airunner_model.runtimes.sidecar_tts_client" in loaded
    assert "airunner_model.runtimes.tts_daemon_runtime_settings" in loaded
    assert "airunner_model.runtimes.whisper_cpp_runtime_settings" in loaded
    assert not any(name.startswith("airunner_services") for name in loaded)
    assert not any(name == "airunner" or name.startswith("airunner.") for name in loaded)


def test_model_management_surface_omits_service_only_exports() -> None:
    import airunner_model.model_management as model_management

    assert not hasattr(model_management, "BaseModelManager")
    assert not hasattr(model_management, "ModelLoadBalancer")


def test_runtime_surface_omits_service_only_exports() -> None:
    import airunner_model.runtimes as runtimes

    assert not hasattr(runtimes, "LocalFallbackArtClient")
    assert not hasattr(runtimes, "LocalFallbackLLMClient")
    assert not hasattr(runtimes, "LocalFallbackSTTClient")
    assert not hasattr(runtimes, "LocalFallbackTTSClient")
    assert not hasattr(runtimes, "RuntimeRegistrySTTExecutor")
    assert not hasattr(runtimes, "SidecarArtLauncher")
    assert not hasattr(runtimes, "SidecarTTSLauncher")
    assert not hasattr(runtimes, "build_runtime_registry")
    assert not hasattr(runtimes, "register_local_fallback_clients")