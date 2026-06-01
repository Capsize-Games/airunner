#!/usr/bin/env python
"""CivitAI model downloader CLI tool.

Download models from CivitAI using URLs. Supports progress bars and resumable downloads.

Usage:
    airunner-civitai-download <url>                       # Download model from URL
    airunner-civitai-download <url> --output-dir /path    # Download to specific directory
    airunner-civitai-download <url> --api-key <key>       # Use API key for authentication

Example:
    airunner-civitai-download https://civitai.com/models/995002/70s-sci-fi-movie?modelVersionId=1880417
"""

import argparse
import asyncio
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from tqdm import tqdm

from airunner_services.config.local_settings_store import get_setting
from airunner_services.downloads.job_service import DownloadJobService
from airunner_services.settings import MODELS_DIR


# Terminal colors
class Colors:
    """ANSI color codes for terminal output."""

    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


def parse_civitai_url(url: str) -> Dict[str, Any]:
    """Extract model_id and model_version_id from a CivitAI URL.

    Args:
        url: CivitAI model URL (e.g., https://civitai.com/models/995002/70s-sci-fi-movie?modelVersionId=1880417)

    Returns:
        Dictionary with 'model_id' and 'model_version_id' keys
    """
    model_id = None
    model_version_id = None

    # Match model ID from URL path
    match = re.search(r"/models/(\d+)", url)
    if match:
        model_id = match.group(1)

    # Match version ID from query parameters
    match = re.search(r"modelVersionId=(\d+)", url)
    if match:
        model_version_id = match.group(1)

    return {"model_id": model_id, "model_version_id": model_version_id}


def get_api_key() -> str:
    """Get CivitAI API key from environment or settings.

    Returns:
        API key string or empty string if not found
    """
    # Check environment variable first
    api_key = os.environ.get("CIVITAI_API_KEY", "")
    if api_key:
        return api_key

    return get_setting("civitai/api_key", "")


def fetch_model_info(model_id: str, api_key: str = "") -> Dict[str, Any]:
    """Fetch model metadata from CivitAI API.

    Args:
        model_id: CivitAI model ID
        api_key: Optional API key for authentication

    Returns:
        Model metadata dictionary

    Raises:
        requests.RequestException: On API error
    """
    url = f"https://civitai.com/api/v1/models/{model_id}"
    headers = {"Content-Type": "application/json"}

    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


def sanitize_filename(name: str) -> str:
    """Sanitize filename for filesystem compatibility.

    Args:
        name: Original filename

    Returns:
        Sanitized filename safe for all filesystems
    """
    # Replace problematic characters with underscores
    sanitized = re.sub(r'[<>:"/\\|?*]', "_", name)
    # Remove leading/trailing whitespace and dots
    sanitized = sanitized.strip(". ")
    # Replace multiple underscores/spaces with single underscore
    sanitized = re.sub(r"[_\s]+", "_", sanitized)
    return sanitized


def select_version(
    model_info: Dict[str, Any], version_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Select model version to download.

    Args:
        model_info: Model metadata from API
        version_id: Optional specific version ID

    Returns:
        Version dictionary or None if not found
    """
    versions = model_info.get("modelVersions", [])
    if not versions:
        return None

    if version_id:
        for version in versions:
            if str(version.get("id")) == str(version_id):
                return version
        return None

    # Return latest version (first in list)
    return versions[0]


def get_files_to_download(
    version: Dict[str, Any], model_path: Path
) -> List[Dict[str, Any]]:
    """Get list of files that need to be downloaded.

    Args:
        version: Version metadata from API
        model_path: Directory where files will be saved

    Returns:
        List of file dictionaries with name, url, and size
    """
    files_info = version.get("files", [])
    files_to_download = []

    for file_info in files_info:
        filename = file_info.get("name", "")
        download_url = file_info.get("downloadUrl", "")
        file_size = file_info.get("sizeKB", 0) * 1024  # Convert to bytes

        if not filename or not download_url:
            continue

        # Check if file already exists with correct size
        final_path = model_path / filename
        if final_path.exists() and final_path.stat().st_size == file_size:
            print(
                f"{Colors.YELLOW}Skipping {filename} (already exists){Colors.ENDC}"
            )
            continue

        files_to_download.append(
            {
                "filename": filename,
                "url": download_url,
                "size": file_size,
            }
        )

    return files_to_download


def download_file(
    url: str,
    filepath: Path,
    file_size: int,
    api_key: str = "",
    chunk_size: int = 8192,
) -> bool:
    """Download a single file with progress bar.

    Args:
        url: Download URL
        filepath: Path where file will be saved
        file_size: Expected file size in bytes
        api_key: Optional API key for authentication
        chunk_size: Size of download chunks

    Returns:
        True if download succeeded, False otherwise
    """
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        # First attempt with auth header
        response = requests.get(
            url, headers=headers, stream=True, timeout=30, allow_redirects=True
        )

        # If 401, retry with token in URL
        if response.status_code == 401 and api_key:
            sep = "&" if "?" in url else "?"
            url_with_token = f"{url}{sep}token={api_key}"
            response = requests.get(
                url_with_token, stream=True, timeout=30, allow_redirects=True
            )

        response.raise_for_status()

        # Get actual file size from response if available
        content_length = response.headers.get("content-length")
        if content_length:
            file_size = int(content_length)

        # Ensure parent directory exists
        filepath.parent.mkdir(parents=True, exist_ok=True)

        # Download with progress bar
        with (
            open(filepath, "wb") as f,
            tqdm(
                total=file_size,
                unit="B",
                unit_scale=True,
                unit_divisor=1024,
                desc=filepath.name,
                ncols=80,
            ) as pbar,
        ):
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    pbar.update(len(chunk))

        return True

    except requests.RequestException as e:
        print(f"{Colors.RED}Error downloading {filepath.name}: {e}{Colors.ENDC}")
        # Clean up partial download
        if filepath.exists():
            filepath.unlink()
        return False


def download_model(
    url: str, output_dir: Optional[str] = None, api_key: Optional[str] = None
) -> bool:
    """Download a model from CivitAI URL.

    Args:
        url: CivitAI model URL
        output_dir: Optional output directory (defaults to models/art/models/civitai)
        api_key: Optional API key for authentication

    Returns:
        True if download succeeded, False otherwise
    """
    if api_key is None:
        api_key = get_api_key()

    job_service = DownloadJobService()
    job_id = asyncio.run(
        job_service.start_civitai_model_download(
            url,
            output_dir=output_dir,
            api_key=api_key,
        )
    )
    return _wait_for_download_job(job_service, job_id)


def _wait_for_download_job(
    job_service: DownloadJobService,
    job_id: str,
) -> bool:
    """Poll one CivitAI download job until it reaches a terminal state."""
    last_progress = -1

    while True:
        job = asyncio.run(job_service.get_status(job_id))
        if job is None:
            print(f"{Colors.RED}Error: download job disappeared{Colors.ENDC}")
            return False

        progress = int(job.progress)
        if progress != last_progress:
            print(
                f"\r{Colors.CYAN}Downloading: {progress:3d}%{Colors.ENDC}",
                end="",
                flush=True,
            )
            last_progress = progress

        if job.status.value == "completed":
            paths = (job.result or {}).get("paths") or []
            saved_path = paths[0] if paths else "unknown"
            print(f"\n{Colors.GREEN}Download complete{Colors.ENDC}")
            print(f"Saved to: {saved_path}")
            return True
        if job.status.value == "failed":
            print(f"\n{Colors.RED}Error: {job.error}{Colors.ENDC}")
            return False
        if job.status.value == "cancelled":
            print(f"\n{Colors.YELLOW}Download cancelled{Colors.ENDC}")
            return False

        time.sleep(0.1)


def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description="Download models from CivitAI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  airunner-civitai-download https://civitai.com/models/995002/70s-sci-fi-movie
  airunner-civitai-download https://civitai.com/models/995002?modelVersionId=1880417
  airunner-civitai-download <url> --output-dir /path/to/models
  airunner-civitai-download <url> --api-key your_api_key

Environment Variables:
  CIVITAI_API_KEY    API key for CivitAI (alternative to --api-key)
""",
    )

    parser.add_argument(
        "url",
        help="CivitAI model URL (e.g., https://civitai.com/models/12345/model-name)",
    )

    parser.add_argument(
        "--output-dir",
        "-o",
        help="Output directory for downloaded model (default: models/art/models/civitai)",
    )

    parser.add_argument(
        "--api-key",
        "-k",
        help="CivitAI API key for authentication (or set CIVITAI_API_KEY env var)",
    )

    args = parser.parse_args()

    print()
    print(
        f"{Colors.BOLD}{Colors.HEADER}╔══════════════════════════════════════════════════════════════╗{Colors.ENDC}"
    )
    print(
        f"{Colors.BOLD}{Colors.HEADER}║              AI Runner - CivitAI Model Downloader            ║{Colors.ENDC}"
    )
    print(
        f"{Colors.BOLD}{Colors.HEADER}╚══════════════════════════════════════════════════════════════╝{Colors.ENDC}"
    )
    print()

    success = download_model(args.url, args.output_dir, args.api_key)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
