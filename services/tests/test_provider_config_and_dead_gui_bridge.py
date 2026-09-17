"""Regression test for issue #2188, continued investigation into
llm_services.py's real shape (llm_response.py/llm_request.py/
llm_services.py itself remain deliberately unresolved -- see the
issue comments).

Two separate findings resolved here:

1. provider_config.py was a genuine two-way fork (unlike
   thinking_parser.py/gpt_oss_parser.py, this one turned out to be a
   clean case: services' copy is a strict superset of desktop's --
   same LOCAL_MODELS catalog, same methods, plus a newer
   get_gguf_runtime_profile() method and gguf_runtime_profiles data
   desktop's copy lacked entirely). Confirmed via an AST-level
   comparison of LOCAL_MODELS' keys (identical model id sets) before
   deleting the desktop copy.

2. Investigating llm_services.py's relationship to services found a
   third file (services/src/airunner_services/llm/api/llm_services.py,
   a GUI-bridge LLMAPIService subclass) that had zero callers anywhere
   in the repository -- services/runtimes/local_fallback.py, the only
   real instantiation site outside the desktop app, imports the
   canonical airunner_services.api.services.llm_services.LLMAPIService
   directly, never the subclass. Confirmed dead code and removed
   (issue #2188's own scope note: not a duplicate needing
   reconciliation, a straightforwardly dead file).
"""

from __future__ import annotations

from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_desktop_provider_config_is_gone():
    dead_path = (
        _PROJECT_ROOT
        / "src"
        / "airunner"
        / "components"
        / "llm"
        / "config"
        / "provider_config.py"
    )
    assert not dead_path.exists()


def test_no_remaining_desktop_provider_config_import_paths():
    fragment = "components.llm.config.provider_config"
    offenders = []
    for path in (_PROJECT_ROOT / "src").rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        if fragment in path.read_text(encoding="utf-8"):
            offenders.append(str(path))
    assert offenders == []


def test_dead_gui_bridge_llm_api_service_is_gone():
    dead_dir = (
        _PROJECT_ROOT
        / "services"
        / "src"
        / "airunner_services"
        / "llm"
        / "api"
    )
    assert not dead_dir.exists()


def test_local_fallback_still_imports_the_canonical_service():
    """The one real caller must keep pointing at the canonical class."""
    import sys

    sys.path[:0] = [str(_PROJECT_ROOT / "services" / "src")]
    from airunner_services.api.services.llm_services import (
        LLMAPIService,
    )

    text = (
        _PROJECT_ROOT
        / "services"
        / "src"
        / "airunner_services"
        / "runtimes"
        / "local_fallback.py"
    ).read_text(encoding="utf-8")
    assert "airunner_services.api.services.llm_services" in text
    assert LLMAPIService.__module__ == (
        "airunner_services.api.services.llm_services"
    )


def test_provider_config_local_models_are_a_superset_of_the_old_desktop_set():
    """The surviving copy must still cover every model the desktop copy had.

    Guards against a future edit accidentally dropping a model id that
    desktop's GUI widgets (llm_settings_widget.py and friends) expect
    to exist.
    """
    import sys

    sys.path[:0] = [str(_PROJECT_ROOT / "services" / "src")]
    from airunner_services.llm.provider_config import LLMProviderConfig

    expected_ids = {
        "qwen2.5-7b",
        "qwen3.5-9b",
        "gpt-oss-20b",
        "qwen3-14b",
        "qwen3-32b",
        "qwen3-30b-a3b",
        "qwen2.5-coder-7b",
        "qwen3-coder-30b-a3b",
        "custom",
    }
    assert expected_ids <= set(LLMProviderConfig.LOCAL_MODELS.keys())
