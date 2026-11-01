"""Local fallback split keeps every public import path working.

The signal-runtime client, the art request resolvers and the
STT client live in their own modules; ``local_fallback``
re-exports the names existing callers import from it, as the
identical objects.
Hermetic: imports only, no services are constructed.
"""

from __future__ import annotations

from airunner_services.runtimes import local_fallback
from airunner_services.runtimes import local_fallback_art_helpers
from airunner_services.runtimes import local_fallback_stt_client
from airunner_services.runtimes import signal_runtime_client
from airunner_services.runtimes.local_fallback import (
    LocalFallbackArtClient,
    LocalFallbackLLMClient,
    LocalFallbackSTTClient,
    LocalFallbackTTSClient,
    register_local_fallback_clients,
)

_CLIENTS = (
    LocalFallbackArtClient,
    LocalFallbackLLMClient,
    LocalFallbackSTTClient,
    LocalFallbackTTSClient,
)


def test_public_names_importable_from_local_fallback() -> None:
    """The five public names resolve on the legacy module."""
    for client in _CLIENTS:
        assert getattr(local_fallback, client.__name__) is client
    register = local_fallback.register_local_fallback_clients
    assert register is register_local_fallback_clients


def test_signal_client_reexported_identically() -> None:
    """The extracted base client is one shared class object."""
    shared = signal_runtime_client._SignalRuntimeClient
    assert local_fallback._SignalRuntimeClient is shared
    for client in _CLIENTS:
        assert issubclass(client, shared)


def test_signal_helpers_live_in_signal_module() -> None:
    """Loaded-model helpers moved with the signal client."""
    for name in (
        "DEFAULT_TIMEOUT_SECONDS",
        "HealthProvider",
        "LoadedModelProvider",
        "_build_signal_mediator",
        "_default_timeout_seconds",
        "_is_loaded_model_status",
        "_model_health_status",
        "_model_status_value",
        "_served_model_metadata",
    ):
        assert hasattr(signal_runtime_client, name), name
    timeout = signal_runtime_client.DEFAULT_TIMEOUT_SECONDS
    assert local_fallback.DEFAULT_TIMEOUT_SECONDS == timeout
    status_value = signal_runtime_client._model_status_value
    assert local_fallback._model_status_value is status_value


def test_art_resolvers_live_in_art_helpers_module() -> None:
    """Art metadata resolvers moved as identical callables."""
    for name in (
        "_decode_art_metadata_image",
        "_resolve_art_active_rect",
        "_resolve_art_generator_section",
        "_resolve_art_operation",
        "_resolve_art_pipeline_action",
        "_resolve_art_request_image",
        "_resolve_art_request_mask",
        "_resolve_art_request_outpaint_mask_blur",
        "_resolve_art_request_scheduler",
        "_resolve_art_request_strength",
        "_resolve_art_request_version",
    ):
        assert hasattr(local_fallback_art_helpers, name), name
    moved = local_fallback_art_helpers._resolve_art_operation
    assert local_fallback._resolve_art_operation is moved


def test_stt_client_lives_in_stt_module() -> None:
    """The extracted STT client is one shared class object."""
    moved = local_fallback_stt_client.LocalFallbackSTTClient
    assert moved is LocalFallbackSTTClient
    assert local_fallback.LocalFallbackSTTClient is moved
    assert moved.__module__.endswith("local_fallback_stt_client")
    build = local_fallback_stt_client._build_stt_service
    assert local_fallback._build_stt_service is build
    moved_cap = local_fallback_stt_client.MAX_LOCAL_FALLBACK_AUDIO_BYTES
    assert local_fallback.MAX_LOCAL_FALLBACK_AUDIO_BYTES == moved_cap
    resolve = signal_runtime_client._resolve_model_type
    assert local_fallback._resolve_model_type is resolve
    assert local_fallback_stt_client._resolve_model_type is resolve


def test_runtimes_package_lazy_exports_resolve() -> None:
    """Package-level lazy exports still return the same objects."""
    import airunner_services.runtimes as runtimes

    for client in _CLIENTS:
        assert getattr(runtimes, client.__name__) is client
    register = runtimes.register_local_fallback_clients
    assert register is register_local_fallback_clients
