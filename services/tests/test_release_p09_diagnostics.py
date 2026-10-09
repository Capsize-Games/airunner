"""P09 verdict, serialization, and collector diagnostics tests.

Proves fixture hardware profiles produce precise
supported/unsupported/unknown prerequisite verdicts and that
missing ML runtime modules are reported as structured
diagnostics before any model work. CPU-only: no model,
network, GPU, or DB use.
"""

from __future__ import annotations

import json
import sys

from airunner_services.model_management import prerequisites
from airunner_services.model_management.prerequisite_types import (
    PrerequisiteStatus,
)
from test_release_p09_support import _check, _good_measurements


def test_supported_fixture_reports_supported() -> None:
    """A fully-capable fixture passes every required check."""
    report = prerequisites.evaluate_prerequisites(_good_measurements())
    assert report.overall is PrerequisiteStatus.SUPPORTED
    for check_id in (
        "gpu_present",
        "vram_capacity",
        "gpu_driver",
        "free_disk",
        "runtime_torch",
    ):
        assert _check(report, check_id).status is PrerequisiteStatus.SUPPORTED


def test_small_vram_reports_unsupported_with_repair() -> None:
    """8 GB VRAM fails precisely, naming the 16 GB floor and repair."""
    report = prerequisites.evaluate_prerequisites(
        _good_measurements(total_vram_gb=8.0)
    )
    assert report.overall is PrerequisiteStatus.UNSUPPORTED
    vram = _check(report, "vram_capacity")
    assert vram.status is PrerequisiteStatus.UNSUPPORTED
    assert "16 GB" in vram.detail
    assert "16 GB" in vram.remediation


def test_missing_gpu_is_unsupported_with_unknown_details() -> None:
    """No GPU fails the presence gate; unmeasurable facts stay unknown."""
    report = prerequisites.evaluate_prerequisites(
        _good_measurements(
            gpu_detected=False,
            device_name=None,
            total_vram_gb=None,
            cuda_compute_capability=None,
            driver_version=None,
        )
    )
    assert report.overall is PrerequisiteStatus.UNSUPPORTED
    assert (
        _check(report, "gpu_present").status is PrerequisiteStatus.UNSUPPORTED
    )
    assert _check(report, "vram_capacity").status is PrerequisiteStatus.UNKNOWN
    assert _check(report, "gpu_compute").status is PrerequisiteStatus.UNKNOWN


def test_missing_torch_is_a_structured_diagnostic() -> None:
    """A missing ML module is reported, never an import traceback."""
    report = prerequisites.evaluate_prerequisites(
        _good_measurements(module_versions={"torchvision": "0.28.0+cu129"})
    )
    assert report.overall is PrerequisiteStatus.UNSUPPORTED
    torch_check = _check(report, "runtime_torch")
    assert torch_check.status is PrerequisiteStatus.UNSUPPORTED
    assert "not installed" in torch_check.detail
    assert "re-run" in torch_check.remediation


def test_below_ampere_compute_is_advisory_only() -> None:
    """A pre-Ampere GPU loses the fast path but not the verdict."""
    report = prerequisites.evaluate_prerequisites(
        _good_measurements(cuda_compute_capability=(7, 5))
    )
    assert report.overall is PrerequisiteStatus.SUPPORTED
    compute = _check(report, "gpu_compute")
    assert compute.status is PrerequisiteStatus.UNSUPPORTED
    assert "may still work" in compute.detail
    assert compute.to_dict()["required"] is False


def test_ram_and_driver_report_measurements_honestly() -> None:
    """RAM has no published gate; driver notes its pending floor."""
    report = prerequisites.evaluate_prerequisites(_good_measurements())
    ram = _check(report, "system_ram")
    assert ram.status is PrerequisiteStatus.UNKNOWN
    assert "64.0" in ram.detail
    assert ram.to_dict()["required"] is False
    driver = _check(report, "gpu_driver")
    assert driver.status is PrerequisiteStatus.SUPPORTED
    assert "550.54.14" in driver.detail
    assert "No minimum" in driver.detail
    unreadable = prerequisites.evaluate_prerequisites(
        _good_measurements(driver_version=None)
    )
    assert unreadable.overall is PrerequisiteStatus.UNKNOWN
    check = _check(unreadable, "gpu_driver")
    assert check.status is PrerequisiteStatus.UNKNOWN


def test_disk_reports_unknown_and_below_floor() -> None:
    """Unmeasurable disk is unknown; 10 GB misses the planning floor."""
    missing = prerequisites.evaluate_prerequisites(
        _good_measurements(free_disk_gb=None)
    )
    assert missing.overall is PrerequisiteStatus.UNKNOWN
    assert _check(missing, "free_disk").status is PrerequisiteStatus.UNKNOWN
    low = prerequisites.evaluate_prerequisites(
        _good_measurements(free_disk_gb=10.0)
    )
    assert low.overall is PrerequisiteStatus.UNSUPPORTED
    assert "30 GB" in _check(low, "free_disk").detail


def test_report_serializes_and_renders_for_repair() -> None:
    """Dict and text views carry verdicts and repair steps."""
    report = prerequisites.evaluate_prerequisites(
        _good_measurements(total_vram_gb=8.0)
    )
    payload = json.loads(json.dumps(report.to_dict()))
    assert payload["overall"] == "unsupported"
    vram = next(
        c for c in payload["checks"] if c["check_id"] == "vram_capacity"
    )
    assert vram["status"] == "unsupported"
    assert vram["required"] is True
    text = prerequisites.format_report_text(report)
    assert "Prerequisite report: unsupported" in text
    assert "[required] Total VRAM: unsupported" in text
    assert "[advisory] System RAM: unknown" in text
    assert "Repair: Use a GPU with at least 16 GB of VRAM." in text
    assert "never start automatically" in text


def test_collectors_report_missing_without_importing() -> None:
    """Module probing never imports and never raises on garbage."""
    versions = prerequisites.collect_module_versions(
        ("sys", "missing_module_p09")
    )
    assert versions == {"sys": "unknown", "missing_module_p09": None}
    assert "missing_module_p09" not in sys.modules
