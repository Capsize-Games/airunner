"""Service-owned helpers for CivitAI metadata (browser/search)."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional

import requests

from airunner_services.downloads.civitai_download import _auth_headers
from airunner_services.downloads.civitai_filters import (
    normalize_base_models,
    normalize_base_model,
    normalize_model_types,
    normalize_model_type,
    supported_files,
)

logger = logging.getLogger(__name__)
_CIVITAI_API_URL = "https://civitai.com/api/v1"


def _match_url_token(url: str, pattern: str) -> Optional[str]:
    match = re.search(pattern, url)
    return match.group(1) if match else None


def parse_civitai_url(url: str) -> Dict[str, Any]:
    model_id = _match_url_token(url, r"/models/(\d+)")
    model_version_id = _match_url_token(url, r"modelVersionId=(\d+)")
    return {"model_id": model_id, "model_version_id": model_version_id}


def fetch_model_info(model_id: str, api_key: str = "") -> Dict[str, Any]:
    url = f"{_CIVITAI_API_URL}/models/{model_id}"
    resp = requests.get(url, headers=_auth_headers(api_key), timeout=30)
    resp.raise_for_status()
    return resp.json()


def _search_params(*, query, base_models, model_types, limit, cursor):
    params: Dict[str, Any] = {"limit": max(1, min(int(limit), 50))}
    if query.strip():
        params["query"] = query.strip()
    if cursor:
        params["cursor"] = cursor
    nb = normalize_base_models(base_models)
    if nb:
        params["baseModels"] = sorted(nb)
    nt = normalize_model_types(model_types)
    if nt:
        params["types"] = sorted(nt)
    return params


def _filter_versions(model_info, base_models):
    nb = normalize_base_models(base_models)
    versions = []
    for version in model_info.get("modelVersions", []):
        bm = normalize_base_model(str(version.get("baseModel", "")))
        if nb and bm not in nb:
            continue
        files = supported_files(version.get("files", []))
        if not files:
            continue
        v = dict(version)
        v["files"] = files
        versions.append(v)
    return versions


def _filter_model_payload(model_info, base_models, model_types):
    ntypes = normalize_model_types(model_types)
    mtype = normalize_model_type(str(model_info.get("type", "")))
    if ntypes and mtype not in ntypes:
        return None
    versions = _filter_versions(model_info, base_models)
    if not versions:
        return None
    filtered = dict(model_info)
    filtered["type"] = mtype or model_info.get("type", "")
    filtered["modelVersions"] = versions
    sel = model_info.get("selectedVersion")
    if isinstance(sel, dict):
        sid = sel.get("id")
        filtered["selectedVersion"] = select_version(
            filtered, str(sid) if sid is not None else None,
        )
    return filtered


def _filter_model_items(items, base_models, model_types):
    return [
        f for item in items
        if (f := _filter_model_payload(item, base_models, model_types))
    ]


def search_models(
    query="", *, base_models=None, model_types=None,
    limit=20, cursor=None, api_key="",
):
    url = f"{_CIVITAI_API_URL}/models"
    params = _search_params(
        query=query, base_models=base_models, model_types=model_types,
        limit=limit, cursor=cursor,
    )
    logger.info(
        "CivitAI search params=%s cursor=%s",
        {k: v for k, v in params.items() if k != "cursor"},
        "set" if cursor else None,
    )
    resp = requests.get(
        url, params=params, headers=_auth_headers(api_key), timeout=30,
    )
    resp.raise_for_status()
    payload = resp.json()
    items = payload.get("items", [])
    payload["items"] = _filter_model_items(items, base_models, model_types)
    return payload


def fetch_browser_model_info(
    model_id, *, base_models=None, model_types=None, api_key="",
):
    info = fetch_model_info(model_id, api_key)
    filtered = _filter_model_payload(info, base_models, model_types)
    if filtered is None:
        raise ValueError(
            "Model does not expose a supported file for the selected filters"
        )
    return filtered


def fetch_model_info_for_url(url, api_key=""):
    parsed = parse_civitai_url(url)
    model_id = parsed.get("model_id")
    if not model_id:
        raise ValueError("Invalid CivitAI model URL")
    info = fetch_model_info(model_id, api_key)
    vid = parsed.get("model_version_id")
    sel = select_version(info, vid)
    if vid and sel is not None:
        info["selectedVersion"] = sel
    return info


def select_version(model_info, version_id=None):
    versions = model_info.get("modelVersions", [])
    if not versions:
        return None
    if version_id is None:
        return versions[0]
    for v in versions:
        if str(v.get("id")) == str(version_id):
            return v
    return None


def sanitize_filename(name: str) -> str:
    s = re.sub(r'[<>:"/\\|?*]', "_", name)
    return re.sub(r"[_\s]+", "_", s.strip(". "))
