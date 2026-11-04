"""Neutral contracts shared by embedding runtimes and their consumers.

This module contains value and error shapes only. It has no model, network,
database, or application-domain dependencies.
"""

from __future__ import annotations

from typing import Any

from pydantic import (
    BaseModel, ConfigDict, Field, SerializerFunctionWrapHandler, model_serializer,
)


ERROR_EMBEDDING_SPACE_MISMATCH = "embedding_space_mismatch"


class EmbeddingModelIdentity(BaseModel):
    """Identity of an embedding space, including its vector width."""

    model_config = ConfigDict(extra="forbid")

    model_id: str
    revision: str = "main"
    dimension: int = Field(gt=0)
    space_fingerprint: str | None = None

    @model_serializer(mode="wrap")
    def _serialize_identity(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        """Preserve legacy identity JSON when no space fingerprint is supplied."""
        data = handler(self)
        if self.space_fingerprint is None:
            data.pop("space_fingerprint", None)
        return data

    def matches(self, other: "EmbeddingModelIdentity") -> bool:
        """Return whether two identities describe the same space."""
        return (
            self.model_id == other.model_id
            and self.revision == other.revision
            and self.dimension == other.dimension
            and self.space_fingerprint == other.space_fingerprint
        )


class ServiceErrorCode(BaseModel):
    """Stable structured service error payload."""

    model_config = ConfigDict(extra="forbid")

    code: str
    detail: str = ""
    retryable: bool = False


class ServiceError(Exception):
    """Exception carrying a stable structured service error."""

    def __init__(self, error: ServiceErrorCode) -> None:
        self.error = error
        super().__init__(error.code)


class EmbeddingWorkerUnavailableError(RuntimeError):
    """The owning model worker cannot accept embedding work."""


class EmbeddingWorkerCapacityError(RuntimeError):
    """The bounded model-worker embedding queue is full."""


__all__ = [
    "ERROR_EMBEDDING_SPACE_MISMATCH",
    "EmbeddingModelIdentity",
    "EmbeddingWorkerCapacityError",
    "EmbeddingWorkerUnavailableError",
    "ServiceError",
    "ServiceErrorCode",
]
