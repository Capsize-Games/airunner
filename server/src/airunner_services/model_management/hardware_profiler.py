"""Hardware profiling helpers for model resource management."""

from __future__ import annotations

import logging
import platform
from dataclasses import dataclass

import psutil
import torch


logger = logging.getLogger(__name__)


def _nvml_device_count() -> int:
    """Return number of NVIDIA GPUs via NVML."""
    try:
        import pynvml  # noqa: PLC0415

        pynvml.nvmlInit()
        count = pynvml.nvmlDeviceGetCount()
        pynvml.nvmlShutdown()
        return count
    except Exception:
        return 0


def _nvml_device_name(index: int = 0) -> str | None:
    """Return NVIDIA GPU name via NVML."""
    try:
        import pynvml  # noqa: PLC0415

        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(index)
        name: str | bytes = pynvml.nvmlDeviceGetName(handle)
        pynvml.nvmlShutdown()
        if isinstance(name, bytes):
            name = name.decode("utf-8")
        return name
    except Exception:
        return None


def _nvml_total_vram_gb() -> float:
    """Return total VRAM in GB for the first NVIDIA GPU via NVML."""
    try:
        import pynvml  # noqa: PLC0415

        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        info = pynvml.nvmlDeviceGetMemoryInfo(handle)
        pynvml.nvmlShutdown()
        return info.total / (1024**3)
    except Exception:
        return 0.0


def _nvml_available_vram_gb() -> float:
    """Return free VRAM in GB for the first NVIDIA GPU via NVML."""
    try:
        import pynvml  # noqa: PLC0415

        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        info = pynvml.nvmlDeviceGetMemoryInfo(handle)
        pynvml.nvmlShutdown()
        return info.free / (1024**3)
    except Exception:
        return 0.0


@dataclass
class HardwareProfile:
    """Hardware capabilities and current resource availability."""

    total_vram_gb: float
    available_vram_gb: float
    total_ram_gb: float
    available_ram_gb: float
    cuda_available: bool
    cuda_compute_capability: tuple[int, int] | None
    device_name: str | None
    cpu_count: int
    platform: str
    num_gpus: int = 0


class HardwareProfiler:
    """Detect and monitor system hardware resources.

    Uses NVML (nvidia-ml-py) for NVIDIA GPU detection — works directly
    with the NVIDIA driver without requiring ``nvidia-smi`` on the system
    path. Falls back to ``torch.cuda`` APIs when NVML is unavailable.
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_profile(self) -> HardwareProfile:
        """Return the current hardware profile."""
        cuda_available = self._cuda_available()
        num_gpus = self._num_gpus()
        return HardwareProfile(
            total_vram_gb=self._get_total_vram_gb(),
            available_vram_gb=self._get_available_vram_gb(),
            total_ram_gb=self._get_total_ram_gb(),
            available_ram_gb=self._get_available_ram_gb(),
            cuda_available=cuda_available,
            cuda_compute_capability=self._get_cuda_compute_capability(),
            device_name=self._get_device_name(),
            cpu_count=self._get_cpu_count(),
            platform=platform.system(),
            num_gpus=num_gpus,
        )

    def is_ampere_or_newer(self) -> bool:
        """Return whether the active GPU is Ampere or newer."""
        capability = self._get_cuda_compute_capability()
        if capability is None:
            return False
        return capability[0] >= 8

    def has_sufficient_vram(self, required_gb: float) -> bool:
        """Return whether enough VRAM is currently available."""
        return self._get_available_vram_gb() >= required_gb

    def has_sufficient_ram(self, required_gb: float) -> bool:
        """Return whether enough RAM is currently available."""
        return self._get_available_ram_gb() >= required_gb

    # ------------------------------------------------------------------
    # VRAM — NVML first, torch.cuda fallback
    # ------------------------------------------------------------------

    def _get_total_vram_gb(self) -> float:
        total = _nvml_total_vram_gb()
        if total > 0:
            return total
        if torch.cuda.is_available():
            return torch.cuda.get_device_properties(0).total_memory / (
                1024**3
            )
        return 0.0

    def _get_available_vram_gb(self) -> float:
        free = _nvml_available_vram_gb()
        if free > 0:
            return free
        if torch.cuda.is_available():
            try:
                free_memory, _ = torch.cuda.mem_get_info()
                return free_memory / (1024**3)
            except Exception as error:
                self.logger.warning(
                    "Could not detect VRAM via torch: %s", error
                )
                return 0.0
        return 0.0

    # ------------------------------------------------------------------
    # CUDA capability
    # ------------------------------------------------------------------

    def _cuda_available(self) -> bool:
        if torch.cuda.is_available():
            return True
        return _nvml_device_count() > 0

    def _get_cuda_compute_capability(self) -> tuple[int, int] | None:
        if not torch.cuda.is_available():
            return None
        props = torch.cuda.get_device_properties(0)
        return props.major, props.minor

    # ------------------------------------------------------------------
    # Device name
    # ------------------------------------------------------------------

    def _get_device_name(self) -> str | None:
        name = _nvml_device_name()
        if name is not None:
            return name
        if torch.cuda.is_available():
            return torch.cuda.get_device_name(0)
        return None

    # ------------------------------------------------------------------
    # GPU count
    # ------------------------------------------------------------------

    def _num_gpus(self) -> int:
        nvml_count = _nvml_device_count()
        if nvml_count > 0:
            return nvml_count
        if torch.cuda.is_available():
            return torch.cuda.device_count()
        return 0

    # ------------------------------------------------------------------
    # RAM
    # ------------------------------------------------------------------

    @staticmethod
    def _get_total_ram_gb() -> float:
        return psutil.virtual_memory().total / (1024**3)

    @staticmethod
    def _get_available_ram_gb() -> float:
        return psutil.virtual_memory().available / (1024**3)

    # ------------------------------------------------------------------
    # CPU
    # ------------------------------------------------------------------

    @staticmethod
    def _get_cpu_count() -> int:
        try:
            count = psutil.cpu_count()
            if count is not None:
                return count
        except Exception:
            pass
        return 1
