"""Prerequisite check rules for the Linux v1 NVIDIA profile.

Each builder maps plain measurements to one outcome triple of
(status, detail, remediation). Builders are pure: no I/O, no imports
beyond this package's types, no GPU use. ``evaluate_prerequisites``
assembles the triples into a report.
"""

from __future__ import annotations

from airunner_services.model_management.prerequisite_types import (
    AMPERE_CAPABILITY,
    MIN_FREE_DISK_GB,
    MIN_VRAM_GB,
    REQUIRED_ML_MODULES,
    PrerequisiteCheck,
    PrerequisiteMeasurements,
    PrerequisiteStatus,
)

_Outcome = tuple[PrerequisiteStatus, str, str]


def _gpu_outcome(m: PrerequisiteMeasurements) -> _Outcome:
    """Outcome data for NVIDIA GPU detection (required)."""
    if m.gpu_detected:
        name = m.device_name or "Unnamed NVIDIA GPU"
        return (
            PrerequisiteStatus.SUPPORTED,
            f"{name} is visible to the runtime probes.",
            "",
        )
    return (
        PrerequisiteStatus.UNSUPPORTED,
        "No NVIDIA GPU answered the torch/nvidia-smi probes.",
        "Install an NVIDIA GPU (16 GB+ VRAM) and the NVIDIA "
        "driver, then re-run this report.",
    )


def _vram_outcome(m: PrerequisiteMeasurements) -> _Outcome:
    """Outcome data for total VRAM against the 16 GB floor."""
    if m.total_vram_gb is None:
        return (
            PrerequisiteStatus.UNKNOWN,
            "VRAM size could not be measured.",
            "Check that nvidia-smi runs, then re-run this report.",
        )
    if m.total_vram_gb >= MIN_VRAM_GB:
        return (
            PrerequisiteStatus.SUPPORTED,
            f"{m.total_vram_gb:.1f} GB meets the 16 GB minimum.",
            "",
        )
    return (
        PrerequisiteStatus.UNSUPPORTED,
        f"{m.total_vram_gb:.1f} GB is below the 16 GB minimum.",
        "Use a GPU with at least 16 GB of VRAM.",
    )


def _measured_compute_outcome(capability: tuple[int, int]) -> _Outcome:
    """Outcome data for a measured compute capability (advisory)."""
    text = f"{capability[0]}.{capability[1]}"
    if capability >= AMPERE_CAPABILITY:
        return (
            PrerequisiteStatus.SUPPORTED,
            f"Compute {text}: flash-attention fast path is on.",
            "",
        )
    return (
        PrerequisiteStatus.UNSUPPORTED,
        f"Compute {text} is below Ampere (8.0): fast path off. "
        "Generation may still work; no hard floor is published.",
        "No action required for generation.",
    )


def _compute_outcome(m: PrerequisiteMeasurements) -> _Outcome:
    """Outcome data for the optional Ampere fast path (advisory)."""
    capability = m.cuda_compute_capability
    if capability is None:
        return (
            PrerequisiteStatus.UNKNOWN,
            "Compute capability could not be measured.",
            "Check that nvidia-smi runs, then re-run this report.",
        )
    return _measured_compute_outcome(capability)


def _driver_missing_outcome(m: PrerequisiteMeasurements) -> _Outcome:
    """Outcome data when no driver version was measured."""
    if m.gpu_detected:
        return (
            PrerequisiteStatus.UNKNOWN,
            "GPU works but the driver version is unreadable.",
            "Install nvidia-smi, then re-run this report.",
        )
    return (
        PrerequisiteStatus.UNSUPPORTED,
        "No NVIDIA driver answered the nvidia-smi probe.",
        "Install the NVIDIA driver, then re-run this report.",
    )


def _driver_outcome(m: PrerequisiteMeasurements) -> _Outcome:
    """Outcome data for NVIDIA driver presence (required)."""
    if m.driver_version is None:
        return _driver_missing_outcome(m)
    return (
        PrerequisiteStatus.SUPPORTED,
        f"Driver {m.driver_version} is responding. No minimum "
        "driver version is published yet.",
        "",
    )


def _ram_outcome(m: PrerequisiteMeasurements) -> _Outcome:
    """Outcome data for system RAM (advisory: no gate published)."""
    if m.total_ram_gb is None:
        return (
            PrerequisiteStatus.UNKNOWN,
            "System RAM could not be measured.",
            "Reinstall the application runtime, then re-run.",
        )
    extra = ""
    if m.available_ram_gb is not None:
        extra = f" ({m.available_ram_gb:.1f} GB available)"
    return (
        PrerequisiteStatus.UNKNOWN,
        f"{m.total_ram_gb:.1f} GB total RAM{extra}. No minimum "
        "RAM is published, so no verdict is given.",
        "",
    )


def _measured_disk_outcome(free_gb: float, disk_path: str) -> _Outcome:
    """Outcome data for a measured free-disk value."""
    if free_gb >= MIN_FREE_DISK_GB:
        return (
            PrerequisiteStatus.SUPPORTED,
            f"{free_gb:.1f} GB free at {disk_path} meets "
            "the 30 GB planning floor.",
            "",
        )
    return (
        PrerequisiteStatus.UNSUPPORTED,
        f"{free_gb:.1f} GB free at {disk_path} is below "
        "the 30 GB planning floor.",
        "Free disk space or choose a data directory with 30 GB free.",
    )


def _disk_outcome(m: PrerequisiteMeasurements) -> _Outcome:
    """Outcome data for free disk against the 30 GB planning floor."""
    if m.free_disk_gb is None:
        return (
            PrerequisiteStatus.UNKNOWN,
            f"Free disk at {m.disk_path} could not be measured.",
            "Check the path exists and is readable, then re-run.",
        )
    return _measured_disk_outcome(m.free_disk_gb, m.disk_path)


def _module_text(name: str, version: str | None) -> tuple[str, str]:
    """Detail and remediation text for one runtime module."""
    if version is None:
        return (
            f"{name} is not installed.",
            "Install the Linux NVIDIA runtime profile for your "
            "installation method, then re-run this report.",
        )
    return (f"{name} {version} is installed.", "")


def module_checks(
    m: PrerequisiteMeasurements,
) -> list[PrerequisiteCheck]:
    """Build one required check per ML runtime module."""
    checks = []
    for name in REQUIRED_ML_MODULES:
        version = m.module_versions.get(name)
        detail, remediation = _module_text(name, version)
        if version is None:
            status = PrerequisiteStatus.UNSUPPORTED
        else:
            status = PrerequisiteStatus.SUPPORTED
        checks.append(
            PrerequisiteCheck(
                f"runtime_{name}",
                f"{name} runtime installed",
                status,
                detail,
                remediation,
            )
        )
    return checks


CHECK_BUILDERS = (
    ("gpu_present", "NVIDIA GPU detected", _gpu_outcome),
    ("vram_capacity", "Total VRAM", _vram_outcome),
    ("gpu_compute", "Compute capability", _compute_outcome),
    ("gpu_driver", "NVIDIA driver responding", _driver_outcome),
    ("system_ram", "System RAM", _ram_outcome),
    ("free_disk", "Free disk", _disk_outcome),
)
