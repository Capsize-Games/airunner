"""Terminal RAG worker results stay bounded when requesters disconnect."""

from __future__ import annotations

from airunner_services.llm.workers import rag_index_admission as admission


def _clear_results():
    with admission._STATE_LOCK:
        admission._JOB_RESULTS.clear()
        admission._ACTIVE_TOKEN = None
        admission._ACTIVE_CLAIMED = False
        admission._ACKS.clear()


def test_abandoned_delete_results_are_bounded(monkeypatch):
    _clear_results()
    monkeypatch.setattr(admission, "JOB_RESULT_MAX", 8)
    try:
        for index in range(40):
            token = admission.reserve_rag_index_job()
            assert token
            admission.record_rag_job_result(token, {"success": True, "index": index})
            admission.release_rag_index_job(token)

        assert len(admission._JOB_RESULTS) == 8
        assert admission.get_rag_job_result(token) == {
            "success": True,
            "index": 39,
        }
    finally:
        _clear_results()


def test_abandoned_delete_results_expire(monkeypatch):
    _clear_results()
    now = [100.0]
    monkeypatch.setattr(admission.time, "monotonic", lambda: now[0])
    try:
        token = admission.reserve_rag_index_job()
        assert token
        admission.record_rag_job_result(token, {"success": True})
        admission.release_rag_index_job(token)

        now[0] += admission.JOB_RESULT_TTL_SECONDS + 1
        assert admission.get_rag_job_result(token) is None
        assert not admission._JOB_RESULTS
    finally:
        _clear_results()
