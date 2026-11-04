"""The explicit RAG reindex endpoint uses bounded admitted worker intake."""

from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from airunner_services.api.admission_middleware import GENERATION_PATHS
from airunner_services.api.routes import llm_rag_routes
from airunner_services.api.routes.llm_contracts import RagIndexRequest
from airunner_services.llm.workers.rag_index_admission import (
    acknowledge_rag_index_job,
    claim_rag_index_job,
    finish_rag_index_dispatch,
    release_rag_index_job,
    reserve_rag_index_job,
)


def test_reindex_route_emits_existing_validated_selected_index_signal(monkeypatch):
    calls = []

    class FakeMediator:
        def emit_signal(self, code, payload):
            token = claim_rag_index_job(payload["_job_token"])
            assert token is not None
            acknowledge_rag_index_job(token, True)
            calls.append((code, payload))

    monkeypatch.setattr(llm_rag_routes, "SignalMediator", FakeMediator)
    response = asyncio.run(
        llm_rag_routes.start_rag_reindex(
            RagIndexRequest(file_paths=["/documents/a.pdf"])
        )
    )

    assert response == {"status": "accepted", "scope": "reindex", "count": 1}
    try:
        assert len(calls) == 1
        assert calls[0][0] == llm_rag_routes.SignalCode.RAG_INDEX_SELECTED_DOCUMENTS
        assert calls[0][1]["file_paths"] == ["/documents/a.pdf"]
        assert calls[0][1]["reindex"] is True
        assert calls[0][1]["_job_token"]
        assert "/api/v1/llm/rag/reindex" in GENERATION_PATHS
    finally:
        if calls:
            release_rag_index_job(calls[0][1]["_job_token"])


def test_reindex_route_requires_at_least_one_path():
    with pytest.raises(HTTPException) as error:
        asyncio.run(llm_rag_routes.start_rag_reindex(RagIndexRequest()))

    assert error.value.status_code == 400


def test_busy_reindex_is_rejected_without_accepting_a_second_job():
    token = reserve_rag_index_job()
    assert token is not None
    try:
        with pytest.raises(HTTPException) as error:
            asyncio.run(
                llm_rag_routes.start_rag_reindex(
                    RagIndexRequest(file_paths=["/documents/a.pdf"])
                )
            )
        assert error.value.status_code == 409
        assert error.value.detail == "rag_index_busy"
    finally:
        release_rag_index_job(token)


@pytest.mark.parametrize("callback_mode", ["no_listener", "throwing_listener"])
def test_missing_or_throwing_worker_does_not_leave_a_stuck_reservation(
    monkeypatch, callback_mode
):
    from airunner_services.llm.workers import rag_index_admission

    captured = []
    monkeypatch.setattr(llm_rag_routes, "ACK_TIMEOUT_SECONDS", 0.01)

    class FakeMediator:
        def emit_signal(self, _code, payload):
            captured.append(payload["_job_token"])
            if callback_mode == "throwing_listener":
                try:
                    raise RuntimeError("worker callback failed")
                except RuntimeError:
                    pass

    monkeypatch.setattr(llm_rag_routes, "SignalMediator", FakeMediator)
    with pytest.raises(HTTPException) as error:
        asyncio.run(
            llm_rag_routes.start_rag_reindex(
                RagIndexRequest(file_paths=["/documents/a.pdf"])
            )
        )
    assert error.value.status_code == 503
    assert error.value.detail == "rag_index_worker_unavailable"

    late_token = captured[0]
    next_token = reserve_rag_index_job()
    assert next_token is not None
    assert claim_rag_index_job(late_token) is None
    assert rag_index_admission.rag_index_cancel_requested() is False
    release_rag_index_job(next_token)


def test_pending_worker_ack_does_not_block_event_loop_and_cancellation_releases(
    monkeypatch,
):
    async def scenario():
        from airunner_services.llm.workers import rag_index_admission

        monkeypatch.setattr(llm_rag_routes, "ACK_TIMEOUT_SECONDS", 1.0)

        class NoAckMediator:
            def emit_signal(self, _code, _payload):
                pass

        monkeypatch.setattr(llm_rag_routes, "SignalMediator", NoAckMediator)
        request_task = asyncio.create_task(
            llm_rag_routes.start_rag_reindex(
                RagIndexRequest(file_paths=["/documents/a.pdf"])
            )
        )
        # This coroutine must run while the endpoint waits for worker ack.
        await asyncio.sleep(0.01)
        assert request_task.done() is False
        token = rag_index_admission._ACTIVE_TOKEN
        assert token is not None
        request_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await request_task

        next_token = reserve_rag_index_job()
        assert next_token is not None
        release_rag_index_job(next_token)

    asyncio.run(scenario())


def test_fast_completed_worker_ack_survives_worker_slot_release(monkeypatch):
    class FastWorkerMediator:
        def emit_signal(self, _code, payload):
            token = claim_rag_index_job(payload["_job_token"])
            assert token is not None
            acknowledge_rag_index_job(token, True)
            # A short job can finish before the HTTP coroutine consumes its ack.
            release_rag_index_job(token)

    monkeypatch.setattr(llm_rag_routes, "SignalMediator", FastWorkerMediator)
    result = asyncio.run(
        llm_rag_routes.start_rag_reindex(
            RagIndexRequest(file_paths=["/documents/a.pdf"])
        )
    )
    assert result["status"] == "accepted"


def test_timeout_cleanup_does_not_release_acknowledged_running_worker():
    from airunner_services.llm.workers import rag_index_admission

    token = reserve_rag_index_job()
    assert token is not None
    assert claim_rag_index_job(token) == token
    acknowledge_rag_index_job(token, True)
    assert finish_rag_index_dispatch(token) is True
    assert rag_index_admission.owns_rag_index_job(token)
    release_rag_index_job(token)


def test_claimed_listener_failure_releases_reservation_and_late_start_is_ignored(
    monkeypatch,
):
    from airunner_services.llm.workers import rag_index_admission

    captured = []

    def failing_worker_callback(payload):
        token = payload["_job_token"]
        captured.append(token)
        assert claim_rag_index_job(token) == token
        raise RuntimeError("worker failed before thread start")

    class ClaimThenFailMediator:
        def emit_signal(self, _code, payload):
            try:
                failing_worker_callback(payload)
            except RuntimeError:
                # Mirrors SignalMediator's callback-error swallowing behavior.
                pass

    monkeypatch.setattr(llm_rag_routes, "ACK_TIMEOUT_SECONDS", 0.01)
    monkeypatch.setattr(llm_rag_routes, "SignalMediator", ClaimThenFailMediator)
    with pytest.raises(HTTPException) as error:
        asyncio.run(
            llm_rag_routes.start_rag_reindex(
                RagIndexRequest(file_paths=["/documents/a.pdf"])
            )
        )
    assert error.value.status_code == 503
    assert claim_rag_index_job(captured[0]) is None
    next_token = reserve_rag_index_job()
    assert next_token is not None
    assert rag_index_admission.owns_rag_index_job(next_token) is False
    release_rag_index_job(next_token)


def test_index_request_bounds_paths_for_worker_admission():
    with pytest.raises(ValidationError):
        RagIndexRequest(file_paths=[f"/documents/{index}.pdf" for index in range(65)])
