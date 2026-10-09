"""Types and R02 gates for Linux v1 prerequisite diagnostics.

Verdicts are three-state: a check is ``supported`` when its gate is
met, ``unsupported`` when a published gate is missed, and ``unknown``
when no gate is published or the value could not be measured. Only
``required`` checks fail a report; advisory checks inform repairs.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

# R02 gates (release-planning/linux-v1/hardware-models.md). The VRAM
# floor is the parent-spec product requirement (R02 section 1: 16 GB
# minimum). The disk floor is the low end of R02 section 3's proposed
# 30-40 GB planning floor (unverified -- detail text says so). The
# compute threshold is the documented Ampere bar for one optional fast
# path (R02 sections 1/4), not a hard floor, so compute is advisory.
MIN_VRAM_GB = 16.0
MIN_FREE_DISK_GB = 30.0
AMPERE_CAPABILITY = (8, 0)
# R02 section 1 pinned lines; matches daemon.OPTIONAL_ML_MODULES.
REQUIRED_ML_MODULES = ("torch", "torchvision", "torchaudio")

REQUIRED_CHECK_IDS = frozenset(
    {
        "gpu_present",
        "vram_capacity",
        "gpu_driver",
        "free_disk",
        "runtime_torch",
        "runtime_torchvision",
        "runtime_torchaudio",
    }
)


class PrerequisiteStatus(str, Enum):
    """Three-state verdict for one prerequisite check."""

    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class PrerequisiteCheck:
    """One evaluated prerequisite with repair guidance."""

    check_id: str
    label: str
    status: PrerequisiteStatus
    detail: str
    remediation: str

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable view of this check."""
        return {
            "check_id": self.check_id,
            "label": self.label,
            "status": self.status.value,
            "detail": self.detail,
            "remediation": self.remediation,
            "required": self.check_id in REQUIRED_CHECK_IDS,
        }


@dataclass(frozen=True)
class PrerequisiteReport:
    """Verdicts for every evaluated prerequisite."""

    checks: tuple[PrerequisiteCheck, ...]

    @property
    def overall(self) -> PrerequisiteStatus:
        """Aggregate required checks; advisories cannot fail."""
        required = [
            check.status
            for check in self.checks
            if check.check_id in REQUIRED_CHECK_IDS
        ]
        if PrerequisiteStatus.UNSUPPORTED in required:
            return PrerequisiteStatus.UNSUPPORTED
        if PrerequisiteStatus.UNKNOWN in required:
            return PrerequisiteStatus.UNKNOWN
        return PrerequisiteStatus.SUPPORTED

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable view of this report."""
        return {
            "overall": self.overall.value,
            "checks": [check.to_dict() for check in self.checks],
        }


@dataclass(frozen=True)
class PrerequisiteMeasurements:
    """Plain-data inputs; fixtures drive verdicts without hardware."""

    gpu_detected: bool
    device_name: str | None
    total_vram_gb: float | None
    cuda_compute_capability: tuple[int, int] | None
    driver_version: str | None
    total_ram_gb: float | None
    available_ram_gb: float | None
    free_disk_gb: float | None
    disk_path: str
    # Installed version per ML module; None (or absent) means missing.
    module_versions: dict[str, str | None]
