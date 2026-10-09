"""Torchless daemon boot probes (issue #2243, Gap 2).

The daemon boots without torch: the torch probe never imports it,
shared memory helpers degrade, and startup degrades to API-only.

CPU-only: torch is blocked (never imported), no model, network,
GPU, or database use. Deterministic with or without torch.
"""

from __future__ import annotations

import importlib.abc
import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

from airunner_services.daemon import AIRunnerDaemon
from airunner_services.daemon import ml_runtime_available
from airunner_services.runtimes.daemon_config import DaemonConfig

mem_stats: ModuleType = importlib.import_module(
    "airunner_services.utils.memory.gpu_memory_stats"
)
ampere_mod: ModuleType = importlib.import_module(
    "airunner_services.utils.memory.is_ampere_or_newer"
)

assert mem_stats.__file__ is not None
_SERVICES_SRC = str(
    Path(mem_stats.__file__).resolve().parents[2]
)

_TORCHLESS_IMPORT_SCRIPT = (
    "import importlib.abc, sys\n"
    "class _B(importlib.abc.MetaPathFinder):\n"
    "    def find_spec(self, n, p=None, t=None):\n"
    "        if n.split('.')[0] in "
    "{'torch', 'torchvision', 'torchaudio'}:\n"
    "            raise ImportError('blocked: ' + n)\n"
    "        return None\n"
    "sys.meta_path.insert(0, _B())\n"
    "import importlib\n"
    "m = importlib.import_module(\n"
    "    'airunner_services.utils.memory.gpu_memory_stats')\n"
    "a = importlib.import_module(\n"
    "    'airunner_services.utils.memory.is_ampere_or_newer')\n"
    "assert m.torch is None\n"
    "assert a.torch is None\n"
    "print('TORCHLESS IMPORT OK')\n"
)


class _BlockTorch(importlib.abc.MetaPathFinder):
    """Meta-path finder that makes torch unimportable."""

    _BLOCKED = frozenset({"torch", "torchvision", "torchaudio"})

    def find_spec(
        self,
        name: str,
        path: Any = None,
        target: Any = None,
    ) -> Any:
        """Raise for blocked modules so find_spec reports them missing."""
        if name.split(".")[0] in self._BLOCKED:
            raise ImportError(f"blocked for test: {name}")
        return None


@pytest.fixture
def torch_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hide torch from imports for one test, restoring state after."""
    monkeypatch.setattr(
        sys, "meta_path", [_BlockTorch()] + sys.meta_path
    )
    for name in ("torch", "torchvision", "torchaudio"):
        monkeypatch.delitem(sys.modules, name, raising=False)


def _stub_daemon(tmp_path: Path) -> AIRunnerDaemon:
    """Return a daemon on a missing config path (defaults, no I/O)."""
    return AIRunnerDaemon(DaemonConfig(tmp_path / "daemon.yaml"))


def test_ml_runtime_probe_false_without_torch(
    torch_blocked: None,
) -> None:
    """The probe reports missing torch without importing anything."""
    assert ml_runtime_available() is False
    assert "torch" not in sys.modules


def test_ml_runtime_probe_true_with_torch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The probe trusts find_spec when torch resolves."""
    real_find_spec = importlib.util.find_spec

    def fake_find_spec(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "torch":
            return object()
        return real_find_spec(name, *args, **kwargs)

    monkeypatch.setattr(importlib.util, "find_spec", fake_find_spec)
    assert ml_runtime_available() is True


def test_gpu_memory_stats_zeroed_without_torch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """gpu_memory_stats degrades to zeros when torch is None."""
    monkeypatch.setattr(mem_stats, "torch", None)
    device: Any = object()
    stats = mem_stats.gpu_memory_stats(device)
    assert stats["total"] == 0.0
    assert stats["device_name"] == "N/A"


def test_is_ampere_or_newer_false_without_torch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """is_ampere_or_newer is False when torch is None."""
    monkeypatch.setattr(ampere_mod, "torch", None)
    assert ampere_mod.is_ampere_or_newer(0) is False


def test_memory_helpers_import_without_torch() -> None:
    """Both memory helpers import in a torchless child process."""
    import os

    env = dict(os.environ)
    env["PYTHONPATH"] = _SERVICES_SRC + os.pathsep + env.get(
        "PYTHONPATH", ""
    )
    completed = subprocess.run(
        [sys.executable, "-c", _TORCHLESS_IMPORT_SCRIPT],
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
    )
    assert completed.returncode == 0, completed.stderr
    assert "TORCHLESS IMPORT OK" in completed.stdout


def test_daemon_degrades_without_torch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Without torch the daemon skips the app but keeps booting."""

    def _forbid_app(self: Any) -> Any:
        raise AssertionError("app must not build without torch")

    monkeypatch.setattr(
        "airunner_services.daemon.ml_runtime_available",
        lambda: False,
    )
    monkeypatch.setattr(
        AIRunnerDaemon, "_create_headless_app", _forbid_app
    )
    daemon = _stub_daemon(tmp_path)
    daemon._init_app_or_degraded()
    assert daemon.app is None
    assert daemon.lifecycle_service is None


def test_daemon_builds_app_with_torch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """With torch the daemon builds app, lifecycle, then preloads."""
    calls: list[str] = []
    monkeypatch.setattr(
        "airunner_services.daemon.ml_runtime_available",
        lambda: True,
    )
    monkeypatch.setattr(
        AIRunnerDaemon,
        "_create_headless_app",
        lambda self: calls.append("app") or SimpleNamespace(),
    )
    monkeypatch.setattr(
        AIRunnerDaemon,
        "_initialize_lifecycle_service",
        lambda self: calls.append("lifecycle"),
    )
    monkeypatch.setattr(
        AIRunnerDaemon,
        "_preload_models",
        lambda self: calls.append("preload"),
    )
    daemon = _stub_daemon(tmp_path)
    daemon._init_app_or_degraded()
    assert calls == ["app", "lifecycle", "preload"]
    assert daemon.app is not None
