"""Worker for CivitAI model downloads using Python threading."""

import os
import threading
from pathlib import Path
import requests

from airunner.components.application.workers.base_download_worker import (
    BaseDownloadWorker,
)
from airunner.enums import SignalCode
from airunner.utils.settings.get_qsettings import get_qsettings
from airunner.settings import MODELS_DIR


class CivitAIDownloadWorker(BaseDownloadWorker):
    """Worker for downloading CivitAI models with parallel file downloading."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def _complete_signal(self) -> SignalCode:
        """Signal to emit on successful download completion."""
        return SignalCode.CIVITAI_DOWNLOAD_COMPLETE

    @property
    def _failed_signal(self) -> SignalCode:
        """Signal to emit on download failure."""
        return SignalCode.CIVITAI_DOWNLOAD_FAILED

    def _download_model(
        self, model_id: str, version_id: str = None, output_dir: str = None
    ):
        """Download model files from CivitAI.

        Args:
            model_id: CivitAI model ID
            version_id: Specific version ID (optional, uses latest if None)
            output_dir: Directory to save the model
        """
        settings = get_qsettings()
        api_key = settings.value("civitai/api_key", "")

        if not output_dir:
            output_dir = os.path.join(MODELS_DIR, "art/models/civitai")

        # Get model metadata from CivitAI API
        try:
            model_info = self._get_model_info(model_id, api_key)
        except Exception as e:
            self.emit_signal(self._failed_signal, {"error": str(e)})
            return

        # Find version to download
        versions = model_info.get("modelVersions", [])
        if not versions:
            self.emit_signal(
                self._failed_signal,
                {"error": f"No versions found for model {model_id}"},
            )
            return

        if version_id:
            version = next(
                (v for v in versions if str(v.get("id")) == str(version_id)),
                None,
            )
            if not version:
                self.emit_signal(
                    self._failed_signal,
                    {
                        "error": f"Version {version_id} not found for model {model_id}"
                    },
                )
                return
        else:
            version = versions[0]  # Latest version

        model_name = model_info.get("name", f"model_{model_id}")
        version_name = version.get("name", "latest")

        # Initialize download
        safe_model_name = self._sanitize_filename(
            f"{model_name}_{version_name}"
        )
        model_path = self._initialize_download(output_dir, safe_model_name)

        self.emit_signal(
            SignalCode.UPDATE_DOWNLOAD_LOG,
            {"message": f"Starting download: {model_name} v{version_name}"},
        )

        # Get list of files from version
        files_info = version.get("files", [])
        if not files_info:
            self.emit_signal(
                self._failed_signal,
                {
                    "error": f"No files found for {model_name} version {version_name}"
                },
            )
            return

        # Build download list
        files_to_download = []
        for file_info in files_info:
            filename = file_info.get("name", "")
            download_url = file_info.get("downloadUrl", "")
            file_size = file_info.get("sizeKB", 0) * 1024  # Convert to bytes

            if not filename or not download_url:
                continue

            # Skip if already exists
            final_path = model_path / filename
            if final_path.exists() and final_path.stat().st_size == file_size:
                self.emit_signal(
                    SignalCode.UPDATE_DOWNLOAD_LOG,
                    {"message": f"File {filename} already exists, skipping"},
                )
                continue

            files_to_download.append(
                {
                    "filename": filename,
                    "size": file_size,
                    "url": download_url,
                }
            )

        if not files_to_download:
            self.emit_signal(
                SignalCode.UPDATE_DOWNLOAD_LOG,
                {"message": "All files already downloaded!"},
            )
            self.emit_signal(
                self._complete_signal,
                {"model_path": str(model_path)},
            )
            return

        self._total_size = sum(f["size"] for f in files_to_download)
        total_gb = self._total_size / (1024**3)

        self.emit_signal(
            SignalCode.UPDATE_DOWNLOAD_LOG,
            {
                "message": f"Downloading {len(files_to_download)} files ({total_gb:.2f} GB)"
            },
        )

        # Start download threads
        for file_info in files_to_download:
            if self.is_cancelled:
                return

            filename = file_info["filename"]
            file_size = file_info["size"]
            download_url = file_info["url"]

            self._file_sizes[filename] = file_size
            self._file_progress[filename] = 0

            self.emit_signal(
                SignalCode.UPDATE_DOWNLOAD_LOG,
                {"message": f"Starting download for {filename}..."},
            )

            thread = threading.Thread(
                target=self._download_file,
                args=(
                    download_url,
                    filename,
                    file_size,
                    self._temp_dir,
                    model_path,
                    api_key,
                ),
                daemon=True,
            )
            self._file_threads[filename] = thread
            thread.start()

        self.emit_signal(
            SignalCode.UPDATE_DOWNLOAD_LOG,
            {
                "message": f"Started {len(files_to_download)} download threads..."
            },
        )

        # Wait for completion
        if not self._wait_for_completion(len(files_to_download)):
            return

        self._cleanup_temp_files()
        self.emit_signal(
            self._complete_signal,
            {"model_path": str(model_path)},
        )

    def _download_file(
        self,
        url: str,
        filename: str,
        file_size: int,
        temp_dir: Path,
        model_path: Path,
        api_key: str,
    ):
        """Download a single file from CivitAI (runs in Python thread).

        Args:
            url: Download URL from CivitAI API
            filename: Name of file to save
            file_size: Expected size in bytes
            temp_dir: Temporary download directory
            model_path: Final model directory
            api_key: CivitAI API key (optional)
        """
        temp_path = temp_dir / filename
        final_path = model_path / filename

        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        try:
            # Try with auth header first
            success = self._attempt_download(
                url, temp_path, final_path, file_size, headers
            )

            # If 401, retry with token query param
            if not success and api_key:
                sep = "&" if "?" in url else "?"
                token_url = f"{url}{sep}token={api_key}"
                success = self._attempt_download(
                    token_url,
                    temp_path,
                    final_path,
                    file_size,
                    headers,
                )

            if not success:
                raise Exception(
                    f"Download failed after retries for {filename}"
                )

            self._mark_file_complete(filename)

        except Exception as e:
            self.logger.error(f"Failed to download {filename}: {e}")
            self._mark_file_failed(filename)

            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass

    def _attempt_download(
        self,
        url: str,
        temp_path: Path,
        final_path: Path,
        file_size: int,
        headers: dict,
    ) -> bool:
        """Attempt to download a file.

        Args:
            url: Download URL
            temp_path: Temporary file path
            final_path: Final file path
            file_size: Expected file size
            headers: Request headers

        Returns:
            True if download successful, False if should retry
        """
        try:
            with requests.get(
                url, headers=headers, stream=True, timeout=30
            ) as response:
                # Return False on 401 to trigger retry
                if response.status_code == 401:
                    return False

                response.raise_for_status()

                content_length = response.headers.get("content-length")
                if content_length:
                    file_size = int(content_length)
                    with self._lock:
                        self._file_sizes[temp_path.name] = file_size

                downloaded = 0
                with open(temp_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if self.is_cancelled:
                            f.close()
                            if temp_path.exists():
                                temp_path.unlink()
                            return False

                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)

                            # Update progress every 1MB
                            if downloaded % (1024 * 1024) < 8192:
                                self._update_file_progress(
                                    temp_path.name, downloaded, file_size
                                )

                self._update_file_progress(
                    temp_path.name, downloaded, file_size
                )

                # Move to final location
                final_path.parent.mkdir(parents=True, exist_ok=True)
                if final_path.exists():
                    final_path.unlink()
                temp_path.rename(final_path)

                return True

        except requests.RequestException as e:
            # Don't retry on non-401 errors
            if not (
                isinstance(e, requests.HTTPError)
                and e.response.status_code == 401
            ):
                raise e
            return False

    def _get_model_info(self, model_id: str, api_key: str) -> dict:
        """Get model metadata from CivitAI API.

        Args:
            model_id: CivitAI model ID
            api_key: CivitAI API key (optional)

        Returns:
            Model metadata dict

        Raises:
            Exception: If API request fails
        """
        url = f"https://civitai.com/api/v1/models/{model_id}"

        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise Exception(f"Failed to fetch model info: {e}")

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """Sanitize filename to remove invalid characters.

        Args:
            filename: Original filename

        Returns:
            Sanitized filename safe for filesystem
        """
        # Replace invalid characters with underscore
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, "_")

        # Remove leading/trailing whitespace and dots
        filename = filename.strip(". ")

        return filename or "model"
