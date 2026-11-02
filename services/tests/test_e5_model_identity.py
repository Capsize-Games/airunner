"""File-manifest and text-contract tests; never load model weights."""

from __future__ import annotations

import hashlib

import pytest

from airunner_services.runtimes import e5_model_identity as identity_module
from airunner_services.runtimes.e5_model_identity import (
    E5ModelIdentity,
    E5ModelIdentityError,
    VerifiedE5Embedder,
    verify_e5_model_directory,
)


def _synthetic_manifest(tmp_path):
    expected = {}
    for name, payload in (("config.json", b"cfg"), ("weights.bin", b"weights")):
        (tmp_path / name).write_bytes(payload)
        expected[name] = (len(payload), hashlib.sha256(payload).hexdigest())
    return expected


def test_manifest_verification_is_bound_to_exact_files(tmp_path):
    expected = _synthetic_manifest(tmp_path)
    result = verify_e5_model_directory(tmp_path, expected_files=expected)
    assert result.file_sha256 == tuple(
        sorted((name, digest) for name, (_, digest) in expected.items())
    )

    (tmp_path / "weights.bin").write_bytes(b"altered")
    with pytest.raises(E5ModelIdentityError, match="size mismatch|digest mismatch"):
        verify_e5_model_directory(tmp_path, expected_files=expected)


def test_manifest_rejects_unexpected_inputs_and_symlinks(tmp_path):
    expected = _synthetic_manifest(tmp_path)
    (tmp_path / "custom.py").write_text("raise RuntimeError()", encoding="utf-8")
    with pytest.raises(E5ModelIdentityError, match="unexpected E5 files"):
        verify_e5_model_directory(tmp_path, expected_files=expected)
    (tmp_path / "custom.py").unlink()
    (tmp_path / "linked.bin").symlink_to(tmp_path / "config.json")
    with pytest.raises(E5ModelIdentityError, match="symlink"):
        verify_e5_model_directory(tmp_path, expected_files=expected)


def test_verified_adapter_adds_e5_prefixes_once():
    expected = {"config.json": (1, hashlib.sha256(b"x").hexdigest())}
    # The temporary manifest can be synthetic; this test exercises only the
    # adapter input contract and never deserializes it as a canonical index.
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as directory:
        Path(directory, "config.json").write_bytes(b"x")
        identity = verify_e5_model_directory(directory, expected_files=expected)

    class FakeEmbedder:
        model_name = "local-test-model"

        def __init__(self):
            self.queries = []
            self.documents = []

        def embed_query(self, text):
            self.queries.append(text)
            return [1.0]

        def embed_documents(self, texts):
            self.documents.append(list(texts))
            return [[1.0] for _ in texts]

    raw = FakeEmbedder()
    wrapped = VerifiedE5Embedder(raw, identity)
    wrapped.embed_query("query: already prefixed")
    wrapped.embed_query("new query")
    wrapped.embed_documents(["passage: existing", "new passage"])
    assert raw.queries == ["query: already prefixed", "query: new query"]
    assert raw.documents == [["passage: existing", "passage: new passage"]]


def test_identity_record_rejects_noncanonical_file_map():
    file_hashes = tuple(
        sorted((name, digest) for name, (_, digest) in identity_module.E5_MODEL_FILES.items())
    )
    identity = E5ModelIdentity(
        model_id=identity_module.E5_LARGE_MODEL_ID,
        revision=identity_module.E5_LARGE_REVISION,
        dimension=identity_module.E5_LARGE_DIMENSION,
        manifest_sha256=identity_module._manifest_digest(file_hashes),
        file_sha256=file_hashes,
    )
    assert E5ModelIdentity.from_dict(identity.to_dict()) == identity
    altered = identity.to_dict()
    altered["file_sha256"] = {"model.safetensors": "0" * 64}
    altered["manifest_sha256"] = identity_module._manifest_digest(
        (("model.safetensors", "0" * 64),)
    )
    with pytest.raises(E5ModelIdentityError, match="reviewed manifest"):
        E5ModelIdentity.from_dict(altered)


def test_shared_identity_keeps_prefix_contract_in_its_space_fingerprint():
    verified = _identity_for_shared_contract()
    shared = verified.to_embedding_model_identity()
    same_model_without_fingerprint = type(shared)(
        model_id=shared.model_id,
        revision=shared.revision,
        dimension=shared.dimension,
    )
    assert shared.space_fingerprint == verified.manifest_sha256
    assert not shared.matches(same_model_without_fingerprint)


def test_identity_json_rejects_coercible_wrong_types():
    file_hashes = tuple(
        sorted((name, digest) for name, (_, digest) in identity_module.E5_MODEL_FILES.items())
    )
    identity = _identity_for_shared_contract()
    bad = identity.to_dict()
    bad["normalized_outputs"] = "false"
    with pytest.raises(E5ModelIdentityError, match="invalid E5 identity"):
        E5ModelIdentity.from_dict(bad)


def _identity_for_shared_contract():
    file_hashes = tuple(
        sorted((name, digest) for name, (_, digest) in identity_module.E5_MODEL_FILES.items())
    )
    return E5ModelIdentity(
        model_id=identity_module.E5_LARGE_MODEL_ID,
        revision=identity_module.E5_LARGE_REVISION,
        dimension=identity_module.E5_LARGE_DIMENSION,
        manifest_sha256=identity_module._manifest_digest(file_hashes),
        file_sha256=file_hashes,
    )
