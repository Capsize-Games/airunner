"""Worker for HuggingFace model downloads using Python threading."""

import os, threading
from pathlib import Path

from airunner_services.contract_enums import SignalCode
from airunner_services.settings import AIRUNNER_BASE_PATH, MODELS_DIR
from airunner_services.bootstrap.model_bootstrap_data import model_bootstrap_data
from airunner_services.config.local_settings_store import get_setting
from airunner_services.downloads.base_download_worker import BaseDownloadWorker
from airunner_services.llm.utils.model_downloader import HuggingFaceDownloader

from ._bootstrap_resolver import (
    get_bootstrap_data_for_model, resolve_bootstrap_files,
    resolve_file_list_from_api,
)
from ._file_verifier import check_existing_file, remove_file, should_skip_transformer_weights
from ._model_path_resolver import resolve_model_path
from ._download_zip_archive import download_and_extract_zip
from ._download_gguf_file import download_gguf_model
from ._download_single_file import download_single_file
from ._zimage_utils import prune_zimage_bootstrap_files, prune_zimage_missing_files


class HuggingFaceDownloadWorker(BaseDownloadWorker):
    """Worker for downloading HuggingFace models with parallel downloads."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.downloader = HuggingFaceDownloader()
        self._current_model_type = None
        self._current_pipeline_action = None

    @property
    def _complete_signal(self) -> SignalCode:
        return SignalCode.HUGGINGFACE_DOWNLOAD_COMPLETE

    @property
    def _failed_signal(self) -> SignalCode:
        return SignalCode.HUGGINGFACE_DOWNLOAD_FAILED

    def _apply_post_download_patches(self, model_path: Path) -> None:
        del model_path

    @staticmethod
    def _resolve_art_download_context(repo_id, version=None, pipeline_action=None):
        rv = version
        rpa = pipeline_action or "txt2img"
        if rv:
            return rv, rpa
        for m in model_bootstrap_data:
            if m.get("model_type") != "art" or m.get("path") != repo_id:
                continue
            rv = m.get("version")
            rpa = m.get("pipeline_action") or rpa
            break
        return rv, rpa

    def _download_model(
        self, repo_id=None, model_type=None, output_dir=None,
        version=None, pipeline_action="txt2img", missing_files=None,
        gguf_filename=None, zip_url=None,
    ):
        rv, rpa = version, pipeline_action
        if model_type == "art":
            rv, rpa = self._resolve_art_download_context(
                repo_id=repo_id, version=version,
                pipeline_action=pipeline_action,
            )
            if not rv:
                err = f"Unable to resolve art model version for {repo_id}."
                self.logger.error(err)
                self.emit_signal(self._failed_signal, {"error": err})
                return

        self._current_model_type = model_type
        self._current_pipeline_action = rpa or pipeline_action

        if model_type == "openvoice_zip" and zip_url:
            download_and_extract_zip(self, zip_url, output_dir)
            return

        if model_type == "gguf" and gguf_filename:
            if not output_dir:
                from airunner_services.llm.config.provider_config import LLMProviderConfig
                output_dir = LLMProviderConfig.get_local_storage_path(
                    AIRUNNER_BASE_PATH, "local",
                    repo_id=repo_id, prefer_pre_quantized=True,
                )
            download_gguf_model(self, repo_id, output_dir, gguf_filename)
            return

        api_key = get_setting("huggingface/api_key", "")
        if not output_dir:
            output_dir = os.path.join(MODELS_DIR, "text/models/llm/causallm")

        model_path = resolve_model_path(output_dir, repo_id, model_type)
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
        self.emit_signal(SignalCode.UPDATE_DOWNLOAD_LOG, {"message": f"Starting download: {repo_id}"})

        files = self._build_file_list(
            model_type=model_type, repo_id=repo_id,
            resolved_version=rv, model_path=model_path,
            missing_files=missing_files,
        )
        if files is None:
            return
        if not files:
            self._apply_post_download_patches(model_path)
            self._emit_done(repo_id, model_path)
            return

        self._total_size = sum(f["size"] for f in files)
        total_gb = self._total_size / (1024**3)
        self.emit_signal(SignalCode.UPDATE_DOWNLOAD_LOG, {"message": f"Downloading {len(files)} files ({total_gb:.2f} GB) in parallel"})

        for fi in files:
            if self.is_cancelled:
                return
            fn, fs = fi["filename"], fi["size"]
            self._file_sizes[fn] = fs
            self._file_progress[fn] = 0
            self.emit_signal(SignalCode.UPDATE_DOWNLOAD_LOG, {"message": f"Starting download for {fn}..."})
            t = threading.Thread(
                target=download_single_file,
                args=(self, repo_id, fn, fs, temp_dir, model_path, api_key),
                daemon=True,
            )
            self._file_threads[fn] = t
            t.start()

        if not self._wait_for_completion(len(files)):
            return
        self._cleanup_temp_files()
        self._apply_post_download_patches(model_path)
        self._emit_done(repo_id, model_path)

    def _emit_done(self, repo_id, model_path):
        self.emit_signal(self._complete_signal, {
            "model_path": str(model_path),
            "repo_id": repo_id,
            "model_type": self._current_model_type,
            "pipeline_action": self._current_pipeline_action,
        })

    def _build_file_list(self, model_type, repo_id, resolved_version, model_path, missing_files):
        is_bs = model_type in ("art", "stt", "tts_openvoice", "rmbg")
        full_data = get_bootstrap_data_for_model(model_type, resolved_version, "txt2img", repo_id, self.logger)
        if model_type == "art" and resolved_version == "Z-Image Turbo":
            missing_files = prune_zimage_missing_files(model_path, missing_files, self.logger)
            if not missing_files:
                full_data = prune_zimage_bootstrap_files(model_path, full_data, self.logger)
        if is_bs:
            return self._build_from_bootstrap(model_type, full_data, missing_files, model_path, repo_id)
        return self._build_from_api(repo_id, model_type, model_path, full_data)

    def _build_from_bootstrap(self, model_type, full_data, missing_files, model_path, repo_id):
        bf = resolve_bootstrap_files(model_type, full_data, model_path, missing_files, self.logger)
        if not bf:
            self.logger.error("No bootstrap data found for %s/%s!", model_type, repo_id)
            self.emit_signal(self._failed_signal, {"error": f"No bootstrap data for {model_type}/{repo_id}"})
            return None
        files = []
        for fn, sz in bf.items():
            fp = model_path / fn
            if check_existing_file(fp, sz, self.logger):
                continue
            if not remove_file(fp, self.logger):
                continue
            if should_skip_transformer_weights(fn, missing_files):
                self.logger.info("Skipping transformer weights (GGUF): %s", fn)
                continue
            files.append({"filename": fn, "size": sz})
        return files

    def _build_from_api(self, repo_id, model_type, model_path, full_data):
        all_f = resolve_file_list_from_api(
            self.downloader, repo_id, model_type, self.logger,
            self.emit_signal, SignalCode.UPDATE_DOWNLOAD_LOG, self._failed_signal,
        )
        if all_f is None:
            return None
        files = []
        for fi in all_f:
            fn, sz = fi["filename"], fi["size"]
            if full_data and isinstance(full_data, dict):
                sz = full_data.get(fn, sz)
            fp = model_path / fn
            if fp.exists():
                actual = fp.stat().st_size
                if sz > 0 and actual < sz:
                    self.logger.warning("File %s incomplete (%d vs %d), re-downloading", fn, actual, sz)
                    remove_file(fp, self.logger)
                else:
                    continue
            files.append({"filename": fn, "size": sz})
        return files
