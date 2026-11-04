"""Generic Document deletion routes use serialized worker cleanup."""

from __future__ import annotations

import asyncio

from airunner_services.api.routes import domain_resource_router, llm_rag_routes
from airunner_services.llm.workers.rag_index_admission import (
    acknowledge_rag_index_job,
    claim_rag_index_job,
    record_rag_job_result,
    release_rag_index_job,
)


class _WorkerMediator:
    def emit_signal(self, signal, payload):
        assert signal == "rag_delete_document_signal"
        token = claim_rag_index_job(payload["_job_token"])
        assert token is not None
        acknowledge_rag_index_job(token, True)
        record_rag_job_result(
            token,
            {"success": True, "deleted": True, "count": len(payload["document_ids"]), "cleanup_pending": []},
        )
        release_rag_index_job(token)


def _client(monkeypatch):
    monkeypatch.setattr(llm_rag_routes, "SignalMediator", _WorkerMediator)
    monkeypatch.setattr(llm_rag_routes, "DELETE_JOB_TIMEOUT_SECONDS", 0.2)
    return domain_resource_router.build_domain_router("library")


def test_singular_document_delete_uses_worker_signal(monkeypatch):
    client = _client(monkeypatch)

    route = next(
        item for item in client.routes
        if getattr(item, "path", None) == "/resources/{resource}/{record_id}"
        and "DELETE" in item.methods
    )
    response = asyncio.run(route.endpoint("Document", 31))

    assert response == {"deleted": True, "count": 1}


def test_bulk_document_delete_uses_worker_cleanup(monkeypatch):
    client = _client(monkeypatch)
    monkeypatch.setattr(
        domain_resource_router,
        "records_to_delete",
        lambda *_args, **_kwargs: [31, 32],
    )

    route = next(
        item for item in client.routes
        if getattr(item, "path", None) == "/resources/{resource}/delete"
    )
    from airunner_services.api.routes.domain_resource_contracts import DeleteRequest
    response = asyncio.run(route.endpoint("Document", DeleteRequest(filters={})))

    assert response == {"deleted": True, "count": 2}
