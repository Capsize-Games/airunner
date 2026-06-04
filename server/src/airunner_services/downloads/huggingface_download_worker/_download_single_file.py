"""Single-file download with HTTP range-request resume support."""

from pathlib import Path
import requests
from airunner_services.contract_enums import SignalCode


def download_single_file(worker, repo_id, filename, file_size, temp_dir, model_path, api_key):
    """Download a single file from HuggingFace in a thread with resume support."""
    worker.logger.info("[THREAD] Starting download for %s from %s", filename, repo_id)
    temp_path = temp_dir / filename
    final_path = model_path / filename
    temp_path.parent.mkdir(parents=True, exist_ok=True)
    url = f"https://huggingface.co/{repo_id}/resolve/main/{filename}"
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    resume_from, file_mode = _check_resume(temp_path, file_size, filename, worker)
    if resume_from < 0:
        return  # file already complete
    downloaded = _do_download(url, headers, temp_path, file_mode, resume_from, file_size, filename, worker)
    if downloaded is None:
        return
    _finalize(downloaded, file_size, filename, temp_path, final_path, worker)


def _check_resume(temp_path, file_size, filename, worker):
    """Check for a partial temp file and return (resume_from, file_mode)."""
    if not temp_path.exists():
        return 0, "wb"
    existing = temp_path.stat().st_size
    if 0 < existing < file_size:
        worker.logger.info("Resuming %s from byte %d", filename, existing)
        return existing, "ab"
    if existing >= file_size:
        worker.logger.info("Temp file %s already complete, moving", filename)
        try:
            fp = worker._model_path / filename
            fp.parent.mkdir(parents=True, exist_ok=True)
            if fp.exists():
                fp.unlink()
            temp_path.rename(fp)
            worker._mark_file_complete(filename)
        except Exception as exc:
            worker.logger.error("Failed to move complete temp %s: %s", filename, exc)
        return -1, "wb"
    return 0, "wb"


def _do_download(url, headers, temp_path, file_mode, resume_from, file_size, filename, worker):
    """Stream the file, retrying on HTTP 416. Returns bytes written or None."""
    cur_resume, cur_headers, cur_mode = resume_from, dict(headers), file_mode
    while True:
        if cur_resume > 0:
            cur_headers["Range"] = f"bytes={cur_resume}-"
        try:
            with requests.get(url, headers=cur_headers, stream=True, timeout=30) as r:
                action = _handle_range(r, cur_resume, filename, worker)
                if action == "restart":
                    _clean_stale(temp_path, filename, worker)
                    cur_resume, cur_mode = 0, "wb"
                    cur_headers = dict(headers)
                    continue
                total_size = _track_size(r, cur_resume, filename, worker)
                return _stream_to_disk(r, temp_path, cur_mode, cur_resume, total_size, filename, worker)
        except requests.RequestException as exc:
            worker.logger.error("Failed to download %s: %s", filename, exc)
            worker.emit_signal(SignalCode.UPDATE_DOWNLOAD_LOG, {"message": f"Error downloading {filename}: {exc}"})
            worker._mark_file_failed(filename)
            return None


def _handle_range(response, resume_from, filename, worker):
    """Check range-response compatibility. Returns None, 'restart', or 'retry'."""
    if resume_from <= 0:
        response.raise_for_status()
        return None
    if response.status_code == 206:
        worker.logger.info("Server accepted range for %s", filename)
        return None
    if response.status_code == 200:
        worker.logger.warning("No range support for %s, restarting", filename)
        return "restart"
    if response.status_code == 416:
        worker.logger.warning("HTTP 416 for %s, deleting temp and retrying", filename)
        worker.emit_signal(SignalCode.UPDATE_DOWNLOAD_LOG, {"message": f"Stale partial for {filename}. Restarting..."})
        return "retry"
    response.raise_for_status()
    return None


def _clean_stale(temp_path, filename, worker):
    try:
        temp_path.unlink(missing_ok=True)
    except Exception as exc:
        worker.logger.warning("Failed to delete stale temp %s: %s", filename, exc)


def _track_size(response, resume_from, filename, worker):
    """Update worker size tracking from Content-Length."""
    cl = response.headers.get("content-length")
    if not cl:
        return worker._file_sizes.get(filename, 0)
    total = resume_from + int(cl)
    with worker._lock:
        old = worker._file_sizes.get(filename, 0)
        if old == 0 and total > 0:
            worker._total_size += total
        elif old != total:
            worker._total_size += total - old
        worker._file_sizes[filename] = total
    return total


def _stream_to_disk(response, temp_path, file_mode, resume_from, total_size, filename, worker):
    downloaded = resume_from
    with open(temp_path, file_mode) as f:
        for chunk in response.iter_content(chunk_size=8192):
            if worker.is_cancelled:
                return downloaded
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if downloaded % (1024 * 1024) < 8192:
                    worker._update_file_progress(filename, downloaded, total_size)
    worker._update_file_progress(filename, downloaded, total_size)
    return downloaded


def _finalize(downloaded, file_size, filename, temp_path, final_path, worker):
    if downloaded < file_size:
        worker.logger.error("Download incomplete for %s: %d vs %d", filename, downloaded, file_size)
        worker._mark_file_failed(filename)
        return
    final_path.parent.mkdir(parents=True, exist_ok=True)
    if final_path.exists():
        final_path.unlink()
    temp_path.rename(final_path)
    worker._mark_file_complete(filename)
