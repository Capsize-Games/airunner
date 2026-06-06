"""RPC handlers: settings CRUD (resource store)."""

from __future__ import annotations

from typing import Any

from airunner_services.api.routes.events import _rpc_register
from airunner_services.api.routes.rpc_handlers import (
    resource_store_table,
)


@_rpc_register("GET", "/api/v1/settings/resources/{name}/singleton")
async def _rpc_settings_singleton(body: dict, **kw: Any) -> dict[str, Any]:
    """Get or create a singleton resource."""
    pp: dict = kw.get("path_params", {})
    resource_name = pp.get("name", "")
    try:
        from airunner_services.database.session import session_scope

        table = resource_store_table(resource_name)
        with session_scope() as session:
            item = session.query(table).first()
            if item is None:
                item = table()
                session.add(item)
                session.commit()
            record = {
                c.name: getattr(item, c.name) for c in table.__table__.columns
            }
            return {"status": 200, "body": {"record": record}}
    except Exception:
        return {"status": 200, "body": {"record": {}}}


@_rpc_register("PUT", "/api/v1/settings/resources/{name}/singleton")
async def _rpc_settings_singleton_update(
    body: dict, **kw: Any
) -> dict[str, Any]:
    """Update a singleton resource."""
    pp: dict = kw.get("path_params", {})
    resource_name = pp.get("name", "")
    values: dict = body.get("values", {})
    try:
        from airunner_services.database.session import session_scope

        table = resource_store_table(resource_name)
        with session_scope() as session:
            item = session.query(table).first()
            if item is None:
                item = table()
                session.add(item)
            for key, val in values.items():
                if hasattr(item, key):
                    setattr(item, key, val)
            session.commit()
            record = {
                c.name: getattr(item, c.name) for c in table.__table__.columns
            }
            return {"status": 200, "body": record}
    except Exception as exc:
        return {"status": 500, "body": {"error": str(exc)}}


@_rpc_register("POST", "/api/v1/settings/resources/{name}/query")
async def _rpc_settings_query(body: dict, **kw: Any) -> dict[str, Any]:
    """Query resources."""
    pp: dict = kw.get("path_params", {})
    resource_name = pp.get("name", "")
    try:
        from airunner_services.database.session import session_scope

        table = resource_store_table(resource_name)
        with session_scope() as session:
            items = session.query(table).all()
            records = [
                {
                    c.name: getattr(item, c.name)
                    for c in table.__table__.columns
                }
                for item in items
            ]
            return {"status": 200, "body": {"records": records}}
    except Exception:
        return {"status": 200, "body": {"records": []}}


@_rpc_register("POST", "/api/v1/settings/resources/{name}/first")
async def _rpc_settings_first(body: dict, **kw: Any) -> dict[str, Any]:
    """Query first resource matching filters."""
    pp: dict = kw.get("path_params", {})
    resource_name = pp.get("name", "")
    try:
        from airunner_services.database.session import session_scope

        table = resource_store_table(resource_name)
        with session_scope() as session:
            item = session.query(table).first()
            record = (
                {
                    c.name: getattr(item, c.name)
                    for c in table.__table__.columns
                }
                if item
                else {}
            )
            return {"status": 200, "body": {"record": record}}
    except Exception:
        return {"status": 200, "body": {"record": {}}}
