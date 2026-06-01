"""Hardware profiling — queries the daemon for host hardware info.

All hardware queries now go through the daemon. This module only needs
``psutil`` and no longer requires ``torch`` as a GUI dependency.
"""

from __future__ import annotations

import platform

import psutil

from airunner.daemon_client.runtime_mixin import HardwareProfile
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger


class HardwareProfiler:
    """Query hardware info from the daemon, with local psutil fallback."""

    def __init__(self) -> None:
        self.logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)

    def get_profile(self) -> HardwareProfile:
        """Return the host hardware profile, preferring the daemon."""
        try:
            from airunner.daemon_client.gui_daemon_client import (
                GuiDaemonClient,
            )

            client = GuiDaemonClient()
            return client.get_hardware_profile()
        except Exception as exc:
            self.logger.debug(
                "Falling back to local psutil profile: %s", exc,
            )
            return self._local_fallback()

    # ------------------------------------------------------------------
    # Local fallback (psutil only, no torch)
    # ------------------------------------------------------------------

    @staticmethod
    def _local_fallback() -> HardwareProfile:
        """Return a reduced local profile when the daemon is unreachable."""
        mem = psutil.virtual_memory()
        return HardwareProfile(
            total_vram_gb=0.0,
            available_vram_gb=0.0,
            total_ram_gb=mem.total / (1024**3),
            available_ram_gb=mem.available / (1024**3),
            cuda_available=False,
            device_name=None,
            cpu_count=psutil.cpu_count() or 1,
            platform=platform.system(),
        )

    def is_ampere_or_newer(self) -> bool:
        """Return whether the GPU is Ampere or newer."""
        profile = self.get_profile()
        return profile.cuda_available  # simplified; full check is daemon-side

    def has_sufficient_vram(self, required_gb: float) -> bool:
        """Return whether enough VRAM is currently available."""
        profile = self.get_profile()
        return profile.available_vram_gb >= required_gb

    def has_sufficient_ram(self, required_gb: float) -> bool:
        """Return whether enough RAM is currently available."""
        profile = self.get_profile()
        return profile.available_ram_gb >= required_gb
