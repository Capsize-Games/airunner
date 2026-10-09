"""Hardware profiling helpers for model resource management.

GPU facts never import torch at module scope: torch is an optional ML
runtime (see ``daemon.OPTIONAL_ML_MODULES``), and the prerequisite
diagnostics built on this module must keep working -- and report torch
as missing -- when it is not installed. CUDA facts come from a lazy
torch probe first, then from ``nvidia-smi`` (a driver query that loads
no CUDA context and runs no GPU workload), then degrade to zeros/None.
"""

from __future__ import annotations

import logging
import platform
import subprocess
from dataclasses import dataclass
from typing import Any

_NVIDIA_SMI_FIELDS = "name,driver_version,memory.total,memory.free,compute_cap"
_MIB_PER_GIB = 1024.0


def _torch_cuda() -> tuple[bool, Any | None]:
    """Return (cuda_available, cuda_module); never raises."""
    try:
        import torch
    except ImportError:
        return False, None
    try:
        if not torch.cuda.is_available():
            return False, None
    except Exception:
        return False, None
    return True, torch.cuda


def _run_nvidia_smi() -> str | None:
    """Return raw nvidia-smi output, or None when unavailable."""
    command = [
        "nvidia-smi",
        f"--query-gpu={_NVIDIA_SMI_FIELDS}",
        "--format=csv,noheader,nounits",
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=2.0,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def _parse_gpu_csv(output: str) -> dict[str, str] | None:
    """Parse the first nvidia-smi GPU row into field values."""
    line = next(
        (row for row in output.splitlines() if row.strip()),
        "",
    )
    values = [value.strip() for value in line.split(",")]
    keys = _NVIDIA_SMI_FIELDS.split(",")
    if len(values) != len(keys):
        return None
    return dict(zip(keys, values))


def _query_nvidia_smi() -> dict[str, str] | None:
    """Return first-GPU nvidia-smi fields; None when unusable."""
    output = _run_nvidia_smi()
    if output is None:
        return None
    return _parse_gpu_csv(output)


def _total_vram_gb(cuda: Any | None, smi: dict[str, str] | None) -> float:
    """Return total VRAM in GiB; torch first, then nvidia-smi."""
    if cuda is not None:
        try:
            props = cuda.get_device_properties(0)
            return float(props.total_memory) / (1024**3)
        except Exception:
            pass
    if smi is not None:
        try:
            return float(smi["memory.total"]) / _MIB_PER_GIB
        except (KeyError, ValueError):
            pass
    return 0.0


def _free_vram_gb(cuda: Any | None, smi: dict[str, str] | None) -> float:
    """Return free VRAM in GiB; torch first, then nvidia-smi."""
    if cuda is not None:
        try:
            free_memory, _ = cuda.mem_get_info()
            return float(free_memory) / (1024**3)
        except Exception:
            pass
    if smi is not None:
        try:
            return float(smi["memory.free"]) / _MIB_PER_GIB
        except (KeyError, ValueError):
            pass
    return 0.0


def _compute_capability(
    cuda: Any | None, smi: dict[str, str] | None
) -> tuple[int, int] | None:
    """Return compute capability; torch first, then nvidia-smi."""
    if cuda is not None:
        try:
            props = cuda.get_device_properties(0)
            return int(props.major), int(props.minor)
        except Exception:
            pass
    if smi is not None:
        try:
            major, minor = smi["compute_cap"].split(".")
            return int(major), int(minor)
        except (KeyError, ValueError):
            pass
    return None


def _device_name(cuda: Any | None, smi: dict[str, str] | None) -> str | None:
    """Return the GPU name; torch first, then nvidia-smi."""
    if cuda is not None:
        try:
            return str(cuda.get_device_name(0))
        except Exception:
            pass
    if smi is not None:
        return smi.get("name") or None
    return None


def _driver_version(smi: dict[str, str] | None) -> str | None:
    """Return the NVIDIA driver version, or None."""
    if smi is None:
        return None
    return smi.get("driver_version") or None


def _gpu_source(cuda_available: bool, smi: dict[str, str] | None) -> str:
    """Name the probe that produced GPU facts."""
    if cuda_available:
        return "torch"
    if smi is not None:
        return "nvidia-smi"
    return "none"


def _ram_gb(field: str) -> float:
    """Return total/available RAM in GiB; 0.0 when unreadable."""
    try:
        import psutil
    except ImportError:
        return 0.0
    try:
        value = getattr(psutil.virtual_memory(), field)
        return float(value) / (1024**3)
    except Exception:
        return 0.0


def _cpu_count() -> int:
    """Return the CPU count, defaulting to 1 when unreadable."""
    try:
        import psutil
    except ImportError:
        return 1
    try:
        return int(psutil.cpu_count() or 1)
    except Exception:
        return 1


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
    driver_version: str | None = None
    gpu_source: str = "none"


class HardwareProfiler:
    """Detect and monitor system hardware resources."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)

    def get_profile(self) -> HardwareProfile:
        """Return the current hardware profile; never raises."""
        cuda_available, cuda = _torch_cuda()
        smi = _query_nvidia_smi()
        if not cuda_available and smi is None:
            self.logger.debug("No GPU probe produced GPU facts.")
        return HardwareProfile(
            total_vram_gb=_total_vram_gb(cuda, smi),
            available_vram_gb=_free_vram_gb(cuda, smi),
            total_ram_gb=_ram_gb("total"),
            available_ram_gb=_ram_gb("available"),
            cuda_available=cuda_available,
            cuda_compute_capability=_compute_capability(cuda, smi),
            device_name=_device_name(cuda, smi),
            cpu_count=_cpu_count(),
            platform=platform.system(),
            driver_version=_driver_version(smi),
            gpu_source=_gpu_source(cuda_available, smi),
        )

    def is_ampere_or_newer(self) -> bool:
        """Return whether the GPU is Ampere or newer, any probe."""
        capability = self.get_profile().cuda_compute_capability
        return capability is not None and capability >= (8, 0)

    def has_sufficient_vram(self, required_gb: float) -> bool:
        """Return whether enough VRAM is currently available."""
        return self.get_profile().available_vram_gb >= required_gb

    def has_sufficient_ram(self, required_gb: float) -> bool:
        """Return whether enough RAM is currently available."""
        return self.get_profile().available_ram_gb >= required_gb
