"""Evaluate and collect Linux v1 prerequisite diagnostics.

``evaluate_prerequisites`` is pure: fixtures drive every verdict with
no I/O. The collectors below gather live measurements without
importing torch or any ML runtime -- module presence uses
``importlib.find_spec`` (no code execution) and versions use
``importlib.metadata`` (no import), so missing dependencies surface as
structured diagnostics instead of tracebacks. Nothing here loads the
GPU or starts downloads.
"""

from __future__ import annotations

import importlib.metadata
import importlib.util
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from airunner_services.model_management.prerequisite_checks import (
    CHECK_BUILDERS,
    module_checks,
)
from airunner_services.model_management.prerequisite_types import (
    REQUIRED_CHECK_IDS,
    REQUIRED_ML_MODULES,
    PrerequisiteCheck,
    PrerequisiteMeasurements,
    PrerequisiteReport,
    PrerequisiteStatus,
)

if TYPE_CHECKING:
    from airunner_services.model_management.hardware_profiler import (
        HardwareProfile,
    )


def evaluate_prerequisites(
    m: PrerequisiteMeasurements,
) -> PrerequisiteReport:
    """Evaluate measurements into verdicts. Pure: no I/O, no imports."""
    checks = [
        PrerequisiteCheck(check_id, label, *outcome(m))
        for check_id, label, outcome in CHECK_BUILDERS
    ]
    checks.extend(module_checks(m))
    return PrerequisiteReport(checks=tuple(checks))


def _module_version(name: str) -> str | None:
    """Return an installed module version; None means missing."""
    try:
        found = importlib.util.find_spec(name) is not None
    except ImportError:
        return None
    if not found:
        return None
    try:
        return importlib.metadata.version(name)
    except Exception:
        return "unknown"


def collect_module_versions(
    names: tuple[str, ...] = REQUIRED_ML_MODULES,
) -> dict[str, str | None]:
    """Find ML modules without importing them; None means missing."""
    return {name: _module_version(name) for name in names}


def measure_free_disk_gb(path: str | Path) -> float | None:
    """Return free GiB at a path; None when it cannot be read."""
    try:
        return shutil.disk_usage(path).free / (1024**3)
    except OSError:
        return None


def _positive_or_none(value: float) -> float | None:
    """Map a 0.0/unreadable profile measurement to None."""
    return value if value > 0 else None


def _profile_gpu_detected(profile: HardwareProfile) -> bool:
    """Return whether a live profile shows a working GPU."""
    return profile.device_name is not None or profile.cuda_available


def _measurements_from_profile(
    profile: HardwareProfile,
    disk_path: str | Path,
    module_versions: dict[str, str | None],
) -> PrerequisiteMeasurements:
    """Translate one live profile into plain measurements."""
    return PrerequisiteMeasurements(
        gpu_detected=_profile_gpu_detected(profile),
        device_name=profile.device_name,
        total_vram_gb=_positive_or_none(profile.total_vram_gb),
        cuda_compute_capability=profile.cuda_compute_capability,
        driver_version=profile.driver_version,
        total_ram_gb=_positive_or_none(profile.total_ram_gb),
        available_ram_gb=_positive_or_none(profile.available_ram_gb),
        free_disk_gb=measure_free_disk_gb(disk_path),
        disk_path=str(disk_path),
        module_versions=module_versions,
    )


def report_from_profile(
    profile: HardwareProfile,
    disk_path: str | Path,
    module_versions: dict[str, str | None] | None = None,
) -> PrerequisiteReport:
    """Evaluate one live HardwareProfile into a report."""
    if module_versions is None:
        module_versions = collect_module_versions()
    measurements = _measurements_from_profile(
        profile, disk_path, module_versions
    )
    return evaluate_prerequisites(measurements)


def format_report_text(report: PrerequisiteReport) -> str:
    """Render the report as lines for CLIs, logs and repair flows."""
    lines = [f"Prerequisite report: {report.overall.value}"]
    for check in report.checks:
        text = f"[{_scope(check)}] {check.label}: {check.status.value}"
        lines.append(text)
        lines.append(f"  {check.detail}")
        if check.status is not PrerequisiteStatus.SUPPORTED:
            lines.append(f"  Repair: {check.remediation}")
    lines.append("Model downloads never start automatically.")
    return "\n".join(lines)


def _scope(check: PrerequisiteCheck) -> str:
    """Return the report scope label for one check."""
    if check.check_id in REQUIRED_CHECK_IDS:
        return "required"
    return "advisory"
