"""RPC handlers: art options + bootstrap + remove-background."""

from __future__ import annotations

import asyncio
import base64
import logging
from io import BytesIO
from typing import Any

from PIL import Image

from airunner_services.api.routes.events import _rpc_register

logger = logging.getLogger(__name__)

# Module-level singleton so the model stays resident between requests.
_rmbg_manager = None
_RMBG_MODEL_ID = "briaai/RMBG-2.0"
_RMBG_MODEL_TYPE = "rmbg"


def _emit_rmbg_status(status: str) -> None:
    """Push a model-status event for the RMBG model to all subscribers."""
    try:
        from airunner_services.api.routes.models_status import (  # noqa: PLC0415
            _notify_status_subscribers,
            _external_models,
            _external_models_lock,
        )

        with _external_models_lock:
            if status in ("unloaded", "failed"):
                _external_models.pop(_RMBG_MODEL_ID, None)
            else:
                _external_models[_RMBG_MODEL_ID] = {
                    "model_id": _RMBG_MODEL_ID,
                    "model_type": _RMBG_MODEL_TYPE,
                    "status": status,
                    "can_unload": status == "loaded",
                    "vram_gb": 0.0,
                    "ram_gb": 0.0,
                    "name": "RMBG-2.0",
                }

        _notify_status_subscribers({
            "type": "model_status",
            "model_id": _RMBG_MODEL_ID,
            "model_type": _RMBG_MODEL_TYPE,
            "status": status,
        })
    except Exception as exc:
        logger.debug("Could not emit RMBG status %s: %s", status, exc)


def get_rmbg_manager():
    """Return the module-level RMBG manager singleton."""
    return _rmbg_manager


def unload_rmbg() -> None:
    """Unload the RMBG singleton and broadcast the status change."""
    global _rmbg_manager
    mgr = _rmbg_manager
    _rmbg_manager = None
    if mgr is not None:
        try:
            mgr.unload()
        except Exception as exc:
            logger.warning("Error during RMBG unload: %s", exc)
    _emit_rmbg_status("unloaded")


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
    """Remove the background from a base64-encoded PNG image.

    Expects ``{"image_b64": "..."}`` in the body. Decodes the PNG,
    runs it through the RMBG model, and returns the result as base64.
    """
    global _rmbg_manager

    image_b64 = (body or {}).get("image_b64", "")
    if not image_b64:
        return {"status": 400, "body": {"error": "Missing image_b64"}}
    try:
        raw_bytes = base64.b64decode(image_b64)
        image = Image.open(BytesIO(raw_bytes)).convert("RGBA")

        from airunner_services.art.managers.rmbg import RMBGModelManager  # noqa: PLC0415

        if _rmbg_manager is None:
            _rmbg_manager = RMBGModelManager()

        if not _rmbg_manager.is_loaded:
            _emit_rmbg_status("loading")

        result_image = await asyncio.to_thread(
            _rmbg_manager.remove_background, image
        )

        if _rmbg_manager.is_loaded:
            _emit_rmbg_status("loaded")

        buf = BytesIO()
        result_image.save(buf, format="PNG")
        result_b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return {
            "status": 200,
            "body": {"image_b64": result_b64},
        }
    except Exception as exc:
        logger.exception("Background removal failed: %s", exc)
        _emit_rmbg_status("failed")
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
