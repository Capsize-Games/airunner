"""Service adapter for the model-owned art sidecar client."""

from __future__ import annotations

from typing import Optional

import requests

from airunner_model.runtimes.art_daemon_runtime_settings import (
    ArtDaemonRuntimeSettings,
)
from airunner_model.runtimes.sidecar_art_client import (
    ArtLauncherFactory,
    ArtLauncherLike,
)
from airunner_model.runtimes.sidecar_art_client import (
    SidecarArtClient as _SidecarArtClient,
)
from airunner_model.runtimes.sidecar_art_client import (
    register_sidecar_art_client as _register_sidecar_art_client,
)
from airunner_model.runtimes.base import RuntimeClient
from airunner_model.runtimes.registry import RuntimeRegistry
from airunner_services.runtimes.sidecar_art_launcher import SidecarArtLauncher


def _service_art_launcher_factory(
    settings: ArtDaemonRuntimeSettings,
) -> ArtLauncherLike:
    """Create the service-owned art launcher for one client instance."""
    return SidecarArtLauncher(settings)


class SidecarArtClient(_SidecarArtClient):
    """Model-owned art client with service launcher wiring."""

    def __init__(
        self,
        provider: str = "local",
        *,
        settings: Optional[ArtDaemonRuntimeSettings] = None,
        launcher: Optional[ArtLauncherLike] = None,
        launcher_factory: Optional[ArtLauncherFactory] = None,
        session: Optional[requests.Session] = None,
    ) -> None:
        super().__init__(
            provider,
            settings=settings,
            launcher=launcher,
            launcher_factory=(
                launcher_factory
                or (_service_art_launcher_factory if launcher is None else None)
            ),
            session=session,
        )


def register_sidecar_art_client(
    registry: RuntimeRegistry,
    art_client: Optional[RuntimeClient] = None,
) -> RuntimeRegistry:
    """Register the service-wired art sidecar client."""
    client = art_client or SidecarArtClient()
    return _register_sidecar_art_client(registry, client)


__all__ = ["SidecarArtClient", "register_sidecar_art_client"]