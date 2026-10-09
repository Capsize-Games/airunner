"""Regression coverage for the full-tree allocator skew (issue #2241).

Full-tree pytest collection imports the art-service-runtime tests first.
Their ``service_app`` import chain must set the torch allocator env vars
before torch itself loads: a late change makes torch's load-time parse
(``native``) disagree with its runtime parse (``cudaMallocAsync``),
tripping ``CUDAAllocatorConfig.cpp:44`` and segfaulting the first CUDA
malloc. The repro runs in a subprocess so a regression fails this test
instead of killing the suite.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("torch")

_TEST_ROOT = Path(__file__).resolve().parent
_PROJECT_ROOT = _TEST_ROOT.parent.parent

_PROBE = """\
import os
import sys

events = []

def hook(event, args):
    if event == "import" and args and args[0] == "torch":
        events.append(os.environ.get("PYTORCH_CUDA_ALLOC_CONF", "<unset>"))

sys.addaudithook(hook)
from airunner_services.app.service_app import ServiceApp
import torch

after = os.environ.get("PYTORCH_CUDA_ALLOC_CONF", "<unset>")
first = events[0] if events else "<torch-missing>"
print("alloc-at-torch-import=%s" % first)
print("alloc-after-app-import=%s" % after)
if not events or first != after:
    print("SKEWED torch allocator environment")
    raise SystemExit(42)
if torch.cuda.is_available():
    probe = torch.randn(512, 64, device="cuda", dtype=torch.bfloat16)
    assert tuple(probe.shape) == (512, 64)
    print("cuda-randn-ok")
else:
    print("cuda-unavailable")
"""


def _probe_env() -> dict[str, str]:
    """Return one subprocess environment rooted at this checkout."""
    entries = [
        str(_PROJECT_ROOT / "services" / "src"),
        str(_PROJECT_ROOT / "native" / "src"),
        str(_PROJECT_ROOT / "src"),
    ]
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "").strip()
    if existing:
        entries.append(existing)
    env["PYTHONPATH"] = os.pathsep.join(entries)
    env.pop("PYTORCH_CUDA_ALLOC_CONF", None)
    env.pop("PYTORCH_ALLOC_CONF", None)
    return env


@pytest.mark.timeout(180)
def test_service_app_import_keeps_allocator_env_consistent() -> None:
    """Importing the service app first must not skew torch's allocator."""
    proc = subprocess.run(
        [sys.executable, "-c", _PROBE],
        cwd=str(_PROJECT_ROOT),
        env=_probe_env(),
        capture_output=True,
        text=True,
        timeout=150,
    )
    assert proc.returncode == 0, (
        f"service-app-first import skews the torch allocator "
        f"(exit={proc.returncode}):\n{proc.stdout}\n{proc.stderr}"
    )
    assert "SKEWED" not in proc.stdout
