"""Worker for HuggingFace model downloads using Python threading."""

import hashlib
import os
import re
import threading
from pathlib import Path
from typing import Optional
import requests

from airunner_common.contract_enums import SignalCode
from airunner_common.settings import AIRUNNER_BASE_PATH, MODELS_DIR
from airunner_services.bootstrap.model_bootstrap_data import (
    model_bootstrap_data,
)
from airunner_services.bootstrap.unified_model_files import (
    get_required_files_for_model,
)
from airunner_services.config.local_settings_store import get_setting
from airunner_services.downloads.base_download_worker import (
    BaseDownloadWorker,
)
from airunner_services.llm.utils.model_downloader import (
    HuggingFaceDownloader,
)
from airunner_services.utils.zip_utils import safe_extract_zip


class HuggingFaceDownloadWorker(BaseDownloadWorker):
    """Worker for downloading HuggingFace models with parallel file downloading."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.downloader = HuggingFaceDownloader()
        self._current_model_type = None  # Set by _download_model for completion signals
        self._current_pipeline_action = None  # Set by _download_model for completion signals

    @property
    def _complete_signal(self) -> SignalCode:
        """Signal to emit on successful download completion."""
        return SignalCode.HUGGINGFACE_DOWNLOAD_COMPLETE

    @property
    def _failed_signal(self) -> SignalCode:
        """Signal to emit on download failure."""
        return SignalCode.HUGGINGFACE_DOWNLOAD_FAILED

    def _apply_post_download_patches(self, model_path: Path) -> None:
        """Run any post-download housekeeping required by one model."""
        del model_path

    @staticmethod
    def _resolve_bootstrap_revision(repo_id: str) -> str:
        """Return the pinned revision for a curated repo_id, else "main".

        model_bootstrap_data entries already declare a ``branch`` (e.g.
        the SDXL Inpaint entry pins "fp16"), but nothing previously read
        it — every download hardcoded ``resolve/main`` regardless. This
        only stops ignoring a pin that was already declared; it does not
        invent new pins for repos with no curated entry (custom models),
        which continue to resolve "main" exactly as before (release
        issue D01).
        """
        for model in model_bootstrap_data:
            if model.get("path") == repo_id:
                return model.get("branch") or "main"
        return "main"

    @staticmethod
    def _file_sha256(path: Path) -> str:
        """Return the hex SHA256 digest of a file, reading in chunks."""
        hasher = hashlib.sha256()
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    @staticmethod
    def _identity_sidecar_path(temp_path: Path) -> Path:
        """Return the sidecar path recording one temp file's server identity."""
        return temp_path.with_name(temp_path.name + ".identity")

    @staticmethod
    def _response_identity(response: "requests.Response") -> Optional[str]:
        """Return a stable identity string for one HTTP response's target.

        Prefers ETag; Last-Modified is a reasonable fallback. Returns
        None when a server provides neither, in which case identity
        cannot be checked and resume proceeds on trust as before
        (release issue D02).
        """
        return response.headers.get("etag") or response.headers.get(
            "last-modified"
        )

    @classmethod
    def _read_stored_identity(cls, temp_path: Path) -> Optional[str]:
        """Return the identity recorded for one temp file's prior attempt.

        Returns ``None`` only when no sidecar file exists at all, i.e.
        this worker has never recorded an attempt for this temp file
        (unknown provenance -- must not be trusted on resume; release
        issue D02 review finding F3). An empty string is a real,
        previously-recorded value meaning "the server provided no
        identity header on that attempt", and is distinct from "nothing
        was ever recorded".
        """
        try:
            return cls._identity_sidecar_path(temp_path).read_text(
                encoding="utf-8"
            )
        except OSError:
            return None

    @classmethod
    def _write_stored_identity(
        cls, temp_path: Path, identity: Optional[str]
    ) -> None:
        """Record one temp file's current attempt's server identity.

        Always writes a sidecar file, even when ``identity`` is falsy:
        the sidecar's mere presence is what lets ``_read_stored_identity``
        distinguish "this worker started this download and the server
        gave no identity header" (safe to keep trusting the same way on
        a resume) from "no sidecar was ever written for this temp file"
        (unknown provenance, must not be trusted -- see
        ``_read_stored_identity``).
        """
        sidecar = cls._identity_sidecar_path(temp_path)
        try:
            sidecar.write_text(identity or "", encoding="utf-8")
        except OSError:
            pass

    @classmethod
    def _clear_stored_identity(cls, temp_path: Path) -> None:
        """Remove one temp file's identity sidecar entirely."""
        try:
            cls._identity_sidecar_path(temp_path).unlink(missing_ok=True)
        except OSError:
            pass

    @classmethod
    def _discard_temp_file(cls, temp_path: Path) -> None:
        """Delete one temp file and its identity sidecar, ignoring errors.

        Used whenever a partial download can no longer be trusted (the
        server's identity changed, or it returned an invalid partial
        response) so a restart never appends new bytes onto stale ones
        (release issue D02).
        """
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass
        cls._clear_stored_identity(temp_path)

    @staticmethod
    def _content_range_start_matches(
        content_range: str, expected_start: int
    ) -> bool:
        """Return whether a 206 response's Content-Range starts as expected.

        A malformed or missing header is treated as not matching: a
        caller cannot trust an unverifiable partial response to be the
        continuation it asked for (release issue D02).
        """
        match = re.match(r"bytes\s+(\d+)-\d+/(?:\d+|\*)", content_range or "")
        return bool(match) and int(match.group(1)) == expected_start

    def _verify_and_finalize(
        self,
        *,
        temp_path: Path,
        final_path: Path,
        filename: str,
        expected_sha256: Optional[str],
    ) -> bool:
        """Verify an optional digest, then move temp_path into place.

        A same-sized but corrupted (or tampered) file must not be loaded
        just because its byte count matches (release issue D01): when a
        digest is pinned, it is checked before the file is ever moved to
        its final, loadable location. On mismatch the temp file is
        deleted and the file is marked failed rather than silently used.
        When no digest is pinned (the common case today — see
        ``_resolve_bootstrap_revision``), this only performs the move,
        preserving prior behavior for unverified/custom models.
        """
        if expected_sha256:
            actual_sha256 = self._file_sha256(temp_path)
            if actual_sha256.lower() != expected_sha256.lower():
                self.logger.error(
                    "Digest mismatch for %s: expected %s, got %s. "
                    "Deleting corrupt download; it will not be loaded.",
                    filename,
                    expected_sha256,
                    actual_sha256,
                )
                try:
                    self._discard_temp_file(temp_path)
                except Exception as exc:
                    self.logger.warning(
                        f"Failed to delete corrupt temp file {filename}: {exc}"
                    )
                self._mark_file_failed(filename)
                return False

        final_path.parent.mkdir(parents=True, exist_ok=True)
        # os.replace() atomically overwrites an existing destination in one
        # step. The previous unlink-then-rename left a window where, if the
        # process died between the two calls, a valid prior file was already
        # gone with nothing to replace it (release issue D02).
        os.replace(temp_path, final_path)
        self._clear_stored_identity(temp_path)
        self._mark_file_complete(filename)
        return True

    @staticmethod
    def _resolve_art_download_context(
        repo_id: str,
        version: str = None,
        pipeline_action: str = None,
    ):
        """Resolve art-model bootstrap lookup keys.

        Art downloads must use the exact version/pipeline pair that matches the
        bootstrap manifest. Falling back to an unrelated model version causes the
        downloader to request invalid files.
        """
        resolved_version = version
        resolved_pipeline_action = pipeline_action or "txt2img"

        if resolved_version:
            return resolved_version, resolved_pipeline_action

        for model in model_bootstrap_data:
            if model.get("model_type") != "art":
                continue
            if model.get("path") != repo_id:
                continue

            resolved_version = model.get("version")
            if not pipeline_action:
                resolved_pipeline_action = (
                    model.get("pipeline_action") or resolved_pipeline_action
                )
            break

        return resolved_version, resolved_pipeline_action

    def _download_model(
        self,
        repo_id: str = None,
        model_type: str = None,
        output_dir: str = None,
        version: str = None,
        pipeline_action: str = "txt2img",
        missing_files: list = None,
        gguf_filename: str = None,
        zip_url: str = None,
    ):
        """Download model files from HuggingFace or direct URL.

        Args:
            repo_id: HuggingFace repository ID (e.g., "Tongyi-MAI/Z-Image-Turbo")
            model_type: Type of model (llm, art, gguf, openvoice_zip, etc.)
            output_dir: Directory to save the model
            version: Version name for bootstrap data lookup (e.g.,
                "SDXL 1.0", "Z-Image Turbo")
            pipeline_action: Pipeline action (txt2img, inpaint, etc.)
            missing_files: Specific list of files to download (if provided, only these files will be downloaded)
            gguf_filename: For GGUF downloads, the specific .gguf file to download
            zip_url: For ZIP downloads, the direct URL to download

        """
        resolved_version = version
        resolved_pipeline_action = pipeline_action
        if model_type == "art":
            resolved_version, resolved_pipeline_action = self._resolve_art_download_context(
                repo_id=repo_id,
                version=version,
                pipeline_action=pipeline_action,
            )
            if not resolved_version:
                error = (
                    f"Unable to resolve art model version for repo {repo_id}. "
                    "Provide version/pipeline metadata when queueing the download."
                )
                self.logger.error(error)
                self.emit_signal(self._failed_signal, {"error": error})
                return

            if not version:
                self.logger.info(
                    "Resolved art download context from repo_id=%s to version=%s pipeline_action=%s",
                    repo_id,
                    resolved_version,
                    resolved_pipeline_action,
                )

        # Store model_type and pipeline_action immediately for use in completion signals
        self._current_model_type = model_type
        self._current_pipeline_action = resolved_pipeline_action or pipeline_action
        
        self.logger.info(
            f"_download_model called with repo_id={repo_id}, model_type={model_type}, "
            f"output_dir={output_dir}, version={resolved_version}, pipeline_action={resolved_pipeline_action}, "
            f"missing_files={missing_files}, gguf_filename={gguf_filename}, zip_url={zip_url}"
        )

        # Handle ZIP file downloads (OpenVoice checkpoints)
        if model_type == "openvoice_zip" and zip_url:
            self._download_and_extract_zip(zip_url, output_dir)
            return

        # Handle GGUF downloads specially - just download the single file
        if model_type == "gguf" and gguf_filename:
            if not output_dir:
                from airunner_services.llm.config.provider_config import (
                    LLMProviderConfig,
                )

                output_dir = LLMProviderConfig.get_local_storage_path(
                    AIRUNNER_BASE_PATH,
                    "local",
                    repo_id=repo_id,
                    prefer_pre_quantized=True,
                )
            self._download_gguf_model(
                repo_id,
                output_dir,
                gguf_filename,
                revision=self._resolve_bootstrap_revision(repo_id),
            )
            return

        api_key = get_setting("huggingface/api_key", "")

        if not output_dir:
            output_dir = os.path.join(MODELS_DIR, "text/models/llm/causallm")

        # For art/stt/tts/rmbg models, don't create a subdirectory.
        # The provided output_dir already points at the final model location.
        is_stt_tts = model_type in ("stt", "tts_openvoice")
        is_rmbg = model_type == "rmbg"
        if model_type == "art" or is_stt_tts or is_rmbg:
            model_path = Path(output_dir)
            self.logger.info(
                f"Using output_dir directly for {model_type} model: {model_path}"
            )
        else:
            model_name = repo_id.split("/")[-1]
            model_path = Path(output_dir) / model_name
            self.logger.info(
                f"Creating subdirectory for LLM model: {model_path}"
            )

        # Initialize download state
        self.is_cancelled = False
        self._completed_files.clear()
        self._failed_files.clear()
        self._file_progress.clear()
        self._file_sizes.clear()
        self._file_threads.clear()
        self._total_downloaded = 0
        self._total_size = 0

        temp_dir = self._prepare_temp_dir(model_path)

        self._model_path = model_path
        self._temp_dir = temp_dir

        self.emit_signal(
            SignalCode.UPDATE_DOWNLOAD_LOG,
            {"message": f"Starting download: {repo_id}"},
        )

        # Filter files to download
        # If specific missing_files list is provided, use ONLY those files
        # Otherwise, use the comprehensive bootstrap data
        is_art_model = model_type == "art"
        is_stt_tts_model = model_type in ("stt", "tts_openvoice")
        is_rmbg_model = model_type == "rmbg"
        is_llm_model = model_type in ("llm", "gguf")

        # For art/stt/tts/rmbg models, use bootstrap data directly.
        # For LLM models, we still need API to discover model shards
        bootstrap_files = None
        full_bootstrap_data = None  # Full bootstrap data for size lookups

        # First, get the full bootstrap data based on model type
        if is_art_model:
            full_bootstrap_data = get_required_files_for_model(
                "art",
                resolved_version,
                resolved_version,
                resolved_pipeline_action,
            )
            if full_bootstrap_data:
                self.logger.info(
                    f"Found bootstrap data for {resolved_version} with {len(full_bootstrap_data)} files"
                )
        elif is_stt_tts_model:
            # For STT/TTS models, get the list of required files from bootstrap data
            full_bootstrap_data = get_required_files_for_model(
                model_type, repo_id
            )
            if full_bootstrap_data:
                self.logger.info(
                    f"Found bootstrap data for {model_type}/{repo_id} with {len(full_bootstrap_data)} files"
                )
        elif is_rmbg_model:
            full_bootstrap_data = get_required_files_for_model(
                "rmbg", repo_id
            )
            if full_bootstrap_data:
                self.logger.info(
                    f"Found bootstrap data for rmbg/{repo_id} with {len(full_bootstrap_data)} files"
                )
        elif is_llm_model:
            # For LLM models, get bootstrap data for file size validation
            full_bootstrap_data = get_required_files_for_model("llm", repo_id)
            if full_bootstrap_data:
                self.logger.info(
                    f"Found bootstrap data for llm/{repo_id} with {len(full_bootstrap_data)} files"
                )
            else:
                self.logger.warning(
                    f"No bootstrap data found for llm/{repo_id} - file sizes will be fetched from API"
                )

        if is_art_model and resolved_version == "Z-Image Turbo":
            missing_files = self._prune_zimage_missing_files(
                output_dir=model_path,
                missing_files=missing_files,
            )
            if not missing_files:
                bootstrap_files = self._prune_zimage_bootstrap_files(
                    output_dir=model_path,
                    bootstrap_files=full_bootstrap_data,
                )

        if missing_files:
            # Use the explicitly provided missing files list
            # Look up expected sizes from bootstrap data
            self.logger.info(
                f"Using explicitly provided missing_files list ({len(missing_files)} files)"
            )
            bootstrap_files = {}
            for f in missing_files:
                # Get expected size from full bootstrap data if available
                expected_size = 0
                if full_bootstrap_data and isinstance(full_bootstrap_data, dict) and f in full_bootstrap_data:
                    expected_size = full_bootstrap_data[f]
                    self.logger.info(f"Missing file {f}: expected size {expected_size} (from bootstrap)")
                else:
                    self.logger.warning(f"Missing file {f}: no expected size found in bootstrap data")
                bootstrap_files[f] = expected_size
        elif is_art_model:
            if bootstrap_files is None:
                bootstrap_files = full_bootstrap_data

            if bootstrap_files is None or len(bootstrap_files) == 0:
                self.logger.error(
                    f"No bootstrap data found for {model_type} (version={resolved_version}, pipeline_action={resolved_pipeline_action})! Cannot determine required files."
                )
                self.emit_signal(
                    self._failed_signal,
                    {
                        "error": f"No bootstrap data found for {model_type} (version={resolved_version}, pipeline_action={resolved_pipeline_action})"
                    },
                )
                return
        elif is_stt_tts_model or is_rmbg_model:
            # For STT/TTS/RMBG models, bootstrap data is a list of filenames.
            # Convert to dict with size=0 (unknown) for compatibility
            if full_bootstrap_data:
                bootstrap_files = {f: 0 for f in full_bootstrap_data}
            else:
                self.logger.error(
                    f"No bootstrap data found for {model_type}/{repo_id}! Cannot determine required files."
                )
                self.emit_signal(
                    self._failed_signal,
                    {
                        "error": f"No bootstrap data found for {model_type}/{repo_id}"
                    },
                )
                return

        # For art/stt/tts/rmbg models with bootstrap data, skip the API call.
        if (is_art_model or is_stt_tts_model or is_rmbg_model) and bootstrap_files:
            files_to_download = []

            for filename, expected_size in bootstrap_files.items():
                # Check if file already exists and is complete
                final_path = model_path / filename

                if final_path.exists():
                    actual_size = final_path.stat().st_size
                    if expected_size > 0 and actual_size < expected_size:
                        # File is incomplete - needs re-download
                        self.logger.warning(
                            f"File {filename} is incomplete: {actual_size} bytes vs expected {expected_size} bytes. "
                            "Will re-download."
                        )
                        self.emit_signal(
                            SignalCode.UPDATE_DOWNLOAD_LOG,
                            {
                                "message": f"Incomplete file detected: {filename} ({actual_size / (1024**2):.1f} MB / {expected_size / (1024**2):.1f} MB). Re-downloading..."
                            },
                        )
                        # Delete incomplete file so it can be re-downloaded
                        try:
                            final_path.unlink()
                        except Exception as e:
                            self.logger.error(f"Failed to delete incomplete file {filename}: {e}")
                            continue
                    elif expected_size == 0 and actual_size < 1024:
                        # No expected size known, but file is suspiciously small (< 1KB)
                        # This likely means the download was interrupted very early
                        self.logger.warning(
                            f"File {filename} exists but is very small ({actual_size} bytes) with unknown expected size. "
                            "Assuming incomplete and re-downloading."
                        )
                        try:
                            final_path.unlink()
                        except Exception as e:
                            self.logger.error(f"Failed to delete suspicious file {filename}: {e}")
                            continue
                    else:
                        # File exists and appears complete (or we can't verify)
                        self.logger.debug(f"File {filename} exists ({actual_size} bytes), skipping")
                        continue

                # Skip transformer weights if using GGUF (only when not explicitly provided)
                if (
                    not missing_files
                    and "transformer/diffusion_pytorch_model" in filename
                    and filename.endswith(".safetensors")
                ):
                    self.logger.info(
                        f"Skipping transformer weights (using GGUF): {filename}"
                    )
                    continue

                files_to_download.append(
                    {"filename": filename, "size": expected_size}
                )

        else:
            # For LLM models, get list of files from HuggingFace API
            self.logger.info(f"Fetching file list from HuggingFace API for {repo_id}...")
            self.emit_signal(
                SignalCode.UPDATE_DOWNLOAD_LOG,
                {"message": f"Fetching file list from HuggingFace..."},
            )
            try:
                all_files = self.downloader.get_model_files(repo_id)
                self.logger.info(f"Got {len(all_files)} files from HuggingFace API")
            except Exception as e:
                self.logger.error(f"Failed to get file list: {e}")
                self.emit_signal(self._failed_signal, {"error": str(e)})
                return

            # For LLM models, use the minimal required files from downloader
            required_files = self.downloader.REQUIRED_FILES.get(
                model_type, self.downloader.REQUIRED_FILES["llm"]
            )

            files_to_download = []

            for file_info in all_files:
                filename = file_info.get("path", "")
                expected_size = file_info.get("size", 0)

                # Skip directories
                if file_info.get("type") == "directory":
                    continue

                # Check if file already exists and is complete
                final_path = model_path / filename
                if final_path.exists():
                    actual_size = final_path.stat().st_size
                    if expected_size > 0 and actual_size < expected_size:
                        # File is incomplete - needs re-download
                        self.logger.warning(
                            f"File {filename} is incomplete: {actual_size} bytes vs expected {expected_size} bytes. "
                            "Will re-download."
                        )
                        self.emit_signal(
                            SignalCode.UPDATE_DOWNLOAD_LOG,
                            {
                                "message": f"Incomplete file detected: {filename} ({actual_size / (1024**2):.1f} MB / {expected_size / (1024**2):.1f} MB). Re-downloading..."
                            },
                        )
                        # Delete incomplete file so it can be re-downloaded
                        try:
                            final_path.unlink()
                        except Exception as e:
                            self.logger.error(f"Failed to delete incomplete file {filename}: {e}")
                            continue
                    else:
                        # File exists and appears complete
                        continue

                # Include required files (config, tokenizer files) for LLM models
                if filename in required_files:
                    files_to_download.append(
                        {"filename": filename, "size": expected_size}
                    )
                    continue

                # For LLM models: Include model shards and config files
                # EXCLUDE consolidated.safetensors - we need individual shards for gradual loading
                if filename == "consolidated.safetensors":
                    continue

                # Include all config/tokenizer/model files (.json, .txt, .model, .jinja, .safetensors)
                if filename.endswith((".safetensors", ".json", ".txt", ".model", ".jinja")):
                    files_to_download.append(
                        {"filename": filename, "size": expected_size}
                    )

        if not files_to_download:
            self.emit_signal(
                SignalCode.UPDATE_DOWNLOAD_LOG,
                {"message": "All files already downloaded!"},
            )
            # Run post-download housekeeping even when files already exist.
            self._apply_post_download_patches(model_path)
            self.emit_signal(
                self._complete_signal,
                {"model_path": str(model_path), "repo_id": repo_id, "model_type": self._current_model_type, "pipeline_action": self._current_pipeline_action},
            )
            return

        self._total_size = sum(f["size"] for f in files_to_download)
        total_gb = self._total_size / (1024**3)

        self.emit_signal(
            SignalCode.UPDATE_DOWNLOAD_LOG,
            {
                "message": f"Downloading {len(files_to_download)} files ({total_gb:.2f} GB) in parallel"
            },
        )

        # Start download threads
        resolved_revision = self._resolve_bootstrap_revision(repo_id)
        for file_info in files_to_download:
            if self.is_cancelled:
                return

            filename = file_info["filename"]
            file_size = file_info["size"]

            self._file_sizes[filename] = file_size
            self._file_progress[filename] = 0

            self.emit_signal(
                SignalCode.UPDATE_DOWNLOAD_LOG,
                {"message": f"Starting download thread for {filename}..."},
            )

            thread = threading.Thread(
                target=self._download_file,
                args=(
                    repo_id,
                    filename,
                    file_size,
                    self._temp_dir,
                    model_path,
                    api_key,
                ),
                kwargs={"revision": resolved_revision},
                daemon=True,
            )
            self._file_threads[filename] = thread
            thread.start()

        self.emit_signal(
            SignalCode.UPDATE_DOWNLOAD_LOG,
            {
                "message": f"Started {len(files_to_download)} download threads, waiting for completion..."
            },
        )

        # Wait for completion
        if not self._wait_for_completion(len(files_to_download)):
            return

        self._cleanup_temp_files()
        
        # Run post-download housekeeping after a successful transfer.
        self._apply_post_download_patches(model_path)
        
        self.emit_signal(
            self._complete_signal,
            {"model_path": str(model_path), "repo_id": repo_id, "model_type": self._current_model_type, "pipeline_action": self._current_pipeline_action},
        )

    def _prune_zimage_bootstrap_files(
        self,
        output_dir: Path,
        bootstrap_files: dict | None,
    ) -> dict | None:
        """Return a lean bootstrap subset when an FP8 checkpoint already exists."""
        if not bootstrap_files:
            return bootstrap_files
        # Imported lazily: zimage_bundle_requirements imports torch, and this
        # module must stay importable in torch-free installs (issue #2054).
        from airunner_services.art.managers.zimage.zimage_bundle_requirements import (
            find_active_checkpoint,
            get_active_zimage_load_mode,
            get_downloadable_files_for_mode,
        )

        checkpoint = find_active_checkpoint(output_dir)
        if checkpoint is None:
            return bootstrap_files
        load_mode = get_active_zimage_load_mode(checkpoint)
        downloadable = set(get_downloadable_files_for_mode(checkpoint, load_mode))
        pruned = {
            filename: size
            for filename, size in bootstrap_files.items()
            if filename in downloadable
        }
        self.logger.info(
            "Pruned Z-Image bootstrap file set for %s from %d files to %d files",
            load_mode,
            len(bootstrap_files),
            len(pruned),
        )
        return pruned

    def _prune_zimage_missing_files(
        self,
        output_dir: Path,
        missing_files: list | None,
    ) -> list | None:
        """Drop Z-Image missing files that are not needed for the active load mode."""
        if not missing_files:
            return missing_files
        # Imported lazily: zimage_bundle_requirements imports torch, and this
        # module must stay importable in torch-free installs (issue #2054).
        from airunner_services.art.managers.zimage.zimage_bundle_requirements import (
            find_active_checkpoint,
            get_active_zimage_load_mode,
            get_downloadable_files_for_mode,
        )

        checkpoint = find_active_checkpoint(output_dir)
        if checkpoint is None:
            return missing_files
        load_mode = get_active_zimage_load_mode(checkpoint)
        downloadable = set(get_downloadable_files_for_mode(checkpoint, load_mode))
        pruned = [
            file_name for file_name in missing_files if file_name in downloadable
        ]
        dropped = sorted(set(missing_files) - set(pruned))
        if dropped:
            self.logger.info(
                "Dropped %d unneeded Z-Image download files for %s: %s",
                len(dropped),
                load_mode,
                dropped,
            )
        return pruned

    def _download_and_extract_zip(self, zip_url: str, output_dir: str):
        """Download and extract a ZIP file with progress tracking.

        Args:
            zip_url: Direct URL to the ZIP file
            output_dir: Directory to extract to
        """
        import zipfile

        filename = os.path.basename(zip_url)
        model_path = Path(output_dir)
        model_path.mkdir(parents=True, exist_ok=True)

        # Initialize download state
        self.is_cancelled = False
        self._completed_files.clear()
        self._failed_files.clear()
        self._file_progress.clear()
        self._file_sizes.clear()
        self._file_threads.clear()
        self._total_downloaded = 0
        self._total_size = 0

        temp_dir = self._prepare_temp_dir(model_path)

        self._model_path = model_path
        self._temp_dir = temp_dir

        self.emit_signal(
            SignalCode.UPDATE_DOWNLOAD_LOG,
            {"message": f"Starting ZIP download: {filename}"},
        )

        # Get file size
        try:
            head_response = requests.head(zip_url, allow_redirects=True, timeout=30)
            head_response.raise_for_status()
            file_size = int(head_response.headers.get("Content-Length", 0))
        except requests.RequestException as e:
            self.logger.error(f"Failed to get ZIP file size: {e}")
            file_size = 0

        self._total_size = file_size
        self._file_sizes[filename] = file_size

        size_mb = file_size / (1024 * 1024)
        self.emit_signal(
            SignalCode.UPDATE_DOWNLOAD_LOG,
            {"message": f"Downloading: {filename} ({size_mb:.1f} MB)"},
        )

        # Download the file
        temp_path = temp_dir / filename
        try:
            with requests.get(zip_url, stream=True, timeout=300) as response:
                response.raise_for_status()

                downloaded = 0
                with open(temp_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if self.is_cancelled:
                            self.emit_signal(
                                self._failed_signal,
                                {"error": "Download cancelled"},
                            )
                            return

                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)

                            # Update progress every ~1MB
                            if downloaded % (1024 * 1024) < 8192:
                                self._update_file_progress(
                                    filename, downloaded, file_size
                                )

                self._update_file_progress(filename, downloaded, file_size)

            self.emit_signal(
                SignalCode.UPDATE_DOWNLOAD_LOG,
                {"message": f"Extracting {filename}..."},
            )

            # Extract the ZIP
            with zipfile.ZipFile(temp_path, "r") as zip_ref:
                safe_extract_zip(zip_ref, model_path)

            # Clean up
            temp_path.unlink()
            self._cleanup_temp_files()

            self.emit_signal(
                SignalCode.UPDATE_DOWNLOAD_LOG,
                {"message": f"Successfully extracted {filename}"},
            )

            self.emit_signal(
                self._complete_signal,
                {"model_path": str(model_path), "model_type": "openvoice_zip"},
            )

        except Exception as e:
            self.logger.error(f"Failed to download/extract ZIP: {e}")
            self.emit_signal(
                self._failed_signal,
                {"error": str(e)},
            )

    def _download_gguf_model(
        self,
        repo_id: str,
        output_dir: str,
        gguf_filename: str,
        revision: str = "main",
        expected_sha256: Optional[str] = None,
    ):
        """Download a single GGUF model file from HuggingFace.

        GGUF models are pre-quantized and don't need additional processing.
        We just download the single .gguf file directly.

        Args:
            repo_id: HuggingFace repository ID (e.g., "Qwen/Qwen3.5-9B-GGUF")
            output_dir: Directory to save the model
            gguf_filename: The .gguf file to download (e.g., "Qwen3.5-9B-Q4_K_M.gguf")
            revision: Git revision/branch/tag to resolve the file against,
                instead of always assuming "main" (release issue D01).
            expected_sha256: Optional pinned digest; verified before the
                file is moved into its final, loadable location.
        """
        api_key = get_setting("huggingface/api_key", "")

        model_path = Path(output_dir)
        model_path.mkdir(parents=True, exist_ok=True)

        # Initialize download state
        self.is_cancelled = False
        self._completed_files.clear()
        self._failed_files.clear()
        self._file_progress.clear()
        self._file_sizes.clear()
        self._file_threads.clear()
        self._total_downloaded = 0
        self._total_size = 0

        temp_dir = self._prepare_temp_dir(model_path)

        self._model_path = model_path
        self._temp_dir = temp_dir

        self.emit_signal(
            SignalCode.UPDATE_DOWNLOAD_LOG,
            {"message": f"Starting GGUF download: {repo_id}/{gguf_filename}"},
        )

        # Get file size from HuggingFace API
        url = f"https://huggingface.co/{repo_id}/resolve/{revision}/{gguf_filename}"
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        try:
            head_response = requests.head(url, headers=headers, allow_redirects=True, timeout=30)
            head_response.raise_for_status()
            file_size = int(head_response.headers.get("Content-Length", 0))
        except requests.RequestException as e:
            self.logger.error(f"Failed to get GGUF file size: {e}")
            # Continue without size - progress will be approximate
            file_size = 0

        self._total_size = file_size
        self._file_sizes[gguf_filename] = file_size

        self.logger.info(
            f"Downloading GGUF file: {gguf_filename} ({file_size / (1024**3):.2f} GB)"
        )

        self.emit_signal(
            SignalCode.UPDATE_DOWNLOAD_LOG,
            {"message": f"Downloading: {gguf_filename} ({file_size / (1024**3):.2f} GB)"},
        )

        # Start download in thread
        thread = threading.Thread(
            target=self._download_file,
            kwargs={
                "repo_id": repo_id,
                "filename": gguf_filename,
                "file_size": file_size,
                "temp_dir": temp_dir,
                "model_path": model_path,
                "api_key": api_key,
                "revision": revision,
                "expected_sha256": expected_sha256,
            },
            daemon=True,
        )
        self._file_threads[gguf_filename] = thread
        thread.start()

        # Wait for completion
        if not self._wait_for_completion(1):
            return

        self._cleanup_temp_files()
        self.emit_signal(
            self._complete_signal,
            {"model_path": str(model_path), "repo_id": repo_id, "model_type": "gguf"},
        )

    def _download_file(
        self,
        repo_id: str,
        filename: str,
        file_size: int,
        temp_dir: Path,
        model_path: Path,
        api_key: str,
        revision: str = "main",
        expected_sha256: Optional[str] = None,
    ):
        """Download a single file from HuggingFace (runs in Python thread).

        Supports resuming partial downloads using HTTP Range headers.

        Args:
            repo_id: HuggingFace repository ID
            filename: Name of file to download
            file_size: Expected size in bytes
            temp_dir: Temporary download directory
            model_path: Final model directory
            api_key: HuggingFace API key (optional)
            revision: Git revision/branch/tag to resolve the file
                against, instead of always assuming "main" (release
                issue D01; see ``_resolve_bootstrap_revision``).
            expected_sha256: Optional pinned digest; verified before the
                file is moved into its final, loadable location, even
                if its size already matches (release issue D01).
        """
        self.logger.info(f"[DOWNLOAD THREAD] Starting download for {filename} from {repo_id}")

        temp_path = temp_dir / filename
        final_path = model_path / filename

        # Create parent directories for files in subdirectories
        temp_path.parent.mkdir(parents=True, exist_ok=True)

        url = f"https://huggingface.co/{repo_id}/resolve/{revision}/{filename}"
        self.logger.debug(f"[DOWNLOAD THREAD] URL: {url}")
        
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        # Check if we can resume a partial download
        resume_from = 0
        file_mode = "wb"
        if temp_path.exists():
            existing_size = temp_path.stat().st_size
            if existing_size > 0 and (
                file_size <= 0 or existing_size < file_size
            ):
                # Attempt to resume from where we left off. When file_size
                # is unknown (<= 0, e.g. a failed HEAD request upstream) an
                # existing temp file is never treated as already complete
                # below -- an arbitrary partial file must never be promoted
                # just because there was no expected size to compare against
                # (release issue D02) -- so it is always resumed/re-verified
                # against the server's own response instead.
                resume_from = existing_size
                file_mode = "ab"  # Append mode
                headers["Range"] = f"bytes={existing_size}-"
                self.logger.info(
                    f"Resuming download of {filename} from byte {existing_size}"
                )
            elif file_size > 0 and existing_size >= file_size:
                # A same-sized temp file must not be promoted just
                # because its byte count matches (release issue D02
                # review finding F3): most models have no pinned digest
                # (see _resolve_bootstrap_revision), so without a check
                # here a stale or corrupted leftover temp file would be
                # silently promoted with zero verification and zero
                # network calls. A lightweight HEAD request confirms the
                # file's identity against the server before trusting it.
                self.logger.info(
                    f"Temp file {filename} already appears complete; "
                    "verifying identity before promoting"
                )
                try:
                    stored_identity = self._read_stored_identity(temp_path)
                    head_response = requests.head(
                        url, headers=headers, allow_redirects=True, timeout=30
                    )
                    head_response.raise_for_status()
                    response_identity = self._response_identity(head_response)
                    identity_confirmed = (
                        stored_identity is not None
                        and response_identity is not None
                        and stored_identity == response_identity
                    )
                    if expected_sha256 or identity_confirmed:
                        self._verify_and_finalize(
                            temp_path=temp_path,
                            final_path=final_path,
                            filename=filename,
                            expected_sha256=expected_sha256,
                        )
                        return
                    self.logger.warning(
                        "Could not confirm identity of already-complete "
                        "temp file %s (stored=%r, current=%r); discarding "
                        "and re-downloading instead of promoting it "
                        "unverified",
                        filename,
                        stored_identity,
                        response_identity,
                    )
                    self._discard_temp_file(temp_path)
                    # Fall through to re-download from scratch.
                except Exception as e:
                    self.logger.error(f"Failed to verify complete temp file {filename}: {e}")
                    # Fall through to re-download

        try:
            request_attempts = 0
            while True:
                request_attempts += 1
                with requests.get(
                    url, headers=headers, stream=True, timeout=30
                ) as response:
                    # Check if server supports range requests
                    if resume_from > 0:
                        if response.status_code == 206:
                            # Partial content: verify it is actually the
                            # continuation of THIS temp file before trusting
                            # it, not just any 206 (release issue D02).
                            range_ok = self._content_range_start_matches(
                                response.headers.get("content-range", ""),
                                resume_from,
                            )
                            stored_identity = self._read_stored_identity(
                                temp_path
                            )
                            response_identity = self._response_identity(
                                response
                            )
                            # Fail closed, not open: a missing sidecar
                            # (stored_identity is None) means this temp
                            # file's provenance is unknown -- it must
                            # never be trusted just because the current
                            # response also lacks an identity header
                            # (release issue D02 review finding F3).
                            identity_ok = (
                                stored_identity is not None
                                and stored_identity == (response_identity or "")
                            )
                            if range_ok and identity_ok:
                                self.logger.info(f"Server accepted range request for {filename}")
                            elif request_attempts == 1:
                                self.logger.warning(
                                    "Unsafe 206 response for %s (range_ok=%s, "
                                    "identity_ok=%s); deleting temp file and "
                                    "restarting",
                                    filename,
                                    range_ok,
                                    identity_ok,
                                )
                                self.emit_signal(
                                    SignalCode.UPDATE_DOWNLOAD_LOG,
                                    {
                                        "message": f"Detected a changed or invalid partial download for {filename}. Restarting..."
                                    },
                                )
                                self._discard_temp_file(temp_path)
                                resume_from = 0
                                file_mode = "wb"
                                headers.pop("Range", None)
                                continue
                            else:
                                raise RuntimeError(
                                    f"Server returned an unsafe partial "
                                    f"response for {filename} and retrying "
                                    "did not resolve it"
                                )
                        elif response.status_code == 200:
                            # Server doesn't support range requests, start over
                            self.logger.warning(
                                f"Server doesn't support range requests for {filename}, restarting download"
                            )
                            resume_from = 0
                            file_mode = "wb"
                            headers.pop("Range", None)
                        elif response.status_code == 416 and request_attempts == 1:
                            # The partial temp file is stale or larger than the current remote file.
                            self.logger.warning(
                                "Server rejected range request for %s with HTTP 416; deleting temp file and restarting",
                                filename,
                            )
                            self.emit_signal(
                                SignalCode.UPDATE_DOWNLOAD_LOG,
                                {
                                    "message": f"Stale partial download detected for {filename}. Restarting that file..."
                                },
                            )
                            self._discard_temp_file(temp_path)
                            resume_from = 0
                            file_mode = "wb"
                            headers.pop("Range", None)
                            continue
                        else:
                            response.raise_for_status()
                    else:
                        response.raise_for_status()

                    if resume_from == 0:
                        # Record this attempt's server identity so a later
                        # resume (even from a fresh worker/process) can tell
                        # whether the upstream content has since changed
                        # (release issue D02).
                        self._write_stored_identity(
                            temp_path, self._response_identity(response)
                        )

                    content_length = response.headers.get("content-length")
                    if content_length:
                        remaining_size = int(content_length)
                        total_file_size = resume_from + remaining_size
                        with self._lock:
                            # Update total_size if bootstrap had 0 for this file
                            old_file_size = self._file_sizes.get(filename, 0)
                            if old_file_size == 0 and total_file_size > 0:
                                self._total_size += total_file_size
                            elif old_file_size != total_file_size:
                                # Adjust total_size for the difference
                                self._total_size += (total_file_size - old_file_size)
                            self._file_sizes[filename] = total_file_size
                    else:
                        total_file_size = file_size

                    downloaded = resume_from
                    with open(temp_path, file_mode) as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if self.is_cancelled:
                                f.close()
                                # Don't delete temp file on cancel - can resume later
                                return

                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)

                                if downloaded % (1024 * 1024) < 8192:
                                    self._update_file_progress(
                                        filename, downloaded, total_file_size
                                    )

                    break

            self._update_file_progress(filename, downloaded, total_file_size)

            # Verify download is complete
            if downloaded < file_size:
                self.logger.error(
                    f"Download incomplete for {filename}: {downloaded} bytes vs expected {file_size}"
                )
                self._mark_file_failed(filename)
                return

            self._verify_and_finalize(
                temp_path=temp_path,
                final_path=final_path,
                filename=filename,
                expected_sha256=expected_sha256,
            )

        except Exception as e:
            import traceback
            self.logger.error(f"Failed to download {filename}: {e}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            self.emit_signal(
                SignalCode.UPDATE_DOWNLOAD_LOG,
                {"message": f"✗ Error downloading {filename}: {e}"},
            )
            self._mark_file_failed(filename)
            # Don't delete temp file - can resume later
