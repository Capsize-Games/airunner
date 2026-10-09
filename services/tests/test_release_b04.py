"""Regression tests for release issue B04.

Proves local companion embeddings carry an explicit index identity:

- Deterministic fake embeddings support an index/query round trip.
- A model/revision/dimension mismatch is detected and can never
  yield mixed-space search results; opening a stale persisted index
  schedules one explicit rebuild job instead.
- Nothing here touches an external transport: the new modules import
  without torch/langchain/http/redis, index operations run with the
  socket layer blocked, and the local adapter refuses remote
  endpoint embedders at construction.

No real model, network, database, or GUI access — all inference
boundaries are fakes, persistence goes to ``tmp_path`` only.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from typing import Any, Dict, List

import pytest

from airunner_services.llm.companion.contracts import (
    ERROR_EMBEDDING_SPACE_MISMATCH,
    ChatbotId,
    CompanionError,
)
from airunner_services.llm.companion.embeddings import (
    INDEX_MANIFEST_FILE,
    CompanionEmbeddingClient,
    CompanionEmbeddingIndex,
    EmbeddingModelIdentity,
    open_companion_index,
    rebuild_companion_index,
)
from airunner_services.llm.companion.scheduler import (
    CompanionJobHandle,
    CompanionJobRequest,
    CompanionJobType,
    CompanionScheduler,
)
from airunner_services.runtimes.local_embeddings import (
    E5_LARGE_MODEL_ID,
    E5_LARGE_REVISION,
    LocalEmbeddingClient,
)

_DIM = 16


class FakeEmbeddingClient:
    """Deterministic hash embeddings: same text, same vector."""

    def __init__(self, identity: EmbeddingModelIdentity) -> None:
        self._identity = identity

    @property
    def identity(self) -> EmbeddingModelIdentity:
        return self._identity

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._vector(text) for text in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._vector(text)

    def _vector(self, text: str) -> List[float]:
        dim = int(self._identity.dimension)
        out: List[float] = []
        block = 0
        while len(out) < dim:
            digest = hashlib.sha256(
                f"b04:{self._identity.model_id}:"
                f"{self._identity.revision}:{block}:{text}".encode()
            ).digest()
            out.extend(byte / 127.5 - 1.0 for byte in digest)
            block += 1
        return out[:dim]


class FakeScheduler:
    """Captures scheduled jobs; satisfies CompanionScheduler."""

    def __init__(self) -> None:
        self.scheduled: List[CompanionJobRequest] = []

    def schedule(self, request: CompanionJobRequest) -> CompanionJobHandle:
        self.scheduled.append(request)
        return CompanionJobHandle(
            job_id=f"job-{len(self.scheduled)}",
            job_type=request.job_type,
            accepted=True,
        )


def _identity(**overrides: Any) -> EmbeddingModelIdentity:
    base: Dict[str, Any] = {
        "model_id": E5_LARGE_MODEL_ID,
        "revision": E5_LARGE_REVISION,
        "dimension": _DIM,
    }
    base.update(overrides)
    return EmbeddingModelIdentity(**base)


def test_fake_client_is_deterministic_and_satisfies_protocol() -> None:
    client = FakeEmbeddingClient(_identity())
    assert isinstance(client, CompanionEmbeddingClient)
    first = client.embed_query("my dog is named Biscuit")
    second = FakeEmbeddingClient(_identity()).embed_query(
        "my dog is named Biscuit"
    )
    assert first == second
    assert len(first) == _DIM
    assert client.embed_query("unrelated text") != first


def test_query_index_round_trip_returns_the_indexed_text() -> None:
    client = FakeEmbeddingClient(_identity())
    index = CompanionEmbeddingIndex(identity=client.identity)
    index.add_texts(
        ["my dog is named Biscuit", "the sky is blue", "tea is hot"],
        client,
        metadatas=[{"turn": 1}, {"turn": 2}, {"turn": 3}],
    )
    assert len(index) == 3
    hits = index.search("my dog is named Biscuit", client, k=2)
    assert hits[0].text == "my dog is named Biscuit"
    assert hits[0].score == pytest.approx(1.0)
    assert hits[0].metadata == {"turn": 1}


def test_search_empty_index_returns_no_results() -> None:
    client = FakeEmbeddingClient(_identity())
    index = CompanionEmbeddingIndex(identity=client.identity)
    assert index.search("anything", client, k=5) == []
    assert index.search("anything", client, k=0) == []


def test_dimension_mismatch_cannot_add_or_search() -> None:
    index = CompanionEmbeddingIndex(identity=_identity())
    narrow = FakeEmbeddingClient(_identity(dimension=8))
    with pytest.raises(CompanionError) as excinfo:
        index.add_texts(["some text"], narrow)
    assert excinfo.value.error.code == ERROR_EMBEDDING_SPACE_MISMATCH
    assert len(index) == 0
    with pytest.raises(CompanionError):
        index.search("some text", narrow, k=1)


def test_revision_and_model_mismatch_cannot_search() -> None:
    client = FakeEmbeddingClient(_identity())
    index = CompanionEmbeddingIndex(identity=client.identity)
    index.add_texts(["remembered text"], client)
    for foreign in (
        FakeEmbeddingClient(_identity(revision="other-branch")),
        FakeEmbeddingClient(_identity(model_id="other/model")),
    ):
        with pytest.raises(CompanionError) as excinfo:
            index.search("remembered text", foreign, k=1)
        assert excinfo.value.error.code == ERROR_EMBEDDING_SPACE_MISMATCH


def test_persisted_index_records_identity_and_round_trips(tmp_path) -> None:
    client = FakeEmbeddingClient(_identity())
    index = CompanionEmbeddingIndex(identity=client.identity)
    index.add_texts(["persisted memory"], client)
    persist_dir = str(tmp_path / "index")
    assert not CompanionEmbeddingIndex.is_persisted(persist_dir)
    index.save(persist_dir)
    assert CompanionEmbeddingIndex.is_persisted(persist_dir)
    manifest = json.loads(
        (tmp_path / "index" / INDEX_MANIFEST_FILE).read_text()
    )
    assert manifest["identity"] == {
        "model_id": E5_LARGE_MODEL_ID,
        "revision": E5_LARGE_REVISION,
        "dimension": _DIM,
    }
    loaded = CompanionEmbeddingIndex.load(persist_dir, client)
    hits = loaded.search("persisted memory", client, k=1)
    assert [hit.text for hit in hits] == ["persisted memory"]


def test_stale_index_schedules_rebuild_and_never_searches(tmp_path) -> None:
    old = FakeEmbeddingClient(_identity())
    persist_dir = str(tmp_path / "index")
    index = CompanionEmbeddingIndex(identity=old.identity)
    index.add_texts(["old-space memory"], old)
    index.save(persist_dir)

    new = FakeEmbeddingClient(_identity(dimension=32))
    scheduler = FakeScheduler()
    with pytest.raises(CompanionError) as excinfo:
        open_companion_index(
            persist_dir,
            ChatbotId(7),
            new,
            scheduler,
            idempotency_key="rebuild-1",
        )
    assert excinfo.value.error.code == ERROR_EMBEDDING_SPACE_MISMATCH
    assert [job.job_type for job in scheduler.scheduled] == [
        CompanionJobType.EMBEDDING_REBUILD
    ]
    job = scheduler.scheduled[0]
    assert job.chatbot_id == 7
    assert job.idempotency_key == "rebuild-1"
    assert job.payload["identity"]["dimension"] == 32


def test_open_fresh_dir_returns_empty_matching_index(tmp_path) -> None:
    client = FakeEmbeddingClient(_identity())
    scheduler = FakeScheduler()
    index = open_companion_index(
        str(tmp_path / "new-index"),
        ChatbotId(7),
        client,
        scheduler,
        idempotency_key="fresh-1",
    )
    assert len(index) == 0
    assert index.identity.matches(client.identity)
    assert scheduler.scheduled == []


def test_rebuild_re_embeds_persisted_texts_into_the_new_space(
    tmp_path,
) -> None:
    old = FakeEmbeddingClient(_identity())
    persist_dir = str(tmp_path / "index")
    index = CompanionEmbeddingIndex(identity=old.identity)
    index.add_texts(["kept through rebuild"], old)
    index.save(persist_dir)

    new = FakeEmbeddingClient(_identity(revision="new-revision"))
    rebuilt = rebuild_companion_index(persist_dir, new)
    assert rebuilt.identity.matches(new.identity)
    hits = rebuilt.search("kept through rebuild", new, k=1)
    assert [hit.text for hit in hits] == ["kept through rebuild"]
    assert CompanionEmbeddingIndex.load(persist_dir, new).identity.matches(
        new.identity
    )


def test_local_client_adapts_duck_typed_embedder() -> None:
    class _LangchainShaped:
        def embed_documents(self, texts: List[str]) -> List[List[float]]:
            return [[float(len(text))] * 4 for text in texts]

        def embed_query(self, text: str) -> List[float]:
            return [float(len(text))] * 4

    identity = _identity(dimension=4)
    client = LocalEmbeddingClient(_LangchainShaped(), identity)
    assert isinstance(client, CompanionEmbeddingClient)
    assert client.identity == identity
    assert client.embed_query("abcd") == [4.0, 4.0, 4.0, 4.0]


def test_local_client_rejects_off_width_vectors_fail_closed() -> None:
    class _WrongWidth:
        def embed_documents(self, texts: List[str]) -> List[List[float]]:
            return [[0.0] * 3 for _ in texts]

        def embed_query(self, text: str) -> List[float]:
            return [0.0] * 3

    client = LocalEmbeddingClient(_WrongWidth(), _identity(dimension=4))
    with pytest.raises(CompanionError) as excinfo:
        client.embed_query("anything")
    assert excinfo.value.error.code == ERROR_EMBEDDING_SPACE_MISMATCH


def test_local_client_refuses_remote_endpoint_embedders() -> None:
    class _OllamaShaped:
        base_url = "http://other-machine:11434"

        def embed_documents(self, texts: List[str]) -> List[List[float]]:
            raise AssertionError("must never be called")

        def embed_query(self, text: str) -> List[float]:
            raise AssertionError("must never be called")

    with pytest.raises(ValueError, match="remote"):
        LocalEmbeddingClient(_OllamaShaped(), _identity())


def test_index_operations_make_no_external_transport_call(
    monkeypatch, tmp_path
) -> None:
    import socket

    def _blocked(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("external transport call attempted")

    monkeypatch.setattr(socket, "socket", _blocked)
    monkeypatch.setattr(socket, "create_connection", _blocked)
    client = FakeEmbeddingClient(_identity())
    index = CompanionEmbeddingIndex(identity=client.identity)
    index.add_texts(["offline text"], client)
    assert index.search("offline text", client, k=1)[0].text == "offline text"
    persist_dir = str(tmp_path / "index")
    index.save(persist_dir)
    CompanionEmbeddingIndex.load(persist_dir, client)


def test_new_modules_import_without_heavy_or_remote_deps() -> None:
    """Importing the B04 modules must not pull torch, langchain, an
    HTTP client, or redis — mirroring test_release_b01.py's
    fresh-subprocess import check."""
    markers = "torch,langchain,httpx,requests,urllib3,redis,openai"
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; before = set(sys.modules); "
            "import airunner_services.llm.companion.embeddings; "
            "import airunner_services.runtimes.local_embeddings; "
            "after = set(sys.modules); new = after - before; "
            f"markers = {markers!r}.split(','); "
            "hits = [m for m in new for mk in markers if mk in m.lower()]; "
            "print(','.join(hits)); sys.exit(1 if hits else 0)",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stdout
