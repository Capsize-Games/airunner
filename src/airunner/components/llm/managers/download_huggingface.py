"""Manager for downloading and preparing HuggingFace LLM models."""

from typing import Optional, Any

from airunner.components.application.workers.worker import Worker
from airunner.components.llm.config.provider_config import LLMProviderConfig
from airunner.enums import SignalCode, QueueType
from airunner.components.application.workers.daemon_huggingface_download_worker import (
    HuggingFaceDownloadWorker,
)
from airunner.settings import AIRUNNER_BASE_PATH
from airunner.utils.application import create_worker


class DownloadHuggingFaceModel(Worker):
    """
    Worker for managing HuggingFace model downloads with GUI integration.

    Coordinates download workers and handles:
    - Multi-file downloads
    - Model type detection
    - Optional quantization setup
    - Progress tracking across multiple files
    """

    queue_type = QueueType.NONE

    def __init__(self):
        super().__init__()
        self.download_worker = None

        self.register(SignalCode.CANCEL_HUGGINGFACE_DOWNLOAD, self.cancel)

    def handle_message(self, message: Any):
        """Not used - downloads triggered via download() method."""

    def download(
        self,
        repo_id: str,
        model_type: str = "llm",
        output_dir: Optional[str] = None,
        setup_quantization: bool = True,
        quantization_bits: int = 4,
        missing_files: Optional[list] = None,
        gguf_filename: Optional[str] = None,
    ):
        """
        Download a HuggingFace model.

        Args:
            repo_id: HuggingFace repo ID (e.g., "Qwen/Qwen3.5-9B")
            model_type: "llm" or "gguf" (determines required files)
            output_dir: Optional output directory (default: ~/.local/share/airunner/text/models/llm/causallm)
            setup_quantization: Ignored - quantization handled separately
            quantization_bits: Ignored - quantization handled separately
            missing_files: Optional list of specific files to download
            gguf_filename: For GGUF downloads, the specific .gguf file to download
        """
        del setup_quantization, quantization_bits
        resolved_download = LLMProviderConfig.resolve_download_target(
            "local",
            repo_id=repo_id,
            prefer_pre_quantized=True,
        )
        if resolved_download and resolved_download.get("model_type") == "gguf":
            resolved_repo_id = resolved_download["repo_id"]
            resolved_gguf_filename = resolved_download["gguf_filename"]
            if (
                repo_id != resolved_repo_id
                or model_type != "gguf"
                or gguf_filename != resolved_gguf_filename
            ):
                self.logger.info(
                    "Preferring pre-quantized GGUF download for %s via %s/%s",
                    repo_id,
                    resolved_repo_id,
                    resolved_gguf_filename,
                )
            repo_id = resolved_repo_id
            model_type = "gguf"
            gguf_filename = resolved_gguf_filename
            missing_files = None

        if output_dir is None and model_type in {"llm", "gguf"}:
            output_dir = LLMProviderConfig.get_local_storage_path(
                AIRUNNER_BASE_PATH,
                "local",
                model_id=(resolved_download or {}).get("model_id"),
                repo_id=repo_id,
                prefer_pre_quantized=model_type == "gguf",
            )

        # Cancel any existing download
        if self.download_worker and self.download_worker.running:
            self.download_worker.cancel()

        # Create download worker using create_worker
        self.download_worker = create_worker(HuggingFaceDownloadWorker)

        # Add task to worker queue
        self.download_worker.add_to_queue(
            {
                "repo_id": repo_id,
                "model_type": model_type,
                "output_dir": output_dir,
                "missing_files": missing_files,
                "gguf_filename": gguf_filename,
            }
        )

    def cancel(self):
        """Cancel the current download."""
        if self.download_worker:
            self.download_worker.cancel()


# Example usage
if __name__ == "__main__":
    """
    Download Qwen3.5-9B.

    from airunner.components.llm.managers.download_huggingface import DownloadHuggingFaceModel

    downloader = create_worker(DownloadHuggingFaceModel)
    downloader.download(
        repo_id="Qwen/Qwen3.5-9B",
        model_type="llm",
    )
    """
