"""P05 spec identity, profile, R01 coverage, and console tests.

Proves packaging/linux/services-bundle-spec.toml names the P04 recipe
and P02 aggregate, covers every R01 feature ID exactly once, and
inventories the services console scripts. CPU-only.
"""

from __future__ import annotations

import re
import types
from typing import Any

from test_release_p05_support import (
    MATRIX_PATH,
    inspect_mod,
    module_file,
    services_setup,
    spec,
)

__all__ = ["inspect_mod", "services_setup", "spec"]


def _matrix_ids() -> set[str]:
    """Return every stable feature ID in the R01 feature matrix."""
    text = MATRIX_PATH.read_text(encoding="utf-8")
    return set(re.findall(r"^\| ([A-Z]+-\d+) \|", text, re.MULTILINE))


def _token_kind(feature: str, token: str, extras: dict[str, Any]) -> str:
    """Return the coverage class of one token (asserts known)."""
    if token in extras or token == "core":
        return "daemon"
    if token == "gui":
        return "gui"
    assert re.fullmatch(r"tracked:[A-Z]+\d+", token), (feature, token)
    return "tracked"


def test_spec_loads_without_structural_errors(
    inspect_mod: types.ModuleType, spec: dict[str, Any]
) -> None:
    assert inspect_mod.spec_errors(spec) == []


def test_tool_pin_matches_services_dev_requirement(
    spec: dict[str, Any], services_setup: types.ModuleType
) -> None:
    """The frozen toolchain is the pinned dev requirement (P04)."""
    assert str(spec["bundle"]["tool"]) in list(
        services_setup.DEVELOPMENT_REQUIREMENTS
    )


def test_profile_aggregates_union_to_desktop(
    spec: dict[str, Any], services_setup: types.ModuleType
) -> None:
    """The spec's profile list is exactly the desktop aggregate."""
    extras = services_setup.build_services_extras_require()
    assert str(spec["profile"]["services_extra"]) == "desktop"
    union: list[str] = []
    for name in spec["profile"]["aggregates"]:
        union.extend(extras[name])
    assert list(dict.fromkeys(union)) == extras["desktop"]


def test_r01_coverage_matches_matrix_exactly(
    spec: dict[str, Any],
) -> None:
    """Every R01 feature ID is covered exactly once -- no gaps, no
    extras. A new matrix row fails here until the spec maps it."""
    covered = set(spec["r01_coverage"])
    assert covered == _matrix_ids()
    assert len(covered) > 60


def test_r01_tokens_are_known(
    spec: dict[str, Any], services_setup: types.ModuleType
) -> None:
    """Coverage tokens name real extras, core, gui, or tracked:XXX."""
    extras = services_setup.build_services_extras_require()
    kinds: set[str] = set()
    for feature, raw in spec["r01_coverage"].items():
        for token in str(raw).split(","):
            kinds.add(_token_kind(feature, token, extras))
    # Guards against mapping everything to daemon extras: the Qt
    # desktop scope and the unimplemented backlog must stay visible.
    assert {"gui", "tracked"} <= kinds


def test_r01_daemon_tokens_ship_in_bundle_profile(
    spec: dict[str, Any], services_setup: types.ModuleType
) -> None:
    """Daemon-side features only name extras the bundle ships."""
    extras = services_setup.build_services_extras_require()
    shipped = set(spec["profile"]["aggregates"])
    for feature, raw in spec["r01_coverage"].items():
        for token in str(raw).split(","):
            if token == "core":
                # Base install_requires ship unconditionally.
                continue
            if token in extras:
                assert token in shipped, (feature, token)


def test_console_scripts_match_services_setup(
    spec: dict[str, Any], services_setup: types.ModuleType
) -> None:
    """The spec's entry inventory equals SERVICE_CONSOLE_SCRIPTS."""
    declared = {}
    for script in services_setup.SERVICE_CONSOLE_SCRIPTS:
        name, target = script.split("=", 1)
        module, function = target.split(":", 1)
        declared[name] = (module, function)
    inventoried = {
        entry["name"]: (entry["module"], entry["function"])
        for entry in spec.get("console_script", [])
    }
    assert inventoried == declared
    primaries = [
        entry["name"]
        for entry in spec.get("console_script", [])
        if entry.get("primary")
    ]
    assert primaries == ["airunner-daemon"]


def test_console_script_modules_exist(spec: dict[str, Any]) -> None:
    for entry in spec.get("console_script", []):
        assert module_file(str(entry["module"])).is_file()
