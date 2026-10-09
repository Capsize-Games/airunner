"""Shared fixtures for P09 prerequisite-diagnostics tests.

Holds the scripted nvidia-smi output, the fully-supported
measurement fixture, the torchless-child runner, and lookup
helpers shared by the diagnostics and profiler test modules.
Defines no test functions of its own.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from airunner_services.model_management import prerequisites
from airunner_services.model_management.prerequisite_types import (
    PrerequisiteCheck,
    PrerequisiteMeasurements,
    PrerequisiteReport,
)

_SERVICES_SRC = Path(prerequisites.__file__).resolve().parents[2]
_SMI_CSV = "NVIDIA GeForce RTX 4090, 550.54.14, 24576, 23000, 8.9\n"
_ML_MODULES = ("torch", "torchvision", "torchaudio")

_CHILD_SCRIPT = (
    "import importlib.abc, json, os, sys\n"
    "blocked = {'torch', 'torchvision', 'torchaudio'}\n"
    "class _B(importlib.abc.MetaPathFinder):\n"
    "    def find_spec(self, n, p=None, t=None):\n"
    "        if n.split('.')[0] in blocked:\n"
    "            raise ImportError('blocked: ' + n)\n"
    "        return None\n"
    "sys.meta_path.insert(0, _B())\n"
    "os.environ['PATH'] = sys.argv[2]\n"
    "from airunner_services.model_management import prerequisites as P\n"
    "from airunner_services.model_management import hardware_profiler as H\n"
    "profile = H.HardwareProfiler().get_profile()\n"
    "report = P.report_from_profile(profile, sys.argv[1])\n"
    "print(json.dumps({'torch_loaded': 'torch' in sys.modules,\n"
    " 'gpu_source': profile.gpu_source,\n"
    " 'overall': report.overall.value,\n"
    " 'statuses': {c.check_id: c.status.value for c in report.checks}}))\n"
)

_BASE: dict[str, Any] = dict(
    gpu_detected=True,
    device_name="NVIDIA RTX 4000 Ada",
    total_vram_gb=20.0,
    cuda_compute_capability=(8, 9),
    driver_version="550.54.14",
    total_ram_gb=64.0,
    available_ram_gb=48.0,
    free_disk_gb=120.0,
    disk_path="/data",
    module_versions={
        "torch": "2.13.0+cu129",
        "torchvision": "0.28.0+cu129",
        "torchaudio": "2.11.0+cu129",
    },
)


class _FakeSubprocess:
    """Fake subprocess module with scripted nvidia-smi output."""

    TimeoutExpired = subprocess.TimeoutExpired

    def __init__(self, stdout: str | None) -> None:
        self.stdout = stdout

    def run(
        self, *args: Any, **kwargs: Any
    ) -> subprocess.CompletedProcess[str]:
        """Replay scripted output, or act as if smi is missing."""
        if self.stdout is None:
            raise FileNotFoundError("nvidia-smi hidden for this test")
        return subprocess.CompletedProcess(args[0], 0, self.stdout, "")


def _good_measurements(**overrides: Any) -> PrerequisiteMeasurements:
    """Build a fully-supported fixture, overridable per field."""
    return PrerequisiteMeasurements(**(_BASE | overrides))


def _check(report: PrerequisiteReport, check_id: str) -> PrerequisiteCheck:
    """Fetch one check by id."""
    return {c.check_id: c for c in report.checks}[check_id]


def _run_torchless_child(
    data_dir: Path, empty_bin: Path
) -> subprocess.CompletedProcess[str]:
    """Run the diagnostics child with torch blocked, smi hidden."""
    env = dict(os.environ, PYTHONPATH=str(_SERVICES_SRC))
    return subprocess.run(
        [sys.executable, "-c", _CHILD_SCRIPT, str(data_dir), str(empty_bin)],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )
