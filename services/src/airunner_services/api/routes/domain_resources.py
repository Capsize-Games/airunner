"""Resource-oriented domain routes for GUI data clients."""

from __future__ import annotations

from .domain_resource_contracts import DeleteRequest, MutationRequest, QueryRequest
from .domain_resource_router import build_domain_router


settings_router = build_domain_router("settings")
catalog_router = build_domain_router("catalog")
library_router = build_domain_router("library")
workspace_router = build_domain_router("workspace")


__all__ = [
    "catalog_router",
    "DeleteRequest",
    "library_router",
    "MutationRequest",
    "QueryRequest",
    "settings_router",
    "workspace_router",
]