"""Unit tests for the companion job row insertion helper.

_insert_job_row was extracted to keep schedule() within the
long-function threshold. These tests pin the row shape, the happy
path, and the concurrent-duplicate backstop.
"""

from enum import Enum
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import IntegrityError

from airunner_services.llm.companion.jobs import DurableCompanionScheduler
from airunner_services.llm.companion.scheduler import CompanionJobType


def _make_service():
    service = DurableCompanionScheduler.__new__(DurableCompanionScheduler)
    service._max_attempts = 3
    return service


def _request():
    return SimpleNamespace(
        chatbot_id="7",
        session_id=None,
        job_type=CompanionJobType.MOOD_UPDATE,
        idempotency_key="k1",
        payload={"a": 1},
    )


def test_insert_happy_path_returns_row():
    service = _make_service()
    db = MagicMock()
    row, duplicate = service._insert_job_row(db, _request(), "now")
    assert duplicate is None
    assert row is not None
    assert row.chatbot_id == 7
    assert row.idempotency_key == "k1"
    assert row.payload == {"a": 1}
    db.add.assert_called_once_with(row)
    db.flush.assert_called_once()


def test_insert_duplicate_returns_duplicate_handle(monkeypatch):
    service = _make_service()
    db = MagicMock()
    db.flush.side_effect = IntegrityError("stmt", "params", Exception("dup"))

    winner = SimpleNamespace(id=42)

    def _furb(_, request):
        return winner

    monkeypatch.setattr(
        "airunner_services.llm.companion.jobs._find_by_key", _furb
    )
    row, duplicate = service._insert_job_row(db, _request(), "now")
    assert row is None
    assert duplicate is not None
    assert duplicate.job_id == "42"
    assert duplicate.accepted is False
    assert duplicate.reason == "duplicate"
    db.begin_nested.return_value.rollback.assert_called_once()


def test_insert_preserves_session_id():
    service = _make_service()
    db = MagicMock()
    request = _request()
    request.session_id = "9"
    row, _ = service._insert_job_row(db, request, "now")
    assert row.session_id == 9
    assert row.payload == {"a": 1}
