"""Parity guard between GUI and services ``ModelState`` enums (issue #2047).

The GUI copy of ``ModelState`` (``src/airunner/components/model_management/
types.py``) and the services copy (``services/src/airunner_services/model_
management/types.py``) describe the same model lifecycle and must not drift:
missing members such as ``LOADED_CPU`` silently change behavior depending on
which tree the caller imports.

The comparison is AST-based so the test runs in either tree's test
environment without requiring ``airunner_services`` (which pulls in torch and
other heavy daemon deps) to be importable from the GUI test process.
"""

from __future__ import annotations

import ast
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[5]
_GUI_TYPES = (
    _REPO_ROOT / "src" / "airunner" / "components" / "model_management" / "types.py"
)
_SERVICES_TYPES = (
    _REPO_ROOT / "services" / "src" / "airunner_services" / "model_management" / "types.py"
)


def _model_state_members(path: Path) -> dict[str, str]:
    """Extract {name: value} for ModelState from one source file."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef) or node.name != "ModelState":
            continue
        members: dict[str, str] = {}
        for stmt in node.body:
            if not isinstance(stmt, ast.Assign):
                continue
            for target in stmt.targets:
                if not isinstance(target, ast.Name):
                    continue
                value = stmt.value
                if isinstance(value, ast.Constant):
                    members[target.id] = str(value.value)
        return members
    raise AssertionError(f"ModelState not found in {path}")


def test_gui_model_state_has_all_services_members() -> None:
    """Every services ModelState member (and value) exists on the GUI enum."""
    gui = _model_state_members(_GUI_TYPES)
    services = _model_state_members(_SERVICES_TYPES)
    missing = {
        name: (services[name], gui.get(name, "<absent>"))
        for name in services
        if name not in gui
    }
    assert not missing, (
        "GUI ModelState is missing members present in services "
        f"ModelState: {missing}"
    )
    mismatched = {
        name: (gui[name], services[name])
        for name in gui
        if name in services and gui[name] != services[name]
    }
    assert not mismatched, (
        f"ModelState member values drifted between GUI and services: {mismatched}"
    )


def test_services_model_state_has_no_extra_members() -> None:
    """The GUI enum must not lag behind; services has no GUI-only members."""
    gui = set(_model_state_members(_GUI_TYPES))
    services = set(_model_state_members(_SERVICES_TYPES))
    assert gui == services, (
        "GUI and services ModelState member sets differ: "
        f"GUI-only={sorted(gui - services)}, "
        f"services-only={sorted(services - gui)}"
    )


def test_gui_model_state_includes_loaded_cpu() -> None:
    """LOADED_CPU must be present on the GUI enum (issue #2047)."""
    gui = _model_state_members(_GUI_TYPES)
    assert "LOADED_CPU" in gui, "GUI ModelState is missing LOADED_CPU"
    assert gui["LOADED_CPU"] == "loaded_cpu"
