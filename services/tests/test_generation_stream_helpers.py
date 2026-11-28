"""Unit tests for the generation stream publication helpers.

_maybe_flush_visible_text and _publish_final_or_denial were
extracted to keep send_end_of_message within the long-function
threshold. These tests pin the once-only flush and the
denial/allow publication branches.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import airunner_services.llm.managers.mixins.generation_stream_support as gs
from airunner_services.llm.managers.mixins.generation_stream_support import (
    _maybe_flush_visible_text,
    _publish_final_or_denial,
)


def _owner(**overrides):
    owner = SimpleNamespace(
        _publication_flushed=False,
        _publication_denied=False,
        _publication_reviewed_text=None,
    )
    for key, value in overrides.items():
        setattr(owner, key, value)
    return owner


def test_flush_emits_and_marks_once(monkeypatch):
    owner = _owner()
    emitted = []
    monkeypatch.setattr(
        gs, "_emit_allowed_visible_text", lambda *a: emitted.append(a)
    )
    _maybe_flush_visible_text(owner, MagicMock(), "hello", [0])
    assert owner._publication_flushed is True
    assert len(emitted) == 1
    # Second call is a no-op (already flushed).
    _maybe_flush_visible_text(owner, MagicMock(), "hello", [0])
    assert len(emitted) == 1


def test_flush_skips_empty_text(monkeypatch):
    owner = _owner()
    emitted = []
    monkeypatch.setattr(
        gs, "_emit_allowed_visible_text", lambda *a: emitted.append(a)
    )
    _maybe_flush_visible_text(owner, MagicMock(), "", [0])
    assert owner._publication_flushed is False
    assert emitted == []


def test_denial_sends_generic_message(monkeypatch):
    owner = _owner(_publication_denied=True)
    sent = []
    monkeypatch.setattr(
        gs, "_send_end_of_message_ungated", lambda *a: sent.append(a)
    )
    _publish_final_or_denial(
        owner, MagicMock(), [0], [], None, None, None, "txt", None, "txt"
    )
    assert len(sent) == 1
    assert sent[0][7] == gs.GENERIC_PUBLICATION_DENIAL_MESSAGE
    assert owner._publication_denied is True


def test_allow_path_flushes_and_sends(monkeypatch):
    owner = _owner()
    sent = []
    emitted = []
    monkeypatch.setattr(
        gs, "_send_end_of_message_ungated", lambda *a: sent.append(a)
    )
    monkeypatch.setattr(
        gs, "_emit_allowed_visible_text", lambda *a: emitted.append(a)
    )
    _publish_final_or_denial(
        owner, MagicMock(), [0], [], None, None, None, "txt", None, "txt"
    )
    assert len(sent) == 1
    assert sent[0][7] == "txt"
    assert len(emitted) == 1
