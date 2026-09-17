"""Regression test for issue #2187.

Seven art modules previously existed as diverged copies in both
``src/airunner/components/art`` and
``services/src/airunner_services/art``, and both copies were imported by
live code. This asserts the desktop fork is gone and the desktop-side
importers reach the single services-owned implementation instead.
"""

from __future__ import annotations

from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DESKTOP_ART = _PROJECT_ROOT / "src" / "airunner" / "components" / "art"
_SERVICES_ART = (
    _PROJECT_ROOT
    / "services"
    / "src"
    / "airunner_services"
    / "art"
)

_FORMERLY_DUPLICATED = [
    "image_generation.py",
    "image_generator_capabilities.py",
    "image_request.py",
    "image_response.py",
    "model_file_checker.py",
    "rect.py",
    "zimage_bundle_requirements.py",
]


def test_desktop_art_tree_has_no_non_gui_basename_collisions():
    """Only __init__.py may share a basename outside the GUI tree.

    A non-``__init__.py`` collision means a module was forked again.
    """
    desktop_basenames = {
        p.name
        for p in _DESKTOP_ART.rglob("*.py")
        if "gui" not in p.relative_to(_DESKTOP_ART).parts
        and "__pycache__" not in p.parts
    }
    services_basenames = {
        p.name
        for p in _SERVICES_ART.rglob("*.py")
        if "__pycache__" not in p.parts
    }
    collisions = desktop_basenames & services_basenames
    assert collisions == {"__init__.py"}, collisions


def test_formerly_duplicated_modules_exist_only_in_services():
    for name in _FORMERLY_DUPLICATED:
        desktop_hits = list(_DESKTOP_ART.rglob(name))
        services_hits = list(_SERVICES_ART.rglob(name))
        assert desktop_hits == [], (
            f"{name} still present on the desktop side: {desktop_hits}"
        )
        assert services_hits, f"{name} missing from services entirely"


def test_desktop_source_has_no_remaining_forked_import_paths():
    """No desktop source file should import the old forked paths."""
    forked_import_fragments = [
        "components.art.managers.stablediffusion.image_generation",
        "components.art.config.image_generator_capabilities",
        "components.art.managers.stablediffusion.image_request",
        "components.art.managers.stablediffusion.image_response",
        "components.art.utils.model_file_checker",
        "components.art.managers.stablediffusion.rect",
        "components.art.managers.zimage.zimage_bundle_requirements",
    ]
    src_root = _PROJECT_ROOT / "src"
    offenders = []
    for path in src_root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        text = path.read_text()
        for fragment in forked_import_fragments:
            if fragment in text:
                offenders.append((str(path), fragment))
    assert offenders == []
