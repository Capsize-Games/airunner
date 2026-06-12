"""RPC handlers: art options + bootstrap + remove-background."""

from __future__ import annotations

import logging
from typing import Any

from airunner_services.api.routes.events import _rpc_register

logger = logging.getLogger(__name__)


def _fetch_art_options_data(session: Any):
    from airunner_services.database.models.ai_models import AIModels
    from airunner_services.database.models.schedulers import Schedulers
    from airunner_services.contract_enums import GeneratorSection

    allowed_pipelines = {
        GeneratorSection.TXT2IMG.value,
        GeneratorSection.INPAINT.value,
    }
    models_by_version: dict[str, list[dict[str, str]]] = {}
    for m in (
        session.query(AIModels)
        .filter(AIModels.enabled.is_(True))
        .filter(AIModels.pipeline_action.in_(allowed_pipelines))
        .all()
    ):
        ver = m.version or ""
        if ver:
            models_by_version.setdefault(ver, []).append(
                {"label": m.name or m.path, "value": m.path}
            )
    # Build per-version scheduler lists
    all_schedulers = session.query(Schedulers).all()
    schedulers_by_version: dict[str, list[dict[str, str]]] = {}
    for r in all_schedulers:
        if not r.display_name:
            continue
        ver = r.model_version or ""
        schedulers_by_version.setdefault(ver, []).append(
            {"label": r.display_name, "value": r.display_name}
        )
    return schedulers_by_version, models_by_version


def _build_versions(
    models_by_version: dict[str, list[dict[str, str]]],
    schedulers_by_version: dict[str, list[dict[str, str]]],
) -> list[dict[str, Any]]:
    return [
        {
            "name": ver,
            "models": model_list,
            "schedulers": schedulers_by_version.get(ver, []),
        }
        for ver, model_list in models_by_version.items()
        if model_list
    ]


@_rpc_register("GET", "/api/v1/art/options")
async def _rpc_art_options(body: dict, **kw: Any) -> dict[str, Any]:
    """Return art model options (versions, models per version, schedulers)."""
    try:
        from airunner_services.database.session import session_scope

        with session_scope() as session:
            schedulers_by_version, models_by_version = _fetch_art_options_data(
                session
            )
        versions = _build_versions(models_by_version, schedulers_by_version)
        return {
            "status": 200,
            "body": {"versions": versions, "precisions": []},
        }
    except Exception as exc:
        logger.exception(
            "Failed to fetch art model options: %s",
            exc,
        )
        return {"status": 200, "body": {"versions": [], "precisions": []}}


@_rpc_register("POST", "/api/v1/art/remove-background")
async def _rpc_art_remove_background(
    body: dict, **kw: Any
) -> dict[str, Any]:
    """Proxy background-removal request to the daemon.

    Expects ``{"image_b64": "..."}`` in the body. Forwards it to the
    daemon's ``POST /api/v1/art/remove-background`` endpoint and returns
    the resulting PNG bytes as a base64-encoded string.
    """
    import base64
    import requests

    image_b64 = (body or {}).get("image_b64", "")
    if not image_b64:
        return {"status": 400, "body": {"error": "Missing image_b64"}}
    try:
        daemon_base = "http://127.0.0.1:8188"
        resp = requests.post(
            f"{daemon_base}/api/v1/art/remove-background",
            json={"image_b64": image_b64},
            timeout=120,
        )
        resp.raise_for_status()
        result_b64 = base64.b64encode(resp.content).decode("ascii")
        return {
            "status": 200,
            "body": {"image_b64": result_b64},
        }
    except Exception as exc:
        logger.exception("Background removal failed: %s", exc)
        return {"status": 500, "body": {"error": str(exc)}}


@_rpc_register("GET", "/api/v1/art/bootstrap")
async def _rpc_art_bootstrap(body: dict, **kw: Any) -> dict[str, Any]:
    """Return bootstrap data."""
    try:
        from airunner_services.model_management.model_registry import (
            ModelRegistry,
        )

        registry = ModelRegistry()
        models = [
            {
                "name": spec.name,
                "version": model_id,
                "category": (
                    getattr(spec.model_type, "value", "")
                    if spec.model_type
                    else ""
                ),
                "path": spec.huggingface_id or model_id,
                "pipeline_action": getattr(spec, "pipeline_action", ""),
            }
            for model_id, spec in registry.models.items()
        ]
        return {
            "status": 200,
            "body": {
                "models": models,
                "pipelines": [],
                "unified_model_files": {},
                "controlnet_bootstrap_data": [],
                "espeak_settings_data": [],
                "llm_file_bootstrap_data": {},
                "openvoice_files": {},
                "openvoice_core_models": [],
                "openvoice_language_models": [],
                "path_settings_data": [],
                "rmbg_files": {},
                "sd_file_bootstrap_data": {},
                "whisper_files": {},
                "imagefilter_bootstrap_data": [],
                "prompt_templates_bootstrap_data": [],
            },
        }
    except Exception:
        return {"status": 200, "body": {"models": []}}
