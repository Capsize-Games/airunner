"""Service-owned helpers for CivitAI metadata and file downloads."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[int, int], None]
CancelCallback = Callable[[], bool]

_CIVITAI_API_URL = "https://civitai.com/api/v1"
_ALLOWED_FILE_EXTENSIONS = (".safetensors", ".gguf")
_ALLOWED_FILE_FORMATS = {"safetensor", "gguf"}
_BASE_MODEL_ALIASES = {
    "SDXL 1.0": "SDXL 1.0",
    "SDXL Hyper": "SDXL Hyper",
    "SDXL Lightning": "SDXL Lightning",
    "Z-Image Turbo": "ZImageTurbo",
    "ZImageTurbo": "ZImageTurbo",
}
_MODEL_TYPE_ALIASES = {
    "CHECKPOINT": "Checkpoint",
    "MODEL": "Checkpoint",
    "LORA": "LORA",
    "EMBEDDING": "TextualInversion",
    "EMBEDDINGS": "TextualInversion",
    "TEXTUAL EMBEDDING": "TextualInversion",
    "TEXTUALINVERSION": "TextualInversion",
    "TEXTUAL INVERSION": "TextualInversion",
    "ADAPTER": "LORA",
    "CONTROLNET": "LORA",
}


def parse_civitai_url(url: str) -> Dict[str, Any]:
    """Extract model and version identifiers from one CivitAI URL."""
    model_id = _match_url_token(url, r"/models/(\d+)")
    model_version_id = _match_url_token(url, r"modelVersionId=(\d+)")
    return {
        "model_id": model_id,
        "model_version_id": model_version_id,
    }


def fetch_model_info(model_id: str, api_key: str = "") -> Dict[str, Any]:
    """Fetch one model metadata payload from the CivitAI API."""
    url = f"{_CIVITAI_API_URL}/models/{model_id}"
    response = requests.get(
        url,
        headers=_auth_headers(api_key),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def search_models(
    query: str = "",
    *,
    base_models: Optional[List[str]] = None,
    model_types: Optional[List[str]] = None,
    limit: int = 20,
    cursor: Optional[str] = None,
    api_key: str = "",
) -> Dict[str, Any]:
    """Return one filtered CivitAI model-search payload."""
    url = f"{_CIVITAI_API_URL}/models"
    params = _search_params(
        query=query,
        base_models=base_models,
        model_types=model_types,
        limit=limit,
        cursor=cursor,
    )
    logger.info(
        "Calling CivitAI API: %s params=%s cursor=%s",
        url, {k: v for k, v in params.items() if k != "cursor"},
        "set" if cursor else None,
    )
    response = requests.get(
        url,
        params=params,
        headers=_auth_headers(api_key),
        timeout=30,
    )
    logger.info(
        "CivitAI API responded: status=%s content_length=%s",
        response.status_code,
        response.headers.get("content-length", "unknown"),
    )
    response.raise_for_status()
    payload = response.json()
    raw_count = len(payload.get("items", []))
    payload["items"] = _filter_model_items(
        payload.get("items", []),
        base_models,
        model_types,
    )
    logger.info(
        "CivitAI search filtered: %d raw items → %d filtered items",
        raw_count,
        len(payload.get("items", [])),
    )
    return payload


def fetch_browser_model_info(
    model_id: str,
    *,
    base_models: Optional[List[str]] = None,
    model_types: Optional[List[str]] = None,
    api_key: str = "",
) -> Dict[str, Any]:
    """Return one filtered model payload for the browser detail pane."""
    model_info = fetch_model_info(model_id, api_key)
    filtered = _filter_model_payload(model_info, base_models, model_types)
    if filtered is None:
        raise ValueError(
            "Model does not expose a supported file for the selected "
            "filters"
        )
    return filtered


def fetch_model_info_for_url(
    url: str,
    api_key: str = "",
) -> Dict[str, Any]:
    """Fetch one model payload and attach the selected version when present."""
    parsed = parse_civitai_url(url)
    model_id = parsed.get("model_id")
    if not model_id:
        raise ValueError("Invalid CivitAI model URL")
    model_info = fetch_model_info(model_id, api_key)
    version_id = parsed.get("model_version_id")
    selected_version = select_version(model_info, version_id)
    if version_id and selected_version is not None:
        model_info["selectedVersion"] = selected_version
    return model_info


def select_version(
    model_info: Dict[str, Any],
    version_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Select one requested or latest model version from metadata."""
    versions = model_info.get("modelVersions", [])
    if not versions:
        return None
    if version_id is None:
        return versions[0]
    for version in versions:
        if str(version.get("id")) == str(version_id):
            return version
    return None


def sanitize_filename(name: str) -> str:
    """Return one filesystem-safe filename for downloaded CivitAI assets."""
    sanitized = re.sub(r'[<>:"/\\|?*]', "_", name)
    sanitized = sanitized.strip(". ")
    return re.sub(r"[_\s]+", "_", sanitized)


def get_files_to_download(
    version: Dict[str, Any],
    model_path: Path,
) -> List[Dict[str, Any]]:
    """Return files that still need downloading for one CivitAI version."""
    files_to_download: List[Dict[str, Any]] = []
    for file_info in version.get("files", []):
        planned_file = _planned_download_file(file_info, model_path)
        if planned_file is not None:
            files_to_download.append(planned_file)
    return files_to_download


def download_file(
    url: str,
    filepath: Path | str,
    file_size: int,
    api_key: str = "",
    chunk_size: int = 8192,
    progress_callback: Optional[ProgressCallback] = None,
    cancel_callback: Optional[CancelCallback] = None,
) -> bool:
    """Download one file with optional progress and cancellation hooks.

    Downloads to ``<path>.part`` and renames to ``<path>`` on success,
    so incomplete files are never visible with the real extension.
    When a partial ``.part`` file exists, sends a ``Range`` header to
    resume from where the previous download left off.
    """
    target_path = Path(filepath)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    part_path = target_path.with_name(target_path.name + ".part")

    # Check if a complete file already exists
    if target_path.exists():
        _emit_progress(progress_callback, target_path.stat().st_size, target_path.stat().st_size)
        return True

    existing_size = part_path.stat().st_size if part_path.exists() else 0
    downloaded = existing_size
    total_size = file_size or existing_size
    try:
        headers = _auth_headers(api_key)
        if existing_size > 0:
            headers["Range"] = f"bytes={existing_size}-"

        response = _open_download(url, api_key, custom_headers=headers)
        remaining = _content_length(response, 0)
        if existing_size > 0:
            cr = response.headers.get("content-range", "")
            if "/" in cr:
                try:
                    total_size = int(cr.split("/")[-1])
                except (ValueError, IndexError):
                    total_size = existing_size + remaining
        else:
            total_size = max(total_size, remaining)

        if total_size > 0 and existing_size >= total_size:
            if part_path.exists():
                part_path.rename(target_path)
            _emit_progress(progress_callback, total_size, total_size)
            return True

        mode = "ab" if existing_size > 0 else "wb"
        with open(part_path, mode) as handle:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if cancel_callback and cancel_callback():
                    _remove_partial_download(part_path)
                    return False
                if not chunk:
                    continue
                handle.write(chunk)
                downloaded += len(chunk)
                _emit_progress(progress_callback, downloaded, total_size)
    except Exception:
        _remove_partial_download(part_path)
        raise

    # Download complete — rename .part to final name
    if part_path.exists():
        part_path.rename(target_path)

    _emit_progress(progress_callback, downloaded, total_size)
    return True


def _match_url_token(url: str, pattern: str) -> Optional[str]:
    """Return one matched capture group from a CivitAI URL pattern."""
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return None


def _search_params(
    *,
    query: str,
    base_models: Optional[List[str]],
    model_types: Optional[List[str]],
    limit: int,
    cursor: Optional[str],
) -> Dict[str, Any]:
    """Build one normalized CivitAI search parameter map."""
    params: Dict[str, Any] = {"limit": max(1, min(int(limit), 50))}
    if query.strip():
        params["query"] = query.strip()
    if cursor:
        params["cursor"] = cursor
    normalized_base_models = _normalize_base_models(base_models)
    if normalized_base_models:
        params["baseModels"] = sorted(normalized_base_models)
    normalized_types = _normalize_model_types(model_types)
    if normalized_types:
        params["types"] = sorted(normalized_types)
    return params


def _filter_model_items(
    items: List[Dict[str, Any]],
    base_models: Optional[List[str]],
    model_types: Optional[List[str]],
) -> List[Dict[str, Any]]:
    """Filter one CivitAI search result set to supported AIRunner items."""
    filtered_items: List[Dict[str, Any]] = []
    for item in items:
        filtered = _filter_model_payload(item, base_models, model_types)
        if filtered is not None:
            filtered_items.append(filtered)
    return filtered_items


def _filter_model_payload(
    model_info: Dict[str, Any],
    base_models: Optional[List[str]],
    model_types: Optional[List[str]],
) -> Optional[Dict[str, Any]]:
    """Filter one model payload down to supported versions and files."""
    normalized_types = _normalize_model_types(model_types)
    model_type = _normalize_model_type(str(model_info.get("type", "")))
    if normalized_types and model_type not in normalized_types:
        return None

    normalized_base_models = _normalize_base_models(base_models)
    versions = []
    for version in model_info.get("modelVersions", []):
        base_model = _normalize_base_model(str(version.get("baseModel", "")))
        if normalized_base_models and base_model not in normalized_base_models:
            continue
        files = _supported_files(version.get("files", []))
        if not files:
            continue
        filtered_version = dict(version)
        filtered_version["files"] = files
        versions.append(filtered_version)

    if not versions:
        return None

    filtered_model = dict(model_info)
    filtered_model["type"] = model_type or model_info.get("type", "")
    filtered_model["modelVersions"] = versions

    selected_version = model_info.get("selectedVersion")
    if isinstance(selected_version, dict):
        selected_version_id = selected_version.get("id")
        filtered_model["selectedVersion"] = select_version(
            filtered_model,
            str(selected_version_id) if selected_version_id is not None else None,
        )
    return filtered_model


def _normalize_base_models(
    base_models: Optional[List[str]],
) -> set[str]:
    """Normalize one requested base-model filter set."""
    normalized = set()
    for base_model in base_models or []:
        value = _normalize_base_model(base_model)
        if value:
            normalized.add(value)
    return normalized


def _normalize_base_model(base_model: str) -> str:
    """Normalize one CivitAI base-model label for API filtering."""
    return _BASE_MODEL_ALIASES.get(base_model.strip(), base_model.strip())


def _normalize_model_types(
    model_types: Optional[List[str]],
) -> set[str]:
    """Normalize one requested model-type filter set."""
    normalized = set()
    for model_type in model_types or []:
        value = _normalize_model_type(model_type)
        if value:
            normalized.add(value)
    return normalized


def _normalize_model_type(model_type: str) -> str:
    """Normalize one CivitAI model-type label for filtering."""
    raw = model_type.strip()
    if not raw:
        return ""
    return _MODEL_TYPE_ALIASES.get(raw.upper(), raw)


def _supported_files(files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return supported files for one model version."""
    supported = []
    for file_info in files:
        if _is_supported_file(file_info):
            supported.append(file_info)
    return supported


def _is_supported_file(file_info: Dict[str, Any]) -> bool:
    """Return whether one CivitAI file matches the browser policy."""
    name = str(file_info.get("name", "")).lower()
    if not file_info.get("downloadUrl") or not name:
        return False
    if name.endswith(_ALLOWED_FILE_EXTENSIONS):
        return True
    metadata = file_info.get("metadata") or {}
    format_name = str(metadata.get("format", "")).lower()
    return format_name in _ALLOWED_FILE_FORMATS


def _auth_headers(api_key: str) -> dict[str, str]:
    """Return one request header map for authenticated CivitAI requests."""
    if not api_key:
        return {"Content-Type": "application/json"}
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }


def _planned_download_file(
    file_info: Dict[str, Any],
    model_path: Path,
) -> Optional[Dict[str, Any]]:
    """Return one planned file payload when the local file is incomplete."""
    filename = file_info.get("name", "")
    download_url = file_info.get("downloadUrl", "")
    file_size = int((file_info.get("sizeKB", 0) or 0) * 1024)
    if not filename or not download_url:
        return None
    final_path = model_path / filename
    if final_path.exists() and final_path.stat().st_size == file_size:
        return None
    return {
        "filename": filename,
        "url": download_url,
        "size": file_size,
    }


def _open_download(
    url: str,
    api_key: str,
    custom_headers: dict | None = None,
) -> requests.Response:
    """Open one download response, retrying 401s with token query auth."""
    headers = custom_headers or _auth_headers(api_key)
    response = requests.get(
        url,
        headers=headers,
        stream=True,
        allow_redirects=True,
        timeout=30,
    )
    if response.status_code != 401 or not api_key:
        response.raise_for_status()
        return response
    response.close()
    retry_url = _url_with_token(url, api_key)
    retry_response = requests.get(
        retry_url,
        stream=True,
        allow_redirects=True,
        timeout=30,
    )
    retry_response.raise_for_status()
    return retry_response


def _url_with_token(url: str, api_key: str) -> str:
    """Return one retry URL that carries the API key as a query token."""
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}token={api_key}"


def _content_length(response: requests.Response, fallback: int) -> int:
    """Return one best-effort total byte count for a download response."""
    try:
        return int(response.headers.get("content-length", fallback) or fallback)
    except (TypeError, ValueError):
        return fallback


def _emit_progress(
    progress_callback: Optional[ProgressCallback],
    downloaded: int,
    total_size: int,
) -> None:
    """Emit one progress update when the caller requested callbacks."""
    if progress_callback is not None:
        progress_callback(downloaded, total_size)


def _remove_partial_download(filepath: Path) -> None:
    """Remove one partial file after a failed or canceled download."""
    try:
        if filepath.exists():
            filepath.unlink()
    except OSError:
        return