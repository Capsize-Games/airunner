"""
HuggingFace model downloader without using HF Hub.

Downloads models directly from HuggingFace's file hosting with progress tracking.
Supports downloading specific files (e.g., safetensors, tokenizer, config).
"""

import os
import requests
from pathlib import Path
from typing import List, Optional, Callable, Dict

from airunner.components.application.gui.windows.main.settings_mixin import SettingsMixin
from airunner.utils.application.mediator_mixin import MediatorMixin


class HuggingFaceDownloader(
    MediatorMixin,
    SettingsMixin,
):
    """
    Download models from HuggingFace without using their Hub client.

    This downloader:
    - Makes direct HTTP requests to HuggingFace's CDN
    - Provides progress callbacks for GUI integration
    - Doesn't cache or phone home
    - Works offline after initial download
    """

    BASE_URL = "https://huggingface.co"

    # Essential files for different model types
    REQUIRED_FILES = {
        "llm": [
            "config.json",
            "generation_config.json",
            "tokenizer_config.json",
            "tokenizer.json",
            "special_tokens_map.json",
            "chat_template.jinja",  # Used by many modern models
        ],
        "mistral": [
            # Keep a minimal core set for Mistral models; some Mistral
            # repos do not include optional or engine-specific files.
            "config.json",
            "generation_config.json",
            "tokenizer_config.json",
            "tokenizer.json",
            "special_tokens_map.json",
            "chat_template.jinja",
        ],
        "ministral3": [
            # Ministral 3 models (vision-language) require tekken tokenizer
            "config.json",
            "generation_config.json",
            "tokenizer_config.json",
            "tokenizer.json",
            "tekken.json",  # Mistral-specific tokenizer
            "chat_template.jinja",
            "processor_config.json",  # For vision capabilities
            "params.json",
            "special_tokens_map.json",  # BF16 version has this
        ],
        "flux": [
            # Flux/Stable Diffusion models need all config files
            "model_index.json",
            "scheduler/scheduler_config.json",
            "text_encoder/config.json",
            "text_encoder_2/config.json",
            "tokenizer/tokenizer_config.json",
            "tokenizer/merges.txt",
            "tokenizer/vocab.json",
            "tokenizer_2/tokenizer_config.json",
            "tokenizer_2/merges.txt",
            "tokenizer_2/vocab.json",
            "transformer/config.json",
            "vae/config.json",
        ],
        "art": [
            # Generic art model files (FLUX)
            "model_index.json",
            "scheduler/scheduler_config.json",
            "text_encoder/config.json",
            "tokenizer/tokenizer_config.json",
            "vae/config.json",
        ],
    }

    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialize downloader.

        Args:
            cache_dir: Directory to store downloaded models
        """
        super().__init__()
        if cache_dir is None:
            cache_dir = os.path.join(
                os.path.expanduser(self.path_settings.base_path),
                f"text/models/llm/causallm",
            )
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_model_files(
        self, repo_id: str, revision: str = "main", recursive: bool = True
    ) -> List[Dict[str, any]]:
        """
        Get list of files in a HuggingFace repository.

        Args:
            repo_id: Repository ID (e.g., "mistralai/Ministral-3-8B-Instruct-2512")
            revision: Git revision/branch (default: "main")
            recursive: If True, recursively fetch files from subdirectories

        Returns:
            List of file info dicts with 'path', 'size', etc.
        """
        # Get HuggingFace API token from settings
        from airunner.utils.settings.get_qsettings import get_qsettings

        settings = get_qsettings()
        api_key = settings.value("huggingface/api_key", "")

        # Prepare headers with authentication if available
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        def fetch_directory(path: str = "") -> List[Dict[str, any]]:
            """Fetch files from a directory path."""
            if path:
                api_url = f"https://huggingface.co/api/models/{repo_id}/tree/{revision}/{path}"
            else:
                api_url = f"https://huggingface.co/api/models/{repo_id}/tree/{revision}"

            try:
                response = requests.get(api_url, headers=headers, timeout=30)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                raise RuntimeError(
                    f"Failed to list files for {repo_id}/{path}: {e}"
                )

        # Fetch root level
        all_files = []
        items = fetch_directory()

        for item in items:
            if item.get("type") == "directory" and recursive:
                # Recursively fetch subdirectory contents
                subdir_path = item.get("path", "")
                subdir_files = fetch_directory(subdir_path)
                all_files.extend(subdir_files)
            else:
                all_files.append(item)

        return all_files

    def download_file(
        self,
        repo_id: str,
        filename: str,
        local_dir: str,
        revision: str = "main",
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Path:
        """
        Download a single file from HuggingFace.

        Args:
            repo_id: Repository ID (e.g., "mistralai/Ministral-3-8B-Instruct-2512")
            filename: File to download (e.g., "model-00001-of-00003.safetensors")
            local_dir: Local directory to save file
            revision: Git revision/branch
            progress_callback: Optional callback(downloaded_bytes, total_bytes)

        Returns:
            Path to downloaded file
        """
        # Construct download URL
        url = f"{self.BASE_URL}/{repo_id}/resolve/{revision}/{filename}"

        local_path = Path(local_dir) / filename
        local_path.parent.mkdir(parents=True, exist_ok=True)

        # Check if file already exists
        if local_path.exists():
            print(f"File already exists: {local_path}")
            return local_path

        print(f"Downloading {filename} from {repo_id}...")

        # Get HuggingFace API token from settings
        from airunner.utils.settings.get_qsettings import get_qsettings

        settings = get_qsettings()
        api_key = settings.value("huggingface/api_key", "")

        # Prepare headers with authentication if available
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        try:
            # Stream download with progress tracking
            response = requests.get(
                url, headers=headers, stream=True, timeout=60
            )
            response.raise_for_status()

            total_size = int(response.headers.get("content-length", 0))
            downloaded = 0

            with open(local_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        if progress_callback and total_size > 0:
                            progress_callback(downloaded, total_size)

            print(f"Downloaded: {local_path}")
            return local_path

        except Exception as e:
            # Cleanup partial download
            if local_path.exists():
                local_path.unlink()
            raise RuntimeError(
                f"Failed to download {filename} from {repo_id}: {e}"
            )

    def download_model(
        self,
        repo_id: str,
        local_dir: Optional[str] = None,
        model_type: str = "llm",
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        revision: str = "main",
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
    ) -> Path:
        """
        Download a complete model from HuggingFace.

        Args:
            repo_id: Repository ID (e.g., "mistralai/Ministral-3-8B-Instruct-2512")
            local_dir: Local directory (default: cache_dir/repo_name)
            model_type: "llm" or "ministral3" (determines required files)
            include_patterns: File patterns to include (e.g., ["*.safetensors", "*.json"])
            exclude_patterns: File patterns to exclude (e.g., ["*.bin"])
            revision: Git revision/branch
            progress_callback: Optional callback(filename, downloaded_bytes, total_bytes)

        Returns:
            Path to model directory
        """
        if local_dir is None:
            model_name = repo_id.split("/")[-1]
            local_dir = self.cache_dir / model_name
        else:
            local_dir = Path(local_dir)

        local_dir.mkdir(parents=True, exist_ok=True)

        # Get list of files
        files = self.get_model_files(repo_id, revision)

        # Filter files
        required_files = self.REQUIRED_FILES.get(
            model_type, self.REQUIRED_FILES["llm"]
        )

        files_to_download = []
        for file_info in files:
            filename = file_info.get("path", "")

            # Skip directories
            if file_info.get("type") == "directory":
                continue

            # Always download required files
            if filename in required_files:
                files_to_download.append(filename)
                continue

            # Apply include/exclude patterns
            if include_patterns:
                if not any(
                    self._match_pattern(filename, p) for p in include_patterns
                ):
                    continue

            if exclude_patterns:
                if any(
                    self._match_pattern(filename, p) for p in exclude_patterns
                ):
                    continue

            files_to_download.append(filename)

        # Download files
        print(f"Downloading {len(files_to_download)} files for {repo_id}...")
        for filename in files_to_download:

            def file_progress(downloaded, total):
                if progress_callback:
                    progress_callback(filename, downloaded, total)

            self.download_file(
                repo_id,
                filename,
                local_dir,
                revision,
                file_progress,
            )

        print(f"Model downloaded to: {local_dir}")
        return local_dir

    def download_gguf_model(
        self,
        repo_id: str,
        filename: str,
        local_dir: Optional[str] = None,
        revision: str = "main",
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
    ) -> Path:
        """
        Download a GGUF model file from HuggingFace.

        GGUF models are single files, so this is simpler than download_model().
        The model will be stored in: local_dir/filename

        Args:
            repo_id: GGUF repository ID (e.g., "Qwen/Qwen3-8B-GGUF")
            filename: GGUF filename (e.g., "Qwen3-8B-Q4_K_M.gguf")
            local_dir: Local directory (default: cache_dir/model_name)
            revision: Git revision/branch
            progress_callback: Optional callback(filename, downloaded_bytes, total_bytes)

        Returns:
            Path to the downloaded .gguf file
        """
        # Extract model name from filename (remove .gguf extension and quant suffix)
        model_name = filename.replace(".gguf", "")
        # Remove common quant suffixes for cleaner folder names
        for suffix in ["-Q4_K_M", "-Q4_K_S", "-Q5_K_M", "-Q8_0", "-q4_k_m", "-q4_k_s", "-q5_k_m", "-q8_0"]:
            model_name = model_name.replace(suffix, "")

        if local_dir is None:
            local_dir = self.cache_dir / model_name
        else:
            local_dir = Path(local_dir)

        local_dir.mkdir(parents=True, exist_ok=True)

        def file_progress(downloaded, total):
            if progress_callback:
                progress_callback(filename, downloaded, total)

        # Download the GGUF file
        gguf_path = self.download_file(
            repo_id,
            filename,
            str(local_dir),
            revision,
            file_progress,
        )

        print(f"GGUF model downloaded to: {gguf_path}")
        return gguf_path

    @staticmethod
    def _match_pattern(filename: str, pattern: str) -> bool:
        """Simple pattern matching (supports * wildcard)."""
        import fnmatch

        return fnmatch.fnmatch(filename, pattern)


# Example usage
if __name__ == "__main__":
    downloader = HuggingFaceDownloader()

    # Download Ministral-3-8B-Instruct-2512 (separate safetensors only)
    model_path = downloader.download_model(
        repo_id="mistralai/Ministral-3-8B-Instruct-2512",
        model_type="ministral3",
        include_patterns=["*.safetensors", "*.json"],
        exclude_patterns=["*.bin", "*consolidated*"],
        progress_callback=lambda f, d, t: print(f"{f}: {d}/{t} bytes"),
    )
    print(f"Model ready at: {model_path}")
