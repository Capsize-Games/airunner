"""P05 data payload, code collection, and sidecar tests.

Proves every spec data glob resolves, the policy signature stays
release-provisioned, legal notices stage at the bundle root, the
freeze recipe covers all runtime-loaded code, and spec sidecars match
the runtime settings. CPU-only.
"""

from __future__ import annotations

import ast
import importlib.util
import types
from pathlib import Path
from typing import Any

from test_release_p05_support import (
    REPO_ROOT,
    SERVICES_SRC,
    inspect_mod,
    module_exists,
    module_file,
    services_setup,
    spec,
)

__all__ = ["inspect_mod", "services_setup", "spec"]


def _module_string_literals(path: Path, prefix: str) -> set[str]:
    """Return string literals under prefix found anywhere in a file."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and node.value.startswith(prefix)
    }


def _exports_table(path: Path, name: str) -> dict[str, str]:
    """Return a module-level {str: str} dict by literal evaluation."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == name
        ):
            value = ast.literal_eval(node.value)
            assert isinstance(value, dict)
            return dict(value)
    raise AssertionError(f"{name} not found in {path}")


def _resolve_runtime_calls() -> set[tuple[str, str]]:
    """Return (env, binary) pairs from resolve_runtime_executable calls."""
    found: set[tuple[str, str]] = set()
    for path in sorted((SERVICES_SRC / "runtimes").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "resolve_runtime_executable"
                and len(node.args) >= 2
                and all(isinstance(arg, ast.Constant) for arg in node.args[:2])
            ):
                found.add((str(node.args[0].value), str(node.args[1].value)))
    return found


def test_data_sources_resolve_in_checkout(spec: dict[str, Any]) -> None:
    """Required globs match real files; optional ones need not."""
    for entry in spec.get("data", []):
        matches = [
            path
            for path in sorted(REPO_ROOT.glob(str(entry["source"])))
            if path.is_file()
        ]
        if entry.get("required", True):
            assert matches, entry["source"]
        assert all(path.is_file() for path in matches)


def test_policy_signature_is_release_provisioned(
    spec: dict[str, Any],
) -> None:
    """Public-checkout assembly must not demand production policy (S06)."""
    sigs = [
        entry
        for entry in spec.get("data", [])
        if str(entry["source"]).endswith(".dat.sig")
    ]
    assert len(sigs) == 1
    assert sigs[0].get("required") is False


def test_legal_entries_cover_root_notices(spec: dict[str, Any]) -> None:
    staged = {
        Path(str(entry["source"])).name
        for entry in spec.get("data", [])
        if str(entry.get("stage")) == "root"
    }
    assert staged == {"LICENSE", "NOTICE", "THIRD_PARTY_NOTICES.md"}


def _assert_collect_parent_exists(parent: str) -> None:
    """Assert one collect parent resolves in the worktree or venv."""
    if parent.startswith("airunner_services."):
        package = module_file(parent).with_suffix("")
        assert (package / "__init__.py").is_file(), parent
        return
    # Third-party parents cover dynamic imports in pinned deps; the
    # toolchain venv must import them (typo/drift guard).
    assert importlib.util.find_spec(parent) is not None, parent


def test_hidden_imports_and_collect_parents_exist(
    spec: dict[str, Any],
) -> None:
    for module in spec["code"].get("hidden_imports", []):
        assert module_exists(str(module)), module
    for parent in spec["code"].get("collect_submodules", []):
        _assert_collect_parent_exists(str(parent))


def test_copy_metadata_names_are_version_lookup_packages(
    spec: dict[str, Any],
) -> None:
    """copy_metadata covers the importlib.metadata lookups (stdlib-only
    module import; reads the real PACKAGE_NAMES contract)."""
    from airunner_services.utils.application.get_version import (
        PACKAGE_NAMES,
    )

    assert set(spec["code"].get("copy_metadata", [])) <= set(PACKAGE_NAMES)


def test_tool_registry_literals_are_collected(
    spec: dict[str, Any],
) -> None:
    """Every runtime-loaded tool module ships via hidden/collect (AST
    re-derivation of tool_registry.py's literal module names, so a newly
    admitted tool module fails here until the recipe covers it)."""
    literals = _module_string_literals(
        SERVICES_SRC / "llm" / "core" / "tool_registry.py",
        "airunner_services.",
    )
    assert len(literals) >= 17
    hidden = set(spec["code"].get("hidden_imports", []))
    parents = [str(p) + "." for p in spec["code"]["collect_submodules"]]
    for module in sorted(literals):
        assert module in hidden or module.startswith(tuple(parents)), module


def test_runtimes_lazy_exports_are_collected(
    spec: dict[str, Any],
) -> None:
    """The lazy _EXPORTS table resolves inside the frozen package."""
    exports = _exports_table(
        SERVICES_SRC / "runtimes" / "__init__.py", "_EXPORTS"
    )
    assert exports
    assert all(
        module.startswith("airunner_services.runtimes.")
        for module in exports.values()
    )
    assert "airunner_services.runtimes" in list(
        spec["code"]["collect_submodules"]
    )


def test_sidecar_names_match_runtime_settings(
    spec: dict[str, Any],
) -> None:
    """Spec sidecars equal the binaries the settings resolve (derived
    by AST from every resolve_runtime_executable call site)."""
    assert _resolve_runtime_calls()
    assert {
        (str(rt["env"]), str(rt["name"])) for rt in spec.get("runtime", [])
    } == _resolve_runtime_calls()


def test_spec_declares_services_only_scope(spec: dict[str, Any]) -> None:
    assert spec["qt"]["required"] is False
    assert spec["qt"]["qt_markers"]
