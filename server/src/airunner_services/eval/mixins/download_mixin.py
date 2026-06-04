"""Download operations mixin for dataset manager."""

import os
import logging
from pathlib import Path
from typing import Optional, Callable, TYPE_CHECKING

import requests
from tqdm import tqdm

if TYPE_CHECKING:
    from ..dataset_manager import DatasetManager

logger = logging.getLogger(__name__)


class DatasetDownloadMixin:
    """Handles dataset downloading from HuggingFace."""

    def _construct_download_url(
        self: "DatasetManager", path: str, file_name: str
    ) -> str:
        """Construct HuggingFace dataset URL."""
        return (
            f"https://huggingface.co/datasets/{path}/resolve/main/{file_name}"
        )

    def _get_auth_headers(self: "DatasetManager") -> dict:
        """Get authentication headers with HF token if available."""
        token = (
            os.getenv("AIRUNNER_HF_TOKEN")
            or os.getenv("HF_TOKEN")
            or os.getenv("HUGGINGFACE_TOKEN")
        )
        if token:
            return {"Authorization": f"Bearer {token}"}
        return {}

    def _download_with_progress(
        self: "DatasetManager",
        response,
        dest_file: Path,
        file_name: str,
        callback: Optional[Callable[[int, int], None]] = None,
    ) -> None:
        """Download file with progress tracking."""
        total_size = int(response.headers.get("content-length", 0))

        if self.headless:
            self._download_with_tqdm(
                response, dest_file, file_name, total_size, callback
            )
        else:
            self._download_with_callback(
                response, dest_file, total_size, callback
            )

        logger.info(
            f"Successfully downloaded {dest_file} ({total_size} bytes)"
        )

    def _download_with_tqdm(
        self: "DatasetManager",
        response,
        dest_file: Path,
        file_name: str,
        total_size: int,
        callback: Optional[Callable],
    ) -> None:
        """Download with tqdm progress bar."""
        with tqdm(
            total=total_size,
            unit="B",
            unit_scale=True,
            desc=file_name.split("/")[-1],
        ) as pbar:
            with open(dest_file, "wb") as f:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        pbar.update(len(chunk))
                        if callback:
                            callback(downloaded, total_size)

    def _download_with_callback(
        self: "DatasetManager",
        response,
        dest_file: Path,
        total_size: int,
        callback: Optional[Callable],
    ) -> None:
        """Download with callback only."""
        with open(dest_file, "wb") as f:
            downloaded = 0
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if callback:
                        callback(downloaded, total_size)

    def _download_file(
        self: "DatasetManager",
        path: str,
        file_name: str,
        file_path: str,
        callback: Optional[Callable[[int, int], None]] = None,
    ) -> None:
        """Download a file directly using requests."""
        url = self._construct_download_url(path, file_name)
        dest_dir = Path(file_path)
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_file = dest_dir / file_name.split("/")[-1]

        logger.info(f"Downloading {url} to {dest_file}")

        headers = self._get_auth_headers()

        try:
            response = self._make_download_request(url, headers)
            self._download_with_progress(
                response, dest_file, file_name, callback
            )

        except requests.exceptions.HTTPError as e:
            self._handle_http_error(e)
            raise
        except Exception as e:
            logger.error(f"Download failed for {url}: {e}")
            raise

    def _make_download_request(
        self: "DatasetManager", url: str, headers: dict
    ):
        """Make HTTP request for download."""
        response = requests.get(
            url,
            stream=True,
            headers=headers,
            timeout=60,
        )
        response.raise_for_status()
        return response

    def _handle_http_error(
        self: "DatasetManager", error: requests.exceptions.HTTPError
    ) -> None:
        """Handle HTTP errors with helpful messages."""
        if error.response.status_code == 401:
            logger.error(
                "Unauthorized (401). A Hugging Face token may be "
                "required. Set AIRUNNER_HF_TOKEN, HF_TOKEN, or "
                "HUGGINGFACE_TOKEN environment variable."
            )

    def download_gsm8k(
        self: "DatasetManager",
        split: str = "test",
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Path:
        """Download GSM8K dataset."""
        config = self.DATASETS["gsm8k"]
        repo = config["repo"]
        filename = config["files"][split]

        dest_path = self.get_dataset_path("gsm8k", split)
        dest_dir = dest_path.parent
        dest_dir.mkdir(parents=True, exist_ok=True)

        if dest_path.exists():
            logger.info(f"GSM8K {split} already exists at {dest_path}")
            return dest_path

        logger.info(f"Downloading GSM8K {split} from {repo}")
        self._download_file(repo, filename, str(dest_dir), progress_callback)

        return dest_path

    def download_math(
        self: "DatasetManager",
        split: str = "test",
        subjects: Optional[list] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Path:
        """Download MATH dataset."""
        config = self.DATASETS["math"]
        repo = config["repo"]

        if subjects is None:
            subjects = config["subjects"]

        dest_dir = self.get_dataset_path("math", split)
        dest_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Downloading MATH {split} for {len(subjects)} subjects")

        self._download_subjects(
            repo, split, subjects, dest_dir, progress_callback
        )

        return dest_dir

    def _download_subjects(
        self: "DatasetManager",
        repo: str,
        split: str,
        subjects: list,
        dest_dir: Path,
        progress_callback: Optional[Callable],
    ) -> None:
        """Download all subjects for MATH dataset."""
        total_subjects = len(subjects)

        def wrapped_callback(current: int, total: int):
            """Wrapper callback for progress tracking.

            Args:
                current: Current bytes downloaded
                total: Total bytes to download
            """
            if progress_callback:
                progress_callback(current, total)

        for idx, subject in enumerate(subjects):
            self._download_subject(
                repo,
                split,
                subject,
                dest_dir,
                idx,
                total_subjects,
                wrapped_callback,
            )

    def _download_subject(
        self: "DatasetManager",
        repo: str,
        split: str,
        subject: str,
        dest_dir: Path,
        idx: int,
        total: int,
        callback: Callable,
    ) -> None:
        """Download a single subject parquet file."""
        filename = f"{split}/{subject}/default-00000-of-00001.parquet"
        subject_file = dest_dir / f"{subject}.parquet"

        if subject_file.exists():
            logger.info(
                f"Subject {subject} ({idx + 1}/{total}) already exists"
            )
            return

        logger.info(f"Downloading subject {subject} ({idx + 1}/{total})")
        self._download_file(repo, filename, str(dest_dir), callback)
