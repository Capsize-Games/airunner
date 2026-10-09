"""P09 profiler, torchless-child, and lazy-export tests.

Proves the hardware profiler degrades without torch or
nvidia-smi, parses smi facts without importing torch, and
that the whole diagnostics path works with torch absent --
no import traceback, no GPU load. CPU-only: nvidia-smi is
faked, real disk reads use tmp_path, no model, network,
GPU, or DB use.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from airunner_services import model_management
from airunner_services.model_management import prerequisites
from airunner_services.model_management import hardware_profiler as profiler
from airunner_services.model_management.hardware_profiler import (
    HardwareProfiler,
)
from airunner_services.model_management.prerequisite_types import (
    PrerequisiteStatus,
)
from test_release_p09_support import (
    _FakeSubprocess,
    _ML_MODULES,
    _SMI_CSV,
    _run_torchless_child,
)


def test_profiler_reports_without_torch_or_smi(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """get_profile degrades to zeros/None instead of raising."""
    for name in _ML_MODULES:
        monkeypatch.setitem(sys.modules, name, None)
    monkeypatch.setattr(profiler, "subprocess", _FakeSubprocess(None))
    profile = HardwareProfiler().get_profile()
    assert profile.cuda_available is False
    assert profile.device_name is None
    assert profile.gpu_source == "none"
    assert profile.total_vram_gb == 0.0
    versions = prerequisites.collect_module_versions()
    assert versions["torch"] is None
    report = prerequisites.report_from_profile(profile, tmp_path, versions)
    assert report.overall is PrerequisiteStatus.UNSUPPORTED
    assert prerequisites.measure_free_disk_gb(tmp_path) is not None
    assert prerequisites.measure_free_disk_gb(tmp_path / "nope") is None


def test_profiler_reads_nvidia_smi_when_torch_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """nvidia-smi facts are parsed without importing torch."""
    for name in _ML_MODULES:
        monkeypatch.setitem(sys.modules, name, None)
    monkeypatch.setattr(profiler, "subprocess", _FakeSubprocess(_SMI_CSV))
    profile = HardwareProfiler().get_profile()
    assert profile.cuda_available is False
    assert profile.device_name == "NVIDIA GeForce RTX 4090"
    assert profile.driver_version == "550.54.14"
    assert profile.gpu_source == "nvidia-smi"
    assert abs(profile.total_vram_gb - 24.0) < 0.001
    assert profile.cuda_compute_capability == (8, 9)
    assert HardwareProfiler().is_ampere_or_newer() is True


def test_diagnostics_subprocess_without_ml_runtime(tmp_path: Path) -> None:
    """A torchless interpreter gets diagnostics, never a traceback."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    empty_bin = tmp_path / "emptybin"
    empty_bin.mkdir()
    proc = _run_torchless_child(data_dir, empty_bin)
    assert proc.returncode == 0, proc.stderr
    assert "Traceback" not in proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["torch_loaded"] is False
    assert payload["gpu_source"] == "none"
    assert payload["overall"] == "unsupported"
    assert payload["statuses"]["runtime_torch"] == "unsupported"
    assert payload["statuses"]["free_disk"] == "supported"


def test_package_lazy_exports_still_resolve() -> None:
    """The table-driven __getattr__ resolves and rejects correctly."""
    assert isinstance(model_management.QuantizationStrategy, type)
    with pytest.raises(AttributeError, match="DoesNotExistP09"):
        model_management.DoesNotExistP09
