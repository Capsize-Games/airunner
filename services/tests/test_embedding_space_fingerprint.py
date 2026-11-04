"""Space fingerprints distinguish identical model commits with new encoders."""

from __future__ import annotations

import json

import pytest

from airunner_services.llm.companion.contracts import (
    ChatbotId,
    CompanionError,
)
from airunner_services.llm.companion.embeddings import (
    CompanionEmbeddingIndex,
    EmbeddingModelIdentity,
    open_companion_index,
)


class _Client:
    def __init__(self, identity):
        self.identity = identity

    def embed_documents(self, texts):
        return [[float(len(text)), 1.0] for text in texts]

    def embed_query(self, text):
        return [float(len(text)), 1.0]


class _Scheduler:
    def __init__(self):
        self.jobs = []

    def schedule(self, job):
        self.jobs.append(job)


def _identity(fingerprint=None):
    return EmbeddingModelIdentity(
        model_id="intfloat/e5-large",
        revision="4dc6d853a804b9c8886ede6dda8a073b7dc08a81",
        dimension=2,
        space_fingerprint=fingerprint,
    )


def test_generic_space_match_includes_fingerprint():
    old = _identity()
    same = _identity()
    different_prefix = _identity("manifest-with-query-passage-v2")

    assert old.matches(same)
    assert not old.matches(different_prefix)
    assert not _identity("prefix-v1").matches(_identity("prefix-v2"))


def test_legacy_companion_manifest_without_fingerprint_schedules_rebuild(
    tmp_path,
):
    old_identity = _identity()
    old_client = _Client(old_identity)
    persist_dir = str(tmp_path / "index")
    index = CompanionEmbeddingIndex(identity=old_identity)
    index.add_texts(["old memory"], old_client)
    index.save(persist_dir)

    manifest_path = tmp_path / "index" / "companion_index.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["identity"].pop("space_fingerprint", None)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    new_client = _Client(_identity("canonical-e5-query-passage-v1"))
    scheduler = _Scheduler()
    with pytest.raises(CompanionError):
        open_companion_index(
            persist_dir,
            ChatbotId(9),
            new_client,
            scheduler,
            idempotency_key="rebuild-fingerprint",
        )

    assert len(scheduler.jobs) == 1
    assert scheduler.jobs[0].payload["identity"]["space_fingerprint"] == (
        "canonical-e5-query-passage-v1"
    )


def test_companion_manifest_rejects_different_prefix_fingerprint(tmp_path):
    persisted = _identity("canonical-e5-query-passage-v1")
    index = CompanionEmbeddingIndex(identity=persisted)
    index.add_texts(["memory"], _Client(persisted))
    persist_dir = str(tmp_path / "index")
    index.save(persist_dir)

    scheduler = _Scheduler()
    with pytest.raises(CompanionError):
        open_companion_index(
            persist_dir,
            ChatbotId(9),
            _Client(_identity("different-prefix-contract")),
            scheduler,
            idempotency_key="rebuild-prefix",
        )
    assert len(scheduler.jobs) == 1


@pytest.mark.parametrize("fingerprint", [None, "canonical-space"])
def test_identity_serialization_preserves_legacy_shape_and_new_fingerprint(fingerprint):
    identity = _identity(fingerprint)
    expected = {"model_id": identity.model_id, "revision": identity.revision, "dimension": 2}
    if fingerprint is not None:
        expected["space_fingerprint"] = fingerprint
    assert identity.model_dump() == expected
    assert json.loads(identity.model_dump_json()) == expected
    assert EmbeddingModelIdentity.model_validate_json(identity.model_dump_json()).matches(identity)
