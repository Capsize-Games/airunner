"""Regression test for issue #2188 (continued from #2205/#2211).

thinking_parser.py and gpt_oss_parser.py were forked between
src/airunner/components/llm/utils and
services/src/airunner_services/llm. Reading both (not just measuring
line counts) found real behavioural differences in each direction:

- thinking_parser.py: services correctly extracted partial thinking
  content from an unclosed ``<think>`` tag (desktop did not), and
  services' strip_thinking_tags() stripped trailing whitespace
  (desktop's did not). Both services behaviours were adopted as-is.
- gpt_oss_parser.py: desktop had looks_like_tool_call_payload() (and
  its supporting constant/helper) that services entirely lacked, and
  desktop's stream parser correctly suppressed "commentary" channel
  messages with a tool-call recipient from visible content, which
  services' _append() also entirely lacked -- a real content-leak
  bug, made worse by a fallback in services' parse_gpt_oss_response()
  that dumped raw Harmony markup into "content" whenever nothing else
  was extracted, treating "correctly parsed and suppressed" the same
  as "not Harmony-formatted at all". Ported desktop's tool-call-lookup
  functions into the services copy, restored the commentary-channel
  suppression rule, and removed the now-unneeded (and actively wrong)
  fallback.

Verified behavioural parity by running both original implementations
side by side against a shared corpus before deleting the desktop
copies -- this test only re-checks the final, single implementation's
own behaviour going forward, not a comparison (there is nothing left
to compare against once the desktop copy is gone).
"""

from __future__ import annotations

from pathlib import Path

from airunner_services.llm.gpt_oss_parser import (
    looks_like_tool_argument_payload,
    looks_like_tool_call_payload,
    parse_gpt_oss_response,
)
from airunner_services.llm.thinking_parser import (
    extract_thinking_and_response,
    strip_thinking_tags,
)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DESKTOP_LLM_UTILS = (
    _PROJECT_ROOT / "src" / "airunner" / "components" / "llm" / "utils"
)


def test_desktop_copies_are_gone():
    assert not (_DESKTOP_LLM_UTILS / "gpt_oss_parser.py").exists()
    assert not (_DESKTOP_LLM_UTILS / "thinking_parser.py").exists()


def test_no_remaining_desktop_import_paths():
    fragments = [
        "components.llm.utils.gpt_oss_parser",
        "components.llm.utils.thinking_parser",
    ]
    offenders = []
    for path in (_PROJECT_ROOT / "src").rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        for fragment in fragments:
            if fragment in text:
                offenders.append((str(path), fragment))
    assert offenders == []


def test_gpt_oss_commentary_with_recipient_is_suppressed():
    """A tool-call routed elsewhere must not leak into visible content.

    Regression for the bug found while reconciling the fork: the
    services copy's _append() had no "commentary" channel handling at
    all, and its now-removed fallback masked the resulting content
    loss by dumping raw Harmony markup as "content" instead.
    """
    text = (
        "<|start|>assistant<|channel|>commentary to=functions.search"
        '<|message|>{"query": "weather"}<|call|>'
    )
    result = parse_gpt_oss_response(text)
    assert result.thinking_content is None
    assert result.content == ""


def test_gpt_oss_commentary_without_recipient_is_visible():
    text = (
        "<|start|>assistant<|channel|>commentary"
        "<|message|>no recipient, should show<|end|>"
    )
    result = parse_gpt_oss_response(text)
    assert result.content == "no recipient, should show"


def test_gpt_oss_tool_call_lookup_ported_from_desktop():
    """looks_like_tool_call_payload existed only on the desktop copy."""
    assert looks_like_tool_call_payload('{"tool": "search", "query": "x"}')
    assert looks_like_tool_call_payload('{"name": "lookup", "args": {}}')
    assert not looks_like_tool_call_payload("plain text")
    # The sibling lookup (already present on both copies) still works.
    assert looks_like_tool_argument_payload('{"file_path": "/tmp/x"}')


def test_thinking_parser_extracts_partial_unclosed_block():
    """services correctly handled an unclosed <think> tag; desktop did not."""
    thinking, content = extract_thinking_and_response(
        "<think>partial thinking, no close tag"
    )
    assert thinking == "partial thinking, no close tag"
    assert content == ""


def test_thinking_parser_strips_trailing_whitespace():
    cleaned = strip_thinking_tags(
        "<think>  padded reasoning  </think>  padded final  "
    )
    assert cleaned == "padded final"
