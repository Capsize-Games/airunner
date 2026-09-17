"""Regression test for issue #2188 (partial).

Four of the twelve LLM modules forked between
``src/airunner/components/llm`` and
``services/src/airunner_services/llm`` were byte-identical or dead on
the desktop side and are eliminated here: ``parse_template.py``,
``strip_names_from_message.py``, ``model_capabilities.py`` and
``model_downloader.py``.

The remaining eight (``document_extraction.py``, ``gpt_oss_parser.py``,
``thinking_parser.py``, ``provider_config.py``, ``llm_request.py``,
``llm_response.py``, ``llm_services.py``, and the client/server pair
``get_chatbot.py``) have real behavioural divergence -- confirmed by
reading, not just measuring -- and are intentionally left forked
pending dedicated follow-up work. This test only asserts the four
resolved modules stay resolved; it is not the "no duplication at all"
check that issue #2188 will need once the rest land.
"""

from __future__ import annotations

from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DESKTOP_LLM = _PROJECT_ROOT / "src" / "airunner" / "components" / "llm"

_RESOLVED = [
    "parse_template.py",
    "strip_names_from_message.py",
    "model_capabilities.py",
    "model_downloader.py",
]


def test_resolved_modules_are_gone_from_desktop():
    for name in _RESOLVED:
        hits = list(_DESKTOP_LLM.rglob(name))
        assert hits == [], f"{name} still present on desktop: {hits}"


def test_desktop_source_has_no_remaining_resolved_import_paths():
    forked_import_fragments = [
        "components.llm.utils.parse_template",
        "components.llm.utils.strip_names_from_message",
        "components.llm.config.model_capabilities",
        "components.llm.utils.model_downloader",
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


def test_get_chatbot_fallback_name_is_not_a_placeholder():
    """Regression for the "Foobar" leftover found while reading #2188.

    Not a dedup target: get_chatbot.py legitimately differs per side
    (desktop goes through the daemon resource_store, services reads
    the DB directly), but the services fallback name was a stray
    placeholder rather than "Default".
    """
    text = (
        _PROJECT_ROOT
        / "services"
        / "src"
        / "airunner_services"
        / "llm"
        / "get_chatbot.py"
    ).read_text()
    assert "Foobar" not in text
