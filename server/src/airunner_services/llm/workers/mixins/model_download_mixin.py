"""Service-owned model download operations for the LLM worker."""

import os
import time
import threading
from typing import Dict, Optional

from airunner_services.contract_enums import ModelStatus, ModelType
from airunner_services.llm.llm_response import LLMResponse
from airunner_services.llm.provider_config import LLMProviderConfig
from airunner_services.utils.application.enum_resolver import signal_code_proxy


SignalCode = signal_code_proxy(
    {
        "HUGGINGFACE_DOWNLOAD_COMPLETE": "huggingface_download_complete",
        "HUGGINGFACE_DOWNLOAD_FAILED": "huggingface_download_failed",
        "LLM_CONVERT_TO_GGUF_SIGNAL": "llm_convert_to_gguf_signal",
        "LLM_TEXT_STREAMED_SIGNAL": "llm_text_streamed_signal",
        "UPDATE_DOWNLOAD_LOG": "update_download_log",
        "UPDATE_DOWNLOAD_PROGRESS": "update_download_progress",
        "UPDATE_FILE_DOWNLOAD_PROGRESS": "update_file_download_progress",
    }
)


class HeadlessDownloadProgress:
    """Track one service model download with tqdm when available."""

    def __init__(self, model_name: str, model_path: str):
        """Initialize download progress state."""
        self.model_name = model_name
        self.model_path = model_path
        self._overall_bar = None
        self._file_bars: Dict[str, object] = {}
        self._lock = threading.Lock()
        self._completed = threading.Event()
        self._failed = False
        self._error_message = ""

        try:
            from tqdm import tqdm

            self._tqdm = tqdm
        except ImportError:
            self._tqdm = None
            print("[Download] tqdm not installed, using simple output")

    def on_log_updated(self, data: Dict) -> None:
        """Handle one download log message."""
        message = data.get("message", "")
        if self._tqdm:
            self._tqdm.write(f"[Download] {message}")
        else:
            print(f"[Download] {message}")

    def on_progress_updated(self, data: Dict) -> None:
        """Handle one overall download progress update."""
        progress = data.get("progress", 0)

        if self._tqdm and self._overall_bar is None:
            self._overall_bar = self._tqdm(
                total=100,
                desc=f"Downloading {self.model_name}",
                unit="%",
                position=0,
                leave=True,
            )

        if self._overall_bar:
            self._overall_bar.n = progress
            self._overall_bar.refresh()
        elif not self._tqdm:
            print(
                f"\r[Download] Overall progress: {progress:.1f}%",
                end="",
                flush=True,
            )

        if self._tqdm:
            self._tqdm.write(f"Download complete: {self.model_name}")
        else:
            print(f"\n[Download] Complete: {self.model_name}")

        self._completed.set()

    def on_download_failed(self, data: Dict) -> None:
        """Mark one download as failed."""
        error = data.get("error", "Unknown error")
        self._failed = True
        self._error_message = error

        with self._lock:
            for bar in self._file_bars.values():
                bar.close()
            self._file_bars.clear()

            if self._overall_bar:
                self._overall_bar.close()
                self._overall_bar = None

        if self._tqdm:
            self._tqdm.write(f"Download failed: {error}")
        else:
            print(f"\n[Download] Failed: {error}")

        self._completed.set()

    def wait_for_completion(self, timeout: float = 3600) -> bool:
        """Wait for download completion and report success."""
        completed = self._completed.wait(timeout=timeout)
        return completed and not self._failed

    @property
    def error_message(self) -> str:
        """Return the last download error message."""
        return self._error_message


class ModelDownloadMixin:
    """Handle LLM model download requests for GUI and flows."""

    def on_llm_model_download_required_signal(self, data: Dict) -> None:
        """Start a model download through the flow."""
        model_type = data.get("model_type", "llm")
        if model_type == "embedding":
            self.logger.debug(
                "Ignoring embedding model download request - "
                "handled by RAG system"
            )
            return

        if self._download_dialog_showing:
            self.logger.debug(
                "Download dialog already showing, ignoring duplicate signal"
            )
            return

        model_path = data.get("model_path", "")
        model_name = data.get("model_name", "Unknown Model")
        repo_id = data.get("repo_id", "")
        gguf_filename = data.get("gguf_filename")
        convert_to_gguf = data.get("convert_to_gguf", False)

        resolved_download = LLMProviderConfig.resolve_download_target(
            "local",
            repo_id=repo_id,
            prefer_pre_quantized=True,
        )
        if resolved_download and resolved_download.get("model_type") == "gguf":
            if (
                repo_id != resolved_download["repo_id"]
                or model_type != "gguf"
                or gguf_filename != resolved_download["gguf_filename"]
            ):
                self.logger.info(
                    "Upgrading LLM download request from %s to GGUF artifact "
                    "%s/%s",
                    repo_id,
                    resolved_download["repo_id"],
                    resolved_download["gguf_filename"],
                )
            repo_id = resolved_download["repo_id"]
            model_type = "gguf"
            gguf_filename = resolved_download["gguf_filename"]
            model_name = resolved_download.get("model_name", model_name)

        self._pending_convert_to_gguf = convert_to_gguf

        is_gguf = model_type == "gguf" or gguf_filename is not None

        self.logger.info(
            "Model download required: %s at %s (GGUF: %s, convert_after: %s)",
            model_name,
            model_path,
            is_gguf,
            convert_to_gguf,
        )

        if not repo_id:
            self.logger.error("No repo_id provided in download request")
            return

        model_info = self._get_model_info(repo_id)
        if not model_info:
            return

        if is_gguf:
            model_info = dict(model_info)
            model_info["is_gguf"] = True
            model_info["gguf_filename"] = gguf_filename

        if self._has_download_ui_delegate():
            if self._request_gui_download(
                model_info,
                model_path,
                repo_id,
                data.get("missing_files"),
            ):
                return
            self.logger.error("Unable to show GUI download dialog")
            return

        self._download(
            model_info,
            model_path,
            repo_id,
            data.get("missing_files"),
        )

    def _has_download_ui_delegate(self) -> bool:
        """Return whether one GUI delegate is available for downloads."""
        delegate = getattr(self, "download_ui_delegate", None)
        return callable(getattr(delegate, "show_llm_download_dialog", None))

    def _request_gui_download(
        self,
        model_info: Dict,
        model_path: str,
        repo_id: str,
        missing_files: Optional[list] = None,
    ) -> bool:
        """Ask one GUI delegate to present the download dialog."""
        delegate = getattr(self, "download_ui_delegate", None)
        show_dialog = getattr(delegate, "show_llm_download_dialog", None)
        if not callable(show_dialog):
            return False
        self._download_dialog_showing = True
        try:
            shown = bool(
                show_dialog(
                    self,
                    model_info,
                    model_path,
                    repo_id,
                    missing_files,
                )
            )
        except Exception as exc:
            self._download_dialog_showing = False
            self.logger.error("Error showing GUI download dialog: %s", exc)
            return False
        if not shown:
            self._download_dialog_showing = False
        return shown

    def _download(
        self,
        model_info: Dict,
        model_path: str,
        repo_id: str,
        missing_files: Optional[list] = None,
    ) -> bool:
        """Download one model in service mode with progress output."""
        from airunner_services.downloads.job_service import DownloadJobService
        from airunner_services.utils.job_tracker import JobStatus

        self._download_dialog_showing = True

        is_gguf = model_info.get("is_gguf", False)
        gguf_filename = model_info.get("gguf_filename")
        model_name = model_info.get("name", repo_id)

        if is_gguf:
            model_name = f"{model_name} (GGUF)"

        self.logger.info(f"Starting download: {model_name}")
        print(f"\n[Download] Model: {model_name}")
        print(f"[Download] Repository: {repo_id}")
        print(f"[Download] Destination: {model_path}\n")

        progress = HeadlessDownloadProgress(model_name, model_path)
        job_service = DownloadJobService()
        download_model_type = "gguf" if is_gguf and gguf_filename else (
            model_info.get("model_type", "llm")
        )
        output_dir = model_path if is_gguf else os.path.dirname(model_path)

        try:
            progress.on_log_updated(
                {"message": f"Starting download: {repo_id}"}
            )
            job_id = job_service.start_huggingface_download_sync(
                repo_id=repo_id,
                model_type=download_model_type,
                output_dir=output_dir,
                missing_files=None if is_gguf else missing_files,
                gguf_filename=gguf_filename if is_gguf else None,
            )

            while True:
                job = job_service.get_status_sync(job_id)
                if job is None:
                    raise RuntimeError("Download job not found")

                progress.on_progress_updated({"progress": job.progress})

                if job.status is JobStatus.COMPLETED:
                    result = job.result or {}
                    paths = result.get("paths") or []
                    complete_data = {
                        "repo_id": repo_id,
                        "model_path": paths[0] if paths else model_path,
                        "model_type": download_model_type,
                    }
                    progress.on_download_complete(complete_data)
                    self.on_huggingface_download_complete_signal(
                        complete_data
                    )
                    self._download_dialog_showing = False
                    return True

                if job.status is JobStatus.FAILED:
                    error = job.error or "Download failed"
                    progress.on_download_failed({"error": error})
                    self.logger.error(f"Download failed: {error}")
                    self._download_dialog_showing = False
                    return False

                if job.status is JobStatus.CANCELLED:
                    progress.on_download_failed(
                        {"error": "Download cancelled"}
                    )
                    self._download_dialog_showing = False
                    return False

                time.sleep(0.1)

        except Exception as exc:
            self.logger.error(f"Error during download: {exc}")
            self._download_dialog_showing = False
            return False

    def _get_model_info(self, repo_id: str) -> Optional[Dict]:
        """Return model metadata for one repository id."""
        model_id = LLMProviderConfig.get_model_id_for_repo_id("local", repo_id)
        if model_id:
            return LLMProviderConfig.get_model_info("local", model_id)

        self.logger.debug(
            "Model info not found for repo_id %s - using fallback config",
            repo_id,
        )
        return {
            "name": repo_id,
            "repo_id": repo_id,
            "model_type": "llm",
            "setup_quantization": False,
            "quantization_bits": 4,
        }

    def on_huggingface_download_complete_signal(self, data: Dict) -> None:
        """Handle download completion and trigger model load or conversion."""
        self._download_dialog_showing = False
        self._download_dialog = None

        model_path = data.get("model_path", "")
        repo_id = data.get("repo_id", "")

        convert_to_gguf = getattr(self, "_pending_convert_to_gguf", False)
        self._pending_convert_to_gguf = False

        self.logger.info(
            "Download complete for model at: %s (repo_id: %s, "
            "convert_to_gguf: %s)",
            model_path,
            repo_id,
            convert_to_gguf,
        )

        if repo_id == "intfloat/e5-large":
            self.logger.debug("Skipping auto-load for embedding model")
            return

        if convert_to_gguf:
            self.logger.info(
                "Triggering GGUF conversion after safetensors download"
            )
            model_name = (
                self.model_manager.model_name
                if self.model_manager
                else "Unknown Model"
            )
            self.emit_signal(
                SignalCode.LLM_CONVERT_TO_GGUF_SIGNAL,
                {
                    "model_path": model_path,
                    "model_name": model_name,
                    "quantization": "Q4_K_M",
                },
            )
            return

        self._emit_download_complete_message()
        self._auto_load_downloaded_model()

    def _emit_download_complete_message(self) -> None:
        """Emit a completion message through the normal LLM stream path."""
        message = (
            "[Download] Complete. Loading model with automatic quantization...\n"
        )

        self.emit_signal(
            SignalCode.LLM_TEXT_STREAMED_SIGNAL,
            {
                "response": LLMResponse(
                    message=message,
                    is_end_of_message=False,
                    is_system_message=True,
                )
            },
        )

    def _auto_load_downloaded_model(self) -> None:
        """Load the downloaded model and replay any pending request."""
        if self.model_manager:
            self.logger.info("Triggering automatic model load after download")

            load_success = self.model_manager.load()
            self.logger.info(f"Model load returned: {load_success}")

            if self.model_manager.model_status[ModelType.LLM] != ModelStatus.LOADED:
                self.logger.error(
                    "Model failed to load after download - status: %s",
                    self.model_manager.model_status[ModelType.LLM],
                )
                if hasattr(self, "_pending_llm_request"):
                    self._pending_llm_request = None
                return

            self.logger.info("Model loaded successfully!")

            if (
                hasattr(self, "_pending_llm_request")
                and self._pending_llm_request
            ):
                self.logger.info(
                    "Retrying pending LLM request after model download"
                )
                self.handle_message(self._pending_llm_request)
                self._pending_llm_request = None
            else:
                self.logger.info("No pending request to retry")
        else:
            self.logger.warning(
                "Model manager not available after download - cannot auto-load"
            )


__all__ = ["HeadlessDownloadProgress", "ModelDownloadMixin"]