"""RPC handlers: art options + bootstrap."""

from __future__ import annotations

from typing import Any

from airunner_services.api.routes.events import _rpc_register


@_rpc_register("GET", "/api/v1/art/options")
async def _rpc_art_options(body: dict, **kw: Any) -> dict[str, Any]:
    """Return art model options (versions, precisions)."""
    try:
        from airunner_services.model_management.model_registry import (
            ModelRegistry,
        )

        registry = ModelRegistry()
        versions: list[dict[str, Any]] = []
        for model_id, spec in registry.models.items():
            if (
                getattr(spec, "model_type", None)
                and getattr(spec.model_type, "value", None) == "sd"
            ):
                versions.append(
                    {
                        "name": spec.name or model_id,
                        "models": [
                            {
                                "label": m.get("name", m.get("path", "")),
                                "value": m.get("path", ""),
                            }
                            for m in getattr(spec, "files", []) or []
                        ],
                        "schedulers": [],
                    }
                )
        return {
            "status": 200,
            "body": {
                "versions": versions,
                "precisions": [
                    {"label": "FP16", "value": "fp16"},
                    {"label": "FP32", "value": "fp32"},
                ],
            },
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
