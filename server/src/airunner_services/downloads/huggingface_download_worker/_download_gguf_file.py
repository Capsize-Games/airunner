"""GGUF model file download handler.

GGUF models are pre-quantized and only need a single ``.gguf`` file
downloaded from HuggingFace.
"""

import threading
from pathlib import Path

import requests

from airunner_services.config.local_settings_store import get_setting
from airunner_services.contract_enums import SignalCode


def download_gguf_model(
    worker,
    repo_id: str,
    output_dir: str,
    gguf_filename: str,
) -> None:
    """Download a single GGUF model file from HuggingFace.

    Args:
        worker: The parent ``HuggingFaceDownloadWorker`` instance.
        repo_id: HuggingFace repository ID.
        output_dir: Directory to save the model.
        gguf_filename: The ``.gguf`` file to download.
    """
    api_key = get_setting("huggingface/api_key", "")

    model_path = Path(output_dir)
    model_path.mkdir(parents=True, exist_ok=True)

    _reset_worker_state(worker)
    temp_dir = worker._prepare_temp_dir(model_path)
    worker._model_path = model_path
    worker._temp_dir = temp_dir

    worker.emit_signal(
        SignalCode.UPDATE_DOWNLOAD_LOG,
        {"message": f"Starting GGUF download: {repo_id}/{gguf_filename}"},
    )

    file_size = _fetch_gguf_file_size(repo_id, gguf_filename, api_key, worker)

    worker._total_size = file_size
    worker._file_sizes[gguf_filename] = file_size

    size_gb = file_size / (1024**3)
    worker.logger.info(
        "Downloading GGUF file: %s (%.2f GB)",
        gguf_filename,
        size_gb,
    )
    worker.emit_signal(
        SignalCode.UPDATE_DOWNLOAD_LOG,
        {"message": f"Downloading: {gguf_filename} ({size_gb:.2f} GB)"},
    )

    thread = threading.Thread(
        target=_start_gguf_download_thread,
        args=(
            worker,
            repo_id,
            gguf_filename,
            file_size,
            temp_dir,
            model_path,
            api_key,
        ),
        daemon=True,
    )
    worker._file_threads[gguf_filename] = thread
    thread.start()

    if not worker._wait_for_completion(1):
        return

    worker._cleanup_temp_files()
    worker.emit_signal(
        worker._complete_signal,
        {
            "model_path": str(model_path),
            "repo_id": repo_id,
            "model_type": "gguf",
        },
    )


def _reset_worker_state(worker) -> None:
    """Clear all download-tracking state on *worker*."""
    worker.is_cancelled = False
    worker._completed_files.clear()
    worker._failed_files.clear()
    worker._file_progress.clear()
    worker._file_sizes.clear()
    worker._file_threads.clear()
    worker._total_downloaded = 0
    worker._total_size = 0


def _fetch_gguf_file_size(
    repo_id: str,
    gguf_filename: str,
    api_key: str,
    worker,
) -> int:
    """Retrieve the remote file size for a GGUF file via HTTP HEAD."""
    url = f"https://huggingface.co/{repo_id}/resolve/main/{gguf_filename}"
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        head = requests.head(
            url,
            headers=headers,
            allow_redirects=True,
            timeout=30,
        )
        head.raise_for_status()
        return int(head.headers.get("Content-Length", 0))
    except requests.RequestException as exc:
        worker.logger.error(
            "Failed to get GGUF file size: %s",
            exc,
        )
        return 0


def _start_gguf_download_thread(
    worker,
    repo_id: str,
    gguf_filename: str,
    file_size: int,
    temp_dir: Path,
    model_path: Path,
    api_key: str,
) -> None:
    """Start a single-file download for the GGUF model.

    This is called in a daemon thread and delegates to the shared
    single-file downloader.
    """
    from airunner_services.downloads.huggingface_download_worker._download_single_file import (
        download_single_file,
    )  # noqa: E501

    download_single_file(
        worker,
        repo_id=repo_id,
        filename=gguf_filename,
        file_size=file_size,
        temp_dir=temp_dir,
        model_path=model_path,
        api_key=api_key,
    )
