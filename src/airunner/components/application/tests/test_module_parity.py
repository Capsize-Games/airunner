"""Drift guards for duplicated modules across the GUI and services trees.

Issue #2048: several modules are intentionally duplicated between
``src/airunner/`` and ``services/src/airunner_services/``. Where the copies
are meant to be identical these tests fail on byte drift; where a copy is
intentionally divergent (for example the services ``url_safety`` SSRF
allow-list) the test normalizes the known, documented difference and still
fails on any *other* drift.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[5]

# (gui_path, services_path) pairs that must stay byte-identical.
_BYTE_IDENTICAL_PAIRS = (
    (
        _REPO_ROOT / "src" / "airunner" / "runtimes" / "file_policy.py",
        _REPO_ROOT
        / "services"
        / "src"
        / "airunner_services"
        / "runtimes"
        / "file_policy.py",
    ),
)

# daemon_config differs ONLY by its runtime-layout import path:
#   GUI:      from airunner.runtimes.runtime_layout import (
#   services: from airunner_services.config.runtime_layout import (
_IMPORT_NORMALIZATIONS = (
    (
        "from airunner_services.config.runtime_layout import (",
        "from airunner.runtimes.runtime_layout import (",
    ),
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_file_policy_byte_identical() -> None:
    """GUI and services file_policy.py must never drift."""
    for gui_path, services_path in _BYTE_IDENTICAL_PAIRS:
        gui = _read(gui_path)
        services = _read(services_path)
        assert gui == services, (
            f"{gui_path.name} drifted between GUI and services:\n"
            f"  GUI:      {gui_path}\n"
            f"  services: {services_path}"
        )


def test_daemon_config_identical_after_import_normalization() -> None:
    """daemon_config.py must be identical apart from the layout import path."""
    gui = _read(_REPO_ROOT / "src" / "airunner" / "runtimes" / "daemon_config.py")
    services = _read(
        _REPO_ROOT
        / "services"
        / "src"
        / "airunner_services"
        / "runtimes"
        / "daemon_config.py"
    )
    for source, replacement in _IMPORT_NORMALIZATIONS:
        services = services.replace(source, replacement)
    assert gui == services, (
        "runtimes/daemon_config.py drifted beyond the documented "
        "runtime-layout import path"
    )


# ---------------------------------------------------------------------------
# url_safety.py — intentional SSRF allow-list divergence
# ---------------------------------------------------------------------------
# The services copy adds an operator-configurable SSRF allow-list (functions
# ``_allowed_host_set`` / ``_host_is_allowed`` plus two call sites in
# ``validate_url_for_fetch``). Every OTHER line must stay identical.
_SSRF_HELPER_FUNCS = ("_allowed_host_set", "_host_is_allowed")


def _strip_ssrf_allowlist(source: str) -> str:
    """Return the services source with the documented SSRF block removed."""
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    keep = [True] * len(lines)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and (
            node.name in _SSRF_HELPER_FUNCS
        ):
            for index in range(node.lineno - 1, node.end_lineno):
                keep[index] = False
    text = "".join(line for line, kept in zip(lines, keep) if kept)
    # Strip the two allow-list call sites:
    #     if _host_is_allowed(hostname, {ip}):
    #         return
    text = re.sub(
        r"\n[ \t]*if _host_is_allowed\([^)]*\):[ \t]*\n[ \t]*return[ \t]*",
        "",
        text,
    )
    return text


def _normalize(source: str) -> str:
    """Normalize whitespace noise (trailing ws, blank-line runs)."""
    source = re.sub(r"[ \t]+$", "", source)
    source = re.sub(r"\n{3,}", "\n\n", source)
    return source.strip()


def test_url_safety_identical_except_ssrf_allowlist() -> None:
    """GUI url_safety must match services minus the documented SSRF block."""
    gui = _read(_REPO_ROOT / "src" / "airunner" / "url_safety.py")
    services = _read(
        _REPO_ROOT / "services" / "src" / "airunner_services" / "url_safety.py"
    )
    stripped = _strip_ssrf_allowlist(services)
    assert _normalize(gui) == _normalize(stripped), (
        "url_safety.py drifted beyond the intentional SSRF allow-list "
        "addition (functions _allowed_host_set/_host_is_allowed and their "
        "two call sites in validate_url_for_fetch)"
    )


def test_url_safety_services_still_has_ssrf_helpers() -> None:
    """The intentional services-only SSRF helpers must remain present."""
    services = _read(
        _REPO_ROOT / "services" / "src" / "airunner_services" / "url_safety.py"
    )
    for name in _SSRF_HELPER_FUNCS:
        assert f"def {name}(" in services, (
            f"services url_safety.py lost the documented SSRF helper {name}"
        )


# ---------------------------------------------------------------------------
# runtime_layout.py — GUI shim must re-export the canonical module
# ---------------------------------------------------------------------------


def test_runtime_layout_shim_re_exports_canonical() -> None:
    """airunner.runtime_layout must be a thin re-export of the canonical
    airunner.runtimes.runtime_layout module (issue #2048)."""
    from airunner import runtime_layout as top_level
    from airunner.runtimes import runtime_layout as canonical

    public = ("RuntimeDirectoryLayout", "build_runtime_directory_layout")
    for name in public:
        assert getattr(top_level, name) is getattr(canonical, name), (
            f"airunner.runtime_layout.{name} is not the canonical "
            f"airunner.runtimes.runtime_layout.{name} object"
        )


def test_runtime_layout_shim_imports_cleanly() -> None:
    """Both layout modules import without circular-import failures."""
    import importlib

    top_level = importlib.import_module("airunner.runtime_layout")
    canonical = importlib.import_module("airunner.runtimes.runtime_layout")
    assert callable(top_level.build_runtime_directory_layout)
    assert callable(canonical.build_runtime_directory_layout)
