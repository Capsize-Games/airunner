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
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from tqdm import tqdm

from airunner.settings import MODELS_DIR


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

    # Try to get from QSettings (if Qt is available)
    try:
        from airunner.utils.settings.get_qsettings import get_qsettings

        settings = get_qsettings()
        api_key = settings.value("civitai/api_key", "")
    except Exception:
        pass

    return api_key


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
    # Parse URL
    parsed = parse_civitai_url(url)
    model_id = parsed.get("model_id")
    version_id = parsed.get("model_version_id")

    if not model_id:
        print(f"{Colors.RED}Error: Invalid CivitAI URL{Colors.ENDC}")
        print(f"Expected format: https://civitai.com/models/<id>/...")
        return False

    # Get API key
    if api_key is None:
        api_key = get_api_key()

    # Set output directory
    if not output_dir:
        output_dir = os.path.join(MODELS_DIR, "art/models/civitai")

    print(f"{Colors.CYAN}Fetching model info for ID: {model_id}...{Colors.ENDC}")

    try:
        model_info = fetch_model_info(model_id, api_key)
    except requests.RequestException as e:
        print(f"{Colors.RED}Error fetching model info: {e}{Colors.ENDC}")
        return False

    # Get model name
    model_name = model_info.get("name", f"model_{model_id}")

    # Select version
    version = select_version(model_info, version_id)
    if not version:
        if version_id:
            print(
                f"{Colors.RED}Error: Version {version_id} not found for model {model_id}{Colors.ENDC}"
            )
        else:
            print(
                f"{Colors.RED}Error: No versions found for model {model_id}{Colors.ENDC}"
            )
        return False

    version_name = version.get("name", "latest")

    print(
        f"{Colors.GREEN}Model: {model_name} v{version_name}{Colors.ENDC}"
    )

    # Prepare output path
    safe_name = sanitize_filename(f"{model_name}_{version_name}")
    model_path = Path(output_dir) / safe_name
    model_path.mkdir(parents=True, exist_ok=True)

    print(f"{Colors.CYAN}Output: {model_path}{Colors.ENDC}")

    # Get files to download
    files_to_download = get_files_to_download(version, model_path)

    if not files_to_download:
        print(f"{Colors.GREEN}All files already downloaded!{Colors.ENDC}")
        return True

    # Calculate total size
    total_size = sum(f["size"] for f in files_to_download)
    total_gb = total_size / (1024**3)

    print(
        f"{Colors.CYAN}Downloading {len(files_to_download)} file(s) ({total_gb:.2f} GB)...{Colors.ENDC}"
    )
    print()

    # Download each file
    success = True
    for file_info in files_to_download:
        filename = file_info["filename"]
        file_url = file_info["url"]
        file_size = file_info["size"]

        filepath = model_path / filename

        if not download_file(file_url, filepath, file_size, api_key):
            success = False
            continue

        print(f"{Colors.GREEN}✓ {filename}{Colors.ENDC}")

    print()
    if success:
        print(f"{Colors.GREEN}{Colors.BOLD}Download complete!{Colors.ENDC}")
        print(f"{Colors.CYAN}Model saved to: {model_path}{Colors.ENDC}")
    else:
        print(
            f"{Colors.YELLOW}Download completed with some errors. Check the output above.{Colors.ENDC}"
        )

    return success


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
