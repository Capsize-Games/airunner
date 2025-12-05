"""Worker for CivitAI model downloads using Python threading.

Refactored version with focused helper methods for maintainability.
"""

import os
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple
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
        # Get API key and output directory
        api_key, output_dir = self._prepare_download_config(output_dir)

        # Fetch model information
        model_info = self._fetch_model_info(model_id, api_key)
        if not model_info:
            return

        # Select version to download
        version = self._select_version(model_info, model_id, version_id)
        if not version:
            return

        # Prepare download paths
        model_name, version_name, model_path = self._prepare_download_paths(
            model_info, version, model_id, output_dir
        )

        # Get files to download
        files_to_download = self._build_download_list(
            version, model_name, version_name, model_path
        )
        if files_to_download is None:  # All files already exist
            self.emit_signal(
                self._complete_signal,
                {"model_path": str(model_path)},
            )
            return

        # Start downloads
        self._start_downloads(files_to_download, model_path, api_key)

        # Wait for completion
        if not self._wait_for_completion(len(files_to_download)):
            return

        self._cleanup_temp_files()
        self.emit_signal(
            self._complete_signal,
            {"model_path": str(model_path)},
        )

    def _prepare_download_config(
        self, output_dir: Optional[str]
    ) -> Tuple[str, str]:
        """Prepare download configuration.

        Args:
            output_dir: Optional output directory

        Returns:
            Tuple of (api_key, output_dir)
        """
        settings = get_qsettings()
        api_key = settings.value("civitai/api_key", "")

        if not output_dir:
            output_dir = os.path.join(MODELS_DIR, "art/models/civitai")

        return api_key, output_dir

    def _fetch_model_info(self, model_id: str, api_key: str) -> Optional[Dict]:
        """Fetch model metadata from CivitAI API.

        Args:
            model_id: CivitAI model ID
            api_key: API key for authentication

        Returns:
            Model info dictionary or None on error
        """
        try:
            return self._get_model_info(model_id, api_key)
        except Exception as e:
            self.emit_signal(self._failed_signal, {"error": str(e)})
            return None

    def _select_version(
        self, model_info: Dict, model_id: str, version_id: Optional[str]
    ) -> Optional[Dict]:
        """Select model version to download.

        Args:
            model_info: Model metadata
            model_id: Model ID
            version_id: Optional specific version ID

        Returns:
            Version dictionary or None if not found
        """
        versions = model_info.get("modelVersions", [])
        if not versions:
            self.emit_signal(
                self._failed_signal,
                {"error": f"No versions found for model {model_id}"},
            )
            return None

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
                return None
            return version
        else:
            return versions[0]  # Latest version

    def _prepare_download_paths(
        self, model_info: Dict, version: Dict, model_id: str, output_dir: str
    ) -> Tuple[str, str, Path]:
        """Prepare download paths and emit start message.

        Args:
            model_info: Model metadata
            version: Version metadata
            model_id: Model ID
            output_dir: Output directory

        Returns:
            Tuple of (model_name, version_name, model_path)
        """
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

        return model_name, version_name, model_path

    def _build_download_list(
        self,
        version: Dict,
        model_name: str,
        version_name: str,
        model_path: Path,
    ) -> Optional[List[Dict]]:
        """Build list of files to download.

        Args:
            version: Version metadata
            model_name: Model name
            version_name: Version name
            model_path: Model directory path

        Returns:
            List of file dictionaries or None if all files exist
        """
        files_info = version.get("files", [])
        if not files_info:
            self.emit_signal(
                self._failed_signal,
                {
                    "error": f"No files found for {model_name} version {version_name}"
                },
            )
            return []

        files_to_download = []
        for file_info in files_info:
            file_dict = self._process_file_info(file_info, model_path)
            if file_dict:
                files_to_download.append(file_dict)

        if not files_to_download:
            self.emit_signal(
                SignalCode.UPDATE_DOWNLOAD_LOG,
                {"message": "All files already downloaded!"},
            )
            return None

        self._emit_download_summary(files_to_download)
        return files_to_download

    def _process_file_info(
        self, file_info: Dict, model_path: Path
    ) -> Optional[Dict]:
        """Process single file info and check if download needed.

        Args:
            file_info: File metadata from API
            model_path: Model directory path

        Returns:
            File dictionary if download needed, None if already exists
        """
        filename = file_info.get("name", "")
        download_url = file_info.get("downloadUrl", "")
        file_size = file_info.get("sizeKB", 0) * 1024  # Convert to bytes

        if not filename or not download_url:
            return None

        # Skip if already exists
        final_path = model_path / filename
        if final_path.exists() and final_path.stat().st_size == file_size:
            self.emit_signal(
                SignalCode.UPDATE_DOWNLOAD_LOG,
                {"message": f"File {filename} already exists, skipping"},
            )
            return None

        return {
            "filename": filename,
            "size": file_size,
            "url": download_url,
        }

    def _emit_download_summary(self, files_to_download: List[Dict]):
        """Emit summary message about files to download.

        Args:
            files_to_download: List of file dictionaries
        """
        self._total_size = sum(f["size"] for f in files_to_download)
        total_gb = self._total_size / (1024**3)

        self.emit_signal(
            SignalCode.UPDATE_DOWNLOAD_LOG,
            {
                "message": f"Downloading {len(files_to_download)} files ({total_gb:.2f} GB)"
            },
        )

    def _start_downloads(
        self, files_to_download: List[Dict], model_path: Path, api_key: str
    ):
        """Start download threads for all files.

        Args:
            files_to_download: List of file dictionaries
            model_path: Model directory path
            api_key: API key for authentication
        """
        for file_info in files_to_download:
            if self.is_cancelled:
                return

            self._start_file_download(file_info, model_path, api_key)

        self.emit_signal(
            SignalCode.UPDATE_DOWNLOAD_LOG,
            {
                "message": f"Started {len(files_to_download)} download threads..."
            },
        )

    def _start_file_download(
        self, file_info: Dict, model_path: Path, api_key: str
    ):
        """Start download thread for a single file.

        Args:
            file_info: File metadata dictionary
            model_path: Model directory path
            api_key: API key for authentication
        """
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

        headers = self._build_auth_headers(api_key)

        try:
            # Try with auth header first
            success = self._attempt_download_with_auth(
                url, temp_path, final_path, file_size, headers, api_key
            )

            if not success:
                raise Exception(
                    f"Download failed after retries for {filename}"
                )

            self._mark_file_complete(filename)

        except Exception as e:
            self.logger.error(f"Failed to download {filename}: {e}")
            self._mark_file_failed(filename)
            self._cleanup_failed_download(temp_path)

    def _build_auth_headers(self, api_key: str) -> Dict:
        """Build authentication headers.

        Args:
            api_key: CivitAI API key

        Returns:
            Headers dictionary
        """
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

    def _attempt_download_with_auth(
        self,
        url: str,
        temp_path: Path,
        final_path: Path,
        file_size: int,
        headers: Dict,
        api_key: str,
    ) -> bool:
        """Attempt download with authentication, retry with token if needed.

        Args:
            url: Download URL
            temp_path: Temporary file path
            final_path: Final file path
            file_size: Expected file size
            headers: Request headers
            api_key: API key for token retry

        Returns:
            True if download successful
        """
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

        return success

    def _cleanup_failed_download(self, temp_path: Path):
        """Clean up temporary file after failed download.

        Args:
            temp_path: Temporary file path to remove
        """
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

                # Validate content type
                if not self._validate_content_type(response):
                    return False

                # Update file size from response if available
                file_size = self._update_file_size_from_response(
                    response, temp_path.name, file_size
                )

                # Download file chunks
                downloaded = self._download_chunks(
                    response, temp_path, file_size
                )
                if downloaded is None:  # Cancelled
                    return False

                # Move to final location
                self._finalize_download(temp_path, final_path)

                return True

        except requests.RequestException as e:
            # Don't retry on non-401 errors
            if not (
                isinstance(e, requests.HTTPError)
                and e.response.status_code == 401
            ):
                self.logger.error(f"Download error: {e}")
                return True  # Don't retry

            return False  # Retry on 401

    def _validate_content_type(self, response: requests.Response) -> bool:
        """Validate response content type.

        Args:
            response: HTTP response object

        Returns:
            True if content type is valid for download
        """
        content_type = response.headers.get("content-type", "").lower()
        valid_types = [
            "application/octet-stream",
            "application/x-",
            "image/",
            "video/",
            "model/",
            "application/zip",
        ]
        if not any(ct in content_type for ct in valid_types):
            self.logger.error(
                f"Invalid content-type for download: {content_type}"
            )
            return False
        return True

    def _update_file_size_from_response(
        self, response: requests.Response, filename: str, default_size: int
    ) -> int:
        """Update file size from Content-Length header if available.

        Args:
            response: HTTP response object
            filename: Name of file being downloaded
            default_size: Default file size

        Returns:
            Updated file size
        """
        content_length = response.headers.get("content-length")
        if content_length:
            file_size = int(content_length)
            with self._lock:
                # Update total_size if bootstrap had 0 for this file
                old_file_size = self._file_sizes.get(filename, 0)
                if old_file_size == 0 and file_size > 0:
                    self._total_size += file_size
                elif old_file_size != file_size:
                    # Adjust total_size for the difference
                    self._total_size += (file_size - old_file_size)
                self._file_sizes[filename] = file_size
            return file_size
        return default_size

    def _download_chunks(
        self, response: requests.Response, temp_path: Path, file_size: int
    ) -> Optional[int]:
        """Download file in chunks with progress tracking.

        Args:
            response: HTTP response object
            temp_path: Temporary file path
            file_size: Expected file size

        Returns:
            Total bytes downloaded or None if cancelled
        """
        downloaded = 0
        with open(temp_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if self.is_cancelled:
                    f.close()
                    if temp_path.exists():
                        temp_path.unlink()
                    return None

                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

                    # Update progress every 1MB
                    if downloaded % (1024 * 1024) < 8192:
                        self._update_file_progress(
                            temp_path.name, downloaded, file_size
                        )

        self._update_file_progress(temp_path.name, downloaded, file_size)
        return downloaded

    def _finalize_download(self, temp_path: Path, final_path: Path):
        """Move downloaded file to final location.

        Args:
            temp_path: Temporary file path
            final_path: Final file path
        """
        final_path.parent.mkdir(parents=True, exist_ok=True)
        if final_path.exists():
            final_path.unlink()
        temp_path.rename(final_path)

    def _get_model_info(self, model_id: str, api_key: str) -> Dict:
        """Get model info from CivitAI API.

        Args:
            model_id: CivitAI model ID
            api_key: API key for authentication

        Returns:
            Model metadata dictionary

        Raises:
            requests.RequestException: On API error
        """
        url = f"https://civitai.com/api/v1/models/{model_id}"
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
