"""Regression tests for release issue #2249 (strip SDXL support).

Proves the removal holds: the bootstrap model catalog carries no
SDXL/Stability-XL repo, version, or branch pin; the deleted
SDXL/ControlNet/art-LoRA modules stay deleted; the desktop version
enum has no SDXL members; and no live Python or Qt UI source names
SDXL, ControlNet, or art LoRA symbols.

Historical Alembic revisions, the verbatim upstream Debian vendor
snapshot, and build artifacts are excluded from the source scan by
design. CPU-only; standard library plus pytest.
"""

from __future__ import annotations

import ast
import importlib.util
import re
from pathlib import Path

from test_release_p11_support import REPO_ROOT

_BOOTSTRAP_PATH = (
    REPO_ROOT
    / "services"
    / "src"
    / "airunner_services"
    / "bootstrap"
    / "model_bootstrap_data.py"
)

_REMOVED_MODULES = (
    "airunner_services.model_management.sdxl_model_manager",
    "airunner_services.art.managers.stablediffusion.controlnet_request",
    "airunner_services.database.models.lora",
    "airunner_services.database.models.controlnet_model",
    "airunner_services.database.models.controlnet_settings",
    "airunner.components.art.api.lora_services",
)

_SDXL_PATTERN = re.compile(r"sdxl|stable.diffusion.xl", re.IGNORECASE)
_STABILITY_XL_PATTERN = re.compile(
    r"stabilityai/(?!stable-diffusion-x4-upscaler)", re.IGNORECASE
)
_CONTROLNET_PATTERN = re.compile(r"controlnet", re.IGNORECASE)
_LORA_PATTERN = re.compile(
    r"(?<![a-zA-Z])loras?(?![a-zA-Z])", re.IGNORECASE
)

_SCAN_ROOTS = ("src", "services/src", "services/tests", "scripts",
               "packaging", "native", "debian")
_SCAN_SUFFIXES = (".py", ".ui")
_EXCLUDED_DIRS = (
    "__pycache__",
    "alembic/versions",
    "debian/vendor",
)
_EXCLUDED_FILES = (Path(__file__).name,)


def _bootstrap_strings() -> list[str]:
    """Return every string literal in the bootstrap catalog."""
    tree = ast.parse(_BOOTSTRAP_PATH.read_text(encoding="utf-8"))
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]


def test_bootstrap_catalog_has_no_sdxl_entries() -> None:
    """No catalog literal names an SDXL repo, version, or pin."""
    offenders = [
        value
        for value in _bootstrap_strings()
        if _SDXL_PATTERN.search(value)
        or _STABILITY_XL_PATTERN.search(value)
    ]
    assert offenders == [], offenders


def test_bootstrap_catalog_has_no_fp16_branch() -> None:
    """The SDXL Inpaint fp16 branch pin left with the catalog."""
    assert '"fp16"' not in _BOOTSTRAP_PATH.read_text(encoding="utf-8")


def test_removed_modules_stay_deleted() -> None:
    """The stripped SDXL/ControlNet/LoRA modules do not resolve."""
    for name in _REMOVED_MODULES:
        assert importlib.util.find_spec(name) is None, name


def test_desktop_version_enum_has_no_sdxl_members() -> None:
    """StableDiffusionVersion carries no SDXL name or value."""
    from airunner.enums import StableDiffusionVersion

    for member in StableDiffusionVersion:
        assert _SDXL_PATTERN.search(member.name) is None, member.name
        assert _SDXL_PATTERN.search(member.value) is None, member.value


def _scanned_files() -> list[Path]:
    """Return every live source file the removal scan covers."""
    files: list[Path] = []
    for root in _SCAN_ROOTS:
        base = REPO_ROOT / root
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if path.suffix not in _SCAN_SUFFIXES:
                continue
            if path.name in _EXCLUDED_FILES:
                continue
            relative = path.relative_to(REPO_ROOT).as_posix()
            if ".egg-info" in relative:
                continue
            if any(part in relative for part in _EXCLUDED_DIRS):
                continue
            files.append(path)
    return files


def _scan_hits(path: Path) -> list[str]:
    """Return the stripped-token matches in one source file."""
    hits: list[str] = []
    for number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if _SDXL_PATTERN.search(line):
            hits.append(f"{path}:{number}: SDXL")
        elif _STABILITY_XL_PATTERN.search(line):
            hits.append(f"{path}:{number}: Stability XL")
        elif _CONTROLNET_PATTERN.search(line):
            hits.append(f"{path}:{number}: ControlNet")
        elif _LORA_PATTERN.search(line):
            hits.append(f"{path}:{number}: LoRA")
    return hits


def test_no_live_sdxl_controlnet_lora_references() -> None:
    """No live source names SDXL, ControlNet, or art LoRA."""
    files = _scanned_files()
    assert len(files) > 1000, len(files)
    hits: list[str] = []
    for path in files:
        hits.extend(_scan_hits(path))
    assert hits == [], hits[:20]
