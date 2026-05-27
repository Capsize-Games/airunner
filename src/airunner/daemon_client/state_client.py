"""Domain-scoped daemon client for persistent GUI state."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from airunner.daemon_client.gui_daemon_client import GuiDaemonClient


class DomainStateClient:
    """Small typed wrapper over one daemon state domain."""

    def __init__(self, daemon_client: GuiDaemonClient, domain: str) -> None:
        self._client = daemon_client
        self._domain = domain

    def execute(
        self,
        model_name: str,
        *,
        operation: str,
        pk: Optional[int] = None,
        first: bool = False,
        values: Optional[Dict[str, Any]] = None,
        defaults: Optional[Dict[str, Any]] = None,
        filters: Optional[Dict[str, Any]] = None,
        expressions: Optional[List[Dict[str, Any]]] = None,
        order_by: Optional[List[Dict[str, Any]]] = None,
        eager_load: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Execute one state operation in the configured domain."""
        response = self._client._request(
            "POST",
            f"/api/v1/state/{self._domain}/{model_name}",
            json_payload={
                "operation": operation,
                "pk": pk,
                "first": first,
                "values": dict(values or {}),
                "defaults": dict(defaults or {}),
                "filters": dict(filters or {}),
                "expressions": list(expressions or []),
                "order_by": list(order_by or []),
                "eager_load": list(eager_load or []),
            },
        )
        return response.json()


class SettingsStateClient(DomainStateClient):
    """Daemon client for application settings and GUI state."""

    def __init__(self, daemon_client: GuiDaemonClient) -> None:
        super().__init__(daemon_client, "settings")


class CatalogStateClient(DomainStateClient):
    """Daemon client for model catalog and asset records."""

    def __init__(self, daemon_client: GuiDaemonClient) -> None:
        super().__init__(daemon_client, "catalog")


class LibraryStateClient(DomainStateClient):
    """Daemon client for document-library records."""

    def __init__(self, daemon_client: GuiDaemonClient) -> None:
        super().__init__(daemon_client, "library")


class WorkspaceStateClient(DomainStateClient):
    """Daemon client for editable workspace records."""

    def __init__(self, daemon_client: GuiDaemonClient) -> None:
        super().__init__(daemon_client, "workspace")