"""Regression tests for run_tests --component (issue #2440).

The flag used to fall through to the missing-dir error for every
input: the alias map was empty and services/tests/ is flat. The map
is now populated with the real filename prefixes present in that
directory. Loading scripts/run_tests.py by path keeps this suite
independent of sys.path bootstrapping; only stdlib imports run.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_RUN_TESTS = _PROJECT_ROOT / "scripts" / "run_tests.py"
_TESTS_DIR = _PROJECT_ROOT / "services" / "tests"


def _load_run_tests() -> types.ModuleType:
    """Load scripts/run_tests.py without executing its CLI."""
    spec = importlib.util.spec_from_file_location(
        "release_component_run_tests", _RUN_TESTS
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_component_prefixes_resolve_to_real_files() -> None:
    """Every documented component maps to existing test files."""
    module = _load_run_tests()
    assert set(module._COMPONENT_FILE_PREFIXES) == {
        "llm",
        "art",
        "tts",
        "stt",
        "daemon",
        "release",
    }
    for component in module._COMPONENT_FILE_PREFIXES:
        resolved = module._component_targets(_TESTS_DIR, component)
        assert resolved is not None, component
        targets, _description = resolved
        assert targets, component
        for target in targets:
            assert target.is_file(), target


def test_unknown_component_still_errors() -> None:
    """An unmapped name keeps the missing-target failure contract."""
    module = _load_run_tests()
    assert module._component_targets(_TESTS_DIR, "nope") is None


def test_all_component_files_live_under_tests_dir() -> None:
    """Resolved targets never escape the services test tree."""
    module = _load_run_tests()
    for component in module._COMPONENT_FILE_PREFIXES:
        resolved = module._component_targets(_TESTS_DIR, component)
        assert resolved is not None, component
        for target in resolved[0]:
            assert _TESTS_DIR in target.parents, target
