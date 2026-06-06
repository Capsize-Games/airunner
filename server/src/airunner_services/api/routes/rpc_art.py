"""RPC handlers: art options + bootstrap."""

from __future__ import annotations

from typing import Any

from airunner_services.api.routes.events import _rpc_register


def _fetch_art_options_data(session: Any):
    from airunner_services.database.models.ai_models import AIModels
    from airunner_services.database.models.schedulers import Schedulers

    schedulers = [
        {"label": r.display_name, "value": r.display_name}
        for r in session.query(Schedulers).all()
        if r.display_name
    ]
    models_by_version: dict[str, list[dict[str, str]]] = {}
    for m in session.query(AIModels).filter(AIModels.enabled.is_(True)).all():
        ver = m.version or ""
        if ver:
            models_by_version.setdefault(ver, []).append(
                {"label": m.name or m.path, "value": m.path}
            )
    return schedulers, models_by_version


def _build_versions(
    models_by_version: dict[str, list[dict[str, str]]],
    schedulers: list[dict[str, str]],
) -> list[dict[str, Any]]:
    from airunner_services.contract_enums import StableDiffusionVersion

    known = [v.value for v in StableDiffusionVersion]
    versions = [
        {
            "name": v,
            "models": models_by_version.get(v, []),
            "schedulers": schedulers,
        }
        for v in known
    ]
    seen = set(known)
    for ver, model_list in models_by_version.items():
        if ver not in seen:
            versions.append(
                {"name": ver, "models": model_list, "schedulers": schedulers}
            )
    return versions


@_rpc_register("GET", "/api/v1/art/options")
async def _rpc_art_options(body: dict, **kw: Any) -> dict[str, Any]:
    """Return art model options (versions, models per version, schedulers)."""
    try:
        from airunner_services.database.session import session_scope

        with session_scope() as session:
            schedulers, models_by_version = _fetch_art_options_data(session)
        versions = _build_versions(models_by_version, schedulers)
        return {
            "status": 200,
            "body": {"versions": versions, "precisions": []},
        }
    except Exception:
        return {"status": 200, "body": {"versions": [], "precisions": []}}


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
