"""RAG dependency isolation regression test.

Part of the RAG extraction audit follow-up. RAG's third-party document and
embedding dependencies were interleaved into ``LLM_NATIVE_REQUIREMENTS``,
so they could not be installed or depended on as a unit. They now live in
``RAG_REQUIREMENTS`` with a standalone ``rag`` extra, while the
``llm-native`` and ``llm`` extras still pull them, so every existing
install resolves the exact same dependency set.

This is a packaging-surface test: it evaluates ``services/setup.py`` with
the ``setup()`` call stripped, then asserts on ``extras_require``.
"""

from __future__ import annotations

import types
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SETUP = _PROJECT_ROOT / "services" / "setup.py"

#: The RAG-only dependency set, pinned exactly. Changing a pin here without
#: changing services/setup.py (or vice versa) fails this test deliberately.
_EXPECTED_RAG_REQUIREMENTS = [
    "sentence_transformers==5.6.1",
    "libzim==3.7.0",
    "langchain-huggingface==1.2.2",
    "langchain-text-splitters==1.1.2",
    "EbookLib==0.19",
    "mobi==0.4.1",
    "pypdf>=5.6.0",
]

#: Dependencies that are NOT RAG-only and must stay in the LLM core list.
_SHARED_WITH_NON_RAG_CODE = ("beautifulsoup4", "rank-bm25", "sumy")


def _load_setup_module():
    """Execute services/setup.py without running setup()."""
    source = _SETUP.read_text(encoding="utf-8").replace(
        'setup(**build_services_setup_kwargs(package_source_dir="src"))', ""
    )
    module = types.ModuleType("services_setup_probe")
    module.__file__ = str(_SETUP)
    exec(compile(source, str(_SETUP), "exec"), module.__dict__)
    return module


def test_rag_extra_exists_with_expected_pins() -> None:
    """The standalone `rag` extra is exactly the RAG dependency set."""
    extras = _load_setup_module().build_services_extras_require()
    assert extras.get("rag") == _EXPECTED_RAG_REQUIREMENTS


def test_rag_dependencies_are_separated_from_the_llm_native_list() -> None:
    """RAG-only deps no longer live in LLM_NATIVE_REQUIREMENTS."""
    module = _load_setup_module()
    for dependency in _EXPECTED_RAG_REQUIREMENTS:
        assert dependency not in module.LLM_NATIVE_REQUIREMENTS, dependency


def test_full_installs_still_pull_rag_dependencies() -> None:
    """`llm-native` and `llm` keep including the RAG deps (additive change)."""
    extras = _load_setup_module().build_services_extras_require()
    for extra_name in ("llm-native", "llm", "headless", "desktop"):
        for dependency in _EXPECTED_RAG_REQUIREMENTS:
            assert dependency in extras[extra_name], (extra_name, dependency)


def test_non_rag_shared_dependencies_stay_out_of_the_rag_extra() -> None:
    """Deps used by non-RAG code are not swept into the `rag` extra."""
    extras = _load_setup_module().build_services_extras_require()
    rag_extra = extras["rag"]
    for prefix in _SHARED_WITH_NON_RAG_CODE:
        assert not any(
            dependency.startswith(prefix) for dependency in rag_extra
        ), prefix
