"""Verified local artifact identity and input contract for intfloat/e5-large.

This module inspects local model files only. It does not import a model
runtime, download artifacts, or execute code from the model directory.
"""

from __future__ import annotations

from dataclasses import dataclass
from contextlib import nullcontext
import hashlib
import json
import os
from pathlib import Path
import stat
from typing import Mapping

from airunner_services.runtimes.embedding_contracts import EmbeddingModelIdentity


E5_LARGE_MODEL_ID = "intfloat/e5-large"
E5_LARGE_REVISION = "4dc6d853a804b9c8886ede6dda8a073b7dc08a81"
E5_LARGE_DIMENSION = 1024
E5_MAX_SEQUENCE_LENGTH = 512
E5_PREFIX_POLICY = "e5-query-passage-v1"
E5_NORMALIZED_OUTPUTS = True

# SHA-256 and byte sizes were compared to the pinned upstream Git/LFS metadata.
E5_MODEL_FILES: dict[str, tuple[int, str]] = {
    "1_Pooling/config.json": (
        201,
        "56c469dba9e31869bb7dfceb9b3d76ac06549d1ba869509d8eb4e8aeb31d62d1",
    ),
    "config.json": (
        611,
        "d960925459889922fd6b3078e05d89c5b0fadd0018d26421699066cdd98bfb3a",
    ),
    "model.safetensors": (
        1340616616,
        "93e04bd3ec4911982905395e3c48ee739ddb8aa88380b8ce27f1fd20bfa5fa8e",
    ),
    "modules.json": (
        387,
        "c6e29747481e8b5dd2b58401966aeac910de39092f90cda9a704b1545f902b04",
    ),
    "sentence_bert_config.json": (
        57,
        "948201d8329907aae938fa62f9ceeed53f5694dacc2b87b9f3b78b37ee986529",
    ),
    "special_tokens_map.json": (
        112,
        "303df45a03609e4ead04bc3dc1536d0ab19b5358db685b6f3da123d05ec200e3",
    ),
    "tokenizer.json": (
        466081,
        "5fd1c882abbd30517dced455a2c9768945ec726b96727927e4959348d9de550b",
    ),
    "tokenizer_config.json": (
        385,
        "8ccb5459f367df07ad1a072b1f12480183163386b6e889cff5463040ef7aed3d",
    ),
    "vocab.txt": (
        231508,
        "07eced375cec144d27c900241f3e339478dec958f92fddbc551f295c992038a3",
    ),
}

_NON_RUNTIME_FILES = frozenset({"README.md"})
# One owner-local compatibility file is emitted by Sentence Transformers 5.6.1.
# Its exact empty version mapping is read as optional metadata, ignored by the
# pinned loader, and does not contribute to the E5 runtime identity.
_REVIEWED_NON_RUNTIME_FILES: dict[str, tuple[int, str]] = {
    "config_sentence_transformers.json": (
        24,
        "bf6a7016c2a0706a987d180e3a323823a5754214261f2c20beb5d4fcec7aad23",
    ),
}
_HASH_BLOCK_BYTES = 1024 * 1024


class E5ModelIdentityError(ValueError):
    """A local E5 artifact does not match the reviewed file manifest."""

    code = "embedding_model_identity_mismatch"


@dataclass(frozen=True, slots=True)
class E5ModelIdentity:
    """Immutable identity for the exact E5 bytes and encoding contract."""

    model_id: str
    revision: str
    dimension: int
    manifest_sha256: str
    file_sha256: tuple[tuple[str, str], ...]
    prefix_policy: str = E5_PREFIX_POLICY
    max_sequence_length: int = E5_MAX_SEQUENCE_LENGTH
    normalized_outputs: bool = E5_NORMALIZED_OUTPUTS

    def matches(self, other: object) -> bool:
        return isinstance(other, E5ModelIdentity) and self == other

    def to_embedding_model_identity(self) -> EmbeddingModelIdentity:
        """Return the shared model/revision/dimension identity contract."""
        return EmbeddingModelIdentity(
            model_id=self.model_id,
            revision=self.revision,
            dimension=self.dimension,
            space_fingerprint=self.manifest_sha256,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "model_id": self.model_id,
            "revision": self.revision,
            "dimension": self.dimension,
            "manifest_sha256": self.manifest_sha256,
            "file_sha256": dict(self.file_sha256),
            "prefix_policy": self.prefix_policy,
            "max_sequence_length": self.max_sequence_length,
            "normalized_outputs": self.normalized_outputs,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "E5ModelIdentity":
        try:
            if type(value.get("schema_version")) is not int or value.get("schema_version") != 1:
                raise ValueError("unsupported identity schema")
            files_value = value["file_sha256"]
            if not isinstance(files_value, Mapping):
                raise ValueError("file_sha256 must be a mapping")
            if any(
                not isinstance(name, str) or not isinstance(digest, str)
                for name, digest in files_value.items()
            ):
                raise ValueError("file_sha256 entries must be strings")
            if (
                not isinstance(value.get("model_id"), str)
                or not isinstance(value.get("revision"), str)
                or not isinstance(value.get("manifest_sha256"), str)
                or not isinstance(value.get("prefix_policy"), str)
                or type(value.get("dimension")) is not int
                or type(value.get("max_sequence_length")) is not int
                or type(value.get("normalized_outputs")) is not bool
            ):
                raise ValueError("identity fields have invalid JSON types")
            files = tuple(sorted(files_value.items()))
            identity = cls(
                model_id=value["model_id"], revision=value["revision"],
                dimension=value["dimension"],
                manifest_sha256=value["manifest_sha256"], file_sha256=files,
                prefix_policy=value["prefix_policy"],
                max_sequence_length=value["max_sequence_length"],
                normalized_outputs=value["normalized_outputs"],
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise E5ModelIdentityError("invalid E5 identity record") from exc
        if identity.manifest_sha256 != _manifest_digest(identity.file_sha256):
            raise E5ModelIdentityError("E5 identity manifest digest is invalid")
        if (identity.model_id != E5_LARGE_MODEL_ID or identity.revision != E5_LARGE_REVISION
                or identity.dimension != E5_LARGE_DIMENSION
                or identity.prefix_policy != E5_PREFIX_POLICY
                or identity.max_sequence_length != E5_MAX_SEQUENCE_LENGTH
                or identity.normalized_outputs is not E5_NORMALIZED_OUTPUTS):
            raise E5ModelIdentityError("E5 identity does not match this runtime")
        canonical_files = tuple(
            (name, digest) for name, (_, digest) in sorted(E5_MODEL_FILES.items())
        )
        if identity.file_sha256 != canonical_files:
            raise E5ModelIdentityError("E5 identity files differ from the reviewed manifest")
        return identity


class VerifiedE5Embedder:
    """Apply E5 retrieval prefixes to a locally verified model exactly once."""

    def __init__(
        self,
        embedder: object,
        identity: E5ModelIdentity,
        *,
        activity_lock: object | None = None,
    ) -> None:
        if not callable(getattr(embedder, "embed_query", None)) or not callable(
            getattr(embedder, "embed_documents", None)
        ):
            raise TypeError("E5 embedder must provide query and document methods")
        self._embedder = embedder
        self._activity_lock = activity_lock
        self.verified_identity = identity
        self.identity = identity.to_embedding_model_identity()
        self.model_name = getattr(embedder, "model_name", E5_LARGE_MODEL_ID)

    def embed_query(self, text: str) -> list[float]:
        guard = self._activity_lock or nullcontext()
        with guard:
            return self._embedder.embed_query(_with_prefix(text, "query: "))

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        guard = self._activity_lock or nullcontext()
        with guard:
            prefixed = [_with_prefix(text, "passage: ") for text in texts]
            vectors = self._embedder.embed_documents(prefixed)
            if len(vectors) != len(texts):
                raise ValueError("E5 embedder returned an invalid batch")
            return vectors


def _with_prefix(text: str, prefix: str) -> str:
    if not isinstance(text, str):
        raise TypeError("embedding input must be a string")
    return text if text.startswith(prefix) else prefix + text


def verify_e5_model_directory(
    model_dir: str | os.PathLike[str],
    *,
    expected_files: Mapping[str, tuple[int, str]] | None = None,
    optional_files: Mapping[str, tuple[int, str]] | None = None,
) -> E5ModelIdentity:
    """Verify local E5 files and return identity bound to their exact hashes.

    ``expected_files`` and ``optional_files`` are overrideable for bounded
    tests that build tiny synthetic directories. Runtime callers use the
    reviewed module constants.
    """
    required = E5_MODEL_FILES if expected_files is None else expected_files
    optional = {} if optional_files is None else optional_files
    root = Path(model_dir).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise E5ModelIdentityError("E5 model path is not a directory")

    allowed = (
        set(required)
        | set(optional)
        | set(_NON_RUNTIME_FILES)
        | set(_REVIEWED_NON_RUNTIME_FILES)
    )
    actual_files: set[str] = set()
    for entry in root.rglob("*"):
        relative = entry.relative_to(root).as_posix()
        if entry.is_symlink():
            raise E5ModelIdentityError(f"symlink is not allowed: {relative}")
        if entry.is_file():
            actual_files.add(relative)
        elif not entry.is_dir():
            raise E5ModelIdentityError(f"unsupported filesystem entry: {relative}")

    missing = sorted(set(required) - actual_files)
    if missing:
        raise E5ModelIdentityError(
            "required E5 files are missing: " + ", ".join(missing)
        )
    unexpected = sorted(actual_files - allowed)
    if unexpected:
        raise E5ModelIdentityError(
            "unexpected E5 files: " + ", ".join(unexpected)
        )

    # Validate narrowly reviewed loader metadata without adding it to the
    # runtime file identity below. This preserves the same identity for the
    # canonical nine runtime files whether or not the stub is present.
    for relative in sorted(set(_REVIEWED_NON_RUNTIME_FILES) & actual_files):
        expected_size, expected_sha256 = _REVIEWED_NON_RUNTIME_FILES[relative]
        digest, actual_size = _hash_regular_file(root / relative)
        if actual_size != expected_size:
            raise E5ModelIdentityError(
                f"E5 file size mismatch for {relative}: expected "
                f"{expected_size}, found {actual_size}"
            )
        if digest != expected_sha256:
            raise E5ModelIdentityError(f"E5 file digest mismatch: {relative}")

    file_hashes: list[tuple[str, str]] = []
    for relative in sorted(set(required) | (set(optional) & actual_files)):
        expected_size, expected_sha256 = (required if relative in required else optional)[relative]
        digest, actual_size = _hash_regular_file(root / relative)
        if actual_size != expected_size:
            raise E5ModelIdentityError(
                f"E5 file size mismatch for {relative}: expected "
                f"{expected_size}, found {actual_size}"
            )
        if digest != expected_sha256:
            raise E5ModelIdentityError(f"E5 file digest mismatch: {relative}")
        file_hashes.append((relative, digest))

    immutable_files = tuple(file_hashes)
    return E5ModelIdentity(
        model_id=E5_LARGE_MODEL_ID,
        revision=E5_LARGE_REVISION,
        dimension=E5_LARGE_DIMENSION,
        manifest_sha256=_manifest_digest(immutable_files),
        file_sha256=immutable_files,
    )


def _hash_regular_file(path: Path) -> tuple[str, int]:
    """Hash one regular file without following symlinks or reading it whole."""
    try:
        before = path.stat(follow_symlinks=False)
        if not stat.S_ISREG(before.st_mode):
            raise E5ModelIdentityError(f"not a regular E5 file: {path.name}")
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        digest = hashlib.sha256()
        size = 0
        with os.fdopen(descriptor, "rb") as handle:
            opened = os.fstat(handle.fileno())
            if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
                raise E5ModelIdentityError(f"E5 file changed while opening: {path.name}")
            while block := handle.read(_HASH_BLOCK_BYTES):
                digest.update(block)
                size += len(block)
            after = os.fstat(handle.fileno())
    except E5ModelIdentityError:
        raise
    except OSError as exc:
        raise E5ModelIdentityError(f"cannot read E5 file: {path.name}") from exc
    if (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) != (
        opened.st_dev,
        opened.st_ino,
        opened.st_size,
        opened.st_mtime_ns,
    ):
        raise E5ModelIdentityError(f"E5 file changed while hashing: {path.name}")
    if size != after.st_size:
        raise E5ModelIdentityError(f"E5 file changed while hashing: {path.name}")
    return digest.hexdigest(), size


def _manifest_digest(file_hashes: tuple[tuple[str, str], ...]) -> str:
    payload = {
        "schema_version": 1,
        "model_id": E5_LARGE_MODEL_ID,
        "revision": E5_LARGE_REVISION,
        "dimension": E5_LARGE_DIMENSION,
        "prefix_policy": E5_PREFIX_POLICY,
        "max_sequence_length": E5_MAX_SEQUENCE_LENGTH,
        "normalized_outputs": E5_NORMALIZED_OUTPUTS,
        "file_sha256": dict(file_hashes),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def canonical_e5_space_fingerprint() -> str:
    """Return the fingerprint for the reviewed E5 files and encode contract."""
    return _manifest_digest(
        tuple((name, digest) for name, (_, digest) in sorted(E5_MODEL_FILES.items()))
    )


__all__ = [
    "E5_LARGE_DIMENSION",
    "E5_LARGE_MODEL_ID",
    "E5_LARGE_REVISION",
    "E5ModelIdentity",
    "E5ModelIdentityError",
    "VerifiedE5Embedder",
    "canonical_e5_space_fingerprint",
    "verify_e5_model_directory",
]
