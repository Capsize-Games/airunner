"""RPC handlers: privacy settings."""

from __future__ import annotations

from typing import Any

from airunner_services.api.routes.events import _rpc_register


@_rpc_register("GET", "/api/v1/settings/privacy")
async def _rpc_privacy_get(body: dict, **kwargs: Any) -> dict[str, Any]:
    """Return privacy settings."""
    try:
        from airunner_services.database.models import PrivacySetting
        from airunner_services.database.session import session_scope

        with session_scope() as session:
            records = session.query(PrivacySetting).all()
            services = {r.service_name: bool(r.enabled) for r in records}
            return {"status": 200, "body": {"services": services}}
    except Exception:
        return {"status": 200, "body": {"services": {}}}


@_rpc_register("PUT", "/api/v1/settings/privacy")
async def _rpc_privacy_update(body: dict, **kwargs: Any) -> dict[str, Any]:
    """Update privacy settings."""
    services: dict = body.get("services", {})
    try:
        from airunner_services.database.models import PrivacySetting
        from airunner_services.database.session import session_scope

        with session_scope() as session:
            for name, enabled in services.items():
                record = (
                    session.query(PrivacySetting)
                    .filter(
                        PrivacySetting.service_name == name,
                    )
                    .first()
                )
                if record:
                    record.enabled = bool(enabled)
                else:
                    session.add(
                        PrivacySetting(
                            service_name=name,
                            enabled=bool(enabled),
                        )
                    )
            session.commit()
        return {"status": 200, "body": {"services": services}}
    except Exception as exc:
        return {"status": 500, "body": {"error": str(exc)}}
