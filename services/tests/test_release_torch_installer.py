"""Regression tests for installer torch issues #2432-#2434.

P1: install_helpers.sh fetched cu128 wheels while the release pins
cu129 (services/setup.py, the Dockerfile, the constraints lock).
P2: the torch install floated unpinned and ``auto`` kept any
importable torch without checking its version.
P3: the ``llm`` aggregate bundles ML_RUNTIME_REQUIREMENTS (torch)
but was absent from the torch-needs list.

Read-as-text plus services/setup.py probing only: no installs,
no network, no GPU.
"""

from __future__ import annotations

import re
import types
from pathlib import Path

from packaging.markers import default_environment
from packaging.requirements import Requirement

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_HELPERS = _PROJECT_ROOT / "scripts" / "install_helpers.sh"
_SETUP = _PROJECT_ROOT / "services" / "setup.py"
_LOCK = (
    _PROJECT_ROOT / "package" / "constraints-linux-nvidia-cu129.txt"
)

_LINUX_ENV = {**default_environment(), "platform_system": "Linux"}
_LINUX_ENV["python_version"] = "3.13"

_SHELL_VAR = re.compile(r"^AIRUNNER_([A-Z_]+)='([^']+)'", re.M)


def _helpers_text() -> str:
    """Return the installer helpers shell source."""
    return _HELPERS.read_text(encoding="utf-8")


def _shell_pins() -> dict[str, str]:
    """Map installer shell pin variables to their values."""
    return dict(_SHELL_VAR.findall(_helpers_text()))


def _load_services_setup() -> types.ModuleType:
    """Execute services/setup.py without running setup()."""
    source = _SETUP.read_text(encoding="utf-8").replace(
        'setup(**build_services_setup_kwargs(package_source_dir="src"))',
        "",
    )
    module = types.ModuleType("torch_pins_services_setup")
    module.__file__ = str(_SETUP)
    exec(compile(str(source), str(_SETUP), "exec"), module.__dict__)
    return module


def _shell_torch_extras() -> set[str]:
    """Extras names in the service_extra_needs_torch case list."""
    text = _helpers_text()
    start = text.index("service_extra_needs_torch() {")
    body = text[start : text.index("return 1", start)]
    return set(re.findall(r"\*,([A-Za-z0-9_-]+),\*", body))


def _torch_needing_extras() -> set[str]:
    """Extras whose Linux-evaluated closure contains torch."""
    module = _load_services_setup()
    extras = module.build_services_extras_require()
    needing: set[str] = set()
    for name, deps in extras.items():
        for raw in deps:
            req = Requirement(raw)
            if req.marker is not None and not req.marker.evaluate(
                _LINUX_ENV
            ):
                continue
            if req.name == "torch":
                needing.add(name)
    return needing


def _ml_runtime_pin(dist: str) -> str:
    """Pinned requirement string for one ML runtime distribution."""
    module = _load_services_setup()
    for raw in module.ML_RUNTIME_REQUIREMENTS:
        if Requirement(raw).name == dist:
            return raw
    raise AssertionError(f"{dist} missing from ML_RUNTIME_REQUIREMENTS")


def _lock_pin(dist: str) -> str:
    """Locked version for one distribution in the release lock."""
    for line in _LOCK.read_text(encoding="utf-8").splitlines():
        head = line.split("\\", 1)[0].strip()
        if head.startswith(dist + "=="):
            return head.split("==", 1)[1].strip()
    raise AssertionError(f"{dist} missing from the release lock")


def test_cuda_index_is_cu129_everywhere() -> None:
    """No cu128 wheel index may remain in the installer (issue #2432)."""
    text = _helpers_text()
    assert "cu128" not in text, "stale cu128 index URL"
    assert "https://download.pytorch.org/whl/cu129" in text


def test_shell_pins_match_setup_and_lock() -> None:
    """Shell pins track ML_RUNTIME plus the locked torchcodec."""
    pins = _shell_pins()
    assert "torch==" + pins["TORCH_VERSION"] == _ml_runtime_pin(
        "torch"
    )
    assert pins["TORCH_VERSION"] == "2.13.0+cu129"
    assert "torchvision==" + pins["TORCHVISION_VERSION"] == (
        _ml_runtime_pin("torchvision")
    )
    assert "torchaudio==" + pins["TORCHAUDIO_VERSION"] == (
        _ml_runtime_pin("torchaudio")
    )
    assert "torchcodec==" + pins["TORCHCODEC_VERSION"] == (
        "torchcodec==" + _lock_pin("torchcodec")
    )
    assert pins["TORCHCODEC_VERSION"] == "0.9.1"


def test_cuda_install_is_pinned_and_forced() -> None:
    """The CUDA path installs the four pinned wheels forcefully."""
    text = _helpers_text()
    for var in (
        "AIRUNNER_TORCH_VERSION",
        "AIRUNNER_TORCHVISION_VERSION",
        "AIRUNNER_TORCHAUDIO_VERSION",
        "AIRUNNER_TORCHCODEC_VERSION",
    ):
        assert "${%s}" % var in text, var
    assert text.count("--force-reinstall") >= 2
    assert "torchvision==${AIRUNNER_TORCHVISION_VERSION%%+*}" in text


def test_auto_verifies_version_before_skipping() -> None:
    """Auto reinstalls on mismatch instead of keeping any torch."""
    text = _helpers_text()
    start = text.index("install_torch_stack() {")
    auto = text[text.index("auto)", start) :]
    assert "torch_version_matches" in auto
    assert "torch.__version__" in text
    assert "mismatch" in auto.lower()


def test_torch_needs_covers_every_torch_extra() -> None:
    """The shell list matches the setup.py torch closure (issue #2434)."""
    assert _shell_torch_extras() == _torch_needing_extras()


def test_llm_extra_needs_torch() -> None:
    """The llm aggregate (ML_RUNTIME) must request the torch stack."""
    assert "llm" in _shell_torch_extras()
    assert "llm" in _torch_needing_extras()
