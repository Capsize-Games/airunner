"""Download helpers for CivitAI model files."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable

import requests

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[int, int], None]
CancelCallback = Callable[[], bool]


def _auth_headers(api_key: str) -> dict[str, str]:
    if not api_key:
        return {"Content-Type": "application/json"}
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }


def _url_with_token(url: str, api_key: str) -> str:
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}token={api_key}"


def _content_length(response, fallback):
    try:
        return int(
            response.headers.get("content-length", fallback) or fallback
        )
    except (TypeError, ValueError):
        return fallback


def _emit_progress(cb, downloaded, total):
    if cb is not None:
        cb(downloaded, total)


def _remove_partial(path):
    try:
        if path.exists():
            path.unlink()
    except OSError:
        return


def _stream_get(url, headers):
    return requests.get(
        url,
        headers=headers,
        stream=True,
        allow_redirects=True,
        timeout=30,
    )


def _open_download(url, api_key, custom_headers=None):
    headers = custom_headers or _auth_headers(api_key)
    response = _stream_get(url, headers)
    if response.status_code != 401 or not api_key:
        response.raise_for_status()
        return response
    response.close()
    retry = _stream_get(_url_with_token(url, api_key), headers)
    retry.raise_for_status()
    return retry


def _planned_download_file(file_info, model_path):
    filename = file_info.get("name", "")
    download_url = file_info.get("downloadUrl", "")
    file_size = int((file_info.get("sizeKB", 0) or 0) * 1024)
    if not filename or not download_url:
        return None
    final_path = model_path / filename
    if final_path.exists() and final_path.stat().st_size == file_size:
        return None
    return {"filename": filename, "url": download_url, "size": file_size}


def get_files_to_download(version, model_path):
    result = []
    for file_info in version.get("files", []):
        planned = _planned_download_file(file_info, model_path)
        if planned is not None:
            result.append(planned)
    return result


def _calc_resume(response, existing_size, file_size):
    total = file_size or existing_size
    remaining = _content_length(response, 0)
    if existing_size > 0:
        cr = response.headers.get("content-range", "")
        if "/" in cr:
            try:
                total = int(cr.split("/")[-1])
            except (ValueError, IndexError):
                total = existing_size + remaining
    else:
        total = max(total, remaining)
    return total, remaining


def _write_chunks(resp, part_path, chunk_size, on_progress, on_cancel):
    downloaded = part_path.stat().st_size if part_path.exists() else 0
    total = downloaded
    mode = "ab" if downloaded > 0 else "wb"
    with open(part_path, mode) as handle:
        for chunk in resp.iter_content(chunk_size=chunk_size):
            if on_cancel and on_cancel():
                _remove_partial(part_path)
                return False, downloaded
            if not chunk:
                continue
            handle.write(chunk)
            downloaded += len(chunk)
            _emit_progress(on_progress, downloaded, total)
    return True, downloaded


def _prepare_and_resume(url, part_path, file_size, api_key):
    existing = part_path.stat().st_size if part_path.exists() else 0
    headers = _auth_headers(api_key)
    if existing > 0:
        headers["Range"] = f"bytes={existing}-"
    resp = _open_download(url, api_key, custom_headers=headers)
    total, _ = _calc_resume(resp, existing, file_size)
    return resp, existing, total


def _try_download(
    url,
    part_path,
    file_size,
    api_key,
    chunk_size,
    on_progress,
    on_cancel,
):
    resp, existing, total = _prepare_and_resume(
        url,
        part_path,
        file_size,
        api_key,
    )
    if total > 0 and existing >= total:
        return True, total
    ok, downloaded = _write_chunks(
        resp,
        part_path,
        chunk_size,
        on_progress,
        on_cancel,
    )
    return ok, total


def _done(path, total, on_progress):
    path.rename(path.with_name(path.name.replace(".part", "")))
    _emit_progress(on_progress, path.stat().st_size, total)


def download_file(
    url,
    filepath,
    file_size,
    api_key="",
    chunk_size=8192,
    on_progress=None,
    on_cancel=None,
):
    target = Path(filepath)
    target.parent.mkdir(parents=True, exist_ok=True)
    part = target.with_name(target.name + ".part")
    if target.exists():
        _emit_progress(on_progress, *[target.stat().st_size] * 2)
        return True
    try:
        ok, total = _try_download(
            url,
            part,
            file_size,
            api_key,
            chunk_size,
            on_progress,
            on_cancel,
        )
        if ok:
            _done(part, total, on_progress)
    except Exception:
        _remove_partial(part)
        raise
    if not ok:
        return False
    return True
