"""Regression test for issue #2188 (document_extraction.py resolution).

services/src/airunner_services/llm/utils/document_extraction.py was a
dead fork: zero callers anywhere in the repository (confirmed by
grep, not just filename search), and its extract_text() dispatch
silently regressed .mobi/.html files to a naive byte-decode despite
airunner_services.llm.managers.agent.document_loader already having
correct handlers for both -- a latent bug nobody could hit because
nothing called the function. The only live implementation is the
desktop's src/airunner/components/llm/utils/document_extraction.py,
imported by chat_prompt_widget.py.
"""

from __future__ import annotations

from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_services_copy_is_gone():
    dead_path = (
        _PROJECT_ROOT
        / "services"
        / "src"
        / "airunner_services"
        / "llm"
        / "utils"
        / "document_extraction.py"
    )
    assert not dead_path.exists()


def test_no_remaining_references_to_the_dead_services_path():
    fragment = "airunner_services.llm.utils.document_extraction"
    this_file = Path(__file__).resolve()
    offenders = []
    for root_rel in ("src", "services"):
        root = _PROJECT_ROOT / root_rel
        for path in root.rglob("*.py"):
            if "__pycache__" in path.parts or path == this_file:
                continue
            if fragment in path.read_text(encoding="utf-8"):
                offenders.append(str(path))
    assert offenders == []


def test_desktop_document_extraction_still_supports_mobi_and_html():
    """The live implementation keeps its full format coverage."""
    text = (
        _PROJECT_ROOT
        / "src"
        / "airunner"
        / "components"
        / "llm"
        / "utils"
        / "document_extraction.py"
    ).read_text(encoding="utf-8")
    assert "def extract_text_from_mobi" in text
    assert "def extract_text_from_html" in text
