"""Manager for downloading and preparing HuggingFace LLM models."""

from typing import Any, Optional

from airunner_services.downloads.service_download_worker import (
    ServiceDownloadWorker,
)
from airunner_services.downloads.service import (
    prepare_huggingface_download_payload,
)
from airunner_services.utils.application import create_worker
from airunner_services.utils.application.enum_resolver import signal_code_proxy
from airunner_services.workers.worker import QueueType, Worker


SignalCode = signal_code_proxy(
    {"CANCEL_HUGGINGFACE_DOWNLOAD": "cancel_huggingface_download"}
)


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
            repo_id: HuggingFace repo ID (e.g., "mistralai/Ministral-3-8B-Instruct-2512")
            model_type: "ministral3", "llm", or "gguf" (determines required files)
            output_dir: Optional output directory (default: ~/.local/share/airunner/text/models/llm/causallm)
            setup_quantization: Ignored - quantization handled separately
            quantization_bits: Ignored - quantization handled separately
            missing_files: Optional list of specific files to download
            gguf_filename: For GGUF downloads, the specific .gguf file to download
        """
        del setup_quantization, quantization_bits
        download_payload = prepare_huggingface_download_payload(
            repo_id=repo_id,
            model_type=model_type,
            output_dir=output_dir,
            missing_files=missing_files,
            gguf_filename=gguf_filename,
        )

        # Cancel any existing download
        if self.download_worker and self.download_worker.running:
            self.download_worker.cancel()

        # Create download worker using create_worker
        self.download_worker = create_worker(ServiceDownloadWorker)

        # Add task to worker queue
        self.download_worker.add_to_queue(download_payload)

    def cancel(self):
        """Cancel the current download."""
        if self.download_worker:
            self.download_worker.cancel()


# Example usage
if __name__ == "__main__":
    """
    Download Ministral-3-8B.

    from airunner_services.llm.managers.download_huggingface import DownloadHuggingFaceModel

    downloader = create_worker(DownloadHuggingFaceModel)
    downloader.download(
        repo_id="mistralai/Ministral-3-8B-Instruct-2512",
        model_type="ministral3",
    )
    """
