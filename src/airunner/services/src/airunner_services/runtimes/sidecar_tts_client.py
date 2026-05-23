"""Service adapter for the model-owned TTS sidecar client."""

from __future__ import annotations

from typing import Optional

import requests

from airunner_model.runtimes.base import RuntimeClient
from airunner_model.runtimes.registry import RuntimeRegistry
from airunner_model.runtimes.sidecar_tts_client import (
    SidecarTTSClient as _SidecarTTSClient,
)
from airunner_model.runtimes.sidecar_tts_client import (
    TTSLauncherFactory,
    TTSLauncherLike,
)
from airunner_model.runtimes.sidecar_tts_client import (
    register_sidecar_tts_client as _register_sidecar_tts_client,
)
from airunner_model.runtimes.tts_daemon_runtime_settings import (
    TTSDaemonRuntimeSettings,
)
from airunner_services.runtimes.sidecar_tts_launcher import SidecarTTSLauncher


def _service_tts_launcher_factory(
    settings: TTSDaemonRuntimeSettings,
) -> TTSLauncherLike:
    """Create the service-owned TTS launcher for one client instance."""
    return SidecarTTSLauncher(settings)


class SidecarTTSClient(_SidecarTTSClient):
    """Model-owned TTS client with service launcher wiring."""

    def __init__(
        self,
        provider: str = "local",
        *,
        settings: Optional[TTSDaemonRuntimeSettings] = None,
        launcher: Optional[TTSLauncherLike] = None,
        launcher_factory: Optional[TTSLauncherFactory] = None,
        session: Optional[requests.Session] = None,
    ) -> None:
        super().__init__(
            provider,
            settings=settings,
            launcher=launcher,
            launcher_factory=(
                launcher_factory
                or (_service_tts_launcher_factory if launcher is None else None)
            ),
            session=session,
        )


def register_sidecar_tts_client(
    registry: RuntimeRegistry,
    tts_client: Optional[RuntimeClient] = None,
) -> RuntimeRegistry:
    """Register the service-wired TTS sidecar client."""
    client = tts_client or SidecarTTSClient()
    return _register_sidecar_tts_client(registry, client)


__all__ = ["SidecarTTSClient", "register_sidecar_tts_client"]