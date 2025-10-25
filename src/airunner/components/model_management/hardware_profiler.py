import logging
import platform
from dataclasses import dataclass
from typing import Optional

import psutil
import torch


@dataclass
class HardwareProfile:
    """Hardware capabilities and current resource availability."""

    total_vram_gb: float
    available_vram_gb: float
    total_ram_gb: float
    available_ram_gb: float
    cuda_available: bool
    cuda_compute_capability: Optional[tuple]
    device_name: Optional[str]
    cpu_count: int
    platform: str


class HardwareProfiler:
    """Detects and monitors system hardware resources."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def get_profile(self) -> HardwareProfile:
        """Get current hardware profile."""
        return HardwareProfile(
            total_vram_gb=self._get_total_vram_gb(),
            available_vram_gb=self._get_available_vram_gb(),
            total_ram_gb=self._get_total_ram_gb(),
            available_ram_gb=self._get_available_ram_gb(),
            cuda_available=torch.cuda.is_available(),
            cuda_compute_capability=self._get_cuda_compute_capability(),
            device_name=self._get_device_name(),
            cpu_count=self._get_cpu_count(),
            platform=platform.system(),
        )

    def _get_total_vram_gb(self) -> float:
        """Get total VRAM in GB."""
        if not torch.cuda.is_available():
            return 0.0
        return torch.cuda.get_device_properties(0).total_memory / (1024**3)

    def _get_available_vram_gb(self) -> float:
        """Get available VRAM in GB."""
        if not torch.cuda.is_available():
            return 0.0

        try:
            free_memory, _ = torch.cuda.mem_get_info()
            return free_memory / (1024**3)
        except Exception as e:
            self.logger.warning(f"Could not detect VRAM: {e}")
            return 0.0

    def _get_total_ram_gb(self) -> float:
        """Get total system RAM in GB."""
        return psutil.virtual_memory().total / (1024**3)

    def _get_available_ram_gb(self) -> float:
        """Get available system RAM in GB."""
        return psutil.virtual_memory().available / (1024**3)

    def _get_cuda_compute_capability(self) -> Optional[tuple]:
        """Get CUDA compute capability."""
        if not torch.cuda.is_available():
            return None

        props = torch.cuda.get_device_properties(0)
        return (props.major, props.minor)

    def _get_device_name(self) -> Optional[str]:
        """Get GPU device name."""
        if not torch.cuda.is_available():
            return None
        return torch.cuda.get_device_name(0)

    def _get_cpu_count(self) -> int:
        """Get physical CPU core count safely."""
        try:
            count = psutil.cpu_count(logical=False)
            return count if count is not None else psutil.cpu_count()
        except (PermissionError, OSError) as e:
            self.logger.warning(f"Could not detect CPU count: {e}")
            try:
                count = psutil.cpu_count()
                return count if count is not None else 1
            except Exception:
                return 1

    def is_ampere_or_newer(self) -> bool:
        """Check if GPU is Ampere (3.x series) or newer."""
        capability = self._get_cuda_compute_capability()
        if capability is None:
            return False
        return capability[0] >= 8

    def has_sufficient_vram(self, required_gb: float) -> bool:
        """Check if sufficient VRAM is available."""
        return self._get_available_vram_gb() >= required_gb

    def has_sufficient_ram(self, required_gb: float) -> bool:
        """Check if sufficient RAM is available."""
        return self._get_available_ram_gb() >= required_gb
