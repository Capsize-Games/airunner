"""ZIP archive download and extraction for model checkpoints.

Handles downloading a ZIP file from a direct URL with progress tracking,
then safely extracting it to the target model directory.
"""

import os
import zipfile
from pathlib import Path

import requests

from airunner_services.contract_enums import SignalCode
from airunner_services.utils.zip_utils import safe_extract_zip


def download_and_extract_zip(
    worker,
    zip_url: str,
    output_dir: str,
) -> None:
    """Download and extract a ZIP file with progress tracking.

    Args:
        worker: The parent ``HuggingFaceDownloadWorker`` instance.
        zip_url: Direct URL to the ZIP file.
        output_dir: Directory to extract to.
    """
    filename = os.path.basename(zip_url)
    model_path = Path(output_dir)
    model_path.mkdir(parents=True, exist_ok=True)

    _reset_worker_state(worker)
    temp_dir = worker._prepare_temp_dir(model_path)
    worker._model_path = model_path
    worker._temp_dir = temp_dir

    worker.emit_signal(
        SignalCode.UPDATE_DOWNLOAD_LOG,
        {"message": f"Starting ZIP download: {filename}"},
    )

    file_size = _fetch_file_size(zip_url, filename, worker)
    worker._total_size = file_size
    worker._file_sizes[filename] = file_size

    size_mb = file_size / (1024 * 1024)
    worker.emit_signal(
        SignalCode.UPDATE_DOWNLOAD_LOG,
        {"message": f"Downloading: {filename} ({size_mb:.1f} MB)"},
    )

    temp_path = temp_dir / filename
    try:
        downloaded = _stream_zip_to_disk(
            zip_url, temp_path, filename, file_size, worker,
        )
        if worker.is_cancelled:
            return

        worker._update_file_progress(filename, downloaded, file_size)

        worker.emit_signal(
            SignalCode.UPDATE_DOWNLOAD_LOG,
            {"message": f"Extracting {filename}..."},
        )

        with zipfile.ZipFile(temp_path, "r") as zip_ref:
            safe_extract_zip(zip_ref, model_path)

        temp_path.unlink()
        worker._cleanup_temp_files()

        worker.emit_signal(
            SignalCode.UPDATE_DOWNLOAD_LOG,
            {"message": f"Successfully extracted {filename}"},
        )

        worker.emit_signal(
            worker._complete_signal,
            {"model_path": str(model_path), "model_type": "openvoice_zip"},
        )

    except Exception as exc:
        worker.logger.error("Failed to download/extract ZIP: %s", exc)
        worker.emit_signal(
            worker._failed_signal,
            {"error": str(exc)},
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


def _fetch_file_size(
    url: str, filename: str, worker,
) -> int:
    """Retrieve the Content-Length for a URL, returning 0 on failure."""
    try:
        head = requests.head(url, allow_redirects=True, timeout=30)
        head.raise_for_status()
        return int(head.headers.get("Content-Length", 0))
    except requests.RequestException as exc:
        worker.logger.error(
            "Failed to get ZIP file size for %s: %s", filename, exc,
        )
        return 0


def _stream_zip_to_disk(
    url: str,
    temp_path: Path,
    filename: str,
    file_size: int,
    worker,
) -> int:
    """Stream the ZIP file to *temp_path* with cancellation support."""
    downloaded = 0
    with requests.get(url, stream=True, timeout=300) as response:
        response.raise_for_status()
        with open(temp_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if worker.is_cancelled:
                    worker.emit_signal(
                        worker._failed_signal,
                        {"error": "Download cancelled"},
                    )
                    return downloaded

                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

                    if downloaded % (1024 * 1024) < 8192:
                        worker._update_file_progress(
                            filename, downloaded, file_size,
                        )
    return downloaded
